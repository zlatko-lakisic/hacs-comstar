"""Stage HA install payloads for MCP ha_write_file."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(r"d:\Projects\hacs-comstar\custom_components\comstar")
stage = Path(r"d:\Projects\hacs-comstar\.install_payloads")
stage.mkdir(exist_ok=True)
for old in stage.glob("*.json"):
    old.unlink()

n = 0
for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(root).as_posix()
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("skip binary", rel)
        continue
    payload = {
        "path": f"custom_components/comstar/{rel}",
        "content": text,
        "description": f"Install HACS Comstar {rel}",
    }
    (stage / f"{n:04d}.json").write_text(json.dumps(payload), encoding="utf-8")
    n += 1
print("staged", n)
