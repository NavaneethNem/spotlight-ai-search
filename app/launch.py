#!/usr/bin/env python3
"""Open the dedicated popup; --fresh replaces only that popup's window."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

CLASS = "brave-127.0.0.1__spotlight-ai-Default"


def clients():
    return json.loads(subprocess.check_output(["hyprctl", "clients", "-j"]))


def fresh():
    for window in clients():
        if window.get("class") != CLASS:
            continue
        target = "address:" + window["address"]
        command = "hl.dsp.window.close({ window = " + json.dumps(target) + " })"
        subprocess.run(["hyprctl", "dispatch", command], check=True, stdout=subprocess.DEVNULL)
    for _ in range(40):
        if not any(window.get("class") == CLASS for window in clients()):
            return
        time.sleep(.05)
    raise RuntimeError("The previous popup did not close; no duplicate window was opened.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    config = json.loads((Path(__file__).resolve().parent / "runtime.json").read_text())
    if args.fresh:
        fresh()
    subprocess.run(["systemctl", "--user", "start", "spotlight-ai-search.service"], check=True)
    url = "http://127.0.0.1:" + str(config["port"]) + "/spotlight-ai"
    os.execvp("brave", ["brave", "--profile-directory=Default", "--app=" + url])


if __name__ == "__main__":
    main()
