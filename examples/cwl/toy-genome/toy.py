"""Deterministic toy processing: no genomic software, network or dependencies."""
import argparse
from pathlib import Path


def numbers(path):
    return [int(line) for line in Path(path).read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["individuals", "individuals_merge", "sifting", "mutation_overlap", "frequency"])
    parser.add_argument("--chromosome", required=True)
    parser.add_argument("--input")
    parser.add_argument("--counter", type=int)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--parts", nargs="*", default=[])
    parser.add_argument("--population", choices=["AFR", "EUR"])
    parser.add_argument("--sift")
    parser.add_argument("--label")
    args = parser.parse_args()
    if args.command == "individuals":
        values = numbers(args.input)[args.counter - 1:args.stop]
    elif args.command == "individuals_merge":
        values = [value for part in args.parts for value in numbers(part)]
    elif args.command == "sifting":
        values = numbers(args.input)
    else:
        values = numbers(args.input)
        selected = [value for value in values if value in set(numbers(args.sift))]
        # AFR retains all candidates; EUR retains only candidates divisible by 4.
        retained = selected if args.population == "AFR" else [value for value in selected if value % 4 == 0]
        if args.command == "mutation_overlap":
            print(f"overlap {args.label}: " + ",".join(map(str, retained)))
        else:
            print(f"frequency {args.label}: {len(retained)}/{len(values)};sum={sum(retained)}")
        return
    for value in values:
        print(value)


if __name__ == "__main__":
    main()
