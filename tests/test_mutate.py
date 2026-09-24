from redfirst import mutate, targets

from repos import build


def test_the_signature_and_docstring_survive_and_the_body_does_not(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        def shout(text):
            """Loudly."""
            return text.upper() + "!"
    '''})
    target = targets.collect(repo / "pkg")[0]
    original = target.path.read_text()
    with mutate.emptied(target):
        mutated = target.path.read_text()
    assert "def shout(text):" in mutated
    assert '"""Loudly."""' in mutated
    assert "upper" not in mutated
    assert "return None" in mutated
    assert target.path.read_text() == original


def test_a_generator_stays_a_generator(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        def counted(items):
            for item in items:
                yield item
    '''})
    target = targets.collect(repo / "pkg")[0]
    with mutate.emptied(target):
        assert "yield from ()" in target.path.read_text()


def test_the_file_is_restored_even_when_the_block_raises(tmp_path):
    repo = build(tmp_path, {"m.py": "def real():\n    return 1\n"})
    target = targets.collect(repo / "pkg")[0]
    original = target.path.read_text()
    try:
        with mutate.emptied(target):
            raise RuntimeError("the test run blew up")
    except RuntimeError:
        pass
    assert target.path.read_text() == original


def test_indentation_follows_the_function(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        class Thing:
            def method(self):
                return 42
    '''})
    target = targets.collect(repo / "pkg")[0]
    with mutate.emptied(target):
        assert "        return None" in target.path.read_text()
