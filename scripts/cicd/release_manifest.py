#!/usr/bin/env python3
"""Validation and Compose overlay helpers for immutable app releases."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMPONENTS = ("backend", "web", "campo", "agro")
SERVICES_BY_COMPONENT = {
    "backend": ("api", "automations-worker", "background-worker", "outbox-worker"),
    "web": ("web",),
    "campo": ("campo",),
    "agro": ("agro",),
}
PROTECTED_SERVICES = ("postgres", "redis")
PROTECTED_VOLUMES = ("farm_postgres_data", "farm_redis_data", "farm_uploads_data")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_RE = re.compile(
    r"^ghcr\.io/[a-z0-9-]+/deepfarms-(backend|web|campo|agro)@sha256:[0-9a-f]{64}$"
)
ROLLBACK_IMAGE_RE = re.compile(
    r"^localhost/deepfarms-rollback/(backend|web|campo|agro):"
    r"([0-9]{8}T[0-9]{6}Z)-([0-9a-f]{12})$"
)


def validate_image(component: str, reference: str) -> None:
    match = IMAGE_RE.fullmatch(reference)
    if not match or match.group(1) != component:
        raise ValueError(f"imagem inválida para {component}: exige GHCR e digest sha256 imutável")
    expected_owner = os.environ.get("GHCR_OWNER", "maborges").lower()
    actual_owner = reference.split("/", 2)[1]
    if actual_owner != expected_owner:
        raise ValueError(f"imagem deve pertencer ao owner GHCR autorizado: {expected_owner}")


def validate_rollback_image(component: str, reference: str) -> None:
    match = ROLLBACK_IMAGE_RE.fullmatch(reference)
    if not match or match.group(1) != component:
        raise ValueError(f"imagem local de rollback inválida para {component}")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version deve ser 1")
    commit = manifest.get("commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise ValueError("commit deve ser SHA completo de 40 caracteres")
    images = manifest.get("images")
    if not isinstance(images, dict) or not images:
        raise ValueError("images deve conter ao menos um componente")
    if set(images) - set(COMPONENTS):
        raise ValueError("manifesto contém componente não autorizado")
    for component, reference in images.items():
        if not isinstance(reference, str):
            raise ValueError(f"referência de imagem inválida para {component}")
        validate_image(component, reference)
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError("manifesto deve ser um objeto JSON")
    return validate_manifest(payload)


def parse_components(value: str) -> tuple[str, ...]:
    components = tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))
    if not components or set(components) - set(COMPONENTS):
        raise ValueError("components aceita backend, web, campo e agro")
    return components


def services_for(components: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(service for component in components for service in SERVICES_BY_COMPONENT[component])


def make_override(manifest: dict[str, Any], components: tuple[str, ...]) -> dict[str, Any]:
    validate_manifest(manifest)
    missing = set(components) - set(manifest["images"])
    if missing:
        raise ValueError(f"manifesto sem imagens para: {', '.join(sorted(missing))}")
    services: dict[str, dict[str, str]] = {}
    for component in components:
        for service in SERVICES_BY_COMPONENT[component]:
            if service in PROTECTED_SERVICES:
                raise ValueError("serviço persistente não pode ser selecionado")
            services[service] = {"image": manifest["images"][component]}
    return {"services": services}


def resolved_volume_names(config: dict[str, Any]) -> dict[str, str]:
    volumes = config.get("volumes")
    if not isinstance(volumes, dict):
        raise ValueError("Compose não declara volumes nomeados")
    result: dict[str, str] = {}
    for key, value in volumes.items():
        if not isinstance(value, dict):
            value = {}
        result[key] = str(value.get("name") or key)
    return result


def _mount_source(mount: Any) -> str | None:
    if isinstance(mount, dict) and mount.get("type") == "volume":
        source = mount.get("source")
        return str(source) if source else None
    if isinstance(mount, str) and ":" in mount:
        source = mount.split(":", 1)[0]
        if source and source not in (".", "..") and not source.startswith("/"):
            return source
    return None


def validate_compose_config(
    config: dict[str, Any], components: tuple[str, ...]
) -> tuple[str, ...]:
    services = config.get("services")
    if not isinstance(services, dict):
        raise ValueError("Compose não contém services")
    for protected in PROTECTED_SERVICES:
        if protected not in services:
            raise ValueError(f"Compose não contém serviço protegido {protected}")

    app_services = services_for(components)
    for service in app_services:
        definition = services.get(service)
        if not isinstance(definition, dict):
            raise ValueError(f"serviço autorizado ausente no Compose: {service}")
        healthcheck = definition.get("healthcheck")
        if not isinstance(healthcheck, dict) or healthcheck.get("disable") is True:
            raise ValueError(f"serviço sem healthcheck ativo: {service}")
    if set(app_services) & set(PROTECTED_SERVICES):
        raise ValueError("tentativa de atualizar serviço protegido")

    volume_map = resolved_volume_names(config)
    if set(PROTECTED_VOLUMES) - set(volume_map.values()):
        missing = sorted(set(PROTECTED_VOLUMES) - set(volume_map.values()))
        raise ValueError(f"Compose não declara todos os volumes protegidos: {missing}")

    service_volume_names: dict[str, set[str]] = {}
    for service_name, definition in services.items():
        sources = {
            _mount_source(mount)
            for mount in definition.get("volumes", [])
            if _mount_source(mount)
        }
        service_volume_names[service_name] = {
            volume_map.get(source, source) for source in sources if source
        }

    if "farm_postgres_data" not in service_volume_names.get("postgres", set()):
        raise ValueError("farm_postgres_data não está anexado ao serviço postgres")
    if "farm_redis_data" not in service_volume_names.get("redis", set()):
        raise ValueError("farm_redis_data não está anexado ao serviço redis")
    if not any(
        "farm_uploads_data" in service_volume_names.get(service, set())
        for service in services
        if service not in PROTECTED_SERVICES
    ):
        raise ValueError("farm_uploads_data não está anexado a um serviço de aplicação")
    return app_services


def validate_backup_receipt(path: Path, *, now: datetime | None = None) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        receipt = json.load(source)
    if not isinstance(receipt, dict):
        raise ValueError("recibo de backup inválido")
    if receipt.get("scheduled_job_verified") is not True:
        raise ValueError("cron/backup automático ainda não foi confirmado")
    if receipt.get("temporary_file_handling_verified") is not True:
        raise ValueError("manipulação segura dos arquivos temporários ainda não foi confirmada")
    if receipt.get("restore_test") != "passed":
        raise ValueError("teste de restauração isolada não foi aprovado")

    artifact = receipt.get("artifact")
    expected_hash = receipt.get("sha256")
    verified_at_text = receipt.get("verified_at")
    if not isinstance(artifact, str) or not isinstance(expected_hash, str):
        raise ValueError("recibo deve identificar artefato e SHA-256")
    if not SHA256_RE.fullmatch(f"sha256:{expected_hash}"):
        raise ValueError("sha256 do recibo inválido")
    if not isinstance(verified_at_text, str):
        raise ValueError("verified_at ausente")
    try:
        verified_at = datetime.fromisoformat(verified_at_text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("verified_at deve ser ISO-8601 com timezone") from exc
    if verified_at.tzinfo is None:
        raise ValueError("verified_at deve incluir timezone")

    current = now or datetime.now(timezone.utc)
    age = (current - verified_at.astimezone(timezone.utc)).total_seconds()
    if age < 0 or age > 24 * 60 * 60:
        raise ValueError("recibo de backup/restauração deve ter no máximo 24 horas")

    artifact_path = Path(artifact)
    if not artifact_path.is_absolute() or not artifact_path.is_file():
        raise ValueError("artefato do backup deve existir em caminho absoluto")
    if current.timestamp() - artifact_path.stat().st_mtime > 24 * 60 * 60:
        raise ValueError("artefato de backup tem mais de 24 horas")
    digest = hashlib.sha256()
    with artifact_path.open("rb") as backup:
        for block in iter(lambda: backup.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected_hash:
        raise ValueError("checksum do artefato não corresponde ao recibo")
    return receipt


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o640)
    temporary.replace(path)
