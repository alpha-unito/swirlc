#!/usr/bin/env python3
"""Translate and compile C3S layouts without submitting workflow jobs."""

import argparse
from pathlib import Path
import subprocess
import sys

from ruamel.yaml import YAML


def main():
    example = Path(__file__).resolve().parent
    project = example.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("locations", nargs="*", type=int,
                        help="Location counts (default: 1 2 5 10 20)")
    parser.add_argument("--settings", type=Path, default=example / "config-1chr.yml")
    parser.add_argument("--build-root", type=Path,
                        help="Build parent (default: PROJECT/build-genome-c3s-SETTINGS)")
    args = parser.parse_args()
    counts = list(dict.fromkeys(args.locations or [1, 2, 5, 10, 20]))
    if any(n not in (1, 2, 5, 10, 20) for n in counts):
        parser.error("locations must be selected from 1, 2, 5, 10, 20")
    settings = args.settings.resolve()
    if not settings.is_file():
        parser.error(f"Settings file does not exist: {settings}")
    yaml = YAML()
    inputs = yaml.load(settings)
    if not isinstance(inputs, dict):
        parser.error("Settings must be a YAML mapping")
    build_root = (args.build_root or project / f"build-genome-c3s-{settings.stem}").resolve()
    for count in counts:
        build = build_root / str(count)
        build.mkdir(parents=True, exist_ok=True)
        config = yaml.load(example / f"streamflow-c3s-{count}.yml")
        for workflow in config["workflows"].values():
            workflow["config"]["file"] = str(example / "main.cwl")
            workflow["config"]["settings"] = str(settings)
        with (build / "streamflow.yml").open("w") as stream:
            yaml.dump(config, stream)
        scratch = project / "runs" / "1000genome" / settings.stem / str(count) / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        commands = [
            ["translate", "--language", "cwl", str(build / "streamflow.yml"),
             "--outdir", str(build)],
            ["compile", str(build / "workflow.swirl"), str(build / "metadata.yml"),
             "--outdir", str(build), "--tmpdir", str(scratch), "--bundle-dependencies"],
        ]
        print(f"Preparing {count} locations: {build}", flush=True)
        with (build / "prepare.log").open("w") as log:
            for command in commands:
                try:
                    subprocess.run([sys.executable, "-m", "swirlc", *command],
                                   stdout=log, stderr=subprocess.STDOUT, check=True)
                except subprocess.CalledProcessError:
                    raise SystemExit(f"Preparation failed; see {build / 'prepare.log'}")
        print(f"Ready (not launched): {build / 'run.sh'}", flush=True)


if __name__ == "__main__":
    main()
