#!/usr/bin/env python3
import argparse
import shutil
import subprocess
from pathlib import Path
from project_setup import Layout, build_files, install


def main():
    parser = argparse.ArgumentParser(description="Install Spotlight AI Search for the current Omarchy user.")
    parser.add_argument("--port", type=int, default=18476)
    parser.add_argument("--dry-run", action="store_true", help="Show destinations without changing anything")
    parser.add_argument("--no-start", action="store_true", help="Write files without enabling services or reloading Hyprland")
    args = parser.parse_args()
    root, layout = Path(__file__).resolve().parent, Layout.current()
    try:
        files = build_files(root, layout, args.port)
        print("Installs these user-local files:")
        for path in files:
            print(" ", path)
        print("Adds a managed require block to:", layout.bindings)
        print("Rebinds Alt+Space and Super+Alt+Space (Omarchy's Apps-menu shortcut).")
        if args.dry_run:
            return
        missing = [name for name in ("python3", "brave", "hyprctl", "systemctl", "omarchy") if not shutil.which(name)]
        if missing:
            raise RuntimeError("Missing dependencies: " + ", ".join(missing))
        backup = install(root, layout, args.port, activate=not args.no_start)
        print("Installed. Bindings backup:", backup)
        print("Use Alt+Space to open the popup; Super+Alt+Space starts fresh.")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Installation failed: {error}\n")


if __name__ == "__main__":
    main()
