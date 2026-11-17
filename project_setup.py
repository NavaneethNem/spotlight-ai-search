"""User-local installation helpers. The checkout contains no machine configuration."""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

APP_FILES = ("server.py", "launch.py", "index.html", "app.js")
HOOK = '\n-- >>> spotlight-ai-search\nrequire("hypr.spotlight-ai-search")\n-- <<< spotlight-ai-search\n'
UNIT = "spotlight-ai-search.service"


@dataclass
class Layout:
    config: Path
    data: Path

    @classmethod
    def current(cls):
        home = Path.home()
        return cls(Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")),
                   Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")))

    @property
    def app(self):
        return self.data / "spotlight-ai-search"

    @property
    def bindings(self):
        return self.config / "hypr/bindings.lua"

    @property
    def module(self):
        return self.config / "hypr/spotlight-ai-search.lua"

    @property
    def unit(self):
        return self.config / "systemd/user" / UNIT

    @property
    def receipt(self):
        return self.app / ".install-receipt.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def systemd_quote(value):
    return '"' + str(value).replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"') + '"'


def build_files(root, layout, port):
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port between 1024 and 65535.")
    files = {layout.app / name: (root / "app" / name).read_bytes() for name in APP_FILES}
    files[layout.app / "runtime.json"] = (json.dumps({"port": port}, indent=2) + "\n").encode()
    command = "python3 " + shlex.quote(str(layout.app / "launch.py"))
    template = (root / "integration/hyprland.lua.in").read_text()
    template = template.replace("@LAUNCH_COMMAND@", json.dumps(command, ensure_ascii=False))
    template = template.replace("@FRESH_COMMAND@", json.dumps(command + " --fresh", ensure_ascii=False))
    files[layout.module] = template.encode()
    unit = f'''[Unit]
Description=Spotlight AI Search autocomplete
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={systemd_quote(sys.executable)} {systemd_quote(layout.app / 'server.py')} --port {port}
Restart=on-failure
RestartSec=2
UMask=0077

[Install]
WantedBy=graphical-session.target
'''
    files[layout.unit] = unit.encode()
    return files


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True)


def backup_bindings(path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(path.name + ".spotlight-backup-" + stamp)
    shutil.copy2(path, backup)
    return backup


def install(root, layout, port=18476, activate=True):
    if not layout.bindings.is_file():
        raise RuntimeError("Omarchy bindings.lua was not found. See the manual setup instructions.")
    files = build_files(root, layout, port)
    old_receipt = json.loads(layout.receipt.read_text()) if layout.receipt.exists() else {"files": {}}
    if layout.app.exists() and not layout.receipt.exists():
        raise RuntimeError("The install directory already exists without an ownership receipt; it was not changed.")
    for path in files:
        if path.exists() and old_receipt["files"].get(str(path)) != digest(path.read_bytes()):
            raise RuntimeError(f"Existing or edited file would be overwritten: {path}")
    binding_data = layout.bindings.read_bytes()
    if b"-- >>> spotlight-ai-search" in binding_data and HOOK.encode() not in binding_data:
        raise RuntimeError("The managed bindings block was edited; resolve it manually before reinstalling.")
    files[layout.bindings] = binding_data.replace(HOOK.encode(), b"").rstrip() + b"\n" + HOOK.encode()
    owned = {str(path): digest(data) for path, data in files.items() if path != layout.bindings}
    files[layout.receipt] = (json.dumps({"files": owned}, indent=2) + "\n").encode()
    previous = {path: path.read_bytes() if path.exists() else None for path in files}
    app_existed = layout.app.exists()
    backup = backup_bindings(layout.bindings)
    try:
        for path, data in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if activate:
            run("hyprctl", "reload")
            errors = run("hyprctl", "configerrors").stdout.strip()
            if errors:
                raise RuntimeError("Hyprland rejected the configuration:\n" + errors)
            run("systemctl", "--user", "daemon-reload")
            run("systemctl", "--user", "enable", "--now", UNIT)
    except Exception:
        if activate and previous[layout.receipt] is None:
            subprocess.run(["systemctl", "--user", "disable", "--now", UNIT], capture_output=True)
        for path, data in previous.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        if not app_existed:
            try:
                layout.app.rmdir()
            except OSError:
                pass
        if activate:
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["hyprctl", "reload"], capture_output=True)
        raise
    return backup


def uninstall(layout, activate=True):
    if not layout.receipt.exists():
        raise RuntimeError("No Spotlight AI Search installation receipt was found; nothing was removed.")
    receipt = json.loads(layout.receipt.read_text())
    # Only these known destinations may be removed, even if a receipt is edited.
    allowed = [layout.app / name for name in (*APP_FILES, "runtime.json")] + [layout.module, layout.unit]
    if activate:
        run("systemctl", "--user", "disable", "--now", UNIT)
    if layout.bindings.exists():
        data = layout.bindings.read_bytes()
        if HOOK.encode() in data:
            backup_bindings(layout.bindings)
            layout.bindings.write_bytes(data.replace(HOOK.encode(), b""))
        elif b"-- >>> spotlight-ai-search" in data:
            raise RuntimeError("The managed bindings block was edited; remove it manually, then retry.")
    preserved = []
    for path in allowed:
        if not path.exists():
            continue
        if receipt["files"].get(str(path)) == digest(path.read_bytes()):
            path.unlink()
        else:
            preserved.append(path)
    if not preserved:
        layout.receipt.unlink()
        try:
            layout.app.rmdir()  # Never recursively delete a directory containing user files.
        except OSError:
            pass
    if activate:
        run("systemctl", "--user", "daemon-reload")
        run("hyprctl", "reload")
    return preserved
