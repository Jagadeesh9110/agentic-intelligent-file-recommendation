from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document_chunk import DocumentChunk


class ProcessingRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FileProcessingRun(Base):
    __tablename__ = "file_processing_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[ProcessingRunStatus] = mapped_column(
        Enum(ProcessingRunStatus, name="processing_run_status", schema="ai"),
        nullable=False,
        default=ProcessingRunStatus.QUEUED,
        server_default=text("'QUEUED'::ai.processing_run_status"),
    )
    processing_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_details: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="processing_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("id", "file_id", name="uq_file_processing_runs_id_file_id"),
        Index(
            "uq_file_processing_runs_active_file",
            "file_id",
            unique=True,
            postgresql_where=status == ProcessingRunStatus.ACTIVE,
        ),
    )
