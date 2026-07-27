from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.modules.accounts.puc import MAX_CODE_LENGTH
from app.modules.periods.period import AccountingPeriod
from app.modules.vouchers.errors import (
    VoucherAlreadyReversed,
    VoucherIsReversal,
    VoucherNotEditable,
    VoucherNotPosted,
)
from app.modules.vouchers.posting import (
    ZERO,
    Amounts,
    VoucherStatus,
    check_balanced,
    totals,
)
from app.shared.database import Base, TimestampMixin

MONEY = Numeric(18, 2)


class Voucher(Base, TimestampMixin):
    """The accounting voucher and its lines."""
    __tablename__ = "vouchers"
    __table_args__ = (
        UniqueConstraint("number", name="uq_vouchers_number"),
        CheckConstraint(
            "period_month BETWEEN 1 AND 12", name="ck_vouchers_period_month"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int | None] = mapped_column(default=None)

    date: Mapped[dt.date] = mapped_column(Date, index=True)
    period_year: Mapped[int] = mapped_column(index=True)
    period_month: Mapped[int] = mapped_column(index=True)

    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[VoucherStatus] = mapped_column(
        Enum(VoucherStatus, name="voucher_status", native_enum=False, length=20),
        default=VoucherStatus.DRAFT,
        index=True,
    )
    posted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None, index=True
    )
    posted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None
    )

    reverses_voucher_id: Mapped[int | None] = mapped_column(
        ForeignKey("vouchers.id", ondelete="RESTRICT"),
        unique=True,
        default=None,
    )

    lines: Mapped[list[VoucherLine]] = relationship(
        back_populates="voucher",
        cascade="all, delete-orphan",
        order_by="VoucherLine.line_number",
        lazy="selectin",
    )

    if TYPE_CHECKING:
        reversed_by_voucher_id: Mapped[int | None]

    @classmethod
    def open(
        cls,
        *,
        date: dt.date,
        description: str,
        period: AccountingPeriod | None = None,
        created_by_user_id: int | None = None,
    ) -> Voucher:
        resolved = period or AccountingPeriod.of(date)

        return cls(
            date=date,
            period_year=resolved.year,
            period_month=resolved.month,
            description=description.strip(),
            status=VoucherStatus.DRAFT,
            created_by_user_id=created_by_user_id,
        )

    @property
    def period(self) -> AccountingPeriod:
        return AccountingPeriod(year=self.period_year, month=self.period_month)

    @property
    def is_posted(self) -> bool:
        return self.status is VoucherStatus.POSTED

    @property
    def is_reversal(self) -> bool:
        return self.reverses_voucher_id is not None

    @property
    def is_reversed(self) -> bool:
        return self.reversed_by_voucher_id is not None

    @property
    def is_editable(self) -> bool:
        return not self.is_posted

    @property
    def total_debit(self) -> Decimal:
        return totals(self._amounts())[0]

    @property
    def total_credit(self) -> Decimal:
        return totals(self._amounts())[1]

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def require_editable(self) -> None:
        if self.is_posted:
            raise VoucherNotEditable(self.id)

    def require_balanced(self) -> None:
        check_balanced(self._amounts())

    def post(self, number: int, *, user_id: int | None = None) -> None:
        self.require_editable()
        self.require_balanced()

        self.number = number
        self.status = VoucherStatus.POSTED
        self.posted_by_user_id = user_id
        self.posted_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)

    def require_reversible(self) -> None:
        if not self.is_posted:
            raise VoucherNotPosted(self.id)
        if self.is_reversal:
            raise VoucherIsReversal(self.id)
        if self.reversed_by_voucher_id is not None:
            raise VoucherAlreadyReversed(self.id, self.reversed_by_voucher_id)

    def reversal(
        self,
        *,
        date: dt.date,
        description: str,
        period: AccountingPeriod | None = None,
        user_id: int | None = None,
    ) -> Voucher:
        undo = Voucher.open(
            date=date,
            description=description,
            period=period,
            created_by_user_id=user_id,
        )
        undo.reverses_voucher_id = self.id
        undo.lines = [
            VoucherLine.write(
                line_number=line.line_number,
                account_code=line.account_code,
                third_party_id=line.third_party_id,
                debit=line.credit,
                credit=line.debit,
                description=line.description,
            )
            for line in self.lines
        ]
        return undo

    def _amounts(self) -> list[Amounts]:
        return [Amounts(debit=line.debit, credit=line.credit) for line in self.lines]

    def __repr__(self) -> str:
        reference = self.number if self.number is not None else "draft"
        return f"<Voucher {reference} {self.period} {self.description[:30]}>"


class VoucherLine(Base, TimestampMixin):
    __tablename__ = "voucher_lines"
    __table_args__ = (
        UniqueConstraint("voucher_id", "line_number", name="uq_voucher_lines_order"),
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_voucher_lines_signs"),
        CheckConstraint(
            "(debit = 0) <> (credit = 0)", name="ck_voucher_lines_one_column"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("vouchers.id", ondelete="CASCADE"), index=True
    )
    line_number: Mapped[int] = mapped_column()

    account_code: Mapped[str] = mapped_column(
        String(MAX_CODE_LENGTH),
        ForeignKey("accounts.code", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
    )
    third_party_id: Mapped[int | None] = mapped_column(
        ForeignKey("third_parties.id", ondelete="RESTRICT"), index=True, default=None
    )

    debit: Mapped[Decimal] = mapped_column(MONEY, default=ZERO)
    credit: Mapped[Decimal] = mapped_column(MONEY, default=ZERO)
    description: Mapped[str | None] = mapped_column(String(255), default=None)

    voucher: Mapped[Voucher] = relationship(back_populates="lines")

    @classmethod
    def write(
        cls,
        *,
        line_number: int,
        account_code: str,
        debit: Decimal = ZERO,
        credit: Decimal = ZERO,
        third_party_id: int | None = None,
        description: str | None = None,
    ) -> VoucherLine:
        amounts = Amounts(debit=debit, credit=credit)

        return cls(
            line_number=line_number,
            account_code=account_code.strip(),
            third_party_id=third_party_id,
            debit=amounts.debit,
            credit=amounts.credit,
            description=(description or "").strip() or None,
        )

    def __repr__(self) -> str:
        side = f"D {self.debit}" if self.debit else f"C {self.credit}"
        return f"<VoucherLine {self.account_code} {side}>"


_reversal = Voucher.__table__.alias("reversal")

Voucher.reversed_by_voucher_id = column_property(
    select(_reversal.c.id)
    .where(_reversal.c.reverses_voucher_id == Voucher.__table__.c.id)
    .correlate_except(_reversal)
    .scalar_subquery()
)
