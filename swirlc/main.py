from __future__ import annotations

import os
import sys

import antlr4

import swirlc.compiler
import swirlc.translator
from swirlc.antlr.SWIRLLexer import SWIRLLexer
from swirlc.antlr.SWIRLParser import SWIRLParser
from swirlc.config.validator import SwirlValidator
from swirlc.core.compiler import CompileVisitor
from swirlc.log_handler import logger
from swirlc.parser import parser


def main(args):
    try:
        args = parser.parse_args(args)
        if args.context == "version":
            from swirlc.version import VERSION

            print(f"swirlc version {VERSION}")
        elif args.context == "compile":
            config = SwirlValidator().validate_file(args.metadata)
            with open(args.workflow) as f:
                code = f.read()
            if args.target in swirlc.compiler.targets:
                target = swirlc.compiler.targets[args.target]()
                lexer = SWIRLLexer(antlr4.InputStream(code))
                tokens = antlr4.CommonTokenStream(lexer)
                tree = SWIRLParser(tokens).workflow()
                visitor = CompileVisitor(compiler=target, metadata=config)
                visitor.visit(tree)
            else:
                raise Exception(f"Target `{args.target}` not supported")
        elif args.context == "translate":
            if args.language in swirlc.translator.translator_classes.keys():
                translator = swirlc.translator.translator_classes[args.language](
                    args.workflow
                )
                if args.outdir:
                    if not os.path.isdir(args.outdir):
                        raise Exception(
                            f"Output directory `{args.outdir}` does not exist"
                        )
                    with open(
                        os.path.join(args.outdir, "workflow.swirl"), "w"
                    ) as workflow_output, open(
                        os.path.join(args.outdir, "metadata.yml"), "w"
                    ) as metadata_output:
                        translator.translate(workflow_output, metadata_output)
                else:
                    translator.translate(sys.stdout, sys.stdout)
            else:
                raise Exception(
                    f"Translator from `{args.language}` to SWIRL not supported"
                )
        else:
            parser.print_help(file=sys.stderr)
            return 1
        return 0
    except SystemExit as se:
        if se.code != 0:
            logger.exception(se)
        return se.code
    except Exception as e:
        logger.exception(e)
        return 1


def run():
    return main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
