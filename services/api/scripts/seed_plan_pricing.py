"""
Seed de dados iniciais para pricing de planos e configurações do SaaS.

Cria:
1. Configurações globais (dias_bloqueio, etc.)
2. Matriz de pricing para planos existentes

Uso:
    python scripts/seed_plan_pricing.py
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from core.models.billing import PlanoAssinatura
from core.models.configuration import ConfiguracaoSaaS
from core.services.plan_pricing_service import PlanoPricingService

# Tabela progressiva oficial de licenças adicionais de acesso simultâneo (Web)
# No ciclo ANUAL, todas as faixas contam com 20% de desconto (12x mensal * 0.80).
PRICING_PADRAO_POR_PLANO: dict[str, list[dict]] = {
    "Familiar": [
        {"faixa_inicio": 1, "faixa_fim": 2, "mensal": Decimal("89.00"), "anual": Decimal("854.40")},
    ],
    "Pequeno Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 2, "mensal": Decimal("99.00"), "anual": Decimal("950.40")},
        {"faixa_inicio": 3, "faixa_fim": 4, "mensal": Decimal("85.00"), "anual": Decimal("816.00")},
    ],
    "Médio Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 5, "mensal": Decimal("110.00"), "anual": Decimal("1056.00")},
        {"faixa_inicio": 6, "faixa_fim": 10, "mensal": Decimal("90.00"), "anual": Decimal("864.00")},
    ],
    "Grande Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 10, "mensal": Decimal("120.00"), "anual": Decimal("1152.00")},
        {"faixa_inicio": 11, "faixa_fim": 20, "mensal": Decimal("95.00"), "anual": Decimal("912.00")},
    ],
    "Grupo": [
        {"faixa_inicio": 1, "faixa_fim": 15, "mensal": Decimal("110.00"), "anual": Decimal("1056.00")},
        {"faixa_inicio": 16, "faixa_fim": 30, "mensal": Decimal("90.00"), "anual": Decimal("864.00")},
        {"faixa_inicio": 31, "faixa_fim": None, "mensal": Decimal("75.00"), "anual": Decimal("720.00")},
    ],
}

LIMITES_USUARIOS_POR_PLANO: dict[str, dict[str, int | None]] = {
    "Familiar": {"minimo": 1, "maximo": 3},
    "Pequeno Produtor": {"minimo": 2, "maximo": 6},
    "Médio Produtor": {"minimo": 5, "maximo": 15},
    "Grande Produtor": {"minimo": 10, "maximo": 30},
    "Grupo": {"minimo": 20, "maximo": None},
}


async def seed_configuracoes_saas():
    """Cria configurações globais do SaaS."""
    logger.info("=== Seeding configurações do SaaS ===")

    configuracoes = [
        {
            "chave": "dias_bloqueio_inadimplencia",
            "valor": {"dias": 5},
            "descricao": "Dias de tolerância para pagamento antes de bloquear tenant por inadimplência"
        },
        {
            "chave": "dias_vencimento_upgrade",
            "valor": {"dias": 3},
            "descricao": "Dias até vencimento de cobrança de upgrade de plano"
        },
        {
            "chave": "asaas_modo_sandbox",
            "valor": {"ativo": True},
            "descricao": "Usar ambiente sandbox do Asaas (desenvolvimento)"
        },
        {
            "chave": "notificacoes_upgrade",
            "valor": {"email": True, "sms": False, "whatsapp": False},
            "descricao": "Canais de notificação para upgrades de plano"
        }
    ]

    async with async_session_maker() as session:
        for config_data in configuracoes:
            # Verificar se já existe
            stmt = select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == config_data["chave"])
            result = await session.execute(stmt)
            existe = result.scalar_one_or_none()

            if existe:
                logger.info(f"Configuração '{config_data['chave']}' já existe, pulando...")
                continue

            # Criar
            config = ConfiguracaoSaaS(
                chave=config_data["chave"],
                valor=config_data["valor"],
                descricao=config_data["descricao"],
                ativo=True
            )

            session.add(config)
            logger.info(f"✓ Criada configuração: {config_data['chave']}")

        await session.commit()

    logger.info("Configurações do SaaS criadas com sucesso\n")


async def seed_plan_pricing_with_session(session: AsyncSession) -> int:
    """
    Insere de forma idempotente as faixas progressivas de acessos adicionais
    para todos os planos ativos na sessão informada.

    Args:
        session: Sessão assíncrona do banco de dados.

    Returns:
        int: Quantidade de novas faixas de pricing criadas.
    """
    pricing_service = PlanoPricingService(session)
    stmt = select(PlanoAssinatura).where(PlanoAssinatura.ativo == True)
    result = await session.execute(stmt)
    planos = result.scalars().all()

    faixas_criadas = 0
    for plano in planos:
        faixas_existentes = await pricing_service.obter_faixas_plano(plano.id)
        if faixas_existentes:
            continue

        config_plano = PRICING_PADRAO_POR_PLANO.get(plano.nome)
        if not config_plano:
            config_plano = [
                {"faixa_inicio": 1, "faixa_fim": None, "mensal": Decimal("99.00"), "anual": Decimal("950.40")}
            ]

        for faixa in config_plano:
            await pricing_service.criar_faixa_pricing(
                plano_id=plano.id,
                faixa_inicio=faixa["faixa_inicio"],
                faixa_fim=faixa["faixa_fim"],
                preco_mensal=faixa["mensal"],
                preco_anual=faixa["anual"],
            )
            faixas_criadas += 1

        limites = LIMITES_USUARIOS_POR_PLANO.get(plano.nome)
        if limites:
            plano.limite_usuarios_minimo = limites["minimo"]
            plano.limite_usuarios_maximo = limites["maximo"]

    await session.commit()
    return faixas_criadas


async def seed_pricing_exemplo():
    """
    Cria matriz de pricing oficial para os pacotes existentes.
    """
    logger.info("=== Seeding pricing de planos ===")

    async with async_session_maker() as session:
        criadas = await seed_plan_pricing_with_session(session)
        logger.info(f"\nPricing de planos sincronizado ({criadas} novas faixas criadas)\n")


async def main():
    """Executa todos os seeds."""
    logger.info("### SEED: Pricing e Configurações de Planos ###\n")

    try:
        # 1. Configurações globais
        await seed_configuracoes_saas()

        # 2. Pricing dos planos
        await seed_pricing_exemplo()

        logger.info("=== Seed concluído com sucesso! ===")
        logger.info("\n⚠️  IMPORTANTE: Revise os valores de pricing em produção!")
        logger.info("Os valores são exemplos e devem ser ajustados para sua realidade de negócio.\n")

        return True

    except Exception as e:
        logger.error(f"Erro ao executar seed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )

    # Executar seed
    sucesso = asyncio.run(main())
    sys.exit(0 if sucesso else 1)
