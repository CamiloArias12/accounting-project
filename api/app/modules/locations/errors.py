"""Location catalog errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class CountryNotFound(DomainError):
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
    """The three levels of a place do not line up.

    Worth its own error: the whole reason the catalogs are three tables is that
    a city belongs to a department and a department to a country. Storing
    Medellín under Cundinamarca would make every report by region wrong.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
