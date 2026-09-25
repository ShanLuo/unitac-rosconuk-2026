# UniTac @ ROSCon UK 2026

**UniTac: A ROS 2 Framework for Unified Tactile Sensing and Cross-Sensor Robot Learning**

Private development repository for the ROSCon UK 2026 hands-on tutorial (**Thursday 22 October 2026**, morning workshop, **Pentland West**).

This repository is being prepared for collaborator review before public release. It will contain the UniTac ROS 2 workshop materials, the validated Dobot MG400 + GelSight data-collection pipeline, tactile-bench utilities, Docker environment, participant pre-work, and examples for cross-sensor tactile learning.

## Workshop goals

Participants will learn how to:
1. acquire and visualise tactile data through a common ROS 2 workflow;
2. process tactile observations from different sensor types;
3. understand UniTac's shared tactile representation;
4. explore cross-sensor transfer for tactile perception and robot learning;
5. connect tactile observations to reusable perception/manipulation pipelines.

## Repository structure

```text
.
├── config/                    # validated hardware/experiment records
├── docker/                    # ROS 2 workshop image
├── docs/                      # participant, hardware, provenance and data docs
├── examples/                  # hands-on tutorial examples
├── scripts/                   # collection and environment scripts
└── src/unitac_workshop/       # workshop Python package / tactile utilities
```

## Quick start

```bash
git clone https://github.com/ShanLuo/unitac-rosconuk-2026.git
cd unitac-rosconuk-2026
docker compose build
docker compose run --rm workshop
```

For the physical MG400 + GelSight demonstration, use the validated collector only after reading `docs/HARDWARE_SETUP.md`.

## Development status

This repository is currently **private** while collaborators review code provenance and permissions. Do not redistribute repository contents until that review is complete.

The MG400 + GelSight collector is the canonical physical data-collection path. UniTac shared-latent inference examples, model assets and additional sensor adapters will be added as the workshop release is finalised.

## Licensing and provenance

Repository-wide licensing is intentionally **pending** until the upstream-code provenance review is complete. Third-party or derived components retain their applicable upstream terms. See `docs/ACKNOWLEDGEMENTS.md`.
