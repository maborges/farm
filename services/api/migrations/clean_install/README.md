# Clean install lineage

This script location is an independent install snapshot. It has its own
`farms.deepfarms_install_version` table and must never mark the historical
Alembic head as applied. Existing installations continue to use
`services/api/migrations` and its original version table.

The first snapshot invokes the existing baseline revision implementation and
then applies the explicit `clean_install.seed_contract`. Future clean-install
changes must be additive revisions in `versions/` here; upgrades for existing
installations remain in the historical graph and require a separately reviewed
bridge/release policy. No such bridge is implied by this initial snapshot.

