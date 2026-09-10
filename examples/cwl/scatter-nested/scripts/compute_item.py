#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--group", required=True)
    parser.add_argument("-i", "--item", type=int, required=True)
    parser.add_argument("-o", "--output", default="item_result.txt")
    args = parser.parse_args()

    with open(args.group, "r") as f:
        val = int(f.read().strip())

    result = val + args.item
    with open(args.output, "w") as f:
        f.write(f"{result}\n")

if __name__ == "__main__":
    main()
