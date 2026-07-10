from __future__ import annotations

from typing import Any

from pyjsparser import PyJsParser

SUPPORTED_EXPRESSION_NODES = {
    "ArrayExpression",
    "AssignmentExpression",
    "BinaryExpression",
    "BlockStatement",
    "CallExpression",
    "EmptyStatement",
    "ExpressionStatement",
    "ForStatement",
    "Identifier",
    "Literal",
    "LogicalExpression",
    "MemberExpression",
    "NewExpression",
    "ObjectExpression",
    "Program",
    "Property",
    "ReturnStatement",
    "UnaryExpression",
    "UpdateExpression",
    "VariableDeclaration",
    "VariableDeclarator",
}


def _parse_expression_ast(expression: str, label: str) -> dict[str, Any]:
    """Parse supported CWL JavaScript into an ES5 AST."""
    source = expression.strip()
    if source.startswith("${") and source.endswith("}"):
        body = source[2:-1]
    elif source.startswith("$(") and source.endswith(")"):
        body = f"return ({source[2:-1]});"
    else:
        raise ValueError(f"ExpressionTool {label} has invalid expression syntax")

    try:
        program = PyJsParser().parse(f"function __swirl_expression__() {{{body}}}")
        ast = program["body"][0]["body"]
    except Exception as exc:
        raise ValueError(
            f"ExpressionTool {label} contains invalid JavaScript: {exc}"
        ) from exc

    def validate(value) -> None:
        if isinstance(value, list):
            for item in value:
                validate(item)
            return
        if not isinstance(value, dict):
            return
        node_type = value.get("type")
        if node_type and node_type not in SUPPORTED_EXPRESSION_NODES:
            raise NotImplementedError(
                f"ExpressionTool {label} uses unsupported JavaScript node {node_type}"
            )
        for child in value.values():
            validate(child)

    validate(ast)
    return ast


def translate_expression_to_python(expression: str, label: str) -> str:
    """Translate supported CWL JavaScript into a Python function body."""
    ast = _parse_expression_ast(expression, label)

    def member_key(node: dict[str, Any]) -> str:
        if node.get("computed"):
            return emit_expression(node["property"])
        return repr(node["property"]["name"])

    def emit_target(node: dict[str, Any]) -> str:
        if node["type"] == "Identifier":
            return node["name"]
        if node["type"] == "MemberExpression":
            return f"{emit_expression(node['object'])}[{member_key(node)}]"
        raise NotImplementedError(
            f"ExpressionTool {label} uses unsupported assignment target {node['type']}"
        )

    def emit_expression(node: dict[str, Any] | None) -> str:
        if node is None:
            return "None"
        kind = node["type"]
        if kind == "Literal":
            value = node.get("value")
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            return repr(value)
        if kind == "Identifier":
            names = {"parseInt": "_js_parse_int", "undefined": "None"}
            return names.get(node["name"], node["name"])
        if kind == "ArrayExpression":
            return (
                "["
                + ", ".join(emit_expression(item) for item in node["elements"])
                + "]"
            )
        if kind == "ObjectExpression":
            entries = []
            for prop in node["properties"]:
                key = (
                    prop["key"].get("name")
                    if prop["key"]["type"] == "Identifier"
                    else prop["key"].get("value")
                )
                entries.append(f"{key!r}: {emit_expression(prop['value'])}")
            return "{" + ", ".join(entries) + "}"
        if kind == "MemberExpression":
            obj = node["object"]
            prop = node["property"]
            if (
                not node.get("computed")
                and obj["type"] == "Identifier"
                and obj["name"] == "Math"
            ):
                math_names = {
                    "ceil": "math.ceil",
                    "floor": "math.floor",
                    "min": "min",
                    "max": "max",
                }
                name = prop["name"]
                if name not in math_names:
                    raise NotImplementedError(
                        f"ExpressionTool {label} uses unsupported Math.{name}"
                    )
                return math_names[name]
            return f"_js_get({emit_expression(obj)}, {member_key(node)})"
        if kind == "CallExpression":
            arguments = ", ".join(emit_expression(arg) for arg in node["arguments"])
            return f"{emit_expression(node['callee'])}({arguments})"
        if kind == "NewExpression":
            if node["callee"].get("name") != "Array":
                raise NotImplementedError(
                    f"ExpressionTool {label} only supports new Array(...)"
                )
            arguments = node["arguments"]
            if len(arguments) == 1:
                return f"[None] * int({emit_expression(arguments[0])})"
            return "[" + ", ".join(emit_expression(arg) for arg in arguments) + "]"
        if kind == "BinaryExpression":
            operators = {"===": "==", "!==": "!="}
            supported = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="}
            operator = operators.get(node["operator"], node["operator"])
            if operator not in supported:
                raise NotImplementedError(
                    f"ExpressionTool {label} uses unsupported binary operator {node['operator']}"
                )
            return f"({emit_expression(node['left'])} {operator} {emit_expression(node['right'])})"
        if kind == "LogicalExpression":
            operators = {"&&": "and", "||": "or"}
            operator = operators.get(node["operator"])
            if operator is None:
                raise NotImplementedError(
                    f"ExpressionTool {label} uses unsupported logical operator {node['operator']}"
                )
            return f"({emit_expression(node['left'])} {operator} {emit_expression(node['right'])})"
        if kind == "UnaryExpression":
            operators = {"!": "not ", "+": "+", "-": "-"}
            operator = operators.get(node["operator"])
            if operator is None:
                raise NotImplementedError(
                    f"ExpressionTool {label} uses unsupported unary operator {node['operator']}"
                )
            return f"({operator}{emit_expression(node['argument'])})"
        raise NotImplementedError(
            f"ExpressionTool {label} uses unsupported expression node {kind}"
        )

    def emit_simple_statement(node: dict[str, Any], indent: int) -> list[str]:
        prefix = "    " * indent
        kind = node["type"]
        if kind == "VariableDeclaration":
            return [
                f"{prefix}{declaration['id']['name']} = {emit_expression(declaration.get('init'))}"
                for declaration in node["declarations"]
            ]
        if kind == "AssignmentExpression":
            supported = {"=", "+=", "-=", "*=", "/=", "%="}
            if node["operator"] not in supported:
                raise NotImplementedError(
                    f"ExpressionTool {label} uses unsupported assignment operator {node['operator']}"
                )
            return [
                f"{prefix}{emit_target(node['left'])} {node['operator']} {emit_expression(node['right'])}"
            ]
        if kind == "UpdateExpression":
            if node["operator"] not in ("++", "--"):
                raise NotImplementedError(
                    f"ExpressionTool {label} uses unsupported update operator {node['operator']}"
                )
            operator = "+=" if node["operator"] == "++" else "-="
            return [f"{prefix}{emit_target(node['argument'])} {operator} 1"]
        return [f"{prefix}{emit_expression(node)}"]

    def emit_statement(node: dict[str, Any] | None, indent: int = 0) -> list[str]:
        if node is None or node["type"] == "EmptyStatement":
            return []
        prefix = "    " * indent
        kind = node["type"]
        if kind in ("Program", "BlockStatement"):
            return [
                line
                for statement in node["body"]
                for line in emit_statement(statement, indent)
            ]
        if kind == "VariableDeclaration":
            return emit_simple_statement(node, indent)
        if kind == "ExpressionStatement":
            return emit_simple_statement(node["expression"], indent)
        if kind == "ReturnStatement":
            return [f"{prefix}return {emit_expression(node.get('argument'))}"]
        if kind == "ForStatement":
            lines = emit_statement(node.get("init"), indent)
            test = emit_expression(node.get("test")) if node.get("test") else "True"
            lines.append(f"{prefix}while {test}:")
            body = emit_statement(node["body"], indent + 1)
            update = (
                emit_simple_statement(node["update"], indent + 1)
                if node.get("update")
                else []
            )
            lines.extend(body or [f"{prefix}    pass"])
            lines.extend(update)
            return lines
        raise NotImplementedError(
            f"ExpressionTool {label} uses unsupported statement node {kind}"
        )

    lines = emit_statement(ast)
    if not any(line.lstrip().startswith("return ") for line in lines):
        raise ValueError(f"ExpressionTool {label} does not return a value")
    return "\n".join(lines)
