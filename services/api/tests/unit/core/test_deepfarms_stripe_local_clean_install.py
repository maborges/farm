from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from sqlalchemy.engine import URL


REPO_ROOT = Path(__file__).resolve().parents[5]
RUNNER_PATH = REPO_ROOT / "scripts/homologacao/deepfarms_stripe_local_clean_install.py"
SPEC = importlib.util.spec_from_file_location("stripe_local_clean_install", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _target_url(**overrides: object) -> str:
    values = {
        "drivername": "postgresql+asyncpg",
        "username": runner.EXPECTED_USER,
        "password": "test-only",
        "host": runner.EXPECTED_HOST,
        "port": runner.EXPECTED_PORT,
        "database": runner.EXPECTED_DATABASE,
    }
    values.update(overrides)
    return URL.create(**values).render_as_string(hide_password=False)


class StripeLocalCleanInstallTests(unittest.TestCase):
    def test_runner_aceita_somente_destino_local_autorizado(self) -> None:
        runner._validate_target_url(_target_url())

    def test_runner_le_senha_da_variavel_especifica(self) -> None:
        password = "credential-from-local-environment"
        self.assertEqual(
            runner._resolve_password({"DEEPFARMS_STRIPE_TEST_PASSWORD": password}),
            password,
        )

    def test_runner_aceita_pgpassword_quando_variavel_especifica_ausente(self) -> None:
        password = "credential-from-psql-environment"
        self.assertEqual(runner._resolve_password({"PGPASSWORD": password}), password)

    def test_runner_prioriza_credencial_especifica_do_alvo(self) -> None:
        self.assertEqual(
            runner._resolve_password(
                {
                    "DEEPFARMS_STRIPE_TEST_PASSWORD": "dedicated",
                    "PGPASSWORD": "generic",
                }
            ),
            "dedicated",
        )

    def test_runner_recusa_execucao_sem_credencial(self) -> None:
        with self.assertRaisesRegex(runner.InstallGateError, "Credencial ausente"):
            runner._resolve_password({})

    def test_runner_rejeita_destinos_diferentes(self) -> None:
        mismatches = (
            {"host": "192.168.0.2"},
            {"port": 5432},
            {"database": "farms"},
            {"username": "borgus"},
            {"drivername": "postgresql+psycopg"},
            {"query": {"host": "/var/run/postgresql"}},
        )
        for override in mismatches:
            with self.subTest(override=override):
                with self.assertRaisesRegex(runner.InstallGateError, "Destino recusado"):
                    runner._validate_target_url(_target_url(**override))

    def test_runner_vincula_ip_interno_ao_container_que_publica_a_porta_autorizada(self) -> None:
        addresses = runner._container_internal_addresses(
            running=True,
            port_bindings={
                "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55432"}]
            },
            networks={"bridge": {"IPAddress": "172.17.0.2"}},
        )
        self.assertEqual(addresses, frozenset({"172.17.0.2"}))

    def test_runner_rejeita_container_com_publicacao_ou_rede_divergente(self) -> None:
        invalid_containers = (
            {
                "running": False,
                "port_bindings": {
                    "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55432"}]
                },
                "networks": {"bridge": {"IPAddress": "172.17.0.2"}},
            },
            {
                "running": True,
                "port_bindings": {
                    "5432/tcp": [{"HostIp": "0.0.0.0", "HostPort": "55432"}]
                },
                "networks": {"bridge": {"IPAddress": "172.17.0.2"}},
            },
            {
                "running": True,
                "port_bindings": {
                    "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55432"}]
                },
                "networks": {"bridge": {"IPAddress": "8.8.8.8"}},
            },
        )
        for container in invalid_containers:
            with self.subTest(container=container):
                with self.assertRaises(runner.InstallGateError):
                    runner._container_internal_addresses(**container)

    def test_runner_aceita_identidade_postgresql_16_autorizada(self) -> None:
        container_addresses = frozenset({"172.17.0.2"})
        runner._validate_database_identity(
            (
                "deepfarms_stripe_test",
                "stripe_test",
                "172.17.0.2",
                runner.EXPECTED_POSTGRES_PORT,
                160005,
            ),
            container_addresses,
        )

    def test_runner_rejeita_identidade_efetiva_diferente(self) -> None:
        container_addresses = frozenset({"172.17.0.2"})
        mismatches = (
            ("farms", "stripe_test", "172.17.0.2", 5432, 160005),
            ("deepfarms_stripe_test", "borgus", "172.17.0.2", 5432, 160005),
            ("deepfarms_stripe_test", "stripe_test", "172.17.0.3", 5432, 160005),
            ("deepfarms_stripe_test", "stripe_test", "127.0.0.1", 5432, 160005),
            ("deepfarms_stripe_test", "stripe_test", "172.17.0.2", 55432, 160005),
            ("deepfarms_stripe_test", "stripe_test", "172.17.0.2", 5432, 150000),
        )
        for identity in mismatches:
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(
                    runner.InstallGateError, "Identidade PostgreSQL efetiva"
                ):
                    runner._validate_database_identity(identity, container_addresses)

    def test_runner_recusa_banco_com_objetos_ou_historico(self) -> None:
        states = (
            {"schema_exists": True, "application_objects": 0, "migration_history": False},
            {"schema_exists": False, "application_objects": 1, "migration_history": False},
            {"schema_exists": False, "application_objects": 0, "migration_history": True},
        )
        for state in states:
            with self.subTest(state=state):
                with self.assertRaisesRegex(runner.InstallGateError, "Instalação recusada"):
                    runner._validate_empty_database(**state)

    def test_runner_aceita_banco_sem_objetos_de_aplicacao(self) -> None:
        runner._validate_empty_database(
            schema_exists=False, application_objects=0, migration_history=False
        )


if __name__ == "__main__":
    unittest.main()
