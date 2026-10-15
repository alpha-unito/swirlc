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


def parse_term(source: str):
    """Parse a metadata identity with the same syntax and errors as SWIRL."""
    from swirlc.core.utils import get_term

    errors = _Errors()
    lexer = SWIRLLexer(antlr4.InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(errors)
    tokens = antlr4.CommonTokenStream(lexer)
    parser = SWIRLParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(errors)
    term = parser.data(0)
    if errors.messages or tokens.LA(1) != antlr4.Token.EOF:
        raise ValueError(f"Invalid SWIRL identity: {source}")
    return get_term(term)


def validate_bindings(tree: SWIRLParser.WorkflowContext, conditions: dict | None = None) -> None:
    """Check lexical construction and nearest replication ownership."""
    from swirlc.core.utils import get_flow, get_term, normalize_envelope

    def reject_legacy(term):
        if term.kind == "indexed":
            raise ValueError("Legacy indexed scatter is unsupported; use scoped identity envelopes")
        for item in term.items:
            reject_legacy(item)

    def require(term, bound, context):
        reject_legacy(term)
        missing = term.variables() - bound
        if missing:
            raise ValueError(f"Unbound variables {sorted(missing)} in {context}")

    def walk(ctx, bound, replicated=False):
        bound = set(bound)
        if isinstance(ctx, SWIRLParser.TraceParenContext):
            return walk(ctx.trace(), bound, replicated)
        if isinstance(ctx, SWIRLParser.TraceReplContext):
            walk(ctx.trace(), bound, True)
            return bound
        if isinstance(ctx, SWIRLParser.TraceOpContext):
            if ctx.op.type == SWIRLParser.SEQ:
                return walk(ctx.trace(1), walk(ctx.trace(0), bound, replicated), replicated)
            if ctx.guard() and ctx.guard().data():
                require(get_term(ctx.guard().data()), bound, "choice guard")
            elif ctx.guard() and conditions is not None:
                name = ctx.guard().port().getText()
                if name not in conditions:
                    raise ValueError(f"Unknown condition {name}")
                descriptor = conditions[name]
                if descriptor["type"] == "has_data":
                    require(parse_term(descriptor["scope"]), bound, f"condition {name}")
            left = walk(ctx.trace(0), bound, replicated)
            right = walk(ctx.trace(1), bound, replicated)
            return left & right if ctx.op.type == SWIRLParser.CHOICE else left | right
        if isinstance(ctx, SWIRLParser.TracePredContext):
            pred = ctx.pred()
            if pred.end():
                if not replicated:
                    raise ValueError("end() has no enclosing replication owner")
            elif pred.exec():
                inputs, outputs = get_flow(pred.exec())
                for _, term in inputs:
                    require(term, bound, "exec input")
                for _, term in outputs:
                    identity = term.items[1] if term.kind == "collection" else term.identity
                    require(identity, bound, "exec output identity")
                    if term.kind != "collection":
                        bound.update(term.payload.variables())
            else:
                action = pred.recv() or pred.move() or pred.send()
                term = normalize_envelope(get_term(action.data()))
                reject_legacy(term)
                if pred.recv() or pred.move():
                    if term.identity.kind == "path":
                        for prefix in term.identity.items[:-1]:
                            require(prefix, bound, "receive/move identity prefix")
                    bound.update(term.variables())
                else:
                    require(term, bound, "send")
        return bound

    for location in tree.location():
        for pair in location.dataSet().dataPair():
            if pair.collection():
                raise ValueError("Initial dataset cannot contain a collection")
            require(get_term(pair.data()), set(), "initial dataset")
        walk(location.trace(), set())
