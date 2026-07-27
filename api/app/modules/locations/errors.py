from app.shared.errors import DomainError


class CountryNotFound(DomainError):
    """Location catalog errors."""
    def __init__(self, country_id: int) -> None:
        super().__init__(f"Country {country_id} does not exist")
        self.country_id = country_id


class DepartmentNotFound(DomainError):
    def __init__(self, department_id: int) -> None:
        super().__init__(f"Department {department_id} does not exist")
        self.department_id = department_id


class CityNotFound(DomainError):
    def __init__(self, city_id: int) -> None:
        super().__init__(f"City {city_id} does not exist")
        self.city_id = city_id


class InconsistentPlace(DomainError):
    """The three levels of a place do not line up."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
