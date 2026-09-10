#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--summary", required=True)
    parser.add_argument("-t", "--tag", required=True)
    parser.add_argument("-o", "--output", default="tagged_result.txt")
    args = parser.parse_args()

    with open(args.summary, "r") as f:
        summary = f.read().strip()
    with open(args.tag, "r") as f:
        tag = f.read().strip()

    with open(args.output, "w") as f:
        f.write(f"[{tag}] {summary}\n")

if __name__ == "__main__":
    main()
