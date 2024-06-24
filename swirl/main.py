import os
import sys

import antlr4

import swirl.compiler
import swirl.translator
from swirl.antlr.SWIRLLexer import SWIRLLexer
from swirl.antlr.SWIRLParser import SWIRLParser
from swirl.config.validator import SwirlValidator
from swirl.core.compiler import CompileVisitor
from swirl.log_handler import logger
from swirl.parser import parser


def main(args):
    try:
        args = parser.parse_args(args)
        if args.context == "version":
            from swirl.version import VERSION

            print(f"swirl version {VERSION}")
        elif args.context == "compile":
            config = SwirlValidator().validate_file(args.metadata)
            with open(args.workflow) as f:
                code = f.read()
            if args.target in swirl.compiler.targets:
                target = swirl.compiler.targets[args.target]()
                lexer = SWIRLLexer(antlr4.InputStream(code))
                tokens = antlr4.CommonTokenStream(lexer)
                tree = SWIRLParser(tokens).workflow()
                visitor = CompileVisitor(compiler=target, metadata=config)
                visitor.visit(tree)
            else:
                raise Exception(f"Target `{args.target}` not supported")
        elif args.context == "translate":
            if args.language in swirl.translator.translator_classes.keys():
                translator = swirl.translator.translator_classes[args.language](
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
