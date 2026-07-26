"""Pydantic at the edge: what the location catalogs look like over HTTP."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    iso_code: str = Field(examples=["CO"])
    name: str = Field(examples=["Colombia"])


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_id: int
    dane_code: str = Field(examples=["05"])
    name: str = Field(examples=["Antioquia"])


class CityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    dane_code: str = Field(examples=["05001"])
    name: str = Field(examples=["Medellín"])
