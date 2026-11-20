"""Seed idempotente da biblioteca Embrapa de Modelos Zoossanitários globais."""

from __future__ import annotations

import argparse
import asyncio
import copy
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import configure_mappers

API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from core import model_registry
from core.config import settings
from core.database import (
    async_session_maker,
    catalog_admin_async_session_maker,
    catalog_admin_engine,
    engine,
)
from pecuaria.climatico.models import ModeloZoosanitario
from pecuaria.climatico.padroes import PADROES_ESTRESSE_TERMICO
from pecuaria.climatico.schemas import validar_regras_zoosanitarias

VERSAO_REGRA_PADRAO = "2026.11-embrapa-zoo-v1"
TIPO_RISCO_PADRAO = "Estresse Térmico"


@dataclass(frozen=True)
class _PlanejamentoCarga:
    legados: list[ModeloZoosanitario]
    pendentes: list[dict]
    existentes: int


@dataclass(frozen=True)
class _ResumoCarga:
    inseridos: int
    existentes: int
    removidos: int
    dry_run: bool


def _construir_regras_estresse_termico(padrao: dict[str, int | str]) -> dict:
    """Converte um padrão de ITH em regras_risco com metadados auditáveis."""
    return {
        "nivel_medio": padrao["nivel_medio"],
        "nivel_alto": padrao["nivel_alto"],
        "nivel_critico": padrao["nivel_critico"],
        "indice": padrao["indice"],
        "fonte_parametros": padrao["fonte_parametros"],
        "fonte_url": padrao["fonte_url"],
        "observacao": padrao["observacao"],
        "metadados": {
            "tipo_resultado": "referencia_conforto_termico_ith",
            "somente_referencia": True,
            "fonte_parametros": padrao["fonte_parametros"],
            "fonte_url": padrao["fonte_url"],
            "versao_regra": VERSAO_REGRA_PADRAO,
            "observacao": padrao["observacao"],
        },
    }


MODELOS_ZOOSSANITARIOS_BASE: list[dict] = [
    {
        "especie": especie,
        "tipo_risco": TIPO_RISCO_PADRAO,
        "regras_risco": _construir_regras_estresse_termico(padrao),
    }
    for especie, padrao in PADROES_ESTRESSE_TERMICO.items()
]


def _eh_modelo_global_legado(modelo: ModeloZoosanitario) -> bool:
    """Identifica globais legados sem bloco metadados.fonte_parametros."""
    regras = modelo.regras_risco
    if not isinstance(regras, dict):
        return True
    metadados = regras.get("metadados")
    if not isinstance(metadados, dict):
        return True
    return not bool(str(metadados.get("fonte_parametros") or "").strip())


def _validar_ambiente_para_limpeza() -> None:
    """Impede remoção de modelos globais legados em ambiente de produção.

    Raises:
        RuntimeError: Se APP_ENV ou settings.environment indicar production.
    """
    app_env = os.getenv("APP_ENV", "").strip().lower()
    settings_env = str(getattr(settings, "environment", "")).strip().lower()
    if app_env == "production" or settings_env == "production":
        raise RuntimeError(
            "Operação --replace-legacy-globals bloqueada em ambiente de produção."
        )


async def _aplicar_contexto_global(session: AsyncSession) -> None:
    """Configura contexto RLS sem tenant ativo para consulta/escrita global."""
    await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))


async def _carregar_estado_global(session: AsyncSession) -> list[ModeloZoosanitario]:
    """Carrega todos os modelos zoossanitários globais (tenant_id IS NULL)."""
    stmt = select(ModeloZoosanitario).where(ModeloZoosanitario.tenant_id.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _planejar_carga_modelos(
    modelos_globais: list[ModeloZoosanitario], replace_legacy_globals: bool
) -> _PlanejamentoCarga:
    """Calcula legados a substituir, modelos pendentes e já existentes."""
    legados = (
        [modelo for modelo in modelos_globais if _eh_modelo_global_legado(modelo)]
        if replace_legacy_globals
        else []
    )
    legados_ids = {id(modelo) for modelo in legados}
    chaves_ativas = {
        (modelo.especie, modelo.tipo_risco)
        for modelo in modelos_globais
        if id(modelo) not in legados_ids
    }
    pendentes = [
        item
        for item in MODELOS_ZOOSSANITARIOS_BASE
        if (item["especie"], item["tipo_risco"]) not in chaves_ativas
    ]
    existentes = len(MODELOS_ZOOSSANITARIOS_BASE) - len(pendentes)
    return _PlanejamentoCarga(legados=legados, pendentes=pendentes, existentes=existentes)


async def _remover_legados(
    session: AsyncSession, legados: list[ModeloZoosanitario]
) -> None:
    """Remove legados globais e executa flush antes de reinserir chaves únicas."""
    if not legados:
        return
    for legado in legados:
        await session.delete(legado)
    await session.flush()


def _adicionar_modelos_pendentes(
    session: AsyncSession, pendentes: list[dict]
) -> None:
    """Valida e adiciona modelos zoossanitários globais pendentes na sessão."""
    for item in pendentes:
        regras = validar_regras_zoosanitarias(copy.deepcopy(item["regras_risco"]))
        session.add(
            ModeloZoosanitario(
                tenant_id=None,
                especie=item["especie"],
                tipo_risco=item["tipo_risco"],
                regras_risco=regras,
                is_global=True,
            )
        )


async def _tratar_erro_commit_rls(session: AsyncSession, exc: Exception) -> None:
    """Executa rollback e orienta migração/role caso o RLS bloqueie escrita global."""
    await session.rollback()
    texto = str(exc).lower()
    if "row-level security policy" in texto or "permission denied" in texto:
        raise RuntimeError(
            "Escrita no catálogo global bloqueada pelo RLS em modelos_zoosanitarios. "
            "Execute 'alembic upgrade head' (migração 20261119_rls_global_catalog_admin_write) "
            "e configure CATALOG_ADMIN_DATABASE_URL com a role administrativa."
        ) from exc
    raise exc


async def _persistir_alteracoes_modelos(
    session: AsyncSession, planejado: _PlanejamentoCarga
) -> None:
    """Persiste remoção de legados e inserção dos novos modelos globais."""
    try:
        await _remover_legados(session, planejado.legados)
        _adicionar_modelos_pendentes(session, planejado.pendentes)
        await session.commit()
    except Exception as exc:
        await _tratar_erro_commit_rls(session, exc)


async def _executar_carga_modelos(
    session: AsyncSession,
    *,
    dry_run: bool = False,
    replace_legacy_globals: bool = False,
) -> tuple[int, int, int]:
    """Executa o planejamento e a persistência da carga global em uma sessão.

    Args:
        session: Sessão assíncrona ativa.
        dry_run: Quando True, não grava alterações no banco.
        replace_legacy_globals: Quando True (apenas fora de produção), substitui globais legados.

    Returns:
        Tupla (inseridos_ou_pendentes, existentes, legados_removidos_ou_a_remover).

    Raises:
        RuntimeError: Se replace_legacy_globals for acionado em produção ou o RLS bloquear escrita.
    """
    if replace_legacy_globals:
        _validar_ambiente_para_limpeza()

    await _aplicar_contexto_global(session)
    modelos_globais = await _carregar_estado_global(session)
    planejado = _planejar_carga_modelos(modelos_globais, replace_legacy_globals)

    if not dry_run:
        await _persistir_alteracoes_modelos(session, planejado)

    return len(planejado.pendentes), planejado.existentes, len(planejado.legados)


async def _seed_modelos_zoosanitarios(session: AsyncSession) -> tuple[int, int]:
    """Mantém interface simplificada para carga padrão em uma sessão fornecida."""
    inseridos, existentes, _ = await _executar_carga_modelos(session)
    return inseridos, existentes


def _imprimir_resumo_carga(resumo: _ResumoCarga) -> None:
    """Exibe resumo operacional claro sem falso positivo no modo dry-run."""
    if resumo.dry_run:
        print(
            f"[DRY-RUN] Nada foi gravado: {resumo.inseridos} modelos pendentes, "
            f"{resumo.existentes} já cadastrados, {resumo.removidos} legados a remover."
        )
        return
    print(
        f"Carga zoossanitária concluída: {resumo.inseridos} inseridos, "
        f"{resumo.existentes} já existentes, {resumo.removidos} legados removidos."
    )


async def seed(
    *, dry_run: bool = False, replace_legacy_globals: bool = False
) -> tuple[int, int]:
    """Executa a carga inicial idempotente de modelos zoossanitários globais.

    Args:
        dry_run: Apenas simula quantos registros seriam gravados/removidos.
        replace_legacy_globals: Substitui globais sem metadados (bloqueado em produção).

    Returns:
        Tupla (inseridos_ou_pendentes, existentes).

    Raises:
        RuntimeError: Em uso indevido em produção ou bloqueio de RLS.
    """
    if replace_legacy_globals:
        _validar_ambiente_para_limpeza()

    model_registry.register_models()
    configure_mappers()
    session_factory = catalog_admin_async_session_maker or async_session_maker
    async with session_factory() as session:
        inseridos, existentes, removidos = await _executar_carga_modelos(
            session,
            dry_run=dry_run,
            replace_legacy_globals=replace_legacy_globals,
        )

    _imprimir_resumo_carga(
        _ResumoCarga(
            inseridos=inseridos,
            existentes=existentes,
            removidos=removidos,
            dry_run=dry_run,
        )
    )
    return inseridos, existentes


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Interpreta parâmetros de linha de comando do script de carga."""
    parser = argparse.ArgumentParser(
        description="Carga inicial da biblioteca Embrapa de Modelos Zoossanitários globais."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula a execução sem gravar alterações no banco.",
    )
    parser.add_argument(
        "--replace-legacy-globals",
        action="store_true",
        help="Substitui modelos globais legados sem metadados (bloqueado em produção).",
    )
    return parser.parse_args(argv)


async def _encerrar_engines() -> None:
    """Fecha pools de conexão após execução via CLI."""
    if catalog_admin_engine is not None:
        await catalog_admin_engine.dispose()
    await engine.dispose()


async def _executar_cli(args: argparse.Namespace) -> None:
    """Executa o fluxo assíncrono completo e garante encerramento das conexões."""
    try:
        await seed(
            dry_run=args.dry_run,
            replace_legacy_globals=args.replace_legacy_globals,
        )
    finally:
        await _encerrar_engines()


def main() -> None:
    """Ponto de entrada CLI do seed de modelos zoossanitários."""
    args = _parse_args()
    asyncio.run(_executar_cli(args))


if __name__ == "__main__":
    main()
