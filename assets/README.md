# UniTac hardware assets

This directory is the workshop index for physical rig and indenter CAD resources.

## Indenters / stimuli

The UniTac collection trajectory follows the GenForce-style tactile data-collection setup. The public GenForce code repository is maintained at:

- https://github.com/Zhuochenn/GenForce_Code

The currently published GenForce repository does not expose a clearly identified indenter CAD/STL set under its top-level `assets/` directory. For that reason, those CAD files have **not** been copied into UniTac automatically. Once the exact upstream CAD paths and redistribution terms are confirmed, place permitted files under:

```text
assets/
└── indenters/
```

and retain their original copyright/licence notices.

## Dobot MG400 rig

Nathan Lepora has made the tactile-bench repository public and it contains the MG400 rig resources under:

- https://github.com/robot-dexterity/tactile-bench/tree/main/assets/Dobot%20MG400%20rig

These include the baseplate/workspace models and subdirectories for the end flange, mounting plates and standoffs.

The upstream tactile-bench `LICENSE` currently contains a proprietary/confidentiality notice that restricts copying and distribution. Therefore the MG400 CAD files are **linked rather than copied** into this MIT-licensed repository. If the tactile-bench licence is updated to permit redistribution, the permitted files can be vendored here while preserving the upstream notice.

## Licensing

The repository-level MIT licence applies only to UniTac workshop-authored material. It does not override licences or permissions attached to third-party CAD, code, models or data.
