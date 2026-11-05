# Forward benchmark arguments to the Linux environment used by the native targets.
$benchmarkRoot = Split-Path -Parent $PSScriptRoot
& wsl -d Ubuntu --cd $benchmarkRoot -- env `
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 `
    PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin `
    PYTHONPATH=/usr/lib/python3/dist-packages `
    python3 -u scripts/run_nqueens_benchmarks.py @args
exit $LASTEXITCODE
