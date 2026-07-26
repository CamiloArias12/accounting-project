from decimal import Decimal

import pytest

from app.modules.vouchers.posting import (
    Amounts,
    PostingError,
    TooFewLines,
    UnbalancedVoucher,
    check_balanced,
    totals,
)


def debit(value: str) -> Amounts:
    return Amounts(debit=Decimal(value), credit=Decimal("0"))


def credit(value: str) -> Amounts:
    return Amounts(debit=Decimal("0"), credit=Decimal(value))


def test_an_entry_that_balances_is_accepted() -> None:
    check_balanced([debit("150000.00"), credit("100000.00"), credit("50000.00")])


def test_an_entry_that_does_not_balance_is_refused() -> None:
    with pytest.raises(UnbalancedVoucher) as raised:
        check_balanced([debit("100.00"), credit("30.00")])

    assert raised.value.difference == Decimal("70.00")
    assert "off by 70.00" in str(raised.value)


def test_an_entry_needs_at_least_two_lines() -> None:
    """Every movement has a counterpart; one line alone is half an operation."""
    with pytest.raises(TooFewLines, match="at least 2 lines"):
        check_balanced([])

    with pytest.raises(TooFewLines, match="has 1"):
        check_balanced([debit("100.00")])


def test_totals_come_back_in_the_order_debit_credit() -> None:
    assert totals([debit("10.00"), credit("4.00"), credit("6.00")]) == (
        Decimal("10.00"),
        Decimal("10.00"),
    )


def test_balancing_is_exact_not_approximate() -> None:
    # The reason money is a Decimal: as floats, 0.1 + 0.2 != 0.3 and this
    # entry would be rejected.
    check_balanced([debit("0.30"), credit("0.10"), credit("0.20")])


def test_a_line_needs_one_of_the_two_columns() -> None:
    with pytest.raises(PostingError, match="either a debit or a credit"):
        Amounts(debit=Decimal("0"), credit=Decimal("0"))


def test_a_line_cannot_be_both_columns_at_once() -> None:
    with pytest.raises(PostingError, match="cannot be both"):
        Amounts(debit=Decimal("10.00"), credit=Decimal("10.00"))


def test_a_negative_amount_is_refused() -> None:
    # A credit is how a negative debit is written; a minus sign in the column
    # would let the same figure be expressed two ways.
    with pytest.raises(PostingError, match="cannot be negative"):
        Amounts(debit=Decimal("-10.00"), credit=Decimal("0"))


def test_more_than_two_decimals_is_refused() -> None:
    with pytest.raises(PostingError, match="two decimals"):
        Amounts(debit=Decimal("10.001"), credit=Decimal("0"))
