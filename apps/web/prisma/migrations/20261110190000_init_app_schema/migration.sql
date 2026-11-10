-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "app";

-- CreateEnum
CREATE TYPE "app"."catalog_status" AS ENUM ('ACTIVE', 'DELETED');

-- CreateTable
CREATE TABLE "app"."files" (
    "id" UUID NOT NULL,
    "relative_path" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "extension" VARCHAR(32),
    "mime_type" VARCHAR(255),
    "size_bytes" BIGINT NOT NULL,
    "checksum" VARCHAR(128) NOT NULL,
    "catalog_status" "app"."catalog_status" NOT NULL DEFAULT 'ACTIVE',
    "deleted_at" TIMESTAMPTZ(6),
    "deletion_reason" TEXT,
    "source_created_at" TIMESTAMPTZ(6),
    "source_modified_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "files_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "app"."search_queries" (
    "id" UUID NOT NULL,
    "raw_query" TEXT,
    "normalized_query" TEXT NOT NULL,
    "filters" JSONB,
    "selected_strategy" VARCHAR(32),
    "trace_id" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "search_queries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "app"."search_result_events" (
    "id" UUID NOT NULL,
    "search_query_id" UUID NOT NULL,
    "file_id" UUID NOT NULL,
    "rank" INTEGER NOT NULL,
    "score" DOUBLE PRECISION,
    "retrieval_sources" TEXT[] NOT NULL,
    "opened" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "search_result_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "app"."file_access_events" (
    "id" UUID NOT NULL,
    "file_id" UUID NOT NULL,
    "action" VARCHAR(32) NOT NULL,
    "success" BOOLEAN NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "file_access_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "app"."user_preferences" (
    "id" INTEGER NOT NULL DEFAULT 1,
    "preference_data" JSONB,
    "personalization_enabled" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "user_preferences_pkey" PRIMARY KEY ("id")
);

-- PostgreSQL-specific integrity constraints
ALTER TABLE "app"."files"
    ADD CONSTRAINT "files_catalog_status_deleted_at_check"
    CHECK (
        ("catalog_status" = 'DELETED' AND "deleted_at" IS NOT NULL)
        OR
        ("catalog_status" = 'ACTIVE' AND "deleted_at" IS NULL)
    );

ALTER TABLE "app"."user_preferences"
    ADD CONSTRAINT "user_preferences_singleton_id_check"
    CHECK ("id" = 1);

-- CreateIndex
CREATE INDEX "files_catalog_status_idx" ON "app"."files"("catalog_status");

-- CreateIndex
CREATE INDEX "files_relative_path_idx" ON "app"."files"("relative_path");

-- PostgreSQL-specific partial unique index: deleted paths may be reused.
CREATE UNIQUE INDEX "uq_files_active_relative_path"
    ON "app"."files"("relative_path")
    WHERE "catalog_status" <> 'DELETED';

-- CreateIndex
CREATE INDEX "files_checksum_idx" ON "app"."files"("checksum");

-- CreateIndex
CREATE INDEX "search_queries_created_at_idx" ON "app"."search_queries"("created_at");

-- CreateIndex
CREATE INDEX "search_result_events_file_id_created_at_idx" ON "app"."search_result_events"("file_id", "created_at");

-- CreateIndex
CREATE UNIQUE INDEX "search_result_events_search_query_id_file_id_key" ON "app"."search_result_events"("search_query_id", "file_id");

-- CreateIndex
CREATE INDEX "file_access_events_file_id_created_at_idx" ON "app"."file_access_events"("file_id", "created_at");

-- AddForeignKey
ALTER TABLE "app"."search_result_events" ADD CONSTRAINT "search_result_events_search_query_id_fkey" FOREIGN KEY ("search_query_id") REFERENCES "app"."search_queries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "app"."search_result_events" ADD CONSTRAINT "search_result_events_file_id_fkey" FOREIGN KEY ("file_id") REFERENCES "app"."files"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "app"."file_access_events" ADD CONSTRAINT "file_access_events_file_id_fkey" FOREIGN KEY ("file_id") REFERENCES "app"."files"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
