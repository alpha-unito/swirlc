from __future__ import annotations

import argparse

import swirlc.compiler
import swirlc.translator

parser = argparse.ArgumentParser(description="SWIRL command line")
subparsers = parser.add_subparsers(dest="context")

# Swirl compile
compile_parser = subparsers.add_parser(
    "compile", help="Compile a swirl file into a target workflow execution program"
)
compile_parser.add_argument(
    "workflow",
    metavar="SWIRL_FILE",
    type=str,
    help="Path to the SWIRL file describing the workflow execution",
)
compile_parser.add_argument(
    "metadata", metavar="METADATA_FILE", type=str, help="Path to the metadata file"
)
compile_parser.add_argument(
    "--target",
    "-t",
    type=str,
    default="default",
    choices=swirlc.compiler.targets,
    help="The compilation target",
)

# Swirl translator
translate_parser = subparsers.add_parser(
    "translate",
    help="Translate a workflow written in different language into a SWIRL workflow",
)
translate_parser.add_argument(
    "--language",
    "-l",
    type=str,
    required=True,
    choices=swirlc.translator.translator_classes,
    help="The workflow language",
)
translate_parser.add_argument(
    "workflow",
    metavar="WORKFLOW",
    type=str,
    help="Workflow definition. It can be a file path or a directory path or string",
)
translate_parser.add_argument(
    "--outdir",
    "-o",
    type=str,
    help="Output directory path. It will be create two files: `workflow.swirl` and `metadata.yml`",
    default="",
)

# Swirl version
version_parser = subparsers.add_parser(
    "version", help="Only print SWIRL version and exit"
)
