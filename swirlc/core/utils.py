from __future__ import annotations

from dataclasses import dataclass

import antlr4

from swirlc.antlr.SWIRLParser import SWIRLParser


@dataclass(frozen=True)
class Term:
    """A payload, pattern or identity from the shared ANTLR frontend."""
    kind: str
    name: str = ""
    items: tuple[Term, ...] = ()

    def __str__(self) -> str:
        if self.kind == "variable":
            return "?" + self.name
        if self.kind == "tuple":
            return "(" + ", ".join(map(str, self.items)) + ")"
        if self.kind == "path":
            return " / ".join(map(str, self.items))
        if self.kind == "collection":
            return f"U({self.name}, ({self.items[0]}, {self.items[1]}))"
        if self.kind == "indexed":
            return f"{self.name}[{self.items[0]}]"
        return self.name

    def to_dict(self) -> dict:
        return {"kind": self.kind, "name": self.name,
                "items": [item.to_dict() for item in self.items]}

    def variables(self) -> set[str]:
        return ({self.name} if self.kind == "variable" else set()).union(
            *(item.variables() for item in self.items)
        )

    @property
    def payload(self) -> Term:
        return self.items[0] if self.kind == "tuple" and len(self.items) == 2 else self

    @property
    def identity(self) -> Term:
        return self.items[1] if self.kind == "tuple" and len(self.items) == 2 else Term("literal", "root")


def get_term(ctx: SWIRLParser.DataContext) -> Term:
    children = list(ctx.getChildren())
    terms = ctx.data()
    text = ctx.getText()
    if any(child.getText() == "/" for child in children):
        parts = tuple(get_term(term) for term in terms)
        return Term("path", items=tuple(part for term in parts
                    for part in (term.items if term.kind == "path" else (term,))))
    if text.startswith("?"):
        return Term("variable", text[1:])
    if text.startswith("("):
        return Term("tuple", items=tuple(get_term(term) for term in terms))
    if "[" in text:
        ids = ctx.ID()
        return Term("indexed", ids[0].getText(), (Term("literal", ids[1].getText()),))
    return Term("literal", text)


def normalize_envelope(term: Term) -> Term:
    return term if term.kind == "tuple" else Term("tuple", items=(term, Term("literal", "root")))


def flatten_list(ll: list) -> list:
    ret = []
    for i in ll:
        if isinstance(i, (list, set)):
            ret.extend(flatten_list(i))
        else:
            ret.append(i)
    return ret


def get_flow(
    ctx: SWIRLParser.ExecContext, dependencies: dict | None = None,
) -> tuple[list[tuple[str, Term]], list[tuple[str, Term]]]:
    return (
        [get_pair(el, dependencies) for el in ctx.flow().dataSet()[0].dataPair()],
        [get_pair(el, dependencies) for el in ctx.flow().dataSet()[1].dataPair()],
    )


def get_pair(ctx: SWIRLParser.DataPairContext, dependencies: dict | None = None) -> tuple[str, Term]:
    if ctx.collection():
        collection = ctx.collection()
        port = get_name(collection.port())
        return port, Term("collection", port, (Term("literal", get_name(collection.name())), get_term(collection.data())))
    port, term = get_name(ctx.port()), get_term(ctx.data())
    if dependencies and term.kind == "literal" and port in dependencies and term.name not in dependencies:
        port, term = term.name, Term("literal", port)
    return port, normalize_envelope(term)


def get_location_set(ctx: SWIRLParser.LocationSetContext) -> set[str]:
    """Return either spelling of a destination set as location names."""
    return {get_name(name) for name in ctx.name()}


def get_name(el: antlr4.ParserRuleContext) -> str:
    if isinstance(el, SWIRLParser.DataContext):
        return el.getText()
    token = getattr(el, "ID", lambda: None)()
    if isinstance(token, antlr4.TerminalNode):
        return token.getText()
    return el.getText()
