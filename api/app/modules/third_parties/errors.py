from app.shared.errors import DomainError


class ThirdPartyNotFound(DomainError):
    """Third party business errors."""
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
    """A field this kind of person requires is missing, or one alien to it was given."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
