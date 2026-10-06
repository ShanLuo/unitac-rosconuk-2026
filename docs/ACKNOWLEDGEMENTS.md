# Acknowledgements and provenance

UniTac @ ROSCon UK 2026 builds on research and engineering from the tactile-robotics community.

The tactile sensing, simulation and cross-sensor learning design is informed by prior work including:

1. Lin, Y., Lloyd, J., Church, A. and Lepora, N.F. (2022). *Tactile Gym 2.0: Sim-to-real deep reinforcement learning for comparing low-cost high-resolution robot touch*. IEEE Robotics and Automation Letters, 7(4), 10754–10761.
2. Lepora, N.F., Lin, Y., Money-Coomes, B. and Lloyd, J. (2022). *DigiTac: A DIGIT-TacTip Hybrid Tactile Sensor for Comparing Low-Cost High-Resolution Robot Touch*. IEEE Robotics and Automation Letters, 7(4), 9382–9388.
3. Chen, Z., Ou, N., Zhang, X., Wu, Z., Zhao, Y., Wang, Y., Papastavridis, E.S., Lepora, N., Jamone, L., Deng, J. and Luo, S. (2026). *Training tactile sensors to learn force sensing from each other*. Nature Communications.
4. Gomes, D.F., Paoletti, P. and Luo, S. (2021). *Generation of GelSight tactile images for sim2real learning*. IEEE Robotics and Automation Letters, 6(2), 4177–4184.

## GenForce and indenter CAD

The GenForce-style trajectory used in the workshop is based on the public GenForce resources:

https://github.com/Zhuochenn/GenForce_Code

The 18 STL indenter models used by GenForce are published at:

https://github.com/Zhuochenn/GenForce_Code/tree/main/sim/assets/indenters/input/stl

These geometries trace back to the earlier tactile-simulation work of Gomes, Paoletti and Luo (2021), which used 21 indenter shapes. GenForce retained a subset of 18.

Third-party or previously published files should retain their original notices and are not automatically covered by UniTac's MIT licence.

## tactile-bench and MG400 rig

The MG400 rig assets were made publicly accessible by Nathan Lepora through:

https://github.com/robot-dexterity/tactile-bench

At the time of this workshop update, the upstream tactile-bench LICENSE states proprietary/confidential restrictions on copying and distribution. UniTac therefore links to those assets rather than redistributing them. This repository's MIT licence does not supersede the upstream terms.

## UniTac licence scope

Workshop-authored UniTac code and documentation are released under the MIT License. Any third-party code, CAD, models, data or derived components remain governed by their applicable upstream licence or explicit permission.
