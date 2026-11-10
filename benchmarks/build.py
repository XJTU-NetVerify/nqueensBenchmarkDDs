"""Build benchmark drivers without editing upstream library source files."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTERS = ROOT / "benchmarks"
BUILD = ROOT / ".bench-build"
LOCK = json.loads((ADAPTERS / "upstream-lock.json").read_text())
JAR = "ndd-1.0.1-jar-with-dependencies.jar"
TARGET_SOURCES = {
    "BuDDy": "BuDDy", "Sylvan": "sylvan", "CUDD": "cudd", "OxiDD": "oxidd",
    "JDD": "jdd", "ZDD": "jdd", "JavaBDD": "JavaBDD", "JSylvan": "jsylvan",
    "DD-BDD": "DecisionDiagrams", "DD-CBDD": "DecisionDiagrams",
    "NDD": "NDD", "NDD-BCDD": "NDD", "NDD-ZDD": "NDD",
    "NDD-original": "NDD-original", "NDD-reuse": "NDD-reuse",
}


def provenance(target):
    name = TARGET_SOURCES.get(target)
    info = LOCK.get(name, {})
    return {"upstream_url": info.get("url"), "upstream_revision": info.get("revision")}


def source(name):
    info = LOCK[name]
    path = ROOT / info.get("path", name)
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if actual != info["revision"]:
        raise RuntimeError(f"{name}: expected upstream {info['revision']}, found {actual}")
    if subprocess.run(["git", "-c", "core.autocrlf=true", "-c", "core.safecrlf=false",
                       "-C", str(path), "diff", "--quiet", "HEAD", "--"]).returncode:
        raise RuntimeError(f"{name}: upstream tracked files have local edits")
    return path


def cached(name, artifact, inputs):
    digest = hashlib.sha256(Path(__file__).read_bytes())
    digest.update(json.dumps(LOCK, sort_keys=True).encode())
    for path in sorted(inputs):
        digest.update(path.read_bytes())
    stamp = BUILD / name / "build.sha256"
    key = digest.hexdigest()
    return artifact.exists() and stamp.exists() and stamp.read_text() == key, stamp, key


def java_sources_file(name, paths):
    args = BUILD / name / "sources.args"
    args.parent.mkdir(parents=True, exist_ok=True)
    args.write_text("\n".join('"' + str(p).replace("\\", "/") + '"' for p in paths))
    return "@" + str(args)


def dependency(name, run):
    info = LOCK[name]
    path = ROOT / info["path"]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--no-checkout", info["url"], str(path)])
        run(["git", "checkout", "--detach", info["revision"]], cwd=path)
    return source(name)


def prepare(name, run, jobs):
    directory = BUILD / name
    directory.mkdir(parents=True, exist_ok=True)
    repo_name = {"buddy": "BuDDy", "sylvan": "sylvan", "cudd": "cudd",
                 "jdd": "jdd", "javabdd": "JavaBDD", "jsylvan": "jsylvan", "decisiondiagrams": "DecisionDiagrams"}.get(name, name)
    upstream = source(repo_name)
    adapter_dir = ADAPTERS / ("ndd" if name.startswith("NDD") else name)
    inputs = [p for p in adapter_dir.rglob("*") if p.is_file() and "obj" not in p.parts]
    common = sorted(path for path in (ADAPTERS / "common").glob("*") if path.is_file())
    inputs.extend(common)
    artifact = executable(name)
    ready, stamp, key = cached(name, artifact, inputs)
    if ready:
        print(f"[build] Reusing {name} adapter for {LOCK[repo_name]['revision'][:8]}")
        return
    if name in ("buddy", "cudd"):
        # Autotools rejects out-of-tree configuration when an old in-tree build exists.
        # Preserve that generated status file rather than deleting the old build.
        old_status = upstream / "config.status"
        if old_status.exists():
            backup = directory / "previous-config.status"
            if backup.exists():
                raise RuntimeError(f"Preserved config already exists: {backup}")
            old_status.replace(backup)
        library = directory / "library"
        library.mkdir(exist_ok=True)
        run(["bash", str(upstream / "configure")], cwd=library)
        make = ["make", f"-j{jobs}", "ACLOCAL=true", "AUTOMAKE=true", "AUTOCONF=true", "AUTOHEADER=true"]
        run(make + (["-C", "src"] if name == "buddy" else ["cudd/libcudd.la"]), cwd=library)
        if name == "buddy":
            run(["g++", "-O3", "-I" + str(upstream / "src"),
                 str(adapter_dir / "nqueens.cpp"), str(library / "src/.libs/libbdd.a"),
                 "-lm", "-o", str(artifact)])
        else:
            run(["gcc", "-O3", "-I" + str(library), "-I" + str(upstream / "cudd"),
                 str(adapter_dir / "nqueens.c"), str(library / "cudd/.libs/libcudd.a"),
                 "-lm", "-o", str(artifact)])
    elif name == "oxidd":
        env = os.environ.copy()
        cargo = shutil.which("cargo")
        if cargo is None:
            local = BUILD / "tools"
            cargo = str(local / "cargo/bin/cargo")
            env.update(CARGO_HOME=str(local / "cargo"), RUSTUP_HOME=str(local / "rustup"))
            env["PATH"] = str(local / "cargo/bin") + os.pathsep + env["PATH"]
        run([cargo, "build", "--release", "--locked", "--manifest-path", str(adapter_dir / "Cargo.toml"),
             "--target-dir", str(directory), "-j", str(jobs)], env=env)
    elif name == "sylvan":
        lace = dependency("lace", run)
        run(["cmake", "-S", str(adapter_dir), "-B", str(directory),
             "-DUPSTREAM_ROOT=" + str(upstream), "-DSYLVAN_STATS=ON",
             "-DFETCHCONTENT_SOURCE_DIR_LACE=" + str(lace),
             "-DSYLVAN_BUILD_TESTS=OFF", "-DSYLVAN_BUILD_EXAMPLES=OFF", "-DCMAKE_BUILD_TYPE=Release"])
        run(["cmake", "--build", str(directory), "--target", "nqueens", f"-j{jobs}"])
    elif name in ("jdd", "javabdd"):
        classes = directory / "classes"
        classes.mkdir(exist_ok=True)
        source_dir = upstream / ("src/main/java" if name == "javabdd" else "src")
        paths = sorted(source_dir.rglob("*.java")) + sorted(adapter_dir.glob("*.java")) + [ADAPTERS / "common/RowQueens.java"]
        run(["javac", "-encoding", "UTF-8", "-d", str(classes), java_sources_file(name, paths)])
    elif name == "jsylvan":
        native = dependency("jsylvan-native", run)
        core = directory / "sylvan"
        run(["cmake", "-S", str(native), "-B", str(core), "-DBUILD_SHARED_LIBS=OFF",
             "-DCMAKE_POSITION_INDEPENDENT_CODE=ON", "-DCMAKE_BUILD_TYPE=Release",
             "-DCMAKE_C_FLAGS=-Wno-error=array-parameter", "-DSYLVAN_BUILD_EXAMPLES=OFF"])
        run(["cmake", "--build", str(core), "--target", "sylvan", f"-j{jobs}"])
        classes = directory / "classes"
        classes.mkdir(exist_ok=True)
        paths = sorted((upstream / "src/main/java").rglob("*.java")) + [adapter_dir / "JSylvanNQueens.java", ADAPTERS / "common/RowQueens.java"]
        run(["javac", "-encoding", "UTF-8", "-d", str(classes), java_sources_file(name, paths)])
        run(["cmake", "-S", str(adapter_dir), "-B", str(directory / "jni"),
             "-DUPSTREAM_ROOT=" + str(upstream), "-DSYLVAN_ROOT=" + str(native),
             "-DSYLVAN_LIBRARY=" + str(core / "src/libsylvan.a"),
             "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" + str(classes / "linux-x64")])
        run(["cmake", "--build", str(directory / "jni"), f"-j{jobs}"])
        run(["jar", "cf", str(artifact), "-C", str(classes), "."])
    elif name == "decisiondiagrams":
        run(["dotnet", "build", str(adapter_dir / "DecisionDiagramsBenchmark.csproj"),
             "-c", "Release", "-p:DisableStyleCop=true", "-o", str(directory / "out")])
    elif name.startswith("NDD"):
        run(["mvn", "-q", "-DskipTests", "package"], cwd=upstream)
        classes = directory / "classes"
        classes.mkdir(exist_ok=True)
        java = "NDDPrimitiveBenchmark.java" if name == "NDD" else "NDDObjectBenchmark.java"
        bridge = [] if name == "NDD" else [str(adapter_dir /
                  ("original" if name == "NDD-original" else "reuse") / "BackendFields.java")]
        run(["javac", "-cp", str(upstream / "target" / JAR), "-d", str(classes),
             str(adapter_dir / java), str(ADAPTERS / "common/RowQueens.java"), *bridge])
    else:
        raise ValueError(name)
    stamp.write_text(key)
    source(repo_name)


def executable(name):
    if name == "oxidd":
        return BUILD / name / "release/nqueens"
    if name == "javabdd":
        return BUILD / name / "classes/benchmark/javabdd/JavaBDDQueens.class"
    if name == "jdd":
        return BUILD / name / "classes/benchmark/jdd/BDDQueens.class"
    if name == "jsylvan":
        return BUILD / name / "benchmark.jar"
    if name == "decisiondiagrams":
        return BUILD / name / "out/DecisionDiagramsBenchmark.dll"
    if name.startswith("NDD"):
        klass = "NDDPrimitiveBenchmark" if name == "NDD" else "NDDObjectBenchmark"
        return BUILD / name / "classes/benchmark" / (klass + ".class")
    return BUILD / name / "nqueens"


def ndd_command(name, size, mode=None):
    klass = "NDDPrimitiveBenchmark" if name == "NDD" else "NDDObjectBenchmark"
    return ["java", "-cp", os.pathsep.join([str(BUILD / name / "classes"),
            str(ROOT / LOCK[name]["path"] / "target" / JAR)]), "benchmark." + klass,
            *([mode] if mode else []), str(size)]
