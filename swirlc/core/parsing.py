from __future__ import annotations

import antlr4
from antlr4.error.ErrorListener import ErrorListener

from swirlc.antlr.SWIRLLexer import SWIRLLexer
from swirlc.antlr.SWIRLParser import SWIRLParser


class _Errors(ErrorListener):
    def __init__(self) -> None:
        self.messages: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.messages.append(f"{line}:{column}: {msg}")


def parse_workflow(source: str) -> SWIRLParser.WorkflowContext:
    """Parse SWIRL without allowing ANTLR recovery errors into compilation."""
    errors = _Errors()
    lexer = SWIRLLexer(antlr4.InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(errors)
    tokens = antlr4.CommonTokenStream(lexer)
    parser = SWIRLParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(errors)
    tree = parser.workflow()
    if errors.messages:
        raise ValueError("Invalid SWIRL:\n" + "\n".join(errors.messages))
    return tree
