"""Give the function's body away, and put it back.

One function at a time, always restored in a `finally`. The signature, the decorators and the
docstring stay exactly where they were, so line numbers above the body do not move and the rest of
the file is untouched.
"""
import contextlib


def replacement_for(target, indent):
    # A generator whose body is replaced by `return None` stops being a generator, and every
    # caller then fails for the wrong reason. An empty `yield from` keeps the shape and removes
    # the behaviour, which is the question being asked.
    statement = "yield from ()" if target.is_generator else "return None"
    return f"{' ' * indent}{statement}\n"


def indent_of(line):
    return len(line) - len(line.lstrip())


@contextlib.contextmanager
def emptied(target):
    """Rewrite the target's body to do nothing for the duration of the block."""
    original = target.path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    first = lines[target.body_start - 1]
    mutated = (lines[:target.body_start - 1]
               + [replacement_for(target, indent_of(first))]
               + lines[target.body_end:])
    try:
        target.path.write_text("".join(mutated), encoding="utf-8")
        yield
    finally:
        target.path.write_text(original, encoding="utf-8")
