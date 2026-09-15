"""Copy dependency notices into a distributable app directory."""
import importlib.metadata
import shutil
import sys
import sysconfig
from pathlib import Path


def main(destination: Path) -> None:
    licenses = destination / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    for name in ("openpyxl", "et_xmlfile", "XlsxWriter", "python-calamine", "PyInstaller"):
        dist = importlib.metadata.distribution(name)
        matches = [file for file in dist.files or ()
                   if any(term in file.name.lower() for term in ("license", "licence", "copying"))]
        if not matches:
            notices = list((Path(__file__).parent / "licenses").glob(f"{name}-{dist.version}-*"))
            if not notices:
                raise RuntimeError(f"License file missing for {name}")
            for notice in notices:
                shutil.copyfile(notice, licenses / notice.name)
        for index, file in enumerate(matches):
            shutil.copyfile(dist.locate_file(file), licenses / f"{name}-{index}-{file.name}")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.exists():
        python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if not python_license.exists():
        raise RuntimeError("Python license file missing")
    shutil.copyfile(python_license, licenses / "Python-LICENSE.txt")
    # Windows python.org distributions ship Tcl/Tk notices under tcl/.
    tcl_licenses = sorted((Path(sys.base_prefix) / "tcl").rglob("license.terms"))
    if sys.platform == "win32" and not tcl_licenses:
        raise RuntimeError("Tcl/Tk license files missing")
    for index, file in enumerate(tcl_licenses):
        shutil.copyfile(file, licenses / f"TclTk-{index}-license.terms")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
