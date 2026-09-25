# MG400 + GelSight demonstrator setup

This records the validated physical data-collection configuration. It is intended for workshop demonstrators, not unattended participant use.

## Safety before motion

- Confirm the emergency stop and robot workspace are accessible.
- Check the mounted indenter, GelSight sensor and fixture are secure.
- Verify the work frame and TCP against `config/mg400_gelsight.yaml`.
- Confirm camera acquisition before enabling robot motion.
- Start from a clear, low-speed configuration and confirm adequate clearance.
- Do not use a different fixture or calibration without re-validating the trajectory.

## Validated setup

- Robot: Dobot MG400
- Work frame: `[265.36090088, 40.82979202, -114.89134216, 0, 0, 0]`
- TCP: `[0, 0, -50, 0, 0, 0]`
- Nominal Rz: `-31.3 deg`
- GelSight camera source: `2`
- Safe Z: `1.0 mm`
- Indentation depth: `0.5 mm`
- Shear radius: `1.0 mm`

The production collector performs camera preflight before motion, records commanded/actual poses and metadata, uses explicit retraction, and preserves failure information. On interruption/failure it intentionally does not assume that an automatic robot move is safe; the operator must assess the physical state.
