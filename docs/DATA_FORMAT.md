# MG400 + GelSight dataset format

A production run is written under:

```text
tactile_data/gelsight/genforce/<indenter>/<run_id>/
```

Each run contains `reference.png`, `metadata.csv`, `experiment_config.json`, `manifest.json`, per-cycle image directories, and a completion/failure marker.

The validated default trajectory has 5 base points, 1 indentation depth and 8 shear angles: 40 cycles. Each cycle contains `normal_inc`, `shear_inc`, `shear_dec`, and `normal_dec`. With 11 samples per phase, the default run produces 44 tactile frames per cycle plus the reference frame (1761 PNG images in a complete run).

`metadata.csv` records identifiers, timestamps, cycle/phase, commanded pose, measured robot pose, progress and image path.
