#!/usr/bin/env python3
"""Guarded, selective Hostinger app release controller.

This is intentionally not invoked by any GitHub workflow. Production activation
requires an operator to install/review the script and configure the host gates.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from release_manifest import (
    COMPONENTS,
    PROTECTED_VOLUMES,
    SERVICES_BY_COMPONENT,
    load_manifest,
    parse_components,
    validate_backup_receipt,
    validate_compose_config,
    validate_rollback_image,
    write_json_atomic,
)


DEFAULT_COMPOSE = Path("/opt/deepfarms/farm/docker-compose.hostinger.yml")
DEFAULT_HEALTHCHECKS = Path(__file__).resolve().parents[2] / "docker-compose.hostinger.healthchecks.yml"
DEFAULT_STATE = Path("/var/lib/deepfarms-deploy")
PROJECT = "farm"


class DeployError(RuntimeError):
    pass


def run_read(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        # Do not echo raw Compose output: it can contain interpolated env values.
        command_name = command[0] if command else "command"
        raise DeployError(f"{command_name} falhou (exit {result.returncode})")
    return result.stdout.strip()


def compose_command(compose_file: Path, healthcheck_file: Path, project: str) -> list[str]:
    return [
        "docker", "compose", "-p", project,
        "-f", str(compose_file), "-f", str(healthcheck_file),
    ]


def read_compose_config(
    compose_file: Path, healthcheck_file: Path, project: str
) -> dict[str, Any]:
    if not compose_file.is_file() or not healthcheck_file.is_file():
        raise DeployError("Compose principal ou overlay de healthchecks não encontrado")
    raw = run_read(
        compose_command(compose_file, healthcheck_file, project) + ["config", "--format", "json"]
    )
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DeployError("docker compose config não retornou JSON válido") from exc
    if not isinstance(config, dict):
        raise DeployError("configuração Compose inválida")
    return config


def inspect_protected_volumes() -> None:
    for name in PROTECTED_VOLUMES:
        found = run_read(["docker", "volume", "inspect", "--format", "{{.Name}}", name])
        if found != name:
            raise DeployError(f"volume protegido ausente ou divergente: {name}")


def _component_image(
    component: str,
    compose_file: Path,
    healthcheck_file: Path,
    project: str,
    release_stamp: str,
) -> str:
    image_ids: set[str] = set()
    for service in SERVICES_BY_COMPONENT[component]:
        container_ids = run_read(
            compose_command(compose_file, healthcheck_file, project) + ["ps", "-q", service]
        ).splitlines()
        if len(container_ids) != 1:
            raise DeployError(f"esperado exatamente um container ativo para {service}")
        image_id = run_read(["docker", "inspect", "--format", "{{.Image}}", container_ids[0]])
        if not image_id.startswith("sha256:"):
            raise DeployError(f"ID da imagem ativa de {service} é inválido")
        image_ids.add(image_id)
    if len(image_ids) != 1:
        raise DeployError(f"serviços do grupo {component} não compartilham a mesma imagem ativa")

    image_id = image_ids.pop()
    alias = f"localhost/deepfarms-rollback/{component}:{release_stamp}-{image_id.removeprefix('sha256:')[:12]}"
    run_read(["docker", "image", "tag", image_id, alias])
    return alias


def snapshot_previous(
    components: tuple[str, ...], compose_file: Path, healthcheck_file: Path, project: str
) -> dict[str, str]:
    release_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return {
        component: _component_image(
            component, compose_file, healthcheck_file, project, release_stamp
        )
        for component in components
    }


def _healthcheck_status(
    service: str, compose_file: Path, healthcheck_file: Path, project: str
) -> str:
    container_ids = run_read(
        compose_command(compose_file, healthcheck_file, project) + ["ps", "-q", service]
    ).splitlines()
    if len(container_ids) != 1:
        return "missing"
    return run_read(["docker", "inspect", "--format", "{{.State.Health.Status}}", container_ids[0]])


def wait_healthy(
    services: tuple[str, ...], compose_file: Path, healthcheck_file: Path,
    project: str, timeout_seconds: int
) -> None:
    deadline = time.monotonic() + timeout_seconds
    pending = set(services)
    while pending and time.monotonic() < deadline:
        pending = {
            service
            for service in pending
            if _healthcheck_status(service, compose_file, healthcheck_file, project) != "healthy"
        }
        if pending:
            time.sleep(2)
    if pending:
        raise DeployError(f"healthcheck não ficou healthy: {', '.join(sorted(pending))}")


def _apply_images(
    images: dict[str, str],
    components: tuple[str, ...],
    compose_file: Path,
    healthcheck_file: Path,
    project: str,
    timeout_seconds: int,
    *,
    pull_images: bool,
) -> None:
    override = {
        "services": {
            service: {"image": images[component]}
            for component in components
            for service in SERVICES_BY_COMPONENT[component]
        }
    }
    services = tuple(service for component in components for service in SERVICES_BY_COMPONENT[component])

    with tempfile.TemporaryDirectory(prefix="deepfarms-compose-release-") as temporary:
        override_path = Path(temporary) / "images.override.json"
        override_path.write_text(json.dumps(override), encoding="utf-8")
        override_path.chmod(0o600)
        command = compose_command(compose_file, healthcheck_file, project) + ["-f", str(override_path)]
        run_read(command + ["config", "--quiet"])
        if pull_images:
            run_read(command + ["pull", *services])
        run_read(command + ["up", "-d", "--no-deps", "--no-build", "--pull", "never", *services])
        wait_healthy(services, compose_file, healthcheck_file, project, timeout_seconds)


def _append_audit(state_dir: Path, event: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    path = state_dir / "deployments.jsonl"
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, sort_keys=True) + "\n")
    path.chmod(0o640)


def _run_deploy(args: argparse.Namespace) -> int:
    if platform.system() != "Linux":
        raise DeployError("o deploy só pode ser executado no host Linux de produção")
    if os.environ.get("DEEPFARMS_DEPLOY_TARGET") != "hostinger" or not args.confirm_production:
        raise DeployError(
            "deploy bloqueado: defina DEEPFARMS_DEPLOY_TARGET=hostinger e passe "
            "--confirm-production após revisão operacional"
        )

    components = parse_components(args.components)
    manifest = load_manifest(Path(args.manifest))
    if set(components) - set(manifest["images"]):
        raise DeployError("o manifesto não contém imagens para todos os componentes selecionados")
    receipt = validate_backup_receipt(Path(args.backup_receipt))

    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    lock_path = args.state_dir / "deploy.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = read_compose_config(args.compose_file, args.healthcheck_file, args.project)
        services = validate_compose_config(config, components)
        inspect_protected_volumes()
        previous_images = snapshot_previous(
            components, args.compose_file, args.healthcheck_file, args.project
        )
        previous_path = args.state_dir / "previous.json"
        write_json_atomic(
            previous_path,
            {"schema_version": 1, "images": previous_images, "saved_at": datetime.now(timezone.utc).isoformat()},
        )

        try:
            _apply_images(
                manifest["images"], components, args.compose_file, args.healthcheck_file,
                args.project, args.health_timeout, pull_images=True,
            )
        except (DeployError, OSError) as deploy_error:
            try:
                _apply_images(
                    previous_images, components, args.compose_file, args.healthcheck_file,
                    args.project, args.health_timeout, pull_images=False,
                )
                rollback_result = "automatic-app-rollback-healthy"
            except (DeployError, OSError) as rollback_error:
                rollback_result = "rollback-failed"
                _append_audit(
                    args.state_dir,
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "commit": manifest["commit"],
                        "components": list(components),
                        "result": rollback_result,
                    },
                )
                raise DeployError(
                    f"deploy falhou e rollback de aplicação também falhou: {rollback_error}"
                ) from deploy_error
            _append_audit(
                args.state_dir,
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "commit": manifest["commit"],
                    "components": list(components),
                    "result": rollback_result,
                },
            )
            raise DeployError(f"deploy falhou; versão anterior restaurada: {deploy_error}") from deploy_error

        write_json_atomic(
            args.state_dir / "last.json",
            {
                "schema_version": 1,
                "commit": manifest["commit"],
                "components": list(components),
                "images": {component: manifest["images"][component] for component in components},
                "deployed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        _append_audit(
            args.state_dir,
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "commit": manifest["commit"],
                "components": list(components),
                "backup_artifact": Path(receipt["artifact"]).name,
                "result": "healthy",
            },
        )
    print(f"Deploy saudável: {manifest['commit']} ({', '.join(components)})")
    return 0


def _run_rollback(args: argparse.Namespace) -> int:
    if platform.system() != "Linux":
        raise DeployError("rollback só pode ser executado no host Linux de produção")
    if os.environ.get("DEEPFARMS_DEPLOY_TARGET") != "hostinger" or not args.confirm_production:
        raise DeployError("rollback bloqueado sem confirmação explícita do alvo Hostinger")
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o750)
    with (args.state_dir / "deploy.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous_path = args.state_dir / "previous.json"
        if not previous_path.is_file():
            raise DeployError("não existe manifesto de imagem anterior")
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        images = previous.get("images") if isinstance(previous, dict) else None
        if not isinstance(images, dict) or not images:
            raise DeployError("manifesto de rollback inválido")
        components = tuple(images)
        if set(components) - set(COMPONENTS):
            raise DeployError("manifesto de rollback contém componente não permitido")
        for component, reference in images.items():
            validate_rollback_image(component, reference)
            image_id = run_read(["docker", "image", "inspect", "--format", "{{.Id}}", reference])
            if not image_id.startswith("sha256:") or not image_id.removeprefix("sha256:").startswith(
                reference.rsplit("-", 1)[-1]
            ):
                raise DeployError(f"imagem local de rollback divergente para {component}")
        config = read_compose_config(args.compose_file, args.healthcheck_file, args.project)
        services = validate_compose_config(config, components)
        inspect_protected_volumes()

        current = snapshot_previous(
            components, args.compose_file, args.healthcheck_file, args.project
        )
        try:
            _apply_images(
                images, components, args.compose_file, args.healthcheck_file,
                args.project, args.health_timeout, pull_images=False,
            )
        except (DeployError, OSError) as exc:
            _append_audit(
                args.state_dir,
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "components": list(components),
                    "result": "manual-recovery-required",
                },
            )
            raise DeployError(f"rollback não ficou saudável; recuperação manual necessária: {exc}") from exc
        write_json_atomic(
            previous_path,
            {"schema_version": 1, "images": current, "saved_at": datetime.now(timezone.utc).isoformat()},
        )
        _append_audit(
            args.state_dir,
            {"at": datetime.now(timezone.utc).isoformat(), "components": list(components), "result": "rollback-healthy"},
        )
    print(f"Rollback saudável: {', '.join(components)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("deploy", "rollback"):
        sub = subparsers.add_parser(action)
        sub.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE)
        sub.add_argument("--healthcheck-file", type=Path, default=DEFAULT_HEALTHCHECKS)
        sub.add_argument("--project", default=PROJECT, choices=(PROJECT,))
        sub.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
        sub.add_argument("--health-timeout", type=int, default=180, choices=range(30, 601))
        sub.add_argument("--confirm-production", action="store_true")
        if action == "deploy":
            sub.add_argument("--manifest", required=True)
            sub.add_argument("--components", required=True)
            sub.add_argument("--backup-receipt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run_deploy(args) if args.action == "deploy" else _run_rollback(args)
    except (DeployError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"deploy controlado: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
