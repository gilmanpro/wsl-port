import shutil
import re
from pathlib import Path

BASE = Path(r"C:\Users\Gilman\Desktop\COMPARTIDOS\gilberto\WSL siempre en mini pc\proyectos\wsl-port")
WSL_SRC = Path(r"C:\Users\Gilman\Desktop\COMPARTIDOS\gilberto\WSL siempre en mini pc\proyectos\wsl-manager-gui\src")
PF_SRC = Path(r"C:\Users\Gilman\Desktop\COMPARTIDOS\gilberto\WSL siempre en mini pc\proyectos\port-forwarder-app\src")

VENDOR_WSL = BASE / "wsl_port" / "vendor" / "wsl_manager"
VENDOR_PF = BASE / "wsl_port" / "vendor" / "port_forwarder"

for p in [VENDOR_WSL, VENDOR_PF]:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)

def copy_and_patch(src_root: Path, dst_root: Path, vendor_prefix: str):
    count = 0
    for src_path in src_root.rglob("*.py"):
        if "__pycache__" in src_path.parts:
            continue
        rel = src_path.relative_to(src_root)
        dst_path = dst_root / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        text = src_path.read_text(encoding="utf-8")
        text = re.sub(r'\bfrom\s+src\s+import\b', f'from {vendor_prefix} import', text)
        text = re.sub(r'\bfrom\s+src\.', f'from {vendor_prefix}.', text)
        text = re.sub(r'\bimport\s+src\.', f'import {vendor_prefix}.', text)
        text = re.sub(r'\bimport\s+src\b(?!\.)', f'import {vendor_prefix} as src', text)
        dst_path.write_text(text, encoding="utf-8")
        count += 1
    return count

print("Copying wsl-manager-gui/src -> vendor/wsl_manager ...")
n1 = copy_and_patch(WSL_SRC, VENDOR_WSL, "wsl_port.vendor.wsl_manager")
print(f"  {n1} files")

print("Copying port-forwarder-app/src -> vendor/port_forwarder ...")
n2 = copy_and_patch(PF_SRC, VENDOR_PF, "wsl_port.vendor.port_forwarder")
print(f"  {n2} files")

for p in [BASE / "wsl_port" / "vendor" / "__init__.py", VENDOR_WSL / "__init__.py", VENDOR_PF / "__init__.py"]:
    if not p.exists():
        p.write_text("", encoding="utf-8")

print("Vendor copy done")
