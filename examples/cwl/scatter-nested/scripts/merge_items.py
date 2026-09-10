#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputs", nargs="+", required=True)
    parser.add_argument("-o", "--output", default="group_summary.txt")
    args = parser.parse_args()

    total = 0
    for fpath in args.inputs:
        with open(fpath, "r") as f:
            total += int(f.read().strip())

    with open(args.output, "w") as f:
        f.write(f"total={total}\n")

if __name__ == "__main__":
    main()
