"""Build an installable archive without caches or development dependencies."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/taiwan_work_school"
version = json.loads((COMPONENT / "manifest.json").read_text())["version"]
output = ROOT / "dist" / f"taiwan_work_school-{version}.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in sorted(COMPONENT.rglob("*")):
        if (
            path.is_file()
            and path.suffix in (".py", ".json", ".png")
            and "__pycache__" not in path.parts
        ):
            archive.write(path, path.relative_to(ROOT))
    archive.write(ROOT / "README.md", "README.md")
print(output)
