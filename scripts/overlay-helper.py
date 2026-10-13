#!/usr/bin/env python3
"""Install or remove the cTrader notification overlay helper in a Wine bottle."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess


RUN_KEY = r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunServices"
LEGACY_RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "cTraderOverlayFix"
WINDOWS_EXE = r"C:\tools\cTraderOverlayFix\ctrader-overlay-fix.exe"
MARKER = ".ctrader-overlay-fix"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall", "start", "stop"))
    parser.add_argument("--prefix", required=True, type=Path, help="Directory of an existing 64-bit bottle")
    parser.add_argument("--wine", required=True, type=Path, help="Wine executable used by that bottle")
    args = parser.parse_args()
    prefix = args.prefix.expanduser().resolve()
    wine = args.wine.expanduser().absolute()
    if not (prefix / "drive_c").is_dir() or not (prefix / "user.reg").is_file():
        parser.error("--prefix must point to an existing Wine bottle")
    if not wine.is_file() or not os.access(wine, os.X_OK):
        parser.error("--wine must point to an executable Wine runner")
    env = os.environ.copy()
    env["WINEPREFIX"] = str(prefix)
    env["WINEDEBUG"] = "-all"
    for name in ("WINESERVERSOCKET", "WINELOADERNOEXEC", "WINEPRELOADRESERVE"):
        env.pop(name, None)
    directory = prefix / "drive_c/tools/cTraderOverlayFix"
    target = directory / "ctrader-overlay-fix.exe"

    def run(*command, check=True):
        return subprocess.run([str(wine), *command], env=env, check=check, timeout=30)

    def stop():
        if target.is_file():
            run(str(target), "--stop")

    def start():
        if not target.is_file():
            parser.error("helper is not installed; run the install action first")
        subprocess.Popen([str(wine), str(target)], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    if args.action == "install":
        source = Path(__file__).resolve().parent.parent / "build/ctrader-overlay-fix.exe"
        if not source.is_file():
            parser.error("build the helper first with bash scripts/build-overlay-helper.sh")
        if directory.exists() and not (directory / MARKER).is_file():
            parser.error(f"refusing to overwrite an unrecognized directory: {directory}")
        stop()
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        (directory / MARKER).write_text("ctrader-bottles-wayland-fix\n", encoding="utf-8")
        subprocess.run([str(wine), "reg", "delete", LEGACY_RUN_KEY, "/v", RUN_NAME, "/f"],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        for view in ("32", "64"):
            run("reg", "add", RUN_KEY, "/v", RUN_NAME, "/t", "REG_SZ",
                "/d", f'"{WINDOWS_EXE}"', "/f", f"/reg:{view}")
        start()
        print(f"Installed: {target}\nAutostart: {RUN_KEY} → {RUN_NAME}")
    elif args.action == "uninstall":
        if not (directory / MARKER).is_file():
            parser.error("no recognized helper installation found in this bottle")
        stop()
        for view in ("32", "64"):
            run("reg", "delete", RUN_KEY, "/v", RUN_NAME, "/f", f"/reg:{view}")
        target.unlink(missing_ok=True)
        (directory / MARKER).unlink()
        if not any(directory.iterdir()):
            directory.rmdir()
        print("Helper and autostart entry removed. Restart cTrader to recreate its original overlays.")
    elif args.action == "start":
        start()
        print("Helper started; duplicate instances exit automatically.")
    else:
        stop()
        print("Helper stopped. Restart cTrader to recreate its original overlays.")


if __name__ == "__main__":
    main()
