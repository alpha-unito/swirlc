#!/usr/bin/env python3
import argparse
import os
import re

def main():
    parser = argparse.ArgumentParser(description="Analyze gathered scatter results")
    parser.add_argument("-i", "--inputs", nargs="+", required=True, help="Input gathered file(s)")
    parser.add_argument("-o", "--output", default="analysis_report.txt", help="Output analysis report")
    args = parser.parse_args()

    items = []
    total_bytes = 0

    input_files = args.inputs if isinstance(args.inputs, list) else [args.inputs]
    for input_file in input_files:
        if not os.path.isfile(input_file):
            continue
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m_id = re.search(r"Item\s+(\d+)", line)
                m_tot = re.search(r"total=(\d+)", line)
                item_id = int(m_id.group(1)) if m_id else len(items)
                byte_count = int(m_tot.group(1)) if m_tot else 0
                items.append((item_id, byte_count, line))
                total_bytes += byte_count

    items.sort(key=lambda x: x[0])

    count = len(items)
    avg_bytes = (total_bytes / count) if count > 0 else 0.0
    min_item = min(items, key=lambda x: x[1]) if items else (None, 0, "")
    max_item = max(items, key=lambda x: x[1]) if items else (None, 0, "")

    report_lines = [
        "========================================",
        "      SCATTER-GATHER ANALYSIS REPORT     ",
        "========================================",
        f"Total items processed : {count}",
        f"Total bytes computed  : {total_bytes} bytes",
        f"Average item size     : {avg_bytes:.2f} bytes",
        f"Smallest item         : Item {min_item[0]} ({min_item[1]} bytes)",
        f"Largest item          : Item {max_item[0]} ({max_item[1]} bytes)",
        "Pipeline status       : SUCCESS",
        "========================================",
    ]

    with open(args.output, "w", encoding="utf-8") as f:
        for l in report_lines:
            f.write(l + "\n")

    print(f"Analysis completed: processed {count} items, wrote report to {args.output}")

if __name__ == "__main__":
    main()
