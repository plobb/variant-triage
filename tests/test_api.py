"""Integration tests for the FastAPI service layer (Phase 4)."""
from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.db.session as _db_session_module
from app.api.deps import get_db
from app.api.main import app
from app.core.config import settings
from app.db.models import AuditLog, Base, Classification, Sample

# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

_TEST_DB_URL = re.sub(r"/[^/]+$", "/variant_triage_test", settings.DB_URL)
_test_engine = create_async_engine(_TEST_DB_URL, echo=False, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GERMLINE_VCF = (FIXTURES_DIR / "germline_snv.vcf").read_text()
SOMATIC_VCF = (FIXTURES_DIR / "somatic_longread.vcf").read_text()

_TEST_PW = "Testpass1!"       # standard password used across all tests
_WRONG_PW = "BadPass999!"     # intentionally wrong password (never registered)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="function", autouse=True)
async def _setup_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    original_factory = _db_session_module.AsyncSessionLocal
    _db_session_module.AsyncSessionLocal = _TestSessionLocal  # type: ignore[assignment]
    yield
    _db_session_module.AsyncSessionLocal = original_factory  # type: ignore[assignment]
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(loop_scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Direct DB session for assertion queries."""
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient pointed at the test app with get_db overridden."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with _TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="function")
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return auth headers."""
    await client.post(
        "/auth/register",
        json={"email": "testuser@example.com", "password": _TEST_PW},
    )
    resp = await client.post(
        "/auth/token",
        data={"username": "testuser@example.com", "password": _TEST_PW},
    )
    token: str = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _post_germline(
    client: AsyncClient, headers: dict[str, str], vcf: str = GERMLINE_VCF
) -> Any:
    return await client.post(
        "/variants/germline",
        json={"vcf_content": vcf, "sample_name": "SAMPLE_A", "origin": "GERMLINE"},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# 1. Health
# ---------------------------------------------------------------------------


async def test_health_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 2-6. Auth endpoints
# ---------------------------------------------------------------------------


async def test_register_valid_returns_201(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": _TEST_PW},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "id" in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_400(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": _TEST_PW}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_register_weak_password_returns_422(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


async def test_token_valid_credentials_returns_token(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": _TEST_PW},
    )
    resp = await client.post(
        "/auth/token",
        data={"username": "login@example.com", "password": _TEST_PW},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_token_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "auth401@example.com", "password": _TEST_PW},
    )
    resp = await client.post(
        "/auth/token",
        data={"username": "auth401@example.com", "password": _WRONG_PW},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 7-10. Variant endpoints
# ---------------------------------------------------------------------------


async def test_germline_without_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/variants/germline",
        json={"vcf_content": GERMLINE_VCF, "sample_name": "S", "origin": "GERMLINE"},
    )
    assert resp.status_code == 401


async def test_germline_valid_vcf_returns_200_with_results(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await _post_germline(client, auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["variants_processed"] == 5
    assert len(body["results"]) == 5
    result = body["results"][0]
    assert "classification_tier" in result
    assert "acmg_points" in result
    assert "evidence_codes" in result
    assert "summary" in result


async def test_germline_malformed_vcf_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/variants/germline",
        json={
            "vcf_content": "INVALID VCF CONTENT",
            "sample_name": "S",
            "origin": "GERMLINE",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_somatic_valid_vcf_returns_200_with_results(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/variants/somatic",
        json={"vcf_content": SOMATIC_VCF, "sample_name": "TUMOUR", "origin": "SOMATIC"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["variants_processed"] == 5
    result = body["results"][0]
    assert "amp_tier" in result
    assert "confidence" in result
    assert "therapy_implications" in result


# ---------------------------------------------------------------------------
# 11-14. GET variant endpoints
# ---------------------------------------------------------------------------


async def test_get_variant_by_id_returns_correct_result(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    post_resp = await _post_germline(client, auth_headers)
    variant_id: int = post_resp.json()["results"][0]["id"]

    resp = await client.get(f"/variants/{variant_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == variant_id
    assert "classification_tier" in body


async def test_get_variant_other_user_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    post_resp = await _post_germline(client, auth_headers)
    variant_id: int = post_resp.json()["results"][0]["id"]

    await client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": _TEST_PW},
    )
    token_resp = await client.post(
        "/auth/token",
        data={"username": "other@example.com", "password": _TEST_PW},
    )
    other_headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    resp = await client.get(f"/variants/{variant_id}", headers=other_headers)
    assert resp.status_code == 404


async def test_list_variants_returns_only_current_user(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _post_germline(client, auth_headers)

    await client.post(
        "/auth/register",
        json={"email": "userb@example.com", "password": _TEST_PW},
    )
    token_b = (
        await client.post(
            "/auth/token",
            data={"username": "userb@example.com", "password": _TEST_PW},
        )
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    await _post_germline(client, headers_b)

    resp_a = await client.get("/variants/", headers=auth_headers)
    resp_b = await client.get("/variants/", headers=headers_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    ids_a = {v["id"] for v in resp_a.json()}
    ids_b = {v["id"] for v in resp_b.json()}
    assert ids_a.isdisjoint(ids_b)


async def test_list_variants_empty_for_new_user(
    client: AsyncClient,
) -> None:
    await client.post(
        "/auth/register",
        json={"email": "fresh@example.com", "password": _TEST_PW},
    )
    token = (
        await client.post(
            "/auth/token",
            data={"username": "fresh@example.com", "password": _TEST_PW},
        )
    ).json()["access_token"]
    resp = await client.get(
        "/variants/", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# 15-17. Audit log tests
# ---------------------------------------------------------------------------


async def test_audit_log_created_after_germline_post(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_db: AsyncSession,
) -> None:
    await _post_germline(client, auth_headers)
    result = await test_db.execute(
        select(AuditLog).where(AuditLog.resource_type == "variants")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


async def test_audit_log_captures_user_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_db: AsyncSession,
) -> None:
    await _post_germline(client, auth_headers)
    result = await test_db.execute(
        select(AuditLog).where(AuditLog.resource_type == "variants")
    )
    log = result.scalars().first()
    assert log is not None
    assert log.user_id == "testuser@example.com"


async def test_audit_log_created_for_failed_request(
    client: AsyncClient,
    test_db: AsyncSession,
) -> None:
    # Unauthenticated request — 401 but should still produce an audit row
    await client.post(
        "/variants/germline",
        json={"vcf_content": GERMLINE_VCF, "sample_name": "S", "origin": "GERMLINE"},
    )
    result = await test_db.execute(
        select(AuditLog).where(AuditLog.resource_type == "variants")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


# ---------------------------------------------------------------------------
# 18-20. Additional coverage
# ---------------------------------------------------------------------------


async def test_germline_with_somatic_vcf_fixture(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/variants/germline",
        json={
            "vcf_content": SOMATIC_VCF,
            "sample_name": "SOMATIC_AS_GERMLINE",
            "origin": "GERMLINE",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["variants_processed"] == 5


async def test_classification_persisted_to_db(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_db: AsyncSession,
) -> None:
    post_resp = await _post_germline(client, auth_headers)
    clf_id: int = post_resp.json()["results"][0]["id"]

    result = await test_db.execute(
        select(Classification).where(Classification.id == clf_id)
    )
    clf = result.scalar_one_or_none()
    assert clf is not None
    assert clf.tier is not None
    assert clf.is_automated is True


async def test_sample_row_has_correct_user_id_fk(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_db: AsyncSession,
) -> None:
    post_resp = await _post_germline(client, auth_headers)
    sample_id: int = post_resp.json()["sample_id"]

    result = await test_db.execute(select(Sample).where(Sample.id == sample_id))
    sample = result.scalar_one_or_none()
    assert sample is not None
    assert sample.user_id is not None

    from app.db.models import User

    user_result = await test_db.execute(
        select(User).where(User.id == sample.user_id)
    )
    user = user_result.scalar_one_or_none()
    assert user is not None
    assert user.email == "testuser@example.com"
