# Deprecated and legacy implementations

`NDD-SoA/` contains the archived Maven project, including source,
tests, dependencies, and its existing project documentation.

| Benchmark target | Status | Replacement |
| --- | --- | --- |
| `NDD-SoA` | Deprecated | `NDD` |
| `NDD-SoA-BCDD` | Deprecated | `NDD-BCDD` |
| `NDD-SoA-FD-ZDD` | Legacy finite-domain experiment | No direct equivalent |

All three targets share this project. The finite-domain ZDD target is retained
with the deprecated variants because it uses the same source and build; its
value-domain semantics differ from NDD's Boolean-bit ZDD mode.

Java package names and archived source are preserved. These targets have been
removed from the active benchmark runner, including `--targets all`; the runner
no longer builds this project. Use the maintained replacements listed above.
Generated build outputs and IDE metadata have been removed from this archive.
`results/` retains only the current upstream comparison; historical benchmark
CSVs and plots have been removed.
