"""Procedimento de backup online e restauração segura do banco SQLite de identidades do Agro.

Utiliza a API oficial de backup online do SQLite (Connection.backup), permitindo
captura consistente de snapshots atômicos enquanto leitores e escritores continuam
ativos sob o modo WAL.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from loguru import logger

from .config import (
    AGRO_IDENTITY_DB_DIR,
    AGRO_IDENTITY_DB_PATH,
)


def verify_sqlite_integrity(db_path: Path | str) -> bool:
    """Executa checagem profunda de integridade física e estrutural no SQLite.

    Args:
        db_path: Caminho do arquivo de banco a verificar.

    Returns:
        True se a integridade for 'ok', False caso contrário.
    """
    path = Path(db_path)
    if not path.exists():
        return False

    try:
        uri = f"file:{path.resolve()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            rows = cursor.fetchall()
            return bool(rows and rows[0][0] == "ok")
    except Exception as err:
        logger.error(f"Erro ao verificar integridade de {path}: {err}")
        return False


def create_sqlite_backup(
    dest_dir: Path | str | None = None,
    src_path: Path | str | None = None,
) -> Path:
    """Executa backup online consistente do banco SQLite sem indisponibilidade de serviço.

    Garante:
    1. Acesso concorrente sem lock exclusivo no modo WAL.
    2. Permissões restritas 0700 no diretório de destino e 0600 no arquivo gerado.
    3. Verificação de integridade pós-geração antes de confirmar o sucesso.

    Args:
        dest_dir: Diretório onde o backup será salvo.
        src_path: Arquivo de banco de dados de origem.

    Returns:
        Caminho absoluto do arquivo de backup gerado e verificado.

    Raises:
        FileNotFoundError: Se a origem não existir.
        RuntimeError: Se o backup falhar na checagem de integridade.
    """
    source = Path(src_path) if src_path else AGRO_IDENTITY_DB_PATH
    if not source.exists():
        raise FileNotFoundError(f"Arquivo de banco de origem não encontrado: {source}")

    target_dir = Path(dest_dir) if dest_dir else (AGRO_IDENTITY_DB_DIR / "backups")
    target_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    try:
        os.chmod(target_dir, 0o700)
    except OSError:
        pass

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"agro_identity_backup_{timestamp}.db"

    old_umask = os.umask(0o077)
    try:
        src_uri = f"file:{source.resolve()}?mode=ro"
        with sqlite3.connect(src_uri, uri=True) as src_conn:
            with sqlite3.connect(str(backup_file)) as dst_conn:
                src_conn.backup(dst_conn, pages=100)

        # Restringe permissões para somente leitura/escrita do proprietário (0600)
        os.chmod(backup_file, 0o600)
    finally:
        os.umask(old_umask)

    # Verificação de integridade pós-backup
    if not verify_sqlite_integrity(backup_file):
        if backup_file.exists():
            backup_file.unlink(missing_ok=True)
        raise RuntimeError(f"O arquivo de backup gerado falhou na checagem de integridade: {backup_file}")

    logger.info(f"Backup online do SQLite concluído com sucesso e integridade atestada: {backup_file}")
    return backup_file


def restore_sqlite_backup(
    backup_file: Path | str,
    target_path: Path | str | None = None,
) -> bool:
    """Restaura o banco SQLite a partir de um arquivo de backup verificado.

    Args:
        backup_file: Caminho do arquivo de backup a restaurar.
        target_path: Destino da restauração (padrão: AGRO_IDENTITY_DB_PATH).

    Returns:
        True se a restauração e validação de integridade forem bem-sucedidas.

    Raises:
        FileNotFoundError: Se o arquivo de backup não for encontrado.
        ValueError: Se o backup de origem estiver corrompido.
    """
    bkp = Path(backup_file)
    if not bkp.exists():
        raise FileNotFoundError(f"Arquivo de backup não encontrado: {bkp}")

    # 1. Valida integridade do arquivo de backup antes de iniciar
    if not verify_sqlite_integrity(bkp):
        raise ValueError(f"Arquivo de backup corrompido, restauração abortada: {bkp}")

    target = Path(target_path) if target_path else AGRO_IDENTITY_DB_PATH
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)

    old_umask = os.umask(0o077)
    try:
        with sqlite3.connect(str(bkp)) as bkp_conn:
            with sqlite3.connect(str(target)) as dst_conn:
                bkp_conn.backup(dst_conn, pages=100)

        os.chmod(target, 0o600)
        # Remove arquivos WAL e SHM associados para garantir que o snapshot assuma o controle limpo
        for ext in ("-wal", "-shm"):
            aux = Path(str(target) + ext)
            if aux.exists():
                aux.unlink(missing_ok=True)
    finally:
        os.umask(old_umask)

    # 2. Valida integridade do banco restaurado
    if not verify_sqlite_integrity(target):
        raise RuntimeError(f"O banco de dados restaurado falhou na validação de integridade: {target}")

    logger.info(f"Banco SQLite restaurado com sucesso a partir de {bkp} com integridade validada.")
    return True


def cleanup_old_backups(
    dest_dir: Path | str | None = None,
    retention_days: int = 30,
) -> int:
    """Remove backups mais antigos que o período de retenção configurado.

    Args:
        dest_dir: Diretório de backups.
        retention_days: Dias de retenção (padrão: 30 dias).

    Returns:
        Quantidade de arquivos de backup removidos.
    """
    target_dir = Path(dest_dir) if dest_dir else (AGRO_IDENTITY_DB_DIR / "backups")
    if not target_dir.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed_count = 0

    for file in target_dir.glob("agro_identity_backup_*.db"):
        mtime = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            file.unlink(missing_ok=True)
            removed_count += 1

    return removed_count
