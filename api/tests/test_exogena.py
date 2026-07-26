from decimal import Decimal
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exogena.report import Filer, InvalidFiler
from tests.test_third_parties_api import natural_payload, seed_places
from tests.test_vouchers import a_posted_voucher

BASE = "/api/v1/exogena"
ACCOUNTS = "/api/v1/accounts"

#: 5002 is the concept the payment and its withholding both report under, which
#: is what puts `valorBruto` and `valorRetencion` on the same `Registro`.
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
    """The places are seeded once and passed in: seeding them twice trips the
    unique on the DANE codes, which is the catalogue doing its job."""
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
    """Fees paid to a supplier, with the withholding taken off."""
    net = Decimal(gross) - Decimal(withheld)
    lines: list[dict[str, Any]] = [
        {"account_code": "511005", "debit": gross, "third_party_id": supplier},
    ]
    # A line carrying neither a debit nor a credit is refused, so a payment
    # with nothing withheld simply has no withholding line.
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


def parse(xml: str) -> ET.Element:
    return ET.fromstring(xml)


# --- the filer's own NIT -------------------------------------------------


def test_the_filer_nit_is_verified() -> None:
    filer = Filer.of(nit="900000000-5", legal_name="Acme", year=2025)
    assert filer.check_digit == 5


def test_a_wrong_check_digit_is_refused() -> None:
    # A file filed under a mistyped NIT is filed against somebody else.
    with pytest.raises(InvalidFiler, match="is 5, not 9"):
        Filer.of(nit="900000000-9", legal_name="Acme", year=2025)


def test_the_check_digit_is_derived_when_it_is_not_given() -> None:
    assert Filer.of(nit="900000000", legal_name="Acme", year=2025).check_digit == 5


# --- the document ------------------------------------------------------------


async def test_the_xml_has_the_required_shape(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")

    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "0"}
    )

    assert generated.status_code == 200
    assert generated.headers["content-type"].startswith("application/xml")
    assert "attachment" in generated.headers["content-disposition"]

    root = parse(generated.text)
    assert root.tag == "InformacionExogena"
    assert root.attrib["version"] == "1.0"

    # The tags stay Spanish: they are the file format the DIAN mandates, not
    # a naming choice of ours.
    filer = root.find("Informante")
    assert filer is not None
    assert set(filer.attrib) == {"nit", "dv", "razonSocial", "anioGravable"}
    assert filer.attrib["anioGravable"] == "2025"

    registro = root.find("Registros/Registro")
    assert registro is not None
    assert set(registro.attrib) == {
        "tipoDoc",
        "numDoc",
        "nombre",
        "concepto",
        "valorBruto",
        "valorRetencion",
    }
    # 13 is the DIAN's code for a cédula de ciudadanía. The file carries the
    # code, not our label: "Citizen ID" would be rejected.
    assert registro.attrib["tipoDoc"] == "13"
    assert registro.attrib["concepto"] == "5002"
    assert registro.attrib["valorBruto"] == "1000000"
    assert registro.attrib["valorRetencion"] == "100000"
    assert registro.attrib["nombre"] == "Ana Restrepo"


async def test_movements_are_grouped_by_third_party_and_concept(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")
    await a_payment(auth_client, supplier, "500000.00", "50000.00")

    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "0"}
    )

    registros = parse(generated.text).findall("Registros/Registro")
    # Two payments, one third party, one concept: one row.
    assert len(registros) == 1
    assert registros[0].attrib["valorBruto"] == "1500000"
    assert registros[0].attrib["valorRetencion"] == "150000"


async def test_the_totals_match_the_rows(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    first = await a_supplier(auth_client, places)
    second = await a_supplier(
        auth_client, places, document_number="80808080", first_name="Beto"
    )
    await a_payment(auth_client, first, "1000000.00", "100000.00")
    await a_payment(auth_client, second, "700000.00", "70000.00")

    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "0"}
    )

    root = parse(generated.text)
    registros = root.findall("Registros/Registro")
    totales = root.find("Totales")
    assert totales is not None

    assert totales.attrib["registros"] == str(len(registros))
    assert totales.attrib["totalValorBruto"] == str(
        sum(int(r.attrib["valorBruto"]) for r in registros)
    )
    assert totales.attrib["totalRetencion"] == str(
        sum(int(r.attrib["valorRetencion"]) for r in registros)
    )


async def test_drafts_and_untagged_accounts_stay_out(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    # A draft: not in the books. And 110505 carries no concept, so the cash
    # side of every entry is not reportable either.
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

    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "0"}
    )

    totales = parse(generated.text).find("Totales")
    assert totales is not None
    assert totales.attrib["registros"] == "0"


# --- the threshold -----------------------------------------------------------


async def test_a_third_party_below_the_threshold_is_excluded(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    await auth_client.put("/api/v1/uvt/2025", json={"value": "49799.00"})

    places = await seed_places(session)
    big = await a_supplier(auth_client, places)
    small = await a_supplier(
        auth_client, places, document_number="80808080", first_name="Beto"
    )
    # 100 UVT is 4.979.900 pesos.
    await a_payment(auth_client, big, "6000000.00", "0.00")
    await a_payment(auth_client, small, "1000000.00", "0.00")

    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "100"}
    )

    registros = parse(generated.text).findall("Registros/Registro")
    assert [r.attrib["valorBruto"] for r in registros] == ["6000000"]

    history = (await auth_client.get(BASE + "/history")).json()
    assert history[0]["threshold_pesos"] == "4979900.00"
    assert history[0]["excluded_count"] == 1


async def test_a_threshold_without_a_uvt_is_refused(
    auth_client: AsyncClient,
) -> None:
    # Falling back to a neighbouring year would move the threshold by
    # thousands of pesos without anybody noticing.
    refused = await auth_client.post(
        BASE + "/generate", json={"year": 2019, "threshold_uvt": "100"}
    )

    assert refused.status_code == 409
    assert "needs the UVT of 2019" in refused.json()["detail"]


async def test_a_threshold_of_zero_needs_no_uvt(auth_client: AsyncClient) -> None:
    generated = await auth_client.post(
        BASE + "/generate", json={"year": 2019, "threshold_uvt": "0"}
    )

    assert generated.status_code == 200


# --- history and re-download --------------------------------------------------


async def test_a_generation_is_recorded_with_its_parameters(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")
    await auth_client.put("/api/v1/uvt/2025", json={"value": "49799.00"})

    await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "10"}
    )

    history = (await auth_client.get(BASE + "/history")).json()
    assert len(history) == 1
    assert history[0]["year"] == 2025
    assert history[0]["threshold_uvt"] == "10.00"
    assert history[0]["uvt_value"] == "49799.00"
    assert history[0]["generated_at"]
    assert history[0]["generated_by_user_id"] is not None


async def test_the_file_comes_back_byte_for_byte(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    """What was filed, not what the books would produce today."""
    await seed_chart(auth_client)
    places = await seed_places(session)
    supplier = await a_supplier(auth_client, places)
    await a_payment(auth_client, supplier, "1000000.00", "100000.00")

    first = await auth_client.post(
        BASE + "/generate", json={"year": 2025, "threshold_uvt": "0"}
    )
    generation_id = (await auth_client.get(BASE + "/history")).json()[0]["id"]

    # The books move underneath it.
    await a_payment(auth_client, supplier, "9999999.00", "0.00")

    again = await auth_client.get(f"{BASE}/history/{generation_id}/file")
    assert again.status_code == 200
    assert again.text == first.text
    assert "9999999" not in again.text


async def test_a_generation_that_does_not_exist(auth_client: AsyncClient) -> None:
    missing = await auth_client.get(f"{BASE}/history/9999/file")
    assert missing.status_code == 404


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE + "/history")).status_code == 401
