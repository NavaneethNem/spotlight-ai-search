#!/usr/bin/env python3
import argparse
import subprocess
from project_setup import Layout, uninstall


def main():
    parser = argparse.ArgumentParser(description="Remove managed Spotlight AI Search files; preserve edited files.")
    parser.add_argument("--no-services", action="store_true", help="Skip systemd commands and Hyprland reload")
    args = parser.parse_args()
    try:
        preserved = uninstall(Layout.current(), activate=not args.no_services)
        print("Removed the managed installation and keybinding block.")
        for path in preserved:
            print("Preserved an edited file:", path)
        if preserved:
            print("The ownership receipt was retained for the preserved files.")
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Uninstall failed: {error}\n")


if __name__ == "__main__":
    main()
