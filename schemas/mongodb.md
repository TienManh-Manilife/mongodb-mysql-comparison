# MongoDB document layout

Equivalent: one collection per logical table in `benchmark/schema.py`. The logical primary key is stored as `_id` plus its original column name, for stable export and projection. Core indexes include `_id`, unique `cccd` and indexes matching MySQL FK access paths; secondary indexes are created by the runner.

Optimized: `provinces`, `wards`, `households`, `persons`; each person document additionally stores `household_id`, `relationship_to_head`, `current_ward_code`, and `residences` (array of all logical residence_history records). This removes two separate collections. Household data and administrative names remain referenced to avoid unnecessary duplication. MySQL remains normalized in both profiles (same schema and index modes). No database-side MongoDB FK constraint is claimed; source validation enforces the logical relationships at import time.

The optimized profile is a read-oriented schema comparison, not an implementation of complete household/residence update transactions. The write workloads act on person records only.
