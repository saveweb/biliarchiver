#!/usr/bin/env python3
import subprocess

if __name__ == "__main__":
    print("Building i18n...")
    subprocess.run(["msgfmt", "biliarchiver/locales/en/LC_MESSAGES/biliarchiver.po", "-o", "biliarchiver/locales/en/LC_MESSAGES/biliarchiver.mo"])
    print("Building with poetry...")
    subprocess.run(["poetry", "build"])