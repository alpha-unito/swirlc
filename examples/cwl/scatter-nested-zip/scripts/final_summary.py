#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description="Produce final global summary across all zips")
    parser.add_argument("-s", "--summaries", nargs="+", required=True, help="Zip summary files")
    parser.add_argument("-o", "--output", default="final_report.txt", help="Final output file")
    args = parser.parse_args()

    lines = ["====================================", "      GLOBAL WORKFLOW SUMMARY       ", "===================================="]
    lines.append(f"Processed {len(args.summaries)} zip archives.\n")

    for s_path in sorted(args.summaries):
        with open(s_path, "r") as f:
            lines.append(f.read().strip())
            lines.append("-" * 36)

    with open(args.output, "w") as out:
        out.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
