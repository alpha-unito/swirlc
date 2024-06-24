from __future__ import annotations

import antlr4

from swirlc.antlr.SWIRLParser import SWIRLParser


def flatten_list(ll: list) -> list:
    ret = []
    for i in ll:
        if isinstance(i, (list, set)):
            ret.extend(flatten_list(i))
        else:
            ret.append(i)
    return ret


def get_flow(
    ctx: SWIRLParser.ExecContext,
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    return (
        {get_pair(el) for el in ctx.flow().dataSet()[0].dataPair()},
        {get_pair(el) for el in ctx.flow().dataSet()[1].dataPair()},
    )


def get_pair(ctx: SWIRLParser.DataPairContext) -> tuple[str, str]:
    return (get_name(ctx.port()), get_name(ctx.data()))


def get_name(el: antlr4.ParserRuleContext) -> str:
    return el.ID().getText()
