# Deprecated and legacy implementations

`NDD-SoA/` contains the complete archived Maven project, including source,
tests, dependencies, and its existing project documentation.

| Benchmark target | Status | Replacement |
| --- | --- | --- |
| `NDD-SoA` | Deprecated | `NDD` |
| `NDD-SoA-BCDD` | Deprecated | `NDD-BCDD` |
| `NDD-SoA-FD-ZDD` | Legacy finite-domain experiment | No direct equivalent |

All three targets share this project. The finite-domain ZDD target is retained
with the deprecated variants because it uses the same source and build; its
value-domain semantics differ from NDD's Boolean-bit ZDD mode.

Java package names and benchmark target names are preserved. The runner builds
and executes the project from `deprecated/NDD-SoA/` when selected explicitly or
through `--targets all`. These targets are excluded from default runs.

From PowerShell at the repository root:

```powershell
.\scripts\run_nqueens_wsl.ps1 --targets NDD-SoA NDD-SoA-BCDD NDD-SoA-FD-ZDD --sizes 8 --output results/deprecated/nqueens_metrics.csv
```

After building, add `--skip-build` to reuse the compiled JAR. Historical
benchmark CSVs and plots remain in the repository's `results/` directory.
