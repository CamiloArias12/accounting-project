"""The accounting voucher and its lines.

A header plus its entries, and nothing between them. The reference project puts
a table per kind of voucher in the middle — cash receipt, disbursement, note —
which leaves the line table carrying five nullable foreign keys and forces every
query to know which one is set. What distinguishes one voucher from another is
data, not a table.

A voucher is a working document while it is `DRAFT`: editable, deletable, absent
from the balances. Posting it turns it into an accounting record — it takes a
consecutive number, and from then on it cannot be altered.

The company the voucher belongs to is not a column. This deployment keeps one
set of books, so it is the same on every row; it lives in settings and is read
back when a voucher is displayed or printed.
"""

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

#: Big enough for any figure a set of books will hold, with the two decimals
#: money is counted in. Never a float: a ledger cannot afford binary rounding.
MONEY = Numeric(18, 2)


class Voucher(Base, TimestampMixin):
    __tablename__ = "vouchers"
    __table_args__ = (
        # Only posted vouchers have a number, so the constraint has to tolerate
        # many NULLs — which is exactly what a SQL unique index does.
        UniqueConstraint("number", name="uq_vouchers_number"),
        CheckConstraint(
            "period_month BETWEEN 1 AND 12", name="ck_vouchers_period_month"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Null until posted: a draft must not consume a consecutive number, or the
    #: series ends up with gaps that have to be explained to the DIAN.
    number: Mapped[int | None] = mapped_column(default=None)

    date: Mapped[dt.date] = mapped_column(Date, index=True)
    #: Kept apart from `date` on purpose; see `AccountingPeriod`.
    period_year: Mapped[int] = mapped_column(index=True)
    period_month: Mapped[int] = mapped_column(index=True)

    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[VoucherStatus] = mapped_column(
        Enum(VoucherStatus, name="voucher_status", native_enum=False, length=20),
        default=VoucherStatus.DRAFT,
        index=True,
    )
    posted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    #: Who wrote it and who put it in the books, taken from the session rather
    #: than from the form. An accounting record has to say who is answerable for
    #: it, and the two are not always the same person.
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None, index=True
    )
    posted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None
    )

    #: Set on a reversal, pointing at what it undoes. Unique, so a voucher
    #: cannot be reversed twice — which would double the correction.
    reverses_voucher_id: Mapped[int | None] = mapped_column(
        ForeignKey("vouchers.id", ondelete="RESTRICT"),
        unique=True,
        default=None,
    )

    lines: Mapped[list[VoucherLine]] = relationship(
        back_populates="voucher",
        # The lines have no life of their own: removing one from the collection
        # deletes the row, and deleting a draft takes its lines with it.
        cascade="all, delete-orphan",
        order_by="VoucherLine.line_number",
        lazy="selectin",
    )

    if TYPE_CHECKING:
        #: The voucher that undoes this one, or None. Provided by the
        #: `column_property` assigned below the class, which is where a
        #: self-referential query has to live.
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
        """Start a draft. The period defaults to the one the date falls in."""
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
        """Guard every mutation. A posted voucher is a record, not a document."""
        if self.is_posted:
            raise VoucherNotEditable(self.id)

    def require_balanced(self) -> None:
        """Raise unless debits equal credits. The rule the books rest on."""
        check_balanced(self._amounts())

    def post(self, number: int, *, user_id: int | None = None) -> None:
        """Turn the draft into an accounting record.

        The number is passed in because only the session can tell what the next
        one is; everything else that decides whether this is allowed is here.
        """
        self.require_editable()
        self.require_balanced()

        self.number = number
        self.status = VoucherStatus.POSTED
        self.posted_by_user_id = user_id
        # Naive, to match the other timestamp columns.
        self.posted_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)

    def require_reversible(self) -> None:
        """Whether undoing this one makes sense at all."""
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
        """The entry that undoes this one.

        The original is not touched: it keeps its number, its date and its
        lines. Both end up in the ledger and cancel each other out, so what an
        audit sees is the mistake and its correction rather than a gap.
        """
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
                # Swapped, and that is the whole of a reversal: what was a debit
                # becomes a credit and the other way round.
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
        # The domain refuses these before they get here; the database refuses
        # them too, so a direct SQL write cannot leave an entry that no report
        # can make sense of.
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_voucher_lines_signs"),
        CheckConstraint(
            "(debit = 0) <> (credit = 0)", name="ck_voucher_lines_one_column"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("vouchers.id", ondelete="CASCADE"), index=True
    )
    #: Position within the voucher, so the entry reads back in the order it was
    #: written rather than in whatever order the rows come out.
    line_number: Mapped[int] = mapped_column()

    account_code: Mapped[str] = mapped_column(
        String(MAX_CODE_LENGTH),
        ForeignKey("accounts.code", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
    )
    #: Present only where the account calls for one; see
    #: `accounts.requires_third_party`.
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
        """Build a line, refusing the combinations that are not an entry."""
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


#: Whether some other voucher undoes this one.
#:
#: A correlated subquery rather than a relationship: it comes back with every
#: SELECT, so reading a voucher never sets off a second query — which under
#: async would not merely be slow but would fail outright.
_reversal = Voucher.__table__.alias("reversal")

Voucher.reversed_by_voucher_id = column_property(
    select(_reversal.c.id)
    .where(_reversal.c.reverses_voucher_id == Voucher.__table__.c.id)
    .correlate_except(_reversal)
    .scalar_subquery()
)
