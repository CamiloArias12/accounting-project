"""Third party business errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class ThirdPartyNotFound(DomainError):
    def __init__(self, third_party_id: int) -> None:
        super().__init__(f"Third party {third_party_id} does not exist")
        self.third_party_id = third_party_id


class ThirdPartyAlreadyExists(DomainError):
    def __init__(self, document_type: str, document_number: str) -> None:
        super().__init__(
            f"A third party with {document_type} {document_number} already exists"
        )
        self.document_type = document_type
        self.document_number = document_number


class ThirdPartyNotDeleted(DomainError):
    def __init__(self, third_party_id: int) -> None:
        super().__init__(
            f"Third party {third_party_id} is not deleted, so it cannot be restored"
        )
        self.third_party_id = third_party_id


class IncompleteThirdParty(DomainError):
    """A field required for this kind of person is missing, or one that does not
    belong to it was given.

    The columns are nullable because a single table holds both kinds of person,
    so the rule lives here instead of in a NOT NULL constraint.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
