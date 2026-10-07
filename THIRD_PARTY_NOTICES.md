# Third-party components

DeepPick AI 1.2.3
Developer:Chunze Liu

The release includes the third-party runtime components listed below.
Development-only dependencies are not distributed.
Corresponding license texts are included under app/licenses.

PaddleOCR PP-OCRv4 models, dictionary and DB postprocessing:
Copyright (c) 2020 PaddlePaddle Authors. Apache License 2.0.
DB postprocessing source is provided in app/source/deeppick/third_party; optional Paddle Tensor conversion was removed, with a modification notice in its header.
https://github.com/PaddlePaddle/PaddleOCR/tree/v2.9.1
Model download URLs and SHA-256 checksums: models/manifest.json.

PaddlePaddle 2.6.2: Apache License 2.0.
https://github.com/PaddlePaddle/Paddle/tree/v2.6.2

PySide6 / Shiboken6 / Qt 6.8.3: LGPL 3.0 / applicable Qt component licenses.
These libraries are dynamically linked and may be replaced with compatible builds.
DeepPick AI does not prohibit reverse engineering needed to debug modifications
to the LGPL libraries. Application source and build instructions are provided.
Corresponding library sources are available from the original project:
https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
https://download.qt.io/archive/qt/6.8/6.8.3/submodules/

NumPy 1.26.4: BSD-3-Clause and bundled dependency licenses.
OpenCV headless 4.10.0.84: Apache-2.0 and component licenses.
Shapely 2.1.2 / GEOS: BSD-3-Clause / LGPL-2.1 and bundled licenses.
pyclipper 1.3.0.post6: MIT and Boost Software License for Clipper.
HTTPX 0.28.1 / HTTPCore / AnyIO: BSD-3-Clause / MIT.
Cryptography 46.0.1: Apache-2.0 or BSD-3-Clause, bundled OpenSSL licenses.
Python 3.11.9: Python Software Foundation License and bundled licenses.
Other bundled dependencies retain their original licenses, collected under
app/licenses from their installed package metadata.

Third-party model binaries and runtime libraries are unmodified. DB postprocessing was adapted only to remove optional Paddle Tensor conversion. No DeepSeek model is
distributed; DeepSeek is accessed only via the user's own optional API account.

ONNX Runtime 1.20.1: MIT License. Unmodified CPU runtime.
https://github.com/microsoft/onnxruntime/tree/v1.20.1
PP-OCRv4 ONNX models supplied in RapidOCR 1.4.4: Apache-2.0.
https://github.com/RapidAI/RapidOCR
Source and SHA-256 checksums: models/onnx/manifest.json.
Model binaries were not changed. RapidOCR Python implementation is not bundled.
The release uses ONNX Runtime for local PP-OCRv4 inference; PaddlePaddle is not bundled in this release.
UX references (no source code copied): Umi-OCR and Text Grab.
https://github.com/hiroi-sora/Umi-OCR
https://github.com/TheJoeFin/Text-Grab

Official CPython embedded runtime 3.11.9: Python Software Foundation License.
Official signed pythonw.exe was renamed only; executable and DLL contents are unmodified.
https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
Source and SHA-256: app/runtime/manifest.json. License: app/runtime/LICENSE.txt.
