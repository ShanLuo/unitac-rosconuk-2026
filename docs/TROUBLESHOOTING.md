# Troubleshooting

## Camera not found
Check Linux video devices with `v4l2-ctl --list-devices` or inspect `/dev/video*`. The validated demonstrator uses camera source 2; do not assume the same index elsewhere.

## Docker cannot access hardware
Participant Docker is intentionally hardware-neutral. Enable physical camera/robot access only on the demonstrator machine after checking device and network configuration.

## Python import errors
Run `python3 -m pip install -e .` from the repository root, or rebuild the workshop container.

## Robot connection fails
Do not repeatedly issue motion commands. Check MG400 power/state, network connectivity and CRI configuration first.
