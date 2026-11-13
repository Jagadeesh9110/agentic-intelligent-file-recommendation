"""Add the AI full-text retrieval index."""

from alembic import op

revision = "20261113_0002"
down_revision = "20261113_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_document_chunks_normalized_search_text_fts "
        "ON ai.document_chunks USING GIN "
        "(to_tsvector('simple', normalized_search_text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ai.ix_document_chunks_normalized_search_text_fts")
