"""The functions worth asking about, straight from the source.

A target is a function we can empty out without rewriting anything else. Everything here is
syntax: no imports are executed, so a repository that cannot be imported can still be listed.
"""
import ast
import dataclasses
import pathlib

# Emptying these tells you nothing. A missing __repr__ or a missing log line is not a defect the
# suite should be expected to notice, and reporting them buries the findings that matter.
SKIP_NAMES = {"__repr__", "__str__", "__format__", "__hash__", "__del__", "__enter__", "__exit__"}
SKIP_DECORATORS = {"abstractmethod", "abstractproperty", "overload", "setter", "deleter"}


@dataclasses.dataclass
class Target:
    path: pathlib.Path
    qualname: str
    lineno: int           # the `def` line
    body_start: int       # first statement that is not the docstring
    body_end: int
    is_generator: bool
    display: str = ""

    @property
    def label(self):
        return f"{self.display or self.path}:{self.lineno} {self.qualname}"

    def covers(self, line):
        return self.body_start <= line <= self.body_end


def decorator_names(node):
    names = set()
    for decorator in node.decorator_list:
        current = decorator.func if isinstance(decorator, ast.Call) else decorator
        while isinstance(current, ast.Attribute):
            names.add(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            names.add(current.id)
    return names


def is_generator(node):
    for child in ast.walk(node):
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def body_without_docstring(node):
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def trivial(body):
    """A function that already does nothing cannot be made to do less."""
    if not body:
        return True
    if len(body) == 1:
        only = body[0]
        if isinstance(only, ast.Pass):
            return True
        if isinstance(only, ast.Raise):        # a stub that raises NotImplementedError
            return True
        if isinstance(only, ast.Return) and (only.value is None or (
                isinstance(only.value, ast.Constant) and only.value.value is None)):
            return True
    return False


def collect(root, ignore=("tests", "test", ".venv", "build", "dist")):
    """Every function in `root` that is worth gutting, in file order."""
    root = pathlib.Path(root)
    found = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in ignore or part.startswith(".") for part in relative.parts):
            continue
        if relative.name.startswith("test_") or relative.name.endswith("_test.py"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        found.extend(_walk(tree, path))
    return found


def _walk(tree, path, prefix=""):
    found = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            found.extend(_walk(node, path, f"{prefix}{node.name}."))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = f"{prefix}{node.name}"
            body = body_without_docstring(node)
            if node.name in SKIP_NAMES or decorator_names(node) & SKIP_DECORATORS or trivial(body):
                continue
            found.append(Target(
                path=path, qualname=qualname, lineno=node.lineno,
                body_start=body[0].lineno, body_end=node.end_lineno,
                is_generator=is_generator(node)))
            # nested functions are mutated with their parent, not separately
    return found
