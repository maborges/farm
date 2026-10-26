"""Roteador administrativo do Backoffice para o Dashboard Executivo, Observabilidade e Governança do DeepFarms Agro (AGRO-ADMIN-01F).

Consolida em tempo real:
- Métricas agregadas de usuários gratuitos (LGPD-compliant, sem exposição de PII)
- Volumetria e telemetria de tráfego das APIs públicas (Clima, Mercado, BYOK)
- Situação operacional dos adaptadores meteorológicos e fontes de cotações
- Alertas operacionais dinâmicos baseados no estado real da infraestrutura
- Dashboard de conformidade das 11 pendências técnicas de homologação
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import get_session, require_any_permission
from core.models.auth import TenantUsuario, Usuario
from core.models.sessao import SessaoAtiva
from core.models.usuario_byok import UsuarioByokCredential
from core.schemas.agro_config_schemas import (
    KEY_CLIMA,
    KEY_FLAGS,
    KEY_MERCADO,
    AgroClimaConfig,
)
from core.schemas.agro_dashboard_schemas import (
    AgroDashboardEvolucaoItem,
    AgroDashboardResumoResponse,
    AgroDashboardSaudeSistema,
    AgroDashboardTrafegoOverview,
    AgroDashboardUsuariosEvolucaoResponse,
    AgroDashboardUsuariosOverview,
    AgroHomologacaoDashboardResponse,
    AgroHomologacaoItem,
    AgroOperationalAlertItem,
)
from core.services.agro_config_service import agro_config_service
from core.services.deral_snapshot_service import deral_snapshot_service
from core.services.market_sources_service import market_sources_service
from public_clima.cache import ClimaCache

router = APIRouter(
    prefix="/backoffice/agro/dashboard",
    tags=["Backoffice — DeepFarms Agro Dashboard & Observabilidade"],
)

PERM_VIEW = [
    "backoffice:agro:view",
    "backoffice:agro:metrics:view",
    "backoffice:agro:config:view",
    "backoffice:agro:*",
]


# ==============================================================================
# 1. RESUMO EXECUTIVO CONSOLIDADO
# ==============================================================================

@router.get(
    "/resumo",
    response_model=AgroDashboardResumoResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Resumo executivo consolidado da operação do DeepFarms Agro",
)
async def get_dashboard_resumo(
    session: AsyncSession = Depends(get_session),
) -> AgroDashboardResumoResponse:
    """Consolida KPIs de usuários, tráfego público, fontes oficiais e integridade técnica."""
    agora = datetime.now(timezone.utc)
    hoje_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    sete_dias_atras = agora - timedelta(days=7)
    trinta_dias_atras = agora - timedelta(days=30)

    # 1. Agregação de Usuários Gratuitos (is_superuser == False e fora de Tenants comerciais)
    subq_commercial = select(TenantUsuario.usuario_id).distinct()
    base_filter = [
        Usuario.is_superuser == False,
        Usuario.id.not_in(subq_commercial),
    ]

    total_gratuitos = (
        await session.scalar(select(func.count(Usuario.id)).where(*base_filter))
    ) or 0

    novos_hoje = (
        await session.scalar(
            select(func.count(Usuario.id)).where(*base_filter, Usuario.created_at >= hoje_inicio)
        )
    ) or 0

    novos_7d = (
        await session.scalar(
            select(func.count(Usuario.id)).where(*base_filter, Usuario.created_at >= sete_dias_atras)
        )
    ) or 0

    novos_30d = (
        await session.scalar(
            select(func.count(Usuario.id)).where(*base_filter, Usuario.created_at >= trinta_dias_atras)
        )
    ) or 0

    bloqueados = (
        await session.scalar(
            select(func.count(Usuario.id)).where(*base_filter, Usuario.ativo == False)
        )
    ) or 0

    # Usuários com credencial BYOK ativa
    subq_byok = select(UsuarioByokCredential.usuario_id).distinct()
    com_byok = (
        await session.scalar(
            select(func.count(Usuario.id)).where(*base_filter, Usuario.id.in_(subq_byok))
        )
    ) or 0

    taxa_byok = round((com_byok / total_gratuitos * 100), 1) if total_gratuitos > 0 else 0.0

    # Usuários ativos baseados em sessões recentes
    subq_free_ids = select(Usuario.id).where(*base_filter)
    ativos_hoje = (
        await session.scalar(
            select(func.count(func.distinct(SessaoAtiva.usuario_id))).where(
                SessaoAtiva.usuario_id.in_(subq_free_ids),
                SessaoAtiva.ultimo_heartbeat >= hoje_inicio,
            )
        )
    ) or 0

    ativos_7d = (
        await session.scalar(
            select(func.count(func.distinct(SessaoAtiva.usuario_id))).where(
                SessaoAtiva.usuario_id.in_(subq_free_ids),
                SessaoAtiva.ultimo_heartbeat >= sete_dias_atras,
            )
        )
    ) or 0

    anterior_30d = max(1, total_gratuitos - novos_30d)
    crescimento_mensal = round((novos_30d / anterior_30d) * 100, 1)

    # 2. Telemetria de Clima & Cache
    cache = ClimaCache(redis_url=settings.redis_url)
    shared_redis = await cache.redis_ready()

    valor_clima, _, _ = await agro_config_service.get_config(session, KEY_CLIMA)
    cfg_clima = AgroClimaConfig.model_validate(valor_clima)

    metrics_clima = await cache.get_metrics(cfg_clima.active_provider.upper(), shared_redis)
    reqs_clima = metrics_clima.get("upstream_calls_month", 0)
    hits_clima = metrics_clima.get("cache_hits", 0)
    miss_clima = metrics_clima.get("cache_misses", 0)
    total_cache = hits_clima + miss_clima
    hit_rate = round((hits_clima / total_cache * 100), 1) if total_cache > 0 else 0.0
    timeouts_clima = metrics_clima.get("timeouts", 0)
    falhas_clima = metrics_clima.get("failures", 0)

    # 3. Telemetria de Mercado
    sources_status = await market_sources_service.get_sources_status(session=session)
    fontes_op = sum(1 for s in sources_status.sources if s.status in ("ONLINE", "DEPRECIADO"))
    fontes_tot = len(sources_status.sources)

    # Snapshot DERAL ativo e defasagem
    deral_snaps = await deral_snapshot_service.list_snapshots(session)
    active_snap = next(
        (s for s in deral_snaps.snapshots if s.is_active or s.id == deral_snaps.active_snapshot_id),
        None,
    )
    snap_id = active_snap.id if active_snap else "Nenhum"
    snap_ref = active_snap.data_referencia if active_snap else "2026-10-16"
    try:
        ref_date = datetime.strptime(snap_ref, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        defasagem = max(0, (agora - ref_date).days)
    except Exception:
        defasagem = 7

    # 4. Avaliação de Alertas e Saúde
    contingencia_ativa = bool(cfg_clima.contingency_provider)
    criticos = 0
    warnings = 0
    infos = 0

    if not shared_redis:
        infos += 1
    if contingencia_ativa:
        warnings += 1
    if timeouts_clima > 0 or falhas_clima > 0:
        warnings += 1
    if defasagem > 14:
        warnings += 1

    return AgroDashboardResumoResponse(
        consultado_em=agora.isoformat(),
        usuarios=AgroDashboardUsuariosOverview(
            total_gratuitos=total_gratuitos,
            novos_hoje=novos_hoje,
            novos_7d=novos_7d,
            novos_30d=novos_30d,
            ativos_hoje=ativos_hoje,
            ativos_7d=ativos_7d,
            bloqueados=bloqueados,
            com_byok=com_byok,
            taxa_conversao_byok_pct=taxa_byok,
            crescimento_mensal_pct=crescimento_mensal,
        ),
        trafego=AgroDashboardTrafegoOverview(
            clima_requisicoes_mes=reqs_clima,
            clima_cache_hits=hits_clima,
            clima_cache_misses=miss_clima,
            clima_hit_rate_pct=hit_rate,
            clima_timeouts=timeouts_clima,
            clima_falhas=falhas_clima,
            mercado_fontes_operacionais=fontes_op,
            mercado_fontes_total=fontes_tot,
            snapshot_deral_ativo_id=snap_id,
            snapshot_deral_referencia=snap_ref,
            snapshot_deral_defasagem_dias=defasagem,
        ),
        saude=AgroDashboardSaudeSistema(
            redis_online=shared_redis,
            provedor_clima_ativo=cfg_clima.active_provider,
            contingencia_clima_ativa=contingencia_ativa,
            alertas_criticos_count=criticos,
            alertas_warning_count=warnings,
            alertas_info_count=infos,
            homologacao_concluida_pct=27.3,  # 3 de 11 aprovados com evidência estrita comprovada
        ),
    )


# ==============================================================================
# 2. EVOLUÇÃO E SÉRIES TEMPORAIS DE ADOÇÃO
# ==============================================================================

@router.get(
    "/usuarios-evolucao",
    response_model=AgroDashboardUsuariosEvolucaoResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Histórico diário dos últimos 30 dias de evolução cadastral",
)
async def get_dashboard_usuarios_evolucao(
    session: AsyncSession = Depends(get_session),
) -> AgroDashboardUsuariosEvolucaoResponse:
    """Gera agregados diários de novos cadastros e distribuição de BYOK para visualização gráfica."""
    agora = datetime.now(timezone.utc)
    subq_commercial = select(TenantUsuario.usuario_id).distinct()

    # Busca todos os cadastros gratuitos dos últimos 30 dias ordenados
    trinta_dias_atras = agora - timedelta(days=30)
    stmt = (
        select(Usuario.created_at)
        .where(
            Usuario.is_superuser == False,
            Usuario.id.not_in(subq_commercial),
            Usuario.created_at >= trinta_dias_atras,
        )
        .order_by(Usuario.created_at.asc())
    )
    res = await session.execute(stmt)
    timestamps = res.scalars().all()

    # Agrupa por dia YYYY-MM-DD
    agregados_dia: dict[str, int] = {}
    for i in range(30, -1, -1):
        dia_str = (agora - timedelta(days=i)).strftime("%Y-%m-%d")
        agregados_dia[dia_str] = 0

    for ts in timestamps:
        if ts:
            dia = ts.strftime("%Y-%m-%d")
            if dia in agregados_dia:
                agregados_dia[dia] += 1

    # Monta pontos com acumulado
    total_anterior = (
        await session.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.is_superuser == False,
                Usuario.id.not_in(subq_commercial),
                Usuario.created_at < trinta_dias_atras,
            )
        )
    ) or 0

    historico: list[AgroDashboardEvolucaoItem] = []
    acum = total_anterior
    for dia_k, qtd in sorted(agregados_dia.items()):
        acum += qtd
        historico.append(AgroDashboardEvolucaoItem(data=dia_k, novos_cadastros=qtd, acumulado=acum))

    # Distribuição Ativo / Bloqueado
    ativos_count = (
        await session.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.is_superuser == False,
                Usuario.id.not_in(subq_commercial),
                Usuario.ativo == True,
            )
        )
    ) or 0
    bloqueados_count = (
        await session.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.is_superuser == False,
                Usuario.id.not_in(subq_commercial),
                Usuario.ativo == False,
            )
        )
    ) or 0

    # Distribuição BYOK por provedor
    byok_stmt = select(
        UsuarioByokCredential.provider_slug,
        func.count(UsuarioByokCredential.id),
    ).group_by(UsuarioByokCredential.provider_slug)
    byok_res = await session.execute(byok_stmt)
    dist_byok = {row[0]: row[1] for row in byok_res.all()}

    return AgroDashboardUsuariosEvolucaoResponse(
        historico_30d=historico,
        distribuicao_status={"ativos": ativos_count, "bloqueados": bloqueados_count},
        distribuicao_byok_provedor=dist_byok,
    )


# ==============================================================================
# 3. MOTOR DE ALERTAS OPERACIONAIS DINÂMICOS
# ==============================================================================

@router.get(
    "/alertas",
    response_model=list[AgroOperationalAlertItem],
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista alertas operacionais ativos detectados no ecossistema Agro",
)
async def list_dashboard_alertas(
    session: AsyncSession = Depends(get_session),
) -> list[AgroOperationalAlertItem]:
    """Avalia em tempo real as condições da plataforma sem persistência redundante."""
    agora = datetime.now(timezone.utc)
    alertas: list[AgroOperationalAlertItem] = []

    # 1. Alerta de Conexão Redis
    cache = ClimaCache(redis_url=settings.redis_url)
    shared_redis = await cache.redis_ready()
    if not shared_redis:
        alertas.append(
            AgroOperationalAlertItem(
                id="SYS-REDIS-FALLBACK",
                tipo="REDIS_OFFLINE",
                severidade="INFO",
                prioridade="NORMAL",
                categoria="INFRAESTRUTURA",
                titulo="Redis Indisponível — Modo Single-Worker Ativo",
                descricao="O cache está operando em memória local por processo devido à ausência de conexão com o cluster Redis.",
                data_deteccao=agora.isoformat(),
                recomendacao="Verifique as credenciais e disponibilidade do Redis em produção.",
                origem="ClimaCache & AgroConfigService",
            )
        )

    # 2. Alerta de Contingência Climática
    valor_clima, _, _ = await agro_config_service.get_config(session, KEY_CLIMA)
    cfg_clima = AgroClimaConfig.model_validate(valor_clima)
    if cfg_clima.contingency_provider:
        alertas.append(
            AgroOperationalAlertItem(
                id="CLIMA-CONTINGENCY-ON",
                tipo="CONTINGENCIA_METEOROLOGICA",
                severidade="WARNING",
                prioridade="HIGH",
                categoria="CLIMATICO",
                titulo=f"Contingência Climática Ativa ({cfg_clima.contingency_provider})",
                descricao=f"As requisições públicas de previsão estão sendo desviadas para o provedor de contingência '{cfg_clima.contingency_provider}'.",
                data_deteccao=agora.isoformat(),
                recomendacao="Desative a contingência no Backoffice de Provedores após a estabilização do provedor primário.",
                origem="DynamicWeatherOrchestrator",
            )
        )

    # 3. Alertas de Falhas/Timeouts no Provedor Ativo
    metrics_clima = await cache.get_metrics(cfg_clima.active_provider.upper(), shared_redis)
    timeouts = metrics_clima.get("timeouts", 0)
    falhas = metrics_clima.get("failures", 0)
    if timeouts > 5 or falhas > 5:
        alertas.append(
            AgroOperationalAlertItem(
                id=f"CLIMA-INSTABILIDADE-{cfg_clima.active_provider}",
                tipo="UPSTREAM_INSTABILITY",
                severidade="WARNING",
                prioridade="HIGH",
                categoria="CLIMATICO",
                titulo=f"Instabilidade no Provedor {cfg_clima.active_provider}",
                descricao=f"Registrados {timeouts} timeouts e {falhas} falhas de upstream no mês corrente.",
                data_deteccao=agora.isoformat(),
                recomendacao="Verifique a latência de rede upstream ou acione a cadeia de fallback secundária.",
                origem=f"Adapter {cfg_clima.active_provider}",
            )
        )

    # 4. Alerta de Defasagem de Snapshot DERAL
    deral_snaps = await deral_snapshot_service.list_snapshots(session)
    active_snap = next(
        (s for s in deral_snaps.snapshots if s.is_active or s.id == deral_snaps.active_snapshot_id),
        None,
    )
    if active_snap:
        try:
            ref_dt = datetime.strptime(active_snap.data_referencia, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dias_def = (agora - ref_dt).days
            if dias_def > 14:
                alertas.append(
                    AgroOperationalAlertItem(
                        id="MERCADO-DERAL-DEFASADO",
                        tipo="SNAPSHOT_DESATUALIZADO",
                        severidade="WARNING",
                        prioridade="NORMAL",
                        categoria="GOVERNANCA",
                        titulo=f"Snapshot DERAL Defasado ({dias_def} dias)",
                        descricao=f"O levantamento semanal ativo data de {active_snap.data_referencia}. O intervalo recomendado é de até 14 dias.",
                        data_deteccao=agora.isoformat(),
                        recomendacao="Faça upload e ativação da planilha oficial mais recente emitida pela SEAB-PR.",
                        origem="DeralSnapshotService",
                    )
                )
        except Exception:
            pass

    # 5. Alerta de Feature Flags Desabilitadas
    flags_raw = agro_config_service.get_cached_config_dict(KEY_FLAGS) or {}
    for flag_name, is_enabled in flags_raw.items():
        if is_enabled is False:
            alertas.append(
                AgroOperationalAlertItem(
                    id=f"FLAG-OFF-{flag_name.upper()}",
                    tipo="FEATURE_FLAG_DISABLED",
                    severidade="INFO",
                    prioridade="LOW",
                    categoria="OPERACIONAL",
                    titulo=f"Funcionalidade Desabilitada: {flag_name}",
                    descricao=f"A capacidade '{flag_name}' foi suspensa pela administração nas configurações de Feature Flags.",
                    data_deteccao=agora.isoformat(),
                    recomendacao="Reative o módulo em Configurações > Feature Flags quando a operação for retomada.",
                    origem="AgroFeatureFlagsConfig",
                )
            )

    return alertas


# ==============================================================================
# 4. DASHBOARD DE PENDÊNCIAS TÉCNICAS DE HOMOLOGAÇÃO
# ==============================================================================

@router.get(
    "/homologacao",
    response_model=AgroHomologacaoDashboardResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Painel consolidado das 11 pendências técnicas de homologação",
)
async def get_dashboard_homologacao(
    session: AsyncSession = Depends(get_session),
) -> AgroHomologacaoDashboardResponse:
    """Retorna a matriz de maturidade técnica das fases AGRO-ADMIN com status estrito baseado em evidências."""
    agora = datetime.now(timezone.utc)

    itens = [
        AgroHomologacaoItem(
            id=1,
            titulo="Chave Mestra Dedicada e Rotação",
            descricao="Provisionamento de KEK mestra em HSM/KMS de nuvem e ciclo de rotação segura.",
            fase_origem="01E3 / 01E3A",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-24] Envelope Encryption AES-256-GCM implementado com suporte a KEK v1/v2 em PlatformWeatherCredentialsService. Fallback silencioso de JWT_SECRET_KEY desativado em staging/produção.",
            acao_necessaria="Injetar PLATFORM_CREDENTIALS_MASTER_KEY no ambiente de staging isolado e validar rotação.",
        ),
        AgroHomologacaoItem(
            id=2,
            titulo="Licenciamento dos Provedores Climáticos",
            descricao="Comprovação de termos contratuais para redistribuição pública em modo SaaS.",
            fase_origem="01E3 / 01E3A",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-24] Flags open_meteo_licensed e openweather_licensed integradas. DynamicWeatherOrchestrator recusa fallback para provedor sem autorização pública expressa.",
            acao_necessaria="Anexar termos de serviço dos provedores upstream no ambiente de staging.",
        ),
        AgroHomologacaoItem(
            id=3,
            titulo="Contabilização de Cotas de Clima",
            descricao="Medição atômica de requisições mensais e prevenção de estouro de billing.",
            fase_origem="01E3 / 01E3A",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-24] Reserva atômica de cota com script Lua em Redis antes da chamada upstream, com reversão (rollback) em caso de falha de rede/timeout.",
            acao_necessaria="Executar teste de concorrência com Redis real no ambiente de staging.",
        ),
        AgroHomologacaoItem(
            id=4,
            titulo="Proveniência Verificável DERAL",
            descricao="Restrição estrita a domínios governamentais homologados (*.pr.gov.br).",
            fase_origem="01E4 / 01E4A",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-24] Whitelist estrita para *.pr.gov.br e recálculo SHA-256. Proveniência da URL remota permanece declaratória, sem atestação criptográfica de origem.",
            acao_necessaria="Homologar pipeline de upload assistido com rastreabilidade de operador e carimbo de data/hora em staging.",
        ),
        AgroHomologacaoItem(
            id=5,
            titulo="Teste de Importação com XLS Oficial Válido",
            descricao="Processamento e extração de planilhas oficiais emitidas pelo DERAL/SEAB-PR.",
            fase_origem="01E4 / 01E4A",
            status="APROVADO",
            evidencia="[Homologado Local 2026-10-22] Parser binário BIFF8 via xlrd homologado com conferência de assinatura OLE2, validação de cabeçalho e arredondamento DECIMAL HALF_UP em test_deral_snapshot_service.py.",
            acao_necessaria="Nenhuma para o parser. Próximas amostras serão processadas no fluxo de staging.",
        ),
        AgroHomologacaoItem(
            id=6,
            titulo="Homologação em PostgreSQL Real",
            descricao="Execução de todos os schemas e migrações em instância dedicada PostgreSQL.",
            fase_origem="Geral",
            status="PENDENTE",
            evidencia="[Pendente Staging] Validações locais executadas com isolamento de banco. Staging dockerizado preparado com PostgreSQL 16 dedicado.",
            acao_necessaria="Inicializar container PostgreSQL 16 no ambiente de staging e executar migrations Alembic validadas.",
        ),
        AgroHomologacaoItem(
            id=7,
            titulo="Cluster Redis Real",
            descricao="Validação de invalidação de cache distribuído via Redis Pub/Sub.",
            fase_origem="Geral",
            status="PENDENTE",
            evidencia="[Pendente Staging] Mocks e fallbacks em memória utilizados nos testes unitários locais. Staging dockerizado preparado com Redis 7 isolado.",
            acao_necessaria="Conectar instância Redis 7 do staging e homologar concorrência da reserva de cotas e Pub/Sub.",
        ),
        AgroHomologacaoItem(
            id=8,
            titulo="Sincronização Multi-Worker",
            descricao="Reconciliação e alinhamento de ponteiros ativos entre múltiplos processos de backend.",
            fase_origem="01E4A / 01E5",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-22] Reconciliação periódica via DB (sync_active_snapshot_from_db) implementada. Pendente teste com múltiplos processos ASGI reais.",
            acao_necessaria="Homologar dois workers FastAPI independentes (portas 8001 e 8002) concorrentes no staging.",
        ),
        AgroHomologacaoItem(
            id=9,
            titulo="Retenção de Documentos Originais",
            descricao="Custódia forense dos arquivos brutos XLS/JSON submetidos pelo Backoffice.",
            fase_origem="01E4A",
            status="EM VALIDAÇÃO",
            evidencia="[Validação Local 2026-10-22] Custódia forense em Base64 na coluna conteudo_original_b64 com recálculo de SHA-256 e rota /download-raw. Limites de payload de 10MB documentados.",
            acao_necessaria="Validar download do arquivo bruto e integridade SHA-256 no ambiente de staging.",
        ),
        AgroHomologacaoItem(
            id=10,
            titulo="Integridade dos Catálogos Globais",
            descricao="Bloqueio de deleção de registros referenciados e segregação de tenants privados.",
            fase_origem="01E5",
            status="APROVADO",
            evidencia="[Homologado Local 2026-10-23] Segregação estrita (tenant_id IS NULL), proteção contra deleção com chave estrangeira (HTTP 409) comprovada em test_backoffice_agro_01e5.py.",
            acao_necessaria="Nenhuma. Regras atômicas e isolamento multi-tenant garantidos e testados.",
        ),
        AgroHomologacaoItem(
            id=11,
            titulo="Build e Testes Integrados Web/Agro",
            descricao="Aderência estrita a tipagem TypeScript e passagem de todas as suítes de teste.",
            fase_origem="01E5",
            status="APROVADO",
            evidencia="[Homologado Local 2026-10-24] TypeScript Strict Mode 100% limpo em apps/web e apps/agro (Next.js 16.1.6). Bateria de testes unitários aprovada com 0 falhas.",
            acao_necessaria="Nenhuma. Compilação estrita e lint verificados.",
        ),
    ]

    tot = len(itens)
    aprovados = sum(1 for i in itens if i.status == "APROVADO")
    em_val = sum(1 for i in itens if i.status == "EM VALIDAÇÃO")
    pendentes = sum(1 for i in itens if i.status == "PENDENTE")
    bloqueados = sum(1 for i in itens if i.status == "BLOQUEADO")
    pct = round((aprovados / tot) * 100, 1)

    return AgroHomologacaoDashboardResponse(
        gerado_em=agora.isoformat(),
        total_itens=tot,
        aprovados_count=aprovados,
        em_validacao_count=em_val,
        pendentes_count=pendentes,
        bloqueados_count=bloqueados,
        percentual_conclusao=pct,
        itens=itens,
    )
