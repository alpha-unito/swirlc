#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--summaries", nargs="+", required=True)
    parser.add_argument("-t", "--tagged", nargs="+", required=True)
    parser.add_argument("-o", "--output", default="final_report.txt")
    args = parser.parse_args()

    lines = ["=== FINAL WORKFLOW REPORT ==="]
    lines.append("Group Summaries:")
    for fpath in sorted(args.summaries):
        with open(fpath, "r") as f:
            lines.append(f"  {f.read().strip()}")

    lines.append("Tagged Results:")
    for fpath in sorted(args.tagged):
        with open(fpath, "r") as f:
            lines.append(f"  {f.read().strip()}")

    with open(args.output, "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
