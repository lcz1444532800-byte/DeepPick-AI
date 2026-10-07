# All build and runtime data are kept on D:.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = collect_data_files('onnxruntime',includes=['LICENSE','ThirdPartyNotices.txt','Privacy.md'])
binaries = collect_dynamic_libs('onnxruntime')
datas += copy_metadata('onnxruntime')
hidden = ['onnxruntime','deeppick.ocr_worker','deeppick.ocr_engine','cv2','shapely','pyclipper',
           'cryptography.hazmat.primitives.ciphers.aead','multiprocessing.shared_memory']
a = Analysis([str(root/'main.py')],pathex=[str(root)],
             binaries=binaries,datas=datas,hiddenimports=hidden,
             excludes=['paddle','tkinter','matplotlib','scipy','skimage','imgaug','paddleocr',
                       'IPython','pytest','torch','transformers','pandas','onnx',
                       'PySide6.QtWebEngineWidgets','PySide6.QtWebEngineCore','PySide6.QtQml',
                       'PySide6.QtQuick','PySide6.QtMultimedia','PySide6.Qt3DCore'],
             runtime_hooks=[str(root/'assets/runtime_bootstrap.py')],noarchive=False,optimize=1)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='DeepPickAI',
          debug=False,strip=False,upx=False,console=False,
          icon=str(root/'assets'/'DeepPickAI.ico'),version=str(root/'assets'/'version_info.txt'),
          contents_directory='app',manifest=str(root/'assets'/'app.manifest'))
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='DeepPickAI')
