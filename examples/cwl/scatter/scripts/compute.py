#!/usr/bin/env python3
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Worker computation on unpacked tuple components")
    parser.add_argument("--id", required=False, default=None, help="Item ID file")
    parser.add_argument("-a", required=True, help="Input component A")
    parser.add_argument("-b", required=True, help="Input component B")
    parser.add_argument("-o", "--output", default="result.txt", help="Output result file")
    args = parser.parse_args()

    if args.id and os.path.exists(args.id):
        with open(args.id, "r", encoding="utf-8") as f:
            item_id = f.read().strip()
    else:
        item_id = "item"

    with open(args.a, "r", encoding="utf-8") as f:
        content_a = f.read()

    with open(args.b, "r", encoding="utf-8") as f:
        content_b = f.read()

    size_a = len(content_a)
    size_b = len(content_b)

    result_line = f"Item {item_id}: input_a={size_a} bytes, input_b={size_b} bytes, total={size_a + size_b} bytes\n"

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result_line)

    print(f"Computed item {item_id}: {result_line.strip()}")

if __name__ == "__main__":
    main()
