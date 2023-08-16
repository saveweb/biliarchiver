#!/usr/bin/env python3
import subprocess
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Publish to PyPI")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print("Building i18n...")
    subprocess.run(["msgfmt", "biliarchiver/locales/en/LC_MESSAGES/biliarchiver.po", "-o", "biliarchiver/locales/en/LC_MESSAGES/biliarchiver.mo"])
    print("Building with poetry...")
    poetry_comm = ["poetry", "build"]
    subprocess.run(poetry_comm)
    if args.publish:
        poetry_comm = ["poetry", "publish"]
        subprocess.run(poetry_comm)
