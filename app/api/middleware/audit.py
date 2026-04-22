from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.db.models import AuditLog
from app.domain.enums import AuditAction

logger = structlog.get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        body: bytes = await request.body()

        response: Response = Response(status_code=500)
        try:
            response = await call_next(request)
            return response
        except Exception:
            raise
        finally:
            await self._write_audit(request, body, response.status_code)

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        try:
            payload: dict[str, object] = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            sub = payload.get("sub")
            return str(sub) if sub is not None else None
        except Exception:
            return None

    @staticmethod
    async def _write_audit(
        request: Request,
        body: bytes,
        status_code: int,
    ) -> None:
        try:
            user_id = AuditMiddleware._extract_user_id(request)
            path = request.url.path
            parts = path.lstrip("/").split("/")
            resource_type = parts[0] if parts else ""
            resource_id = parts[1] if len(parts) > 1 and parts[1] else None

            action = (
                AuditAction.READ if request.method == "GET" else AuditAction.CREATE
            )
            payload_hash = hashlib.sha256(body).hexdigest()

            audit = AuditLog(
                action=action.value,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                timestamp=datetime.now(UTC),
                ip_address=request.client.host if request.client else None,
                payload_hash=payload_hash,
            )

            import app.db.session as _db_session  # late import so tests can patch
            async with _db_session.AsyncSessionLocal() as session:
                session.add(audit)
                await session.commit()
        except Exception:
            logger.warning("audit_write_failed", path=request.url.path)
