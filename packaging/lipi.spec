# PyInstaller recipe for the Windows app. Build from the project root:
#   python packaging/fetch_models.py      (downloads the OCR models so they get bundled)
#   pyinstaller packaging/lipi.spec --noconfirm
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files

root = os.path.dirname(SPECPATH)
datas, binaries, hiddenimports = [], [], []
for pkg in ("rapidocr", "onnxruntime", "pymupdf"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
datas += collect_data_files("docx")  # Word templates
datas += [
    (os.path.join(root, "smart_ocr", "web_static"), os.path.join("smart_ocr", "web_static")),
    (os.path.join(root, "smart_ocr", "data"), os.path.join("smart_ocr", "data")),
]

a = Analysis(
    [os.path.join(SPECPATH, "launch.py")],
    pathex=[root],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # rapidocr can also run on torch/paddle/openvino; Lipi only uses onnxruntime.
    excludes=["tkinter", "matplotlib", "torch", "paddle", "openvino", "mlx", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Lipi", console=True,
          icon=os.path.join(SPECPATH, "lipi.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="Lipi")
