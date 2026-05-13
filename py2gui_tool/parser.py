from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ArgumentSpec:
    name: str
    kind: str  # positional, option, flag
    option_strings: List[str] = field(default_factory=list)
    default: Optional[str] = None
    help: str = ""
    required: bool = False
    choices: List[str] = field(default_factory=list)
    value_type: str = "str"
    action: Optional[str] = None


@dataclass
class ScriptSpec:
    script_path: str
    script_type: str
    arguments: List[ArgumentSpec]


def parse_script(source: str, script_path: str = "") -> ScriptSpec:
    tree = ast.parse(source)
    if _looks_like_click(tree):
        return ScriptSpec(script_path=script_path, script_type="click", arguments=_parse_click(tree))
    if _looks_like_typer(tree):
        return ScriptSpec(script_path=script_path, script_type="typer", arguments=_parse_typer(tree))
    return ScriptSpec(script_path=script_path, script_type="argparse", arguments=_parse_argparse(tree))


def _looks_like_click(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "click":
            return True
        if isinstance(node, ast.Attribute) and _attr_name(node) == "click":
            return True
    return False


def _looks_like_typer(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "typer":
            return True
        if isinstance(node, ast.Attribute) and _attr_name(node) == "typer":
            return True
    return False


def _parse_argparse(tree: ast.AST) -> List[ArgumentSpec]:
    args: List[ArgumentSpec] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            specs = _parse_add_argument(node)
            args.extend(specs)
    return args


def _parse_add_argument(node: ast.Call) -> List[ArgumentSpec]:
    names = [_literal_string(arg) for arg in node.args if _literal_string(arg) is not None]
    option_strings = [name for name in names if name.startswith("-")]
    positional_names = [name for name in names if not name.startswith("-")]
    kw = _keywords_map(node)
    action = _keyword_string(kw.get("action"))
    default = _literal_to_text(kw.get("default"))
    value_type = _infer_type_name(kw.get("type"))
    help_text = _literal_to_text(kw.get("help")) or ""
    required = _keyword_bool(kw.get("required"))
    choices = _literal_choices(kw.get("choices"))

    if positional_names and not option_strings:
        name = positional_names[0].lstrip("<>").replace("-", "_")
        return [ArgumentSpec(name=name, kind="positional", default=default, help=help_text, required=required, choices=choices, value_type=value_type, action=action)]

    if not option_strings and names:
        name = names[0].lstrip("-").replace("-", "_")
        return [ArgumentSpec(name=name, kind="option", default=default, help=help_text, required=required, choices=choices, value_type=value_type, action=action)]

    dest = _keyword_string(kw.get("dest"))
    if not dest:
        for opt in option_strings:
            if opt.startswith("--"):
                dest = opt[2:].replace("-", "_")
                break
        if not dest and option_strings:
            dest = option_strings[0].lstrip("-").replace("-", "_")
    kind = "flag" if action in {"store_true", "store_false"} else "option"
    return [ArgumentSpec(
        name=dest or "option",
        kind=kind,
        option_strings=option_strings,
        default=default,
        help=help_text,
        required=required,
        choices=choices,
        value_type="bool" if kind == "flag" else value_type,
        action=action,
    )]


def _parse_click(tree: ast.AST) -> List[ArgumentSpec]:
    args: List[ArgumentSpec] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if any(_is_click_command(deco) for deco in node.decorator_list):
                for deco in node.decorator_list:
                    spec = _parse_click_decorator(deco)
                    if spec:
                        args.append(spec)
                if not args:
                    args.extend(_parse_function_signature(node))
                break
    return args


def _parse_click_decorator(node: ast.AST) -> Optional[ArgumentSpec]:
    if not isinstance(node, ast.Call):
        return None
    func_name = _attr_name(node.func) or _name(node.func)
    if func_name == "click.option":
        names = [_literal_string(arg) for arg in node.args if _literal_string(arg) is not None]
        option_strings = [name for name in names if name.startswith("-")]
        kw = _keywords_map(node)
        action = _keyword_string(kw.get("is_flag"))
        default = _literal_to_text(kw.get("default"))
        value_type = _infer_type_name(kw.get("type"))
        choices = _literal_choices(kw.get("type"))
        dest = _keyword_string(kw.get("name")) or _keyword_string(kw.get("param_decls"))
        if not dest:
            for opt in option_strings:
                if opt.startswith("--"):
                    dest = opt[2:].replace("-", "_")
                    break
        if not dest and option_strings:
            dest = option_strings[0].lstrip("-").replace("-", "_")
        return ArgumentSpec(
            name=dest or "option",
            kind="flag" if _keyword_bool(kw.get("is_flag")) else "option",
            option_strings=option_strings,
            default=default,
            value_type="bool" if _keyword_bool(kw.get("is_flag")) else value_type,
            choices=choices,
        )
    if func_name == "click.argument":
        names = [_literal_string(arg) for arg in node.args if _literal_string(arg) is not None]
        name = names[0] if names else _keyword_string(_keywords_map(node).get("name")) or "argument"
        kw = _keywords_map(node)
        default = _literal_to_text(kw.get("default"))
        return ArgumentSpec(name=name.replace("-", "_"), kind="positional", default=default)
    return None


def _parse_typer(tree: ast.AST) -> List[ArgumentSpec]:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if any(_is_typer_command(deco) for deco in node.decorator_list):
                return _parse_typer_function(node)
    return []


def _parse_typer_function(node: ast.FunctionDef) -> List[ArgumentSpec]:
    args: List[ArgumentSpec] = []
    for arg in node.args.args:
        default = None
        kind = "option"
        value_type = "str"
        if node.args.defaults:
            default_index = len(node.args.args) - len(node.args.defaults)
            arg_index = node.args.args.index(arg)
            if arg_index >= default_index:
                default_node = node.args.defaults[arg_index - default_index]
                if isinstance(default_node, ast.Call):
                    call_name = _attr_name(default_node.func) or _name(default_node.func)
                    kw = _keywords_map(default_node)
                    default = _literal_to_text(kw.get("default"))
                    if call_name == "typer.Argument":
                        kind = "positional"
                    if _keyword_bool(kw.get("is_flag")):
                        kind = "flag"
                        value_type = "bool"
                    if kw.get("help"):
                        pass
                else:
                    default = _literal_to_text(default_node)
        if default is None:
            default = None
        args.append(ArgumentSpec(
            name=arg.arg,
            kind=kind,
            option_strings=[f"--{arg.arg.replace('_', '-')}"] if kind != "positional" else [],
            default=default,
            value_type=value_type,
        ))
    return args


def _parse_function_signature(node: ast.FunctionDef) -> List[ArgumentSpec]:
    args: List[ArgumentSpec] = []
    for arg in node.args.args:
        args.append(ArgumentSpec(name=arg.arg, kind="option", option_strings=[f"--{arg.arg.replace('_', '-')}"]))
    return args


def _is_click_command(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return (_attr_name(node.func) or _name(node.func)) in {"click.command", "click.group"}


def _is_typer_command(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func_name = _attr_name(node.func) or _name(node.func)
    return func_name in {"app.command", "typer.command", "app.callback", "typer.Typer"}


def _attr_name(node: ast.AST) -> Optional[str]:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _name(node: ast.AST) -> Optional[str]:
    return node.id if isinstance(node, ast.Name) else None


def _keywords_map(node: ast.Call) -> dict:
    return {kw.arg: kw.value for kw in node.keywords if kw.arg}


def _literal_string(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_to_text(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.List):
        return ", ".join(_literal_to_text(elt) or "" for elt in node.elts)
    if isinstance(node, ast.Tuple):
        return ", ".join(_literal_to_text(elt) or "" for elt in node.elts)
    return None


def _keyword_string(node: Optional[ast.AST]) -> Optional[str]:
    return _literal_to_text(node)


def _keyword_bool(node: Optional[ast.AST]) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return False


def _literal_choices(node: Optional[ast.AST]) -> List[str]:
    if isinstance(node, ast.List):
        return [text for text in (_literal_to_text(elt) for elt in node.elts) if text is not None]
    if isinstance(node, ast.Tuple):
        return [text for text in (_literal_to_text(elt) for elt in node.elts) if text is not None]
    return []


def _infer_type_name(node: Optional[ast.AST]) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "str"
