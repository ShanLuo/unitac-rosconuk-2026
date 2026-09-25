# Participant pre-work

Most participants can complete the software exercises without controlling the physical robot.

## Before ROSCon UK 2026

1. Install Git.
2. Install Docker Engine (Linux) or Docker Desktop (macOS/Windows).
3. Confirm Docker works with `docker run --rm hello-world`.
4. Clone this repository after workshop access is provided.
5. Run:

```bash
docker compose build
docker compose run --rm workshop bash scripts/check_environment.sh
```

Workshop tactile hardware will be provided for guided sessions. The Dobot MG400 + GelSight path is a demonstrator setup and is not required for participant pre-work.
