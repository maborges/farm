from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from loguru import logger

from core.dependencies import get_session, get_current_admin, get_current_tenant, get_current_user_claims, get_current_user
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.tenant import Tenant
from core.models.configuration import ConfiguracaoSaaS
from core.models.tenant_config import ConfiguracaoTenant
from core.models.auth import Usuario
from core.schemas.config_schemas import (
    SaaSConfigResponse, SaaSConfigUpdate, SMTPConfig,
    TenantConfigResponse, TenantConfigUpdate,
    ConfiguracoesGeraisResponse, ConfiguracoesGeraisUpdate,
    ConversaoAreaRequest, ConversaoAreaResponse, UnidadeAreaInfo,
    CategoriaResponse, CategoriaCreateRequest, CategoriaUpdateRequest,
    ConfiguracaoFazendaResponse, ConfiguracaoFazendaUpdate,
    HistoricoConfiguracaoItem,
    OnboardingConfigRequest,
    SegurancaConfigResponse, SegurancaConfigUpdate,
    SequencialConfigResponse, SequencialConfigUpdate, SequencialResetRequest,
)
from core.services.configuracoes_service import (
    ConfiguracoesService, UnidadeAreaConverter, seed_categorias_padrao
)
from agricola.templates.service import PhaseTemplateService, OperationTemplateService
from integracoes.sankhya.services import SankhyaSyncService
from integracoes.events import IntegrationSyncRequested
from events.helpers import publish_domain_event_safe
from core.services.email_service import email_service, SMTPPlatformConfigNotFoundError

router = APIRouter(prefix="/config", tags=["Configurações"])


# =============================================================================
# BACKOFFICE — Configurações SaaS globais
# =============================================================================

@router.get("/saas", response_model=List[SaaSConfigResponse])
async def list_saas_configs(
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims)
):
    stmt = select(ConfiguracaoSaaS)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.put("/saas/{chave}", response_model=SaaSConfigResponse)
async def update_saas_config(
    chave: str,
    data: SaaSConfigUpdate,
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims)
):
    stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == chave)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        config = ConfiguracaoSaaS(chave=chave, valor=data.valor, descricao=data.descricao)
        session.add(config)
    else:
        config.valor = data.valor
        if data.descricao:
            config.descricao = data.descricao
        if data.ativo is not None:
            config.ativo = data.ativo

    await session.commit()
    await session.refresh(config)
    return config


@router.post("/saas/smtp_global/test")
async def test_global_smtp(
    admin: dict = Depends(get_current_admin),
    user: Usuario = Depends(get_current_user),
):
    """Envia um teste do SMTP global para o administrador autenticado."""
    del admin
    try:
        await email_service.send_platform_smtp_test(user.email)
    except SMTPPlatformConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuração SMTP global da plataforma não encontrada.",
        ) from exc
    except Exception as exc:
        logger.exception("Falha no teste do SMTP global da plataforma")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar o e-mail de teste pelo SMTP global.",
        ) from exc

    return {"message": f"E-mail de teste enviado para {user.email}."}


# =============================================================================
# TENANT — Configurações key-value genéricas
# =============================================================================

@router.get("/tenant", response_model=List[TenantConfigResponse])
async def list_tenant_configs(
    categoria: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant.id)
    if categoria:
        stmt = stmt.where(ConfiguracaoTenant.categoria == categoria)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.put("/tenant/{categoria}/{chave}", response_model=TenantConfigResponse)
async def update_tenant_config(
    categoria: str,
    chave: str,
    data: TenantConfigUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(ConfiguracaoTenant).where(
        ConfiguracaoTenant.tenant_id == tenant.id,
        ConfiguracaoTenant.categoria == categoria,
        ConfiguracaoTenant.chave == chave
    )
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        config = ConfiguracaoTenant(
            tenant_id=tenant.id, categoria=categoria, chave=chave,
            valor=data.valor, descricao=data.descricao
        )
        session.add(config)
    else:
        config.valor = data.valor
        if data.descricao:
            config.descricao = data.descricao
        if data.ativo is not None:
            config.ativo = data.ativo

    await session.commit()
    await session.refresh(config)
    return config


# =============================================================================
# CÓDIGOS DE REFERÊNCIA (SEQUENCIAIS) — ex: PED-2026-000123
# =============================================================================

@router.get("/sequenciais", response_model=List[SequencialConfigResponse])
async def list_sequenciais_config(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    service = ConfiguracoesService(session, tenant.id)
    return await service.get_sequenciais_config()


@router.put("/sequenciais/{entidade}", response_model=SequencialConfigResponse)
async def update_sequencial_config(
    entidade: str,
    data: SequencialConfigUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    service = ConfiguracoesService(session, tenant.id)
    try:
        return await service.set_sequencial_config(
            entidade, data.prefixo, data.digitos, data.escopo,
            usuario_id=claims.get("sub"),
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sequenciais/{entidade}/resetar", response_model=SequencialConfigResponse)
async def resetar_sequencial_config(
    entidade: str,
    data: SequencialResetRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    service = ConfiguracoesService(session, tenant.id)
    try:
        return await service.resetar_sequencial(
            entidade, data.ultimo_numero, usuario_id=claims.get("sub"),
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))


# =============================================================================
# SMTP
# =============================================================================

@router.get("/my-smtp", response_model=SMTPConfig)
async def get_my_smtp_config(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    if not tenant.smtp_config:
        return {"host": "", "port": 587, "user": "", "from": ""}
    return tenant.smtp_config


@router.put("/my-smtp")
async def update_my_smtp_config(
    data: SMTPConfig,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    tenant.smtp_config = data.model_dump(by_alias=True)
    await session.commit()
    return {"message": "Configuração SMTP atualizada com sucesso."}


# =============================================================================
# CONFIGURAÇÕES GERAIS DO TENANT
# =============================================================================

@router.get("/geral", response_model=ConfiguracoesGeraisResponse)
async def get_configuracoes_gerais(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    ano_agricola = await svc.get_ano_agricola()
    unidade_area = await svc.get_unidade_area_padrao()
    moeda = await svc.get_moeda_padrao()
    config_fuso = await svc.get_configuracao("geral", "fuso_horario")
    config_idioma = await svc.get_configuracao("geral", "idioma")

    return ConfiguracoesGeraisResponse(
        ano_agricola=ano_agricola,
        unidade_area=unidade_area,
        moeda=moeda,
        fuso_horario=config_fuso.valor if config_fuso else "America/Sao_Paulo",
        idioma=config_idioma.valor if config_idioma else "pt-BR",
    )


@router.patch("/geral", response_model=ConfiguracoesGeraisResponse)
async def update_configuracoes_gerais(
    data: ConfiguracoesGeraisUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    svc = ConfiguracoesService(session, tenant.id)
    usuario_id = UUID(claims.get("sub")) if claims.get("sub") else None

    try:
        if data.ano_agricola_inicio or data.ano_agricola_fim:
            await svc.set_ano_agricola(
                mes_inicio=data.ano_agricola_inicio or 7,
                mes_fim=data.ano_agricola_fim or 6,
                usuario_id=usuario_id,
            )
        if data.unidade_area:
            await svc.set_unidade_area_padrao(data.unidade_area, usuario_id=usuario_id)
        if data.moeda:
            await svc.set_moeda_padrao(data.moeda, usuario_id=usuario_id)
        if data.fuso_horario:
            await svc.set_fuso_horario(data.fuso_horario, usuario_id=usuario_id)
        if data.idioma:
            await svc.set_configuracao("geral", "idioma", data.idioma, usuario_id=usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return await get_configuracoes_gerais(tenant, session)


# =============================================================================
# CONVERSÃO DE UNIDADES DE ÁREA
# =============================================================================

@router.get("/unidades-area", response_model=List[UnidadeAreaInfo])
async def listar_unidades_area():
    return UnidadeAreaConverter.get_unidades_disponiveis()


@router.post("/converter-area", response_model=ConversaoAreaResponse)
async def converter_area(
    data: ConversaoAreaRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        valor_convertido = await svc.converter_area(
            valor=data.valor, de=data.unidade_origem, para=data.unidade_destino
        )
        unidade_destino = data.unidade_destino or await svc.get_unidade_area_padrao()
        return ConversaoAreaResponse(
            valor_original=data.valor,
            unidade_origem=data.unidade_origem,
            valor_convertido=valor_convertido,
            unidade_destino=unidade_destino,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# CATEGORIAS CUSTOMIZÁVEIS
# =============================================================================

@router.get("/categorias/{tipo}", response_model=List[CategoriaResponse])
async def get_categorias(
    tipo: str,
    apenas_ativas: bool = True,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    tipos_validos = ["despesa", "receita", "operacao", "produto", "insumo"]
    if tipo not in tipos_validos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {tipos_validos}")

    svc = ConfiguracoesService(session, tenant.id)
    categorias = await svc.get_categorias(tipo, apenas_ativas=apenas_ativas)
    return categorias


@router.post("/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
async def criar_categoria(
    data: CategoriaCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        categoria = await svc.criar_categoria(
            tipo=data.tipo,
            nome=data.nome,
            parent_id=data.parent_id,
            cor_hex=data.cor_hex,
            icone=data.icone,
            ordem=data.ordem,
        )
        return categoria
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/categorias/{categoria_id}", response_model=CategoriaResponse)
async def atualizar_categoria(
    categoria_id: UUID,
    data: CategoriaUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        return await svc.atualizar_categoria(
            categoria_id=categoria_id,
            nome=data.nome,
            cor_hex=data.cor_hex,
            icone=data.icone,
            ordem=data.ordem,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_categoria(
    categoria_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        removida = await svc.inativar_categoria(categoria_id)
        if not removida:
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# =============================================================================
# OVERRIDE DE CONFIGURAÇÃO POR FAZENDA
# =============================================================================

@router.get("/fazenda/{unidade_produtiva_id}", response_model=ConfiguracaoFazendaResponse, deprecated=True)
async def get_configuracao_fazenda(
    unidade_produtiva_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        cfg = await svc.get_configuracao_fazenda(unidade_produtiva_id)
    except EntityNotFoundError:
        logger.bind(
            event="CONFIG_UP_CROSS_TENANT_BLOCKED",
            tenant_id=str(tenant.id),
            unidade_produtiva_id=str(unidade_produtiva_id),
            endpoint="/config/fazenda/{unidade_produtiva_id}",
            status=404,
            result="blocked",
        ).warning("UP não encontrada no tenant atual ao consultar configuração.")
        raise HTTPException(status_code=404, detail="Unidade Produtiva não encontrada.")
    if not cfg:
        logger.bind(
            event="CONFIG_UP_GET",
            tenant_id=str(tenant.id),
            unidade_produtiva_id=str(unidade_produtiva_id),
            endpoint="/config/fazenda/{unidade_produtiva_id}",
            status=200,
            result="default",
        ).info("Consulta de configuração por Unidade Produtiva retornou defaults.")
        return ConfiguracaoFazendaResponse(unidade_produtiva_id=unidade_produtiva_id, overrides={})
    logger.bind(
        event="CONFIG_UP_GET",
        tenant_id=str(tenant.id),
        unidade_produtiva_id=str(unidade_produtiva_id),
        endpoint="/config/fazenda/{unidade_produtiva_id}",
        status=200,
        result="ok",
    ).info("Consulta de configuração por Unidade Produtiva concluída.")
    return cfg


@router.put("/fazenda/{unidade_produtiva_id}", response_model=ConfiguracaoFazendaResponse, deprecated=True)
async def set_configuracao_fazenda(
    unidade_produtiva_id: UUID,
    data: ConfiguracaoFazendaUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    try:
        cfg = await svc.set_override_fazenda(unidade_produtiva_id, data.overrides)
        await session.commit()
        logger.bind(
            event="CONFIG_UP_PUT",
            tenant_id=str(tenant.id),
            unidade_produtiva_id=str(unidade_produtiva_id),
            endpoint="/config/fazenda/{unidade_produtiva_id}",
            status=200,
            result="ok",
        ).info("Atualização de configuração por Unidade Produtiva concluída.")
        return cfg
    except EntityNotFoundError:
        logger.bind(
            event="CONFIG_UP_CROSS_TENANT_BLOCKED",
            tenant_id=str(tenant.id),
            unidade_produtiva_id=str(unidade_produtiva_id),
            endpoint="/config/fazenda/{unidade_produtiva_id}",
            status=404,
            result="blocked",
        ).warning("UP não encontrada no tenant atual ao atualizar configuração.")
        raise HTTPException(status_code=404, detail="Unidade Produtiva não encontrada.")
    except BusinessRuleError as exc:
        logger.bind(
            event="CONFIG_UP_UNKNOWN_KEY_BLOCKED",
            tenant_id=str(tenant.id),
            unidade_produtiva_id=str(unidade_produtiva_id),
            endpoint="/config/fazenda/{unidade_produtiva_id}",
            status=422,
            result="blocked",
        ).warning("Payload de configuração por UP bloqueado por contrato congelado.")
        raise HTTPException(status_code=422, detail=str(exc))


# =============================================================================
# HISTÓRICO DE CONFIGURAÇÕES
# =============================================================================

@router.get("/historico", response_model=List[HistoricoConfiguracaoItem])
async def get_historico_configuracoes(
    limit: int = 50,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)
    return await svc.get_historico(limit=limit)


# =============================================================================
# ONBOARDING WIZARD
# =============================================================================

@router.post("/onboarding/configurar")
async def completar_onboarding(
    data: OnboardingConfigRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ConfiguracoesService(session, tenant.id)

    try:
        await svc.set_ano_agricola(data.ano_agricola_inicio, data.ano_agricola_fim)
        await svc.set_unidade_area_padrao(data.unidade_area)
        await svc.set_moeda_padrao(data.moeda)
        await svc.set_fuso_horario(data.fuso_horario)
        await svc.set_configuracao("geral", "idioma", data.idioma)

        # Funcionalidades relacionadas à definição de Cultura, ERP e Módulos
        # foram delegadas para o Orquestrador de Implantação (Wizard) ou 
        # resolvidas de forma canônica no sistema.
        # Nenhuma integração deve ser disparada deste endpoint legado.

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if data.aceitar_categorias_padrao:
        await seed_categorias_padrao(session, tenant.id)

    # Marcar onboarding como completo
    tenant.onboarding_configuracao_completo = True
    await session.commit()

    return {
        "message": "Configuração inicial concluída com sucesso",
        "proximo_passo": "/dashboard"
    }


# =============================================================================
# SEGURANÇA (RATE LIMITING)
# =============================================================================

@router.get("/seguranca", response_model=SegurancaConfigResponse)
async def get_seguranca_config(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = ConfiguracoesService(session, tenant.id)
    config = await svc.get_seguranca_config()
    return SegurancaConfigResponse(**config)


@router.patch("/seguranca", response_model=SegurancaConfigResponse)
async def update_seguranca_config(
    data: SegurancaConfigUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = ConfiguracoesService(session, tenant.id)
    atual = await svc.get_seguranca_config()

    config = await svc.set_seguranca_config(
        rate_limiting_ativo=data.rate_limiting_ativo if data.rate_limiting_ativo is not None else atual["rate_limiting_ativo"],
        max_tentativas=data.max_tentativas if data.max_tentativas is not None else atual["max_tentativas"],
        tempo_bloqueio_minutos=data.tempo_bloqueio_minutos if data.tempo_bloqueio_minutos is not None else atual["tempo_bloqueio_minutos"],
    )
    return SegurancaConfigResponse(**config)
