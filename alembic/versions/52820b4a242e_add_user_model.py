"""add_user_model

Revision ID: 52820b4a242e
Revises:
Create Date: 2026-04-21 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "52820b4a242e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("hashed_password", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("patient_pseudonym", sa.String(length=256), nullable=True),
        sa.Column("sequencing_platform", sa.String(length=64), nullable=True),
        sa.Column("panel_version", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_samples_user_id"), "samples", ["user_id"], unique=False)

    op.create_table(
        "variants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.Column("chrom", sa.String(length=32), nullable=False),
        sa.Column("pos", sa.Integer(), nullable=False),
        sa.Column("ref", sa.Text(), nullable=False),
        sa.Column("alt", sa.Text(), nullable=False),
        sa.Column("gene_symbol", sa.String(length=64), nullable=True),
        sa.Column("hgvs_c", sa.String(length=256), nullable=True),
        sa.Column("hgvs_p", sa.String(length=256), nullable=True),
        sa.Column("consequence", sa.String(length=64), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("gnomad_af", sa.Float(), nullable=True),
        sa.Column("raw_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "classifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=64), nullable=False),
        sa.Column("pathogenic_score", sa.Float(), nullable=False),
        sa.Column("evidence_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("classified_by", sa.String(length=128), nullable=True),
        sa.Column("is_automated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("classifications")
    op.drop_table("variants")
    op.drop_index(op.f("ix_samples_user_id"), table_name="samples")
    op.drop_table("samples")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
