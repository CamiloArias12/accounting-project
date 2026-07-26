"""Voucher business errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class VoucherNotFound(DomainError):
    def __init__(self, voucher_id: int) -> None:
        super().__init__(f"Voucher {voucher_id} does not exist")
        self.voucher_id = voucher_id


class VoucherNotEditable(DomainError):
    """A posted voucher is an accounting record, not a working document.

    Correcting one means writing the reversing entry, not rewriting history:
    the books have to show what was recorded and what corrected it.
    """

    def __init__(self, voucher_id: int) -> None:
        super().__init__(
            f"Voucher {voucher_id} is posted and can no longer be changed; "
            "reverse it instead"
        )
        self.voucher_id = voucher_id


class VoucherAlreadyPosted(DomainError):
    def __init__(self, voucher_id: int) -> None:
        super().__init__(f"Voucher {voucher_id} is already posted")
        self.voucher_id = voucher_id


class VoucherNotPosted(DomainError):
    """There is nothing to undo in a draft: it was never in the books.

    A draft that turned out to be wrong is edited or discarded.
    """

    def __init__(self, voucher_id: int) -> None:
        super().__init__(
            f"Voucher {voucher_id} is a draft; edit or discard it instead of "
            "reversing it"
        )
        self.voucher_id = voucher_id


class VoucherAlreadyReversed(DomainError):
    def __init__(self, voucher_id: int, reversal_id: int) -> None:
        super().__init__(
            f"Voucher {voucher_id} was already reversed by voucher {reversal_id}"
        )
        self.voucher_id = voucher_id
        self.reversal_id = reversal_id


class VoucherIsReversal(DomainError):
    """A reversal is already a correction; undoing it would restore the error.

    What is wanted in that case is a fresh entry, which says plainly what it
    does instead of leaving a chain of undos to be unwound.
    """

    def __init__(self, voucher_id: int) -> None:
        super().__init__(
            f"Voucher {voucher_id} is itself a reversal and cannot be reversed"
        )
        self.voucher_id = voucher_id


class AccountNotPostable(DomainError):
    """Entries go on the leaves of the chart, never on a heading.

    Posting to a parent would double-count it: its balance is the sum of its
    children, and a figure of its own would be added on top.
    """

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(f"Account {code} cannot be posted to: {reason}")
        self.code = code
        self.reason = reason


class ThirdPartyRequired(DomainError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Account {code} requires a third party on every entry")
        self.code = code


class UnknownThirdParty(DomainError):
    def __init__(self, third_party_id: int) -> None:
        super().__init__(
            f"Third party {third_party_id} does not exist or has been deleted"
        )
        self.third_party_id = third_party_id
