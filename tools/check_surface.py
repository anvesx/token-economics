"""Public surface check: each package's top-level `__init__.py` says exactly what it exports.

    uv run python tools/check_surface.py

For every existing package, `src/<module>/__init__.py` must define `__all__` as a literal list, every public name
it binds (imported or defined, not starting with `_`) must be in `__all__`, and every name in `__all__` must exist
(bound there, or a submodule of the package). Uses `ast`, so nothing needs to be installed. Exits 1,
one line per problem.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from _layout import ROOT, Layout, existing, load_layout, src_dir


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [n for t in target.elts for n in _target_names(t)]
    return []


def _bound(body: list[ast.stmt], names: set[str], stars: list[int]) -> None:
    """Collect names bound at module level, looking inside if/try/with but not inside functions or classes."""
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            names.update((a.asname or a.name.split(".")[0]) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for a in node.names:
                if a.name == "*":
                    stars.append(node.lineno)
                else:
                    names.add(a.asname or a.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                names.update(_target_names(t))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            names.update(_target_names(node.target))
        elif isinstance(node, ast.If):
            _bound(node.body, names, stars)
            _bound(node.orelse, names, stars)
        elif isinstance(node, ast.Try):
            for part in (node.body, node.orelse, node.finalbody, *[h.body for h in node.handlers]):
                _bound(part, names, stars)
        elif isinstance(node, ast.With):
            _bound(node.body, names, stars)


def _is_all(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "__all__"


def _all_names(body: list[ast.stmt]) -> tuple[list[str] | None, str | None]:
    """The literal value of `__all__` (with `+=` parts added), or an error message."""
    value: list[str] | None = None
    for node in body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, (ast.AnnAssign, ast.AugAssign))
            else []
        )
        expr = getattr(node, "value", None)
        if not any(_is_all(t) for t in targets):
            continue
        if not isinstance(expr, (ast.List, ast.Tuple)) or not all(
            isinstance(e, ast.Constant) and isinstance(e.value, str) for e in expr.elts
        ):
            return None, "__all__ must be a literal list of strings"
        items = [str(e.value) for e in expr.elts if isinstance(e, ast.Constant)]
        value = (value or []) + items if isinstance(node, ast.AugAssign) else items
    return value, None


def check_init(init: Path, rel: str) -> list[str]:
    try:
        tree = ast.parse(init.read_text(), filename=str(init))
    except SyntaxError as exc:
        return [f"{rel}:{exc.lineno}: cannot parse ({exc.msg})"]
    exported, error = _all_names(tree.body)
    if error:
        return [f"{rel}: {error}"]
    if exported is None:
        return [f"{rel}: no __all__ defined"]
    bound: set[str] = set()
    stars: list[int] = []
    _bound(tree.body, bound, stars)
    problems = [f"{rel}:{line}: star import hides the public surface" for line in stars]
    submodules = {p.stem for p in init.parent.iterdir() if p.suffix == ".py" or (p / "__init__.py").exists()}
    public = sorted(n for n in bound if not n.startswith("_"))
    problems += [f"{rel}: public name {n} is not in __all__" for n in public if n not in exported]
    problems += [f"{rel}: __all__ lists {n}, which does not exist" for n in exported if n not in bound | submodules]
    return problems


def check(layout: Layout, root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for key in existing(layout, root):
        init = src_dir(layout, key, root) / "__init__.py"
        rel = init.relative_to(root).as_posix()
        if not init.is_file():
            problems.append(f"{rel}: missing")
            continue
        problems += check_init(init, rel)
    return problems


def main() -> int:
    problems = check(load_layout())
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
