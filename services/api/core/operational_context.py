from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException, Request, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo, CultivoArea
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra, SafraTalhao
from core.cadastros.pessoas.models import Pessoa, PessoaRelacionamento, TipoRelacionamento
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.auth import UnidadeProdutivaUsuario
from core.models.unidade_produtiva import UnidadeProdutiva
from operacional.models.estoque import Deposito, LoteEstoque


@dataclass(frozen=True)
class UnidadeProdutivaContext:
    tenant_id: UUID
    unidade_produtiva_id: UUID
    source: str


def _log_context_failure(event: str, **extra) -> None:
    logger.warning(event, **{key: str(value) if isinstance(value, UUID) else value for key, value in extra.items()})


async def _ensure_unidade_produtiva(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    unidade_produtiva_id: UUID,
) -> UnidadeProdutiva:
    unidade = (
        await session.execute(
            select(UnidadeProdutiva).where(
                UnidadeProdutiva.id == unidade_produtiva_id,
                UnidadeProdutiva.tenant_id == tenant_id,
                UnidadeProdutiva.ativo == True,
            )
        )
    ).scalars().first()
    if not unidade:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="unidade_produtiva_tenant_mismatch",
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        raise BusinessRuleError("Unidade produtiva não localizada ou inacessível para o tenant.")
    return unidade


async def resolve_unidade_produtiva_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    request: Request | None = None,
    unidade_produtiva_id: UUID | None = None,
    user_id: UUID | None = None,
    required: bool = False,
    source: str = "explicit",
) -> UnidadeProdutivaContext | None:
    """Resolve e valida o contexto operacional de fazenda/UP.

    A ordem é: argumento explícito, header x-fazenda-id, query param
    unidade_produtiva_id/fazenda_id. A derivação por entidade fica nos helpers
    específicos para evitar inferência ambígua em endpoints genéricos.
    """
    resolved_id = unidade_produtiva_id
    resolved_source = source

    if resolved_id is None and request is not None:
        header_value = request.headers.get("x-fazenda-id") or request.headers.get("x-unidade-produtiva-id")
        if header_value:
            try:
                resolved_id = UUID(header_value)
                resolved_source = "header"
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Header x-fazenda-id inválido.") from exc

    if resolved_id is None and request is not None:
        query_value = request.query_params.get("unidade_produtiva_id") or request.query_params.get("fazenda_id")
        if query_value:
            try:
                resolved_id = UUID(query_value)
                resolved_source = "query"
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Query param unidade_produtiva_id inválido.") from exc

    if resolved_id is None:
        if required:
            _log_context_failure("multi_up_context_missing", tenant_id=tenant_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contexto de fazenda obrigatório.")
        return None

    await _ensure_unidade_produtiva(session, tenant_id=tenant_id, unidade_produtiva_id=resolved_id)

    if user_id is not None:
        acesso = (
            await session.execute(
                select(UnidadeProdutivaUsuario.id).where(
                    UnidadeProdutivaUsuario.tenant_id == tenant_id,
                    UnidadeProdutivaUsuario.unidade_produtiva_id == resolved_id,
                    UnidadeProdutivaUsuario.usuario_id == user_id,
                    (UnidadeProdutivaUsuario.vigencia_inicio.is_(None) | (UnidadeProdutivaUsuario.vigencia_inicio <= date.today())),
                    (UnidadeProdutivaUsuario.vigencia_fim.is_(None) | (UnidadeProdutivaUsuario.vigencia_fim >= date.today())),
                )
            )
        ).scalar_one_or_none()
        if acesso is None:
            _log_context_failure(
                "multi_up_user_access_denied",
                tenant_id=tenant_id,
                user_id=user_id,
                unidade_produtiva_id=resolved_id,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário sem acesso à fazenda informada.")

    return UnidadeProdutivaContext(tenant_id=tenant_id, unidade_produtiva_id=resolved_id, source=resolved_source)


async def validate_area_in_tenant(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    area_id: UUID,
) -> AreaRural:
    area = (
        await session.execute(
            select(AreaRural).where(
                AreaRural.id == area_id,
                AreaRural.tenant_id == tenant_id,
                AreaRural.ativo == True,
            )
        )
    ).scalars().first()
    if not area:
        _log_context_failure("multi_up_tenant_mismatch", resource="area", tenant_id=tenant_id, area_id=area_id)
        raise EntityNotFoundError(f"Talhão/área {area_id} não encontrado para o tenant.")
    return area


async def validate_safra_in_tenant(session: AsyncSession, *, tenant_id: UUID, safra_id: UUID) -> Safra:
    safra = (
        await session.execute(select(Safra).where(Safra.id == safra_id, Safra.tenant_id == tenant_id))
    ).scalars().first()
    if not safra:
        _log_context_failure("multi_up_tenant_mismatch", resource="safra", tenant_id=tenant_id, safra_id=safra_id)
        raise EntityNotFoundError(f"Safra {safra_id} não encontrada para o tenant.")
    return safra


async def validate_cultivo_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    cultivo_id: UUID,
    safra_id: UUID | None = None,
) -> Cultivo:
    stmt = select(Cultivo).where(Cultivo.id == cultivo_id, Cultivo.tenant_id == tenant_id)
    if safra_id:
        stmt = stmt.where(Cultivo.safra_id == safra_id)
    cultivo = (await session.execute(stmt)).scalars().first()
    if not cultivo:
        _log_context_failure(
            "multi_up_tenant_mismatch",
            resource="cultivo",
            tenant_id=tenant_id,
            safra_id=safra_id,
            cultivo_id=cultivo_id,
        )
        raise BusinessRuleError("Cultivo não localizado ou incompatível com a safra informada.")
    return cultivo


async def validate_safra_area_link(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    safra_id: UUID,
    area_id: UUID,
    cultivo_id: UUID | None = None,
) -> None:
    """Valida vínculo safra/área quando a safra já possui mapeamento explícito.

    Para não quebrar safras legadas sem `safra_talhoes`/`cultivo_areas`, só
    rejeitamos quando há algum vínculo explícito para a safra e a área enviada
    não pertence a esse conjunto.
    """
    direct_link = (
        await session.execute(
            select(SafraTalhao.id).where(
                SafraTalhao.tenant_id == tenant_id,
                SafraTalhao.safra_id == safra_id,
                SafraTalhao.area_id == area_id,
            )
        )
    ).scalar_one_or_none()
    if direct_link is not None:
        return

    cultivo_stmt = (
        select(CultivoArea.id)
        .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
        .where(
            CultivoArea.tenant_id == tenant_id,
            CultivoArea.area_id == area_id,
            Cultivo.tenant_id == tenant_id,
            Cultivo.safra_id == safra_id,
        )
    )
    if cultivo_id:
        cultivo_stmt = cultivo_stmt.where(CultivoArea.cultivo_id == cultivo_id)
    cultivo_link = (await session.execute(cultivo_stmt)).scalar_one_or_none()
    if cultivo_link is not None:
        return

    explicit_links = (
        await session.execute(
            select(func.count()).select_from(SafraTalhao).where(
                SafraTalhao.tenant_id == tenant_id,
                SafraTalhao.safra_id == safra_id,
            )
        )
    ).scalar_one()
    explicit_cultivo_links = (
        await session.execute(
            select(func.count())
            .select_from(CultivoArea)
            .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
            .where(CultivoArea.tenant_id == tenant_id, Cultivo.tenant_id == tenant_id, Cultivo.safra_id == safra_id)
        )
    ).scalar_one()

    if explicit_links or explicit_cultivo_links:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="area_not_linked_to_safra",
            tenant_id=tenant_id,
            safra_id=safra_id,
            area_id=area_id,
            cultivo_id=cultivo_id,
        )
        raise BusinessRuleError("Talhão/área não pertence à safra ou cultivo informado.")

    _log_context_failure(
        "multi_up_legacy_safra_without_area_links",
        tenant_id=tenant_id,
        safra_id=safra_id,
        area_id=area_id,
    )


async def validate_production_unit_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    production_unit_id: UUID,
    safra_id: UUID,
    area_id: UUID,
    cultivo_id: UUID | None = None,
) -> ProductionUnit:
    stmt = select(ProductionUnit).where(
        ProductionUnit.id == production_unit_id,
        ProductionUnit.tenant_id == tenant_id,
        ProductionUnit.safra_id == safra_id,
        ProductionUnit.area_id == area_id,
    )
    if cultivo_id:
        stmt = stmt.where(ProductionUnit.cultivo_id == cultivo_id)
    pu = (await session.execute(stmt)).scalars().first()
    if not pu:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="production_unit_incompatible",
            tenant_id=tenant_id,
            production_unit_id=production_unit_id,
            safra_id=safra_id,
            area_id=area_id,
            cultivo_id=cultivo_id,
        )
        raise BusinessRuleError("ProductionUnit incompatível com safra/talhão/cultivo informados.")
    return pu


async def validate_pessoa_tenant(session: AsyncSession, *, tenant_id: UUID, pessoa_id: UUID) -> Pessoa:
    pessoa = (
        await session.execute(
            select(Pessoa).where(Pessoa.id == pessoa_id, Pessoa.tenant_id == tenant_id, Pessoa.ativo == True)
        )
    ).scalars().first()
    if not pessoa:
        _log_context_failure("multi_up_tenant_mismatch", resource="pessoa", tenant_id=tenant_id, pessoa_id=pessoa_id)
        raise BusinessRuleError("Pessoa não localizada ou inacessível para o tenant.")
    return pessoa


async def validate_operador_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    operador_id: UUID,
    unidade_produtiva_id: UUID | None = None,
) -> Pessoa:
    pessoa = await validate_pessoa_tenant(session, tenant_id=tenant_id, pessoa_id=operador_id)
    if unidade_produtiva_id is None:
        return pessoa

    stmt = (
        select(PessoaRelacionamento)
        .join(TipoRelacionamento, TipoRelacionamento.id == PessoaRelacionamento.tipo_id)
        .where(
            PessoaRelacionamento.pessoa_id == operador_id,
            PessoaRelacionamento.unidade_produtiva_id == unidade_produtiva_id,
            TipoRelacionamento.ativo == True,
            (PessoaRelacionamento.ativo_desde.is_(None) | (PessoaRelacionamento.ativo_desde <= date.today())),
            (PessoaRelacionamento.ativo_ate.is_(None) | (PessoaRelacionamento.ativo_ate >= date.today())),
        )
    )
    rel = (await session.execute(stmt)).scalars().first()
    if rel is None:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="operador_sem_acesso_up",
            tenant_id=tenant_id,
            operador_id=operador_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        raise BusinessRuleError("Operador não possui acesso à unidade produtiva informada.")
    return pessoa


async def validate_deposito_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    deposito_id: UUID,
    expected_unidade_produtiva_id: UUID | None = None,
) -> Deposito:
    dep = (
        await session.execute(
            select(Deposito).where(Deposito.id == deposito_id, Deposito.tenant_id == tenant_id)
        )
    ).scalars().first()
    if not dep:
        _log_context_failure("multi_up_tenant_mismatch", resource="deposito", tenant_id=tenant_id, deposito_id=deposito_id)
        raise EntityNotFoundError(f"Depósito {deposito_id} não encontrado para o tenant.")
    if expected_unidade_produtiva_id and dep.unidade_produtiva_id != expected_unidade_produtiva_id:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="deposito_unidade_produtiva_incompatible",
            tenant_id=tenant_id,
            deposito_id=deposito_id,
            expected_unidade_produtiva_id=expected_unidade_produtiva_id,
            actual_unidade_produtiva_id=dep.unidade_produtiva_id,
        )
        raise BusinessRuleError("Depósito não pertence à unidade produtiva esperada.")
    return dep


async def validate_lote_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    lote_id: UUID,
    produto_id: UUID | None = None,
    deposito_id: UUID | None = None,
    expected_unidade_produtiva_id: UUID | None = None,
) -> LoteEstoque:
    stmt = select(LoteEstoque).join(Deposito, Deposito.id == LoteEstoque.deposito_id).where(
        LoteEstoque.id == lote_id,
        Deposito.tenant_id == tenant_id,
    )
    if produto_id:
        stmt = stmt.where(LoteEstoque.produto_id == produto_id)
    if deposito_id:
        stmt = stmt.where(LoteEstoque.deposito_id == deposito_id)
    if expected_unidade_produtiva_id:
        stmt = stmt.where(Deposito.unidade_produtiva_id == expected_unidade_produtiva_id)
    lote = (await session.execute(stmt)).scalars().first()
    if not lote:
        _log_context_failure(
            "multi_up_context_invalid",
            reason="lote_incompatible",
            tenant_id=tenant_id,
            lote_id=lote_id,
            produto_id=produto_id,
            deposito_id=deposito_id,
            expected_unidade_produtiva_id=expected_unidade_produtiva_id,
        )
        raise BusinessRuleError("Lote não localizado ou incompatível com depósito/produto/UP.")
    return lote
