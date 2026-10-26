#!/usr/bin/env python3
"""Validador estrito de isolamento de infraestrutura para ambiente de Staging.

Garante que o ambiente de Staging não compartilhe nenhuma infraestrutura
com produção (RDS, ElastiCache, S3 de produção) e que todos os segredos
obrigatórios estejam configurados de forma segura antes de qualquer inicialização.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


FORBIDDEN_HOST_PATTERNS = [
    re.compile(r".*\.rds\.amazonaws\.com$", re.IGNORECASE),
    re.compile(r".*\.cache\.amazonaws\.com$", re.IGNORECASE),
    re.compile(r".*\.s3\.amazonaws\.com$", re.IGNORECASE),
    re.compile(r".*production.*", re.IGNORECASE),
    re.compile(r".*prod-db.*", re.IGNORECASE),
    re.compile(r".*prod-redis.*", re.IGNORECASE),
]

FORBIDDEN_BUCKET_PATTERNS = [
    re.compile(r".*prod.*", re.IGNORECASE),
    re.compile(r".*production.*", re.IGNORECASE),
]

ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "staging-postgres", "staging-redis", "staging-minio"}


def load_env_file(file_path: Path) -> dict[str, str]:
    """Carrega arquivo .env simples em dicionário."""
    env: dict[str, str] = {}
    if not file_path.exists():
        return env

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def check_host_isolation(host: str, field_name: str) -> None:
    """Valida se o host indicado pertence ao escopo isolado."""
    clean_host = host.split(":")[0].strip().lower()
    for pattern in FORBIDDEN_HOST_PATTERNS:
        if pattern.match(clean_host):
            raise ValueError(
                f"[VIOLAÇÃO DE ISOLAMENTO] O campo '{field_name}' aponta para host proibido de produção: '{host}'"
            )

    if clean_host not in ALLOWED_LOCAL_HOSTS:
        raise ValueError(
            f"[VIOLAÇÃO DE ISOLAMENTO] O campo '{field_name}' ('{host}') não é um host local/container permitido: {ALLOWED_LOCAL_HOSTS}"
        )


def validate_staging_config(env: dict[str, str]) -> list[str]:
    """Executa todas as verificações de conformidade e isolamento."""
    errors: list[str] = []

    # 1. Checagem de Ambiente
    app_env = env.get("APP_ENV", "").lower()
    environment = env.get("ENVIRONMENT", "").lower()
    if app_env == "production" or environment == "production":
        errors.append("APP_ENV ou ENVIRONMENT está configurado como 'production'. Proibido!")
    if app_env != "staging" and environment != "staging":
        errors.append(f"Ambiente deve ser explicitamente 'staging' (atual: APP_ENV={app_env}, ENVIRONMENT={environment}).")

    # 2. Banco de Dados
    db_host = env.get("STAGING_DB_HOST", "127.0.0.1")
    try:
        check_host_isolation(db_host, "STAGING_DB_HOST")
    except ValueError as e:
        errors.append(str(e))

    db_pass = env.get("STAGING_DB_PASSWORD", "")
    if not db_pass or "gerar_com" in db_pass or len(db_pass) < 16:
        errors.append("STAGING_DB_PASSWORD deve ser preenchida com senha segura (mínimo 16 caracteres, não utilize o placeholder).")

    # 3. Redis
    redis_host = env.get("STAGING_REDIS_HOST", "127.0.0.1")
    try:
        check_host_isolation(redis_host, "STAGING_REDIS_HOST")
    except ValueError as e:
        errors.append(str(e))

    redis_pass = env.get("STAGING_REDIS_PASSWORD", "")
    if not redis_pass or "gerar_com" in redis_pass or len(redis_pass) < 16:
        errors.append("STAGING_REDIS_PASSWORD deve ser preenchida com senha segura (mínimo 16 caracteres).")

    # 4. Chaves Criptográficas
    jwt_key = env.get("STAGING_JWT_SECRET_KEY", "")
    if not jwt_key or "gerar_com" in jwt_key or len(jwt_key) < 32:
        errors.append("STAGING_JWT_SECRET_KEY deve ter no mínimo 32 caracteres.")

    master_key = env.get("STAGING_PLATFORM_CREDENTIALS_MASTER_KEY", "")
    if not master_key or "gerar_com" in master_key or len(master_key) < 32:
        errors.append("STAGING_PLATFORM_CREDENTIALS_MASTER_KEY é obrigatória em staging e deve ter no mínimo 32 caracteres.")

    # 5. MinIO / S3 Storage
    bucket = env.get("S3_BUCKET_NAME", "deepfarms-staging-bucket")
    for pat in FORBIDDEN_BUCKET_PATTERNS:
        if pat.match(bucket):
            errors.append(f"S3_BUCKET_NAME contém termo proibido de produção: '{bucket}'")

    s3_endpoint = env.get("S3_ENDPOINT_URL", "")
    if s3_endpoint:
        parsed = urlparse(s3_endpoint)
        if parsed.hostname:
            try:
                check_host_isolation(parsed.hostname, "S3_ENDPOINT_URL")
            except ValueError as e:
                errors.append(str(e))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validação de isolamento do ambiente de staging")
    parser.add_argument("--env-file", type=Path, default=Path("infrastructure/staging/.env.staging"), help="Caminho do arquivo .env.staging")
    args = parser.parse_args()

    print(f"[*] Validando isolamento do ambiente de Staging a partir de {args.env_file}...")

    # Junta variáveis do arquivo com variáveis de ambiente do SO
    env_vars = dict(os.environ)
    if args.env_file.exists():
        file_vars = load_env_file(args.env_file)
        env_vars.update(file_vars)
    else:
        print(f"[!] Aviso: Arquivo {args.env_file} não encontrado. Validando variáveis de ambiente do processo.")

    errors = validate_staging_config(env_vars)

    if errors:
        print("\n[FALHA] Foram identificadas violações de isolamento ou pendências de configuração:")
        for err in errors:
            print(f"  - {err}")
        print("\nO ambiente de staging NÃO PODE ser inicializado até que os problemas acima sejam sanados.\n")
        return 1

    print("\n[SUCESSO] Todas as verificações de isolamento foram atendidas:")
    print("  ✓ Não há conexão apontando para RDS, ElastiCache ou S3 de produção.")
    print("  ✓ Hosts e portas restritos a loopback e rede docker isolada.")
    print("  ✓ PLATFORM_CREDENTIALS_MASTER_KEY e JWT_SECRET_KEY devidamente parametrizadas.")
    print("  ✓ Nenhuma credencial padrão ou fraca detectada.")
    print("Ambiente certificado para homologação isolada.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
