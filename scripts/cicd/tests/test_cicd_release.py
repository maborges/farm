from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from changed_components import affected_components
from deploy_hostinger import (
    _apply_images,
    _rollback_components,
    _service_image_map,
    main as deploy_main,
    snapshot_previous,
)
from release_manifest import (
    make_override,
    parse_components,
    validate_backup_receipt,
    validate_compose_config,
    validate_manifest,
    validate_rollback_image,
)


COMMIT = "a" * 40


def image(component: str, digest_char: str = "b") -> str:
    return f"ghcr.io/maborges/deepfarms-{component}@sha256:{digest_char * 64}"


def compose_config() -> dict:
    return {
        "services": {
            "postgres": {"volumes": [{"type": "volume", "source": "pg"}]},
            "redis": {"volumes": [{"type": "volume", "source": "cache"}]},
            "api": {"healthcheck": {"test": ["CMD", "true"]}},
            "automations-worker": {"healthcheck": {"test": ["CMD", "true"]}},
            "background-worker": {"healthcheck": {"test": ["CMD", "true"]}},
            "outbox-worker": {"healthcheck": {"test": ["CMD", "true"]}},
            "web": {"healthcheck": {"test": ["CMD", "true"]}},
            "campo": {"healthcheck": {"test": ["CMD", "true"]}},
            "agro": {
                "healthcheck": {"test": ["CMD", "true"]},
                "volumes": [{"type": "volume", "source": "uploads"}],
            },
        },
        "volumes": {
            "pg": {"name": "farm_postgres_data"},
            "cache": {"name": "farm_redis_data"},
            "uploads": {"name": "farm_uploads_data"},
        },
    }


class ChangedComponentsTests(unittest.TestCase):
    def test_component_specific_change_only_rebuilds_that_image(self) -> None:
        self.assertEqual(affected_components(["apps/campo/src/app/page.tsx"]), {"campo"})

    def test_shared_workspace_change_rebuilds_all_frontends(self) -> None:
        self.assertEqual(
            affected_components(["packages/types/src/index.ts"]), {"web", "campo", "agro"}
        )

    def test_backend_scripts_change_rebuilds_shared_backend_image(self) -> None:
        self.assertEqual(affected_components(["scripts/run_worker.py"]), {"backend"})

    def test_docs_do_not_trigger_image_builds(self) -> None:
        self.assertEqual(affected_components(["docs/guide.md"]), set())


class ManifestTests(unittest.TestCase):
    def test_accepts_full_sha_and_immutable_ghcr_digest(self) -> None:
        manifest = {"schema_version": 1, "commit": COMMIT, "images": {"backend": image("backend")}}
        self.assertEqual(validate_manifest(manifest), manifest)

    def test_rejects_mutable_tag(self) -> None:
        manifest = {
            "schema_version": 1,
            "commit": COMMIT,
            "images": {"backend": "ghcr.io/maborges/deepfarms-backend:latest"},
        }
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_rejects_image_from_wrong_component_repository(self) -> None:
        with self.assertRaises(ValueError):
            validate_manifest(
                {"schema_version": 1, "commit": COMMIT, "images": {"web": image("backend")}}
            )

    def test_rejects_image_from_unapproved_registry_owner(self) -> None:
        manifest = {
            "schema_version": 1,
            "commit": COMMIT,
            "images": {"backend": image("backend").replace("maborges", "someone-else")},
        }
        with self.assertRaisesRegex(ValueError, "owner GHCR autorizado"):
            validate_manifest(manifest)

    def test_accepts_component_scoped_local_rollback_alias(self) -> None:
        validate_rollback_image(
            "backend", "localhost/deepfarms-rollback/backend:20261103T120000Z-0123456789ab"
        )

    def test_rejects_rollback_alias_for_wrong_component_or_mutable_name(self) -> None:
        with self.assertRaises(ValueError):
            validate_rollback_image(
                "web", "localhost/deepfarms-rollback/backend:20261103T120000Z-0123456789ab"
            )
        with self.assertRaises(ValueError):
            validate_rollback_image("web", "deepfarms-web:pilot")

    def test_backend_is_a_coordinated_four_service_group(self) -> None:
        self.assertEqual(
            parse_components("backend"),
            ("backend",),
        )
        self.assertEqual(
            make_override(
                {"schema_version": 1, "commit": COMMIT, "images": {"backend": image("backend")}},
                ("backend",),
            ),
            {
                "services": {
                    "api": {"image": image("backend")},
                    "automations-worker": {"image": image("backend")},
                    "background-worker": {"image": image("backend")},
                    "outbox-worker": {"image": image("backend")},
                }
            },
        )

    def test_override_cannot_touch_postgres_or_redis(self) -> None:
        override = make_override(
            {"schema_version": 1, "commit": COMMIT, "images": {"web": image("web")}},
            ("web",),
        )
        self.assertEqual(set(override["services"]), {"web"})
        self.assertNotIn("postgres", override["services"])
        self.assertNotIn("redis", override["services"])


class ComposeGuardTests(unittest.TestCase):
    def test_hostinger_healthcheck_overlay_only_adds_healthchecks(self) -> None:
        overlay_path = Path(__file__).resolve().parents[3] / "docker-compose.hostinger.healthchecks.yml"
        overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
        self.assertEqual(set(overlay), {"services"})
        self.assertEqual(
            set(overlay["services"]),
            {
                "api", "automations-worker", "background-worker", "outbox-worker",
                "web", "campo", "agro", "redis",
            },
        )
        for definition in overlay["services"].values():
            self.assertEqual(set(definition), {"healthcheck"})
            self.assertIn("test", definition["healthcheck"])
        self.assertNotIn("postgres", overlay["services"])

    def test_rejects_missing_app_healthcheck(self) -> None:
        config = compose_config()
        del config["services"]["web"]["healthcheck"]
        with self.assertRaisesRegex(ValueError, "sem healthcheck"):
            validate_compose_config(config, ("web",))

    def test_rejects_missing_protected_volume(self) -> None:
        config = compose_config()
        del config["volumes"]["pg"]
        with self.assertRaisesRegex(ValueError, "volumes protegidos"):
            validate_compose_config(config, ("web",))

    def test_accepts_protected_volumes_and_application_healthcheck(self) -> None:
        services = validate_compose_config(compose_config(), ("backend", "web"))
        self.assertEqual(
            services,
            ("api", "automations-worker", "background-worker", "outbox-worker", "web"),
        )


class BackupReceiptTests(unittest.TestCase):
    def test_requires_recent_checked_backup_and_scheduled_job_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            backup = root / "farms.dump"
            backup.write_bytes(b"isolated backup fixture")
            now = datetime.now(timezone.utc)
            receipt = {
                "artifact": str(backup),
                "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
                "verified_at": now.isoformat(),
                "scheduled_job_verified": True,
                "temporary_file_handling_verified": True,
                "restore_test": "passed",
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(validate_backup_receipt(receipt_path, now=now), receipt)

            receipt["scheduled_job_verified"] = False
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cron/backup"):
                validate_backup_receipt(receipt_path, now=now)

            receipt["scheduled_job_verified"] = True
            receipt["temporary_file_handling_verified"] = False
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "arquivos temporários"):
                validate_backup_receipt(receipt_path, now=now)

    def test_rejects_artifact_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            backup = root / "farms.dump"
            backup.write_bytes(b"not the checksum in receipt")
            now = datetime.now(timezone.utc)
            receipt = {
                "artifact": str(backup),
                "sha256": "0" * 64,
                "verified_at": now.isoformat(),
                "scheduled_job_verified": True,
                "temporary_file_handling_verified": True,
                "restore_test": "passed",
            }
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                validate_backup_receipt(receipt_path, now=now)


class DeploySafetyTests(unittest.TestCase):
    def test_backend_snapshot_keeps_distinct_previous_image_per_service(self) -> None:
        calls = []
        service_image_ids = {
            "api": "sha256:" + "a" * 64,
            "automations-worker": "sha256:" + "b" * 64,
            "background-worker": "sha256:" + "c" * 64,
            "outbox-worker": "sha256:" + "d" * 64,
        }

        def fake_run_read(command: list[str], **_: object) -> str:
            calls.append(command)
            if command[0:2] == ["docker", "compose"]:
                return f"container-{command[-1]}"
            if command[:3] == ["docker", "inspect", "--format"]:
                return service_image_ids[command[-1].removeprefix("container-")]
            if command[:3] == ["docker", "image", "tag"]:
                return ""
            raise AssertionError("comando inesperado no teste")

        with patch("deploy_hostinger.run_read", side_effect=fake_run_read):
            references = snapshot_previous(
                ("backend",), Path("compose.yml"), Path("health.yml"), "farm"
            )

        self.assertEqual(set(references), set(service_image_ids))
        for service, image_id in service_image_ids.items():
            reference = references[service]
            validate_rollback_image(service, reference)
            self.assertIn(f"/backend/{service}:", reference)
            self.assertTrue(reference.endswith("-" + image_id.removeprefix("sha256:")[:12]))
        self.assertEqual(sum(command[:3] == ["docker", "image", "tag"] for command in calls), 4)

    def test_backend_rollback_expands_each_saved_service_image_individually(self) -> None:
        references = {
            "api": "localhost/deepfarms-rollback/backend/api:20261103T120000Z-aaaaaaaaaaaa",
            "automations-worker": "localhost/deepfarms-rollback/backend/automations-worker:20261103T120000Z-bbbbbbbbbbbb",
            "background-worker": "localhost/deepfarms-rollback/backend/background-worker:20261103T120000Z-cccccccccccc",
            "outbox-worker": "localhost/deepfarms-rollback/backend/outbox-worker:20261103T120000Z-dddddddddddd",
        }

        components = _rollback_components(references, 2)
        self.assertEqual(components, ("backend",))
        self.assertEqual(_service_image_map(references, components), references)

    def test_backend_rollback_compose_override_keeps_each_service_reference(self) -> None:
        references = {
            "api": "localhost/deepfarms-rollback/backend/api:20261103T120000Z-aaaaaaaaaaaa",
            "automations-worker": "localhost/deepfarms-rollback/backend/automations-worker:20261103T120000Z-bbbbbbbbbbbb",
            "background-worker": "localhost/deepfarms-rollback/backend/background-worker:20261103T120000Z-cccccccccccc",
            "outbox-worker": "localhost/deepfarms-rollback/backend/outbox-worker:20261103T120000Z-dddddddddddd",
        }
        captured_overrides = []

        def fake_run_read(command: list[str], **_: object) -> str:
            if command[-2:] == ["config", "--quiet"]:
                file_args = [index + 1 for index, part in enumerate(command[:-1]) if part == "-f"]
                captured_overrides.append(json.loads(Path(command[file_args[-1]]).read_text()))
            return ""

        with patch("deploy_hostinger.run_read", side_effect=fake_run_read), patch(
            "deploy_hostinger.wait_healthy"
        ):
            _apply_images(
                references,
                ("backend",),
                Path("compose.yml"),
                Path("health.yml"),
                "farm",
                180,
                pull_images=False,
            )

        self.assertEqual(
            captured_overrides,
            [{"services": {service: {"image": ref} for service, ref in references.items()}}],
        )

    def test_legacy_component_rollback_state_remains_supported(self) -> None:
        references = {
            "backend": "localhost/deepfarms-rollback/backend:20261103T120000Z-aaaaaaaaaaaa"
        }
        components = _rollback_components(references, 1)
        self.assertEqual(components, ("backend",))
        self.assertEqual(
            set(_service_image_map(references, components)),
            {"api", "automations-worker", "background-worker", "outbox-worker"},
        )

    def test_single_service_name_matching_component_is_still_service_rollback(self) -> None:
        references = {
            "web": "localhost/deepfarms-rollback/web/web:20261103T120000Z-eeeeeeeeeeee"
        }
        self.assertEqual(_rollback_components(references, 2), ("web",))
        validate_rollback_image("web", references["web"])

    def test_deploy_refuses_to_run_without_two_production_gates(self) -> None:
        stderr = StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(stderr):
            result = deploy_main(
                [
                    "deploy",
                    "--manifest",
                    "/not-read.json",
                    "--components",
                    "web",
                    "--backup-receipt",
                    "/not-read-backup.json",
                ]
            )
        self.assertEqual(result, 2)
        self.assertIn("deploy bloqueado", stderr.getvalue())

    def test_deploy_script_never_runs_database_migrations_or_volume_removal(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "deploy_hostinger.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("alembic", source.lower())
        self.assertNotIn("--volumes", source)
        self.assertIn('"--no-deps"', source)


if __name__ == "__main__":
    unittest.main()
