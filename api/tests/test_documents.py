import pytest

from app.modules.third_parties.documents import (
    DocumentType,
    InvalidDocument,
    compute_check_digit,
    normalize_document,
    requires_check_digit,
    validate_check_digit,
)


@pytest.mark.parametrize(
    ("nit", "expected"),
    [
        # Real NIT/DV pairs, so the weight table is checked against something
        # other than itself.
        ("800197268", 4),  # DIAN
        ("890903938", 8),  # Bancolombia
    ],
)
def test_check_digit_matches_real_nits(nit: str, expected: int) -> None:
    assert compute_check_digit(nit) == expected


@pytest.mark.parametrize(
    "nit", ["1", "10", "900123456", "9001234567", "123456789012345"]
)
def test_check_digit_is_always_a_single_digit(nit: str) -> None:
    assert compute_check_digit(nit) in range(10)


def test_check_digit_ignores_formatting() -> None:
    assert compute_check_digit("800.197.268") == compute_check_digit("800197268")


def test_validate_check_digit_rejects_a_wrong_one() -> None:
    with pytest.raises(InvalidDocument, match="is 4, not 9"):
        validate_check_digit("800197268", 9)


def test_validate_check_digit_returns_the_digit_it_accepted() -> None:
    assert validate_check_digit("800197268", 4) == 4


def test_only_the_nit_carries_a_check_digit() -> None:
    assert requires_check_digit(DocumentType.NIT)
    assert not requires_check_digit(DocumentType.CITIZEN_ID)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  1.020.304  ", "1020304"),
        ("1 020 304", "1020304"),
        ("1020304", "1020304"),
    ],
)
def test_normalize_strips_separators_and_spacing(raw: str, expected: str) -> None:
    assert normalize_document(raw, DocumentType.CITIZEN_ID) == expected


def test_a_passport_may_hold_letters() -> None:
    assert normalize_document("ab123456", DocumentType.PASSPORT) == "AB123456"


def test_a_citizen_id_may_not_hold_letters() -> None:
    with pytest.raises(InvalidDocument, match="digits only"):
        normalize_document("AB123456", DocumentType.CITIZEN_ID)


def test_a_number_with_the_check_digit_attached_is_refused() -> None:
    # Silently splitting it would store a different number than the one typed.
    with pytest.raises(InvalidDocument, match="must not include the check digit"):
        normalize_document("900123456-7", DocumentType.NIT)


def test_an_empty_document_is_refused() -> None:
    with pytest.raises(InvalidDocument, match="cannot be empty"):
        normalize_document("   ", DocumentType.CITIZEN_ID)


def test_a_nit_longer_than_the_weight_table_is_refused() -> None:
    with pytest.raises(InvalidDocument, match="cannot exceed 15 digits"):
        normalize_document("1" * 16, DocumentType.NIT)
