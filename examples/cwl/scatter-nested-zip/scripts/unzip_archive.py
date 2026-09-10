#!/usr/bin/env python3
import argparse
import os
import zipfile

def main():
    parser = argparse.ArgumentParser(description="Unpack a zip archive to the workdir")
    parser.add_argument("-z", "--zipfile", required=True, help="Path to input zip file")
    args = parser.parse_args()

    with zipfile.ZipFile(args.zipfile, "r") as z:
        z.extractall(".")

if __name__ == "__main__":
    main()
