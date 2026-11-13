from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config.settings import settings
from app.db import models  # noqa: F401
from app.db.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.ai_database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _object_schema(object_) -> str | None:
    schema = getattr(object_, "schema", None)
    if schema is not None:
        return schema
    table = getattr(object_, "table", None)
    return getattr(table, "schema", None)


def include_object(object_, name, type_, reflected, compare_to):
    if type_ == "schema":
        return name == "ai"
    return _object_schema(object_) == "ai"


def run_migrations_offline() -> None:
    context.configure(
        url=settings.ai_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
