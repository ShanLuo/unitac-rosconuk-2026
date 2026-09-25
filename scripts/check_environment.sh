#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import cv2, numpy
from cri.controller import Controller
print('Core workshop Python dependencies: OK')
print('OpenCV:', cv2.__version__)
print('NumPy:', numpy.__version__)
print('CRI import: OK')
PY
