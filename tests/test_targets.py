from redfirst import targets

from repos import build


def test_a_function_that_already_does_nothing_is_not_a_target(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        def real(x):
            return x + 1

        def stub():
            pass

        def planned():
            raise NotImplementedError

        def documented():
            """Only a docstring."""
    '''}, {})
    names = {target.qualname for target in targets.collect(repo / "pkg")}
    assert names == {"real"}


def test_dunder_and_abstract_methods_are_skipped(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        import abc

        class Thing:
            def __repr__(self):
                return "Thing()"

            @abc.abstractmethod
            def later(self):
                return 1

            def kept(self):
                return 2
    '''}, {})
    names = {target.qualname for target in targets.collect(repo / "pkg")}
    assert names == {"Thing.kept"}


def test_the_body_starts_after_the_docstring(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        def documented(x):
            """Explains itself."""
            return x * 2
    '''}, {})
    target = targets.collect(repo / "pkg")[0]
    assert target.lineno == 1
    assert target.body_start == 3


def test_generators_are_recognised(tmp_path):
    repo = build(tmp_path, {"m.py": '''
        def counted(items):
            for item in items:
                yield item
    '''}, {})
    assert targets.collect(repo / "pkg")[0].is_generator


def test_test_files_are_not_targets(tmp_path):
    repo = build(tmp_path, {"m.py": "def real():\n    return 1\n"},
                 {"test_m.py": "def helper():\n    return 2\n"})
    paths = {target.path.name for target in targets.collect(repo)}
    assert "test_m.py" not in paths
