# Shared database views

No cross-schema views are introduced initially. Service communication uses the versioned internal FastAPI contract, while Next.js remains authoritative for file visibility and authorization.

A future shared read-only view would require explicit approval, documented ownership, and coordinated migration. It must not bypass the rule that soft-deleted files are excluded from new search results.
