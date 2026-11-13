import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentExecutionTrace(Base):
    __tablename__ = "agent_execution_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    search_query_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    normalized_query: Mapped[str | None] = mapped_column(Text)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    selected_strategy: Mapped[str | None] = mapped_column(String(32))
    attempts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    tool_decisions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    result_counts: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    timings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    termination_reason: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
