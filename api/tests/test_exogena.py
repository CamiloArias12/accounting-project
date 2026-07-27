from decimal import Decimal
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exogena.report import Filer, InvalidFiler
from tests.test_third_parties_api import natural_payload, seed_places
from tests.test_vouchers import a_posted_voucher

BASE = "/api/v1/exogena"
ACCOUNTS = "/api/v1/accounts"

CHART: list[dict[str, Any]] = [
    {"code": "1", "name": "ACTIVOS", "nature": "Debito"},
    {"code": "11", "name": "DISPONIBLE", "nature": "Debito"},
    {"code": "1105", "name": "CAJA", "nature": "Debito"},
    {"code": "110505", "name": "CAJA GENERAL", "nature": "Debito"},
    {"code": "5", "name": "GASTOS", "nature": "Debito"},
    {"code": "51", "name": "OPERACIONALES", "nature": "Debito"},
    {"code": "5110", "name": "HONORARIOS", "nature": "Debito"},
    {
        "code": "511005",
        "name": "HONORARIOS JUNTA",
        "nature": "Debito",
        "dian_concept": "5002",
    },
    {"code": "2", "name": "PASIVOS", "nature": "Crédito"},
    {"code": "23", "name": "RETENCIONES", "nature": "Crédito"},
    {"code": "2365", "name": "RETEFUENTE", "nature": "Crédito"},
    {
        "code": "236515",
        "name": "RETEFUENTE HONORARIOS",
        "nature": "Crédito",
        "dian_concept": "5002",
        "is_withholding": True,
    },
]


async def seed_chart(auth_client: AsyncClient) -> None:
    for payload in CHART:
        response = await auth_client.post(ACCOUNTS, json=payload)
        assert response.status_code == 201, response.text


async def a_supplier(
    auth_client: AsyncClient, places: dict[str, int], **overrides: Any
) -> int:
    created = await auth_client.post(
        "/api/v1/third-parties", json=natural_payload(places, **overrides)
    )
    assert created.status_code == 201, created.text
    return int(created.json()["id"])


async def a_payment(
    auth_client: AsyncClient,
    supplier: int,
    gross: str,
    withheld: str,
    *,
    year: int = 2025,
) -> None:
    net = Decimal(gross) - Decimal(withheld)
    lines: list[dict[str, Any]] = [
        {"account_code": "511005", "debit": gross, "third_party_id": supplier},
    ]
    if Decimal(withheld) > 0:
        lines.append(
            {
                "account_code": "236515",
                "credit": withheld,
                "third_party_id": supplier,
            }
        )
    lines.append({"account_code": "110505", "credit": f"{net}"})

    await a_posted_voucher(
        auth_client,
        date=f"{year}-06-15",
        period_year=year,
        period_month=6,
        description="Honorarios",
        lines=lines,
    )


async def generate(client: AsyncClient, payload: dict[str, Any]) -> Response:
    created = await client.post(BASE + "/generate", json=payload)
    assert created.status_code == 201, created.text

    return await client.get(f"{BASE}/history/{created.json()['id']}/file")


def test_the_filers_own_nit_is_verified_before_it_is_filed() -> None:
    with pytest.raises(InvalidFiler, match="is 5, not 9"):
        Filer.of(nit="900000000-9", legal_name="Acme", year=2025)

    assert Filer.of(nit="900000000-5", legal_name="Acme", year=2025).check_digit == 5
    assert Filer.of(nit="900000000", legal_name="Acme", year=2025).check_digit == 5


async def test_the_xml_carries_one_row_per_third_party_and_concept(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")
    await a_payment(auth_client, supplier, "500000.00", "50000.00")
    await auth_client.post(
        "/api/v1/vouchers",
        json={
            "date": "2025-06-15",
            "period_year": 2025,
            "period_month": 6,
            "description": "Sin contabilizar",
            "lines": [
                {
                    "account_code": "511005",
                    "debit": "900000.00",
                    "third_party_id": supplier,
                },
                {"account_code": "110505", "credit": "900000.00"},
            ],
        },
    )

    generated = await generate(auth_client, {"year": 2025, "threshold_uvt": "0"})

    assert generated.headers["content-type"].startswith("application/xml")
    root = ET.fromstring(generated.text)
    assert root.tag == "InformacionExogena"

    filer = root.find("Informante")
    assert filer is not None
    assert set(filer.attrib) == {"nit", "dv", "razonSocial", "anioGravable"}
    assert filer.attrib["anioGravable"] == "2025"

    registros = root.findall("Registros/Registro")
    assert len(registros) == 1
    assert set(registros[0].attrib) == {
        "tipoDoc",
        "numDoc",
        "nombre",
        "concepto",
        "valorBruto",
        "valorRetencion",
    }
    assert registros[0].attrib["tipoDoc"] == "13"
    assert registros[0].attrib["concepto"] == "5002"
    assert registros[0].attrib["valorBruto"] == "1500000"
    assert registros[0].attrib["valorRetencion"] == "150000"
    assert registros[0].attrib["nombre"] == "Ana Restrepo"

    totales = root.find("Totales")
    assert totales is not None
    assert totales.attrib["registros"] == "1"
    assert totales.attrib["totalValorBruto"] == "1500000"


async def test_the_threshold_needs_the_uvt_of_that_year(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    await auth_client.put("/api/v1/uvt/2025", json={"value": "49799.00"})

    places = await seed_places(session)
    big = await a_supplier(auth_client, places)
    small = await a_supplier(
        auth_client, places, document_number="80808080", first_name="Beto"
    )
    await a_payment(auth_client, big, "6000000.00", "0.00")
    await a_payment(auth_client, small, "1000000.00", "0.00")

    generated = await generate(auth_client, {"year": 2025, "threshold_uvt": "100"})

    registros = ET.fromstring(generated.text).findall("Registros/Registro")
    assert [r.attrib["valorBruto"] for r in registros] == ["6000000"]

    history = (await auth_client.get(BASE + "/history")).json()
    assert history[0]["threshold_pesos"] == "4979900.00"
    assert history[0]["excluded_count"] == 1
    assert history[0]["uvt_value"] == "49799.00"
    assert history[0]["generated_by_user_id"] is not None

    refused = await auth_client.post(
        BASE + "/generate", json={"year": 2019, "threshold_uvt": "100"}
    )
    assert refused.status_code == 409
    assert "needs the UVT of 2019" in refused.json()["detail"]

    no_uvt_needed = await generate(auth_client, {"year": 2019, "threshold_uvt": "0"})
    assert no_uvt_needed.status_code == 200


async def test_the_file_comes_back_byte_for_byte(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")

    first = await generate(auth_client, {"year": 2025, "threshold_uvt": "0"})
    generation_id = (await auth_client.get(BASE + "/history")).json()[0]["id"]

    straight = await auth_client.post(
        BASE + "/generate",
        params={"download": "true"},
        json={"year": 2025, "threshold_uvt": "0"},
    )
    assert straight.status_code == 201
    assert straight.headers["content-type"].startswith("application/xml")
    assert "attachment" in straight.headers["content-disposition"]
    assert straight.text == first.text

    await a_payment(auth_client, supplier, "9999999.00", "0.00")

    again = await auth_client.get(f"{BASE}/history/{generation_id}/file")
    assert again.status_code == 200
    assert again.text == first.text
    assert "9999999" not in again.text
