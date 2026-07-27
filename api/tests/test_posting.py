"""The rule the whole ledger rests on: debits equal credits, exactly."""

from decimal import Decimal

import pytest

from app.modules.vouchers.posting import (
    Amounts,
    PostingError,
    TooFewLines,
    UnbalancedVoucher,
    check_balanced,
)


def debit(value: str) -> Amounts:
    return Amounts(debit=Decimal(value), credit=Decimal("0"))


def credit(value: str) -> Amounts:
    return Amounts(debit=Decimal("0"), credit=Decimal(value))


def test_an_entry_must_balance() -> None:
    check_balanced([debit("150000.00"), credit("100000.00"), credit("50000.00")])

    with pytest.raises(UnbalancedVoucher) as raised:
        check_balanced([debit("100.00"), credit("30.00")])

    assert raised.value.difference == Decimal("70.00")
    assert "off by 70.00" in str(raised.value)


def test_an_entry_needs_at_least_two_lines() -> None:
    with pytest.raises(TooFewLines, match="at least 2 lines"):
        check_balanced([])

    with pytest.raises(TooFewLines, match="has 1"):
        check_balanced([debit("100.00")])


def test_balancing_is_exact_not_approximate() -> None:
    check_balanced([debit("0.30"), credit("0.10"), credit("0.20")])


def test_a_line_is_one_column_holding_a_positive_amount() -> None:
    with pytest.raises(PostingError, match="either a debit or a credit"):
        Amounts(debit=Decimal("0"), credit=Decimal("0"))

    with pytest.raises(PostingError, match="cannot be both"):
        Amounts(debit=Decimal("10.00"), credit=Decimal("10.00"))

    with pytest.raises(PostingError, match="cannot be negative"):
        Amounts(debit=Decimal("-10.00"), credit=Decimal("0"))

    with pytest.raises(PostingError, match="two decimals"):
        Amounts(debit=Decimal("10.001"), credit=Decimal("0"))
