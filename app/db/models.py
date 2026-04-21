from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    samples: Mapped[list[Sample]] = relationship("Sample", back_populates="user")


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    patient_pseudonym: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sequencing_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    panel_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship("User", back_populates="samples")
    variants: Mapped[list[VariantModel]] = relationship(
        "VariantModel", back_populates="sample", cascade="all, delete-orphan"
    )


class VariantModel(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("samples.id", ondelete="CASCADE"), nullable=False
    )
    chrom: Mapped[str] = mapped_column(String(32), nullable=False)
    pos: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str] = mapped_column(Text, nullable=False)
    alt: Mapped[str] = mapped_column(Text, nullable=False)  # comma-joined
    gene_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hgvs_c: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hgvs_p: Mapped[str | None] = mapped_column(String(256), nullable=True)
    consequence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    gnomad_af: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sample: Mapped[Sample] = relationship("Sample", back_populates="variants")
    classifications: Mapped[list[Classification]] = relationship(
        "Classification", back_populates="variant", cascade="all, delete-orphan"
    )


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("variants.id", ondelete="CASCADE"), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(64), nullable=False)
    pathogenic_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_codes: Mapped[Any] = mapped_column(JSONB, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    classified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_automated: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    variant: Mapped[VariantModel] = relationship(
        "VariantModel", back_populates="classifications"
    )


class AuditLog(Base):
    """Immutable audit trail for all clinical data access and mutations."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # SHA-256 hex digest of the JSON-serialised request payload
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    @staticmethod
    def hash_payload(payload: dict[str, Any]) -> str:
        """Return SHA-256 hex digest of the canonically serialised payload."""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
