import json

import pytest

from snabagent.llm.fake import FakeLLM


@pytest.mark.asyncio
async def test_planner_returns_valid_json():
    llm = FakeLLM()
    sys = "Ты — ассистент отдела снабжения. Маппинг НСИ."
    user = (
        'Фраза: "Швеллер 14 ст3пс 10 тонн"\n'
        "Кандидаты:\n"
        "- sku=MET-SHV-14-3PS | name=\"Швеллер 14 ст3пс\" | category=metals | unit=т | "
        "gost=ГОСТ 8240-97 | typical_price=52800 | similarity=0.91\n"
    )
    resp = await llm.complete(sys, user)
    parsed = json.loads(resp.text)
    assert "items" in parsed
    assert parsed["items"][0]["matched_nsi_sku"] == "MET-SHV-14-3PS"


@pytest.mark.asyncio
async def test_verifier_detects_lead_time_excess():
    llm = FakeLLM()
    sys = "Ты — независимый аудитор."
    user = (
        "Сроки: запрошено 30 дней, в КП — 45.\n"
        "ИНН 7728168971. spark_data_json: {\"active\": true}"
    )
    resp = await llm.complete(sys, user)
    parsed = json.loads(resp.text)
    assert any(d.get("type") == "lead_time_exceeded" for d in parsed["discrepancies"])
