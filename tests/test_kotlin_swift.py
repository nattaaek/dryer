from pathlib import Path

import pytest

from dryer.discover import iter_source_files, language_of
from dryer.extract import entries_in_source
from dryer.scan import find_duplicates


@pytest.mark.parametrize('language,extension', [('kotlin', 'kt'), ('kotlin', 'kts'), ('swift', 'swift')])
def test_discovery(language, extension, tmp_path):
    source = tmp_path / f'Production.{extension}'
    source.write_text('')
    assert language_of(source) == language
    assert iter_source_files([tmp_path]) == [source]


def entries(language, source):
    result, warning = entries_in_source(language, source, 'sample', 'sample')
    assert warning is None
    return result


@pytest.mark.parametrize('language,source', [
    ('kotlin', '''interface Shape { fun declared(): Int }
fun outer(x: Int): Int {
    fun nested() = 1
    return nested() + x
}
class Box {
    fun member(x: Int) = x + 1
}
'''),
    ('swift', '''protocol Shape { func declared() -> Int }
func outer(_ x: Int) -> Int {
    func nested() -> Int { 1 }
    return nested() + x
}
struct Box {
    func member(_ x: Int) -> Int { x + 1 }
}
'''),
])
def test_body_functions_methods_and_nested_boundaries(language, source):
    assert [(e.start_line, e.end_line) for e in entries(language, source)] == [(2, 5), (7, 7)]


@pytest.mark.parametrize('language,source', [
    ('kotlin', '''fun alpha(xs: List<Int>): Int {
    val ys = xs.filter { it > 2 }
    return ys.count()
}
fun beta(items: List<Int>): Int {
    val kept = items.filter { it > 9 }
    return kept.count()
}
'''),
    ('swift', '''func alpha(_ xs: [Int]) -> Int {
    let ys = xs.filter { $0 > 2 }
    return ys.count
}
func beta(_ items: [Int]) -> Int {
    let kept = items.filter { $0 > 9 }
    return kept.count
}
'''),
])
def test_real_fixtures_match_renamed_locals_and_preserve_calls(language, source):
    found = entries(language, source)
    assert len(found) == 2
    assert find_duplicates(found, 0.99)[0].score == 1.0
    assert 'filter' in ' '.join(found[0].fingerprints)
    changed = entries(language, source.replace('.filter', '.select', 1))
    assert find_duplicates(changed, 0.0)[0].score < 1.0


@pytest.mark.parametrize('language,source', [
    ('kotlin', 'fun alpha(x: Int) = x + 1\nfun beta(y: Int) = y - 1\n'),
    ('swift', 'func alpha(_ x: Int) -> Int { x + 1 }\nfunc beta(_ y: Int) -> Int { y - 1 }\n'),
])
def test_operators_stay_distinct(language, source):
    assert find_duplicates(entries(language, source), 0.0)[0].score < 1.0


@pytest.mark.parametrize('language,source', [
    ('kotlin', 'fun alpha(x: Int) = "plain"\nfun beta(y: Int) = "value $y"\n'),
    ('swift', 'func alpha(_ x: Int) -> String { "plain" }\nfunc beta(_ y: Int) -> String { "value \\(y)" }\n'),
])
def test_interpolation_is_not_erased(language, source):
    assert find_duplicates(entries(language, source), 0.0)[0].score < 1.0


def test_build_and_test_directories_are_skipped(tmp_path):
    for directory in ['.build', '.swiftpm', '.gradle', 'Tests', 'src/test', 'src/androidTest', 'src/commonTest']:
        target = tmp_path / directory / 'Sample.kt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('fun sample() = 1')
    assert iter_source_files([tmp_path]) == []


@pytest.mark.parametrize('language,fixture', [('kotlin', 'kotlin/Duplicates.kt'), ('swift', 'swift/Duplicates.swift')])
def test_shipped_fixtures_are_valid_and_report_duplicates(language, fixture):
    from dryer.treesitter import parse

    source = (Path(__file__).parents[1] / 'examples' / fixture).read_text()
    assert not parse(source, language)[1].root_node.has_error
    result = entries(language, source)
    assert [(e.start_line, e.end_line) for e in result] == [(1, 4), (6, 9)]
    assert find_duplicates(result, 0.99)[0].score == 1.0


def test_kotlin_extension_and_swift_extension_methods():
    assert len(entries('kotlin', 'fun String.trimmed(): String = trim()\n')) == 1
    assert len(entries('swift', 'extension String { func trimmed() -> String { self.lowercased() } }')) == 1
