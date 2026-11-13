from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus


class ProcessingActivationError(ValueError):
    """Raised when a processing run cannot be activated."""


def activate_processing_run(
    session: Session,
    *,
    file_id: UUID,
    processing_run_id: UUID,
) -> None:
    """Atomically replace the active processing run for a file.

    The caller must provide a fresh SQLAlchemy session with no active
    transaction. This function owns the transaction and its commit/rollback
    lifecycle; callers must not wrap it in another transaction.
    """
    with session.begin():
        target = session.scalar(
            select(FileProcessingRun).where(
                FileProcessingRun.id == processing_run_id,
                FileProcessingRun.file_id == file_id,
            )
        )
        if target is None:
            raise ProcessingActivationError(
                "The processing run does not belong to the supplied file."
            )
        if target.status is not ProcessingRunStatus.PROCESSING:
            raise ProcessingActivationError("Only a PROCESSING run can be activated.")

        previous = session.scalar(
            select(FileProcessingRun).where(
                FileProcessingRun.file_id == file_id,
                FileProcessingRun.status == ProcessingRunStatus.ACTIVE,
                FileProcessingRun.id != processing_run_id,
            )
        )
        if previous is not None:
            previous.status = ProcessingRunStatus.SUPERSEDED
            session.flush()

        target.status = ProcessingRunStatus.ACTIVE
        target.activated_at = datetime.now(UTC)
        session.flush()
