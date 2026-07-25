import pytest

from app.domain.puc import (
    AccountLevel,
    InvalidAccountCode,
    ancestors_of,
    depth_of,
    level_of,
    parent_code_of,
    validate_code,
)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("1", AccountLevel.CLASS),
        ("11", AccountLevel.GROUP),
        ("1105", AccountLevel.ACCOUNT),
        ("110505", AccountLevel.SUBACCOUNT),
        ("11050501", AccountLevel.AUXILIARY),
        ("1105050101", AccountLevel.AUXILIARY),
    ],
)
def test_level_derives_from_code_length(code: str, expected: AccountLevel) -> None:
    assert level_of(code) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("1", None),
        ("11", "1"),
        ("1105", "11"),
        ("110505", "1105"),
        ("11050501", "110505"),
        ("1105050199", "110505"),
    ],
)
def test_parent_is_the_code_prefix(code: str, expected: str | None) -> None:
    assert parent_code_of(code) == expected


def test_ancestors_go_from_class_to_direct_parent() -> None:
    assert ancestors_of("11050501") == ["1", "11", "1105", "110505"]


def test_class_has_no_ancestors() -> None:
    assert ancestors_of("1") == []


@pytest.mark.parametrize(
    ("code", "expected"),
    [("1", 0), ("11", 1), ("1105", 2), ("110505", 3), ("11050501", 4)],
)
def test_depth_counts_ancestors(code: str, expected: int) -> None:
    assert depth_of(code) == expected


@pytest.mark.parametrize("code", ["", "   ", "11a", "1.5", "-1", "1 1"])
def test_rejects_non_numeric_codes(code: str) -> None:
    with pytest.raises(InvalidAccountCode):
        validate_code(code)


@pytest.mark.parametrize("code", ["110", "11050"])
def test_rejects_lengths_with_no_level(code: str) -> None:
    with pytest.raises(InvalidAccountCode):
        validate_code(code)


def test_rejects_codes_that_are_too_long() -> None:
    with pytest.raises(InvalidAccountCode):
        validate_code("1" * 21)


def test_strips_surrounding_whitespace() -> None:
    assert validate_code("  1105  ") == "1105"
