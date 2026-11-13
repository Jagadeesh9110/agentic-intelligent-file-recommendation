from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models.file_processing_run import FileProcessingRun, ProcessingRunStatus
from app.db.processing_runs import (
    ProcessingActivationError,
    activate_processing_run,
)


class _Transaction(AbstractContextManager[None]):
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __enter__(self) -> None:
        self.session.snapshot = [
            (run, run.status, run.activated_at) for run in self.session.runs
        ]

    def __exit__(self, exception_type, exception, traceback) -> bool:
        if exception_type is not None:
            self.session.rollback()
        return False


class _FakeSession:
    def __init__(
        self,
        scalar_results: list[FileProcessingRun | None],
        *,
        fail_on_flush_number: int | None = None,
        transaction_active: bool = False,
    ) -> None:
        self.runs = [run for run in scalar_results if run is not None]
        self.scalar_results = iter(scalar_results)
        self.fail_on_flush_number = fail_on_flush_number
        self.transaction_active = transaction_active
        self.snapshot: list[
            tuple[FileProcessingRun, ProcessingRunStatus, datetime | None]
        ] = []
        self.rollback_count = 0
        self.begin_called = False
        self.statements = []
        self.flush_count = 0

    def begin(self) -> _Transaction:
        if self.transaction_active:
            raise RuntimeError("session already has an active transaction")
        self.begin_called = True
        return _Transaction(self)

    def scalar(self, statement):
        self.statements.append(statement)
        return next(self.scalar_results)

    def flush(self) -> None:
        self.flush_count += 1
        if self.fail_on_flush_number == self.flush_count:
            raise RuntimeError("simulated activation failure")

    def rollback(self) -> None:
        self.rollback_count += 1
        for run, status, activated_at in self.snapshot:
            run.status = status
            run.activated_at = activated_at


def _run(
    file_id,
    status: ProcessingRunStatus,
) -> FileProcessingRun:
    return FileProcessingRun(
        id=uuid4(),
        file_id=file_id,
        source_checksum="checksum",
        status=status,
    )


def test_activation_supersedes_previous_run_and_activates_target() -> None:
    file_id = uuid4()
    previous = _run(file_id, ProcessingRunStatus.ACTIVE)
    target = _run(file_id, ProcessingRunStatus.PROCESSING)
    session = _FakeSession([target, previous])

    activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert previous.status is ProcessingRunStatus.SUPERSEDED
    assert target.status is ProcessingRunStatus.ACTIVE
    assert target.activated_at is not None
    assert session.rollback_count == 0


def test_activation_rolls_back_when_activation_fails() -> None:
    file_id = uuid4()
    previous = _run(file_id, ProcessingRunStatus.ACTIVE)
    target = _run(file_id, ProcessingRunStatus.PROCESSING)
    session = _FakeSession([target, previous], fail_on_flush_number=2)

    with pytest.raises(RuntimeError, match="simulated activation failure"):
        activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert previous.status is ProcessingRunStatus.ACTIVE
    assert target.status is ProcessingRunStatus.PROCESSING
    assert target.activated_at is None
    assert session.rollback_count == 1


def test_activation_rejects_a_run_not_owned_by_the_file() -> None:
    file_id = uuid4()
    target = _run(uuid4(), ProcessingRunStatus.PROCESSING)
    session = _FakeSession([None])

    with pytest.raises(
        ProcessingActivationError, match="does not belong to the supplied file"
    ):
        activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert target.status is ProcessingRunStatus.PROCESSING


@pytest.mark.parametrize(
    "status",
    [ProcessingRunStatus.ACTIVE, ProcessingRunStatus.FAILED],
)
def test_activation_rejects_invalid_target_status(status: ProcessingRunStatus) -> None:
    file_id = uuid4()
    target = _run(file_id, status)
    session = _FakeSession([target])

    with pytest.raises(ProcessingActivationError, match="Only a PROCESSING run"):
        activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert target.status is status


def test_activation_does_not_change_another_files_run() -> None:
    file_id = uuid4()
    other_file_id = uuid4()
    target = _run(file_id, ProcessingRunStatus.PROCESSING)
    unrelated = _run(other_file_id, ProcessingRunStatus.ACTIVE)
    session = _FakeSession([target, None])

    activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert target.status is ProcessingRunStatus.ACTIVE
    assert unrelated.status is ProcessingRunStatus.ACTIVE


def test_activation_scopes_previous_run_query_to_file() -> None:
    file_id = uuid4()
    previous = _run(file_id, ProcessingRunStatus.ACTIVE)
    target = _run(file_id, ProcessingRunStatus.PROCESSING)
    session = _FakeSession([target, previous])

    activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert "file_processing_runs.file_id" in str(session.statements[1])


def test_activation_requires_a_fresh_session() -> None:
    file_id = uuid4()
    target = _run(file_id, ProcessingRunStatus.PROCESSING)
    session = _FakeSession([target], transaction_active=True)

    with pytest.raises(RuntimeError, match="active transaction"):
        activate_processing_run(session, file_id=file_id, processing_run_id=target.id)

    assert session.begin_called is False
