"""Tests for app/interpretation — assistant, guardrails, and schemas.

No real API calls are made; httpx.AsyncClient is fully mocked.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.interpretation.assistant import VariantInterpretationAssistant
from app.interpretation.guardrails import DISCLAIMER, GuardrailChecker
from app.interpretation.schemas import (
    InterpretationError,
    InterpretationRequest,
    InterpretationResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_germline_request(**kwargs: Any) -> InterpretationRequest:
    defaults: dict[str, Any] = {
        "variant_id": "var-001",
        "chrom": "chr17",
        "pos": 41_223_094,
        "ref": "G",
        "alt": "A",
        "gene": "BRCA1",
        "classification_tier": "Pathogenic",
        "evidence_codes": ["PVS1", "PM2"],
        "acmg_points": 8,
        "origin": "GERMLINE",
    }
    defaults.update(kwargs)
    return InterpretationRequest(**defaults)


def _make_somatic_request(**kwargs: Any) -> InterpretationRequest:
    defaults: dict[str, Any] = {
        "variant_id": "var-002",
        "chrom": "chr7",
        "pos": 55_259_515,
        "ref": "T",
        "alt": "G",
        "gene": "EGFR",
        "classification_tier": "Tier_I",
        "evidence_codes": [],
        "amp_tier": "Tier_I",
        "therapy_implications": ["erlotinib", "gefitinib"],
        "oncokb_oncogenicity": "Oncogenic",
        "origin": "SOMATIC",
    }
    defaults.update(kwargs)
    return InterpretationRequest(**defaults)


def _make_mock_api_response(
    text: str = "This variant is consistent with pathogenic classification. "
    "The evidence is suggestive of loss-of-function. "
    "This interpretation requires review by a qualified clinical geneticist before clinical use.",
) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": text}],
        "model": "claude-3-5-haiku-20241022",
        "usage": {"input_tokens": 150, "output_tokens": 89},
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _patch_httpx(mock_response: MagicMock) -> Any:
    """Return a patch context manager that mocks httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("httpx.AsyncClient", mock_class), mock_client


# ---------------------------------------------------------------------------
# GuardrailChecker tests  (1–6)
# ---------------------------------------------------------------------------


def test_guardrail_clean_text_no_flags() -> None:
    checker = GuardrailChecker()
    flags = checker.check(
        "This variant is consistent with pathogenic classification. "
        "The evidence supports loss-of-function. "
        "This interpretation requires review by a qualified clinical geneticist before clinical use."
    )
    assert flags == []


def test_guardrail_diagnosis_statement_triggers_flag() -> None:
    checker = GuardrailChecker()
    flags = checker.check("You have a hereditary cancer syndrome based on this variant.")
    assert len(flags) >= 1
    assert any("you (have|has|suffer|are diagnosed)" in f for f in flags)


def test_guardrail_treatment_recommendation_triggers_flag() -> None:
    checker = GuardrailChecker()
    flags = checker.check("The patient should start olaparib immediately.")
    assert len(flags) >= 1
    assert any("(start|begin|take|prescribe|administer)" in f for f in flags)


def test_guardrail_overconfident_language_triggers_flag() -> None:
    checker = GuardrailChecker()
    flags = checker.check("This variant is definitely pathogenic.")
    assert len(flags) >= 1
    assert any("(definitely|certainly|absolutely)" in f for f in flags)


def test_guardrail_sanitize_adds_warning_when_flags_present() -> None:
    checker = GuardrailChecker()
    text = "You have cancer based on this result."
    sanitized = checker.sanitize(text)
    assert "⚠️" in sanitized
    assert "flagged for review" in sanitized
    assert sanitized.startswith(text)


def test_guardrail_sanitize_unchanged_when_no_flags() -> None:
    checker = GuardrailChecker()
    text = (
        "This variant is consistent with pathogenic classification. "
        "This interpretation requires review by a qualified clinical geneticist before clinical use."
    )
    assert checker.sanitize(text) == text


# ---------------------------------------------------------------------------
# Schema construction tests  (7–9)
# ---------------------------------------------------------------------------


def test_interpretation_request_valid_germline() -> None:
    req = _make_germline_request()
    assert req.variant_id == "var-001"
    assert req.origin == "GERMLINE"
    assert req.classification_tier == "Pathogenic"
    assert "PVS1" in req.evidence_codes
    assert req.amp_tier is None


def test_interpretation_request_valid_somatic() -> None:
    req = _make_somatic_request()
    assert req.variant_id == "var-002"
    assert req.origin == "SOMATIC"
    assert req.amp_tier == "Tier_I"
    assert "erlotinib" in req.therapy_implications
    assert req.acmg_points is None


def test_interpretation_response_disclaimer_always_present() -> None:
    resp = InterpretationResponse(
        variant_id="var-001",
        interpretation="Some interpretation text.",
        confidence="high",
        guardrail_flags=[],
        disclaimer=DISCLAIMER,
        model_used="claude-3-5-haiku-20241022",
        generated_at=datetime.now(UTC),
    )
    assert resp.disclaimer == DISCLAIMER
    assert "RESEARCH USE ONLY" in resp.disclaimer


# ---------------------------------------------------------------------------
# VariantInterpretationAssistant.interpret() tests  (10–17)
# ---------------------------------------------------------------------------


async def test_assistant_interpret_returns_response_on_success() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request()
    ctx, _ = _patch_httpx(_make_mock_api_response())
    with ctx:
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationResponse)
    assert result.variant_id == "var-001"
    assert result.disclaimer == DISCLAIMER
    assert result.model_used == "claude-3-5-haiku-20241022"


async def test_assistant_interpret_uses_germline_template() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request()
    mock_resp = _make_mock_api_response()
    ctx, mock_client = _patch_httpx(mock_resp)
    with ctx:
        await assistant.interpret(request)
    call_kwargs = mock_client.post.call_args
    body = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    user_content: str = body["messages"][0]["content"]
    assert "Germline" in user_content
    assert "BRCA1" in user_content
    assert "ACMG score" in user_content


async def test_assistant_interpret_uses_somatic_template() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_somatic_request()
    mock_resp = _make_mock_api_response()
    ctx, mock_client = _patch_httpx(mock_resp)
    with ctx:
        await assistant.interpret(request)
    call_kwargs = mock_client.post.call_args
    body = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    user_content: str = body["messages"][0]["content"]
    assert "Somatic" in user_content
    assert "AMP/ASCO/CAP Tier" in user_content
    assert "erlotinib" in user_content


async def test_assistant_interpret_confidence_high_for_pathogenic() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request(classification_tier="Pathogenic")
    ctx, _ = _patch_httpx(_make_mock_api_response())
    with ctx:
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationResponse)
    assert result.confidence == "high"
    assert result.guardrail_flags == []


async def test_assistant_interpret_confidence_medium_for_vus() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request(classification_tier="VUS")
    ctx, _ = _patch_httpx(_make_mock_api_response())
    with ctx:
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationResponse)
    assert result.confidence == "medium"


async def test_assistant_interpret_confidence_low_when_flags_triggered() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request(classification_tier="Pathogenic")
    flagged_text = "You have a hereditary cancer syndrome. This interpretation requires review."
    ctx, _ = _patch_httpx(_make_mock_api_response(text=flagged_text))
    with ctx:
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationResponse)
    assert result.confidence == "low"
    assert len(result.guardrail_flags) >= 1


async def test_assistant_interpret_returns_error_on_api_exception() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
    with patch("httpx.AsyncClient", mock_class):
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationError)
    assert result.variant_id == "var-001"
    assert "Connection refused" in result.error


async def test_assistant_interpret_guardrail_flags_populate_response() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    request = _make_germline_request()
    flagged = "This is definitely pathogenic. This interpretation requires review."
    ctx, _ = _patch_httpx(_make_mock_api_response(text=flagged))
    with ctx:
        result = await assistant.interpret(request)
    assert isinstance(result, InterpretationResponse)
    assert len(result.guardrail_flags) >= 1
    assert "⚠️" in result.interpretation


# ---------------------------------------------------------------------------
# VariantInterpretationAssistant.interpret_batch() tests  (18–20)
# ---------------------------------------------------------------------------


async def test_assistant_interpret_batch_runs_all_requests() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")
    requests = [
        _make_germline_request(variant_id=f"var-{i}") for i in range(3)
    ]
    ctx, _ = _patch_httpx(_make_mock_api_response())
    with ctx:
        results = await assistant.interpret_batch(requests)
    assert len(results) == 3
    assert all(isinstance(r, InterpretationResponse) for r in results)
    ids = {r.variant_id for r in results if isinstance(r, InterpretationResponse)}
    assert ids == {"var-0", "var-1", "var-2"}


async def test_assistant_interpret_batch_handles_partial_failures() -> None:
    assistant = VariantInterpretationAssistant(api_key="test-key")

    now = datetime.now(UTC)

    async def mock_interpret(
        req: InterpretationRequest,
    ) -> InterpretationResponse | InterpretationError:
        if req.variant_id == "var-fail":
            return InterpretationError(
                variant_id=req.variant_id,
                error="Forced failure",
                generated_at=now,
            )
        return InterpretationResponse(
            variant_id=req.variant_id,
            interpretation="Consistent with classification.",
            confidence="high",
            guardrail_flags=[],
            disclaimer=DISCLAIMER,
            model_used="claude-3-5-haiku-20241022",
            generated_at=now,
        )

    with patch.object(assistant, "interpret", side_effect=mock_interpret):
        results = await assistant.interpret_batch(
            [
                _make_germline_request(variant_id="var-ok"),
                _make_germline_request(variant_id="var-fail"),
            ]
        )

    assert len(results) == 2
    assert any(isinstance(r, InterpretationResponse) for r in results)
    assert any(isinstance(r, InterpretationError) for r in results)


async def test_assistant_interpret_batch_respects_semaphore() -> None:
    """Five requests with Semaphore(3) — all should complete successfully."""
    assistant = VariantInterpretationAssistant(api_key="test-key")
    requests = [_make_germline_request(variant_id=f"var-{i}") for i in range(5)]
    ctx, _ = _patch_httpx(_make_mock_api_response())
    with ctx:
        results = await assistant.interpret_batch(requests)
    assert len(results) == 5
    assert all(isinstance(r, InterpretationResponse) for r in results)
    assert [r.variant_id for r in results if isinstance(r, InterpretationResponse)] == [
        f"var-{i}" for i in range(5)
    ]
