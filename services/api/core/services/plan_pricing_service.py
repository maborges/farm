"""
Service para gerenciamento de pricing dinâmico de planos.

Implementa cálculo de preços por faixa de usuários com preços progressivos.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.models.plan_changes import PlanoPricing
from core.models.billing import PlanoAssinatura
from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError


class PlanoPricingService(BaseService[PlanoPricing]):
    """Service para gerenciar pricing de planos."""

    def __init__(self, session: AsyncSession):
        """Inicializa o service sem tenant_id (dados globais de pricing)."""
        super().__init__(PlanoPricing, session, tenant_id=None)

    async def calcular_preco_total(
        self,
        plano_id: UUID,
        quantidade_usuarios: int,
        ciclo: str = "MENSAL"
    ) -> tuple[Decimal, list[dict]]:
        """
        Calcula o preço total da assinatura compondo o valor base do pacote com
        o valor dos acessos simultâneos contratados a mais.

        Regra de negócio:
        - O pacote possui um preço base (`preco_mensal` ou `preco_anual`) que já
          inclui a franquia base de acessos simultâneos (`limite_usuarios_minimo`, padrão 1).
        - Caso o assinante contrate acessos simultâneos adicionais (`quantidade_usuarios > limite_usuarios_minimo`),
          os acessos excedentes (`usuarios_adicionais`) são precificados pela tabela progressiva
          de faixas do pacote (`PlanoPricing`).

        Args:
            plano_id: ID do pacote/plano.
            quantidade_usuarios: Quantidade total de acessos simultâneos desejados.
            ciclo: MENSAL ou ANUAL.

        Returns:
            tuple[Decimal, list[dict]]: (valor_total, detalhamento_faixas)

        Raises:
            EntityNotFoundError: Se plano não existe.
            BusinessRuleError: Se quantidade de usuários inválida ou sem faixa para excedentes.
        """
        # Validar plano e limites mínimo/máximo
        plano = await self._validar_plano(plano_id, quantidade_usuarios)

        preco_base_raw = plano.preco_anual if ciclo == "ANUAL" else plano.preco_mensal
        preco_pacote = Decimal(str(preco_base_raw or 0))
        usuarios_inclusos = max(1, int(plano.limite_usuarios_minimo or 1))
        usuarios_adicionais = max(0, quantidade_usuarios - usuarios_inclusos)

        valor_total = preco_pacote
        detalhamento: list[dict] = [
            {
                "tipo": "PACOTE_BASE",
                "faixa_inicio": 1,
                "faixa_fim": usuarios_inclusos,
                "usuarios_nesta_faixa": min(quantidade_usuarios, usuarios_inclusos),
                "preco_unitario": float(preco_pacote),
                "valor_faixa": float(preco_pacote),
            }
        ]

        if usuarios_adicionais == 0:
            logger.info(
                f"Calculado preço base para pacote {plano.nome}: {quantidade_usuarios} acessos "
                f"(inclusos={usuarios_inclusos}) = R$ {valor_total} ({ciclo})"
            )
            return valor_total, detalhamento

        # Buscar faixas de pricing para os acessos adicionais ordenadas por faixa_inicio
        stmt = (
            select(PlanoPricing)
            .where(PlanoPricing.plano_id == plano_id)
            .where(PlanoPricing.ativo == True)
            .order_by(PlanoPricing.faixa_inicio)
        )
        result = await self.session.execute(stmt)
        faixas = result.scalars().all()

        if not faixas:
            raise BusinessRuleError(
                f"Plano {plano.nome} não possui tabela de preços configurada para "
                f"acessos simultâneos adicionais ({usuarios_adicionais} adicional(is)). "
                "Contate o comercial."
            )

        usuarios_restantes = usuarios_adicionais

        for faixa in faixas:
            if usuarios_restantes <= 0:
                break

            # Determinar quantos acessos adicionais cabem nesta faixa (1..usuarios_adicionais)
            usuarios_nesta_faixa = self._calcular_usuarios_na_faixa(
                usuarios_restantes,
                faixa.faixa_inicio,
                faixa.faixa_fim,
                usuarios_adicionais
            )

            if usuarios_nesta_faixa <= 0:
                continue

            preco_unitario = Decimal(
                str(
                    faixa.preco_por_usuario_anual if ciclo == "ANUAL"
                    else faixa.preco_por_usuario_mensal
                )
            )

            valor_faixa = preco_unitario * usuarios_nesta_faixa
            valor_total += valor_faixa

            detalhamento.append({
                "tipo": "ACESSO_ADICIONAL",
                "faixa_inicio": faixa.faixa_inicio,
                "faixa_fim": faixa.faixa_fim,
                "usuarios_nesta_faixa": usuarios_nesta_faixa,
                "preco_unitario": float(preco_unitario),
                "valor_faixa": float(valor_faixa),
            })

            usuarios_restantes -= usuarios_nesta_faixa

        if usuarios_restantes > 0:
            raise BusinessRuleError(
                f"Plano {plano.nome} não possui faixa de preço configurada para "
                f"{usuarios_adicionais} acessos adicionais (total solicitado: {quantidade_usuarios}). "
                f"Máximo adicional configurado: {usuarios_adicionais - usuarios_restantes}. "
                "Contate o comercial."
            )

        logger.info(
            f"Calculado preço composto para pacote {plano.nome}: {quantidade_usuarios} acessos "
            f"(base={usuarios_inclusos}, adicionais={usuarios_adicionais}) = R$ {valor_total} ({ciclo})"
        )

        return valor_total, detalhamento

    async def calcular_diferenca_planos(
        self,
        plano_origem_id: UUID,
        usuarios_origem: int,
        plano_destino_id: UUID,
        usuarios_destino: int,
        ciclo: str = "MENSAL"
    ) -> dict:
        """
        Calcula a diferença de preço entre dois planos/quantidades.

        Args:
            plano_origem_id: Plano atual
            usuarios_origem: Usuários atuais
            plano_destino_id: Plano novo
            usuarios_destino: Usuários novos
            ciclo: MENSAL ou ANUAL

        Returns:
            dict com valores e diferenças
        """
        # Calcular preço atual
        valor_atual, detalhes_atual = await self.calcular_preco_total(
            plano_origem_id, usuarios_origem, ciclo
        )

        # Calcular preço novo
        valor_novo, detalhes_novo = await self.calcular_preco_total(
            plano_destino_id, usuarios_destino, ciclo
        )

        diferenca = valor_novo - valor_atual

        return {
            "valor_atual": valor_atual,
            "detalhes_atual": detalhes_atual,
            "valor_novo": valor_novo,
            "detalhes_novo": detalhes_novo,
            "diferenca": diferenca,
            "percentual_diferenca": (
                float((diferenca / valor_atual) * 100) if valor_atual > 0 else 0
            ),
            "ciclo": ciclo
        }

    async def validar_quantidade_usuarios(
        self,
        plano_id: UUID,
        quantidade: int
    ) -> bool:
        """
        Valida se a quantidade de usuários está dentro dos limites do plano.

        Args:
            plano_id: ID do plano
            quantidade: Quantidade de usuários

        Returns:
            True se válido

        Raises:
            BusinessRuleError: Se quantidade inválida
        """
        plano = await self._validar_plano(plano_id, quantidade)
        return True

    async def obter_faixas_plano(self, plano_id: UUID) -> list[PlanoPricing]:
        """Retorna todas as faixas de pricing de um plano."""
        stmt = (
            select(PlanoPricing)
            .where(PlanoPricing.plano_id == plano_id)
            .where(PlanoPricing.ativo == True)
            .order_by(PlanoPricing.faixa_inicio)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def criar_faixa_pricing(
        self,
        plano_id: UUID,
        faixa_inicio: int,
        faixa_fim: Optional[int],
        preco_mensal: Decimal,
        preco_anual: Decimal
    ) -> PlanoPricing:
        """
        Cria nova faixa de pricing para um plano.

        Valida overlaps e ordem das faixas.
        """
        # Validar plano existe
        stmt = select(PlanoAssinatura).where(PlanoAssinatura.id == plano_id)
        result = await self.session.execute(stmt)
        plano = result.scalar_one_or_none()

        if not plano:
            raise EntityNotFoundError("Plano não encontrado.")

        # Validar se faixa não sobrepõe existentes
        await self._validar_overlap_faixas(plano_id, faixa_inicio, faixa_fim)

        # Criar faixa
        nova_faixa = PlanoPricing(
            plano_id=plano_id,
            faixa_inicio=faixa_inicio,
            faixa_fim=faixa_fim,
            preco_por_usuario_mensal=preco_mensal,
            preco_por_usuario_anual=preco_anual,
            ativo=True
        )

        self.session.add(nova_faixa)
        await self.session.commit()
        await self.session.refresh(nova_faixa)

        logger.info(
            f"Criada faixa de pricing: Plano {plano.nome}, "
            f"{faixa_inicio}-{faixa_fim or '∞'} users, "
            f"R${preco_mensal}/user (mensal)"
        )

        return nova_faixa

    # ========================================================================
    # Métodos privados
    # ========================================================================

    async def _validar_plano(
        self,
        plano_id: UUID,
        quantidade_usuarios: int
    ) -> PlanoAssinatura:
        """Valida existência do plano e limites de usuários."""
        stmt = select(PlanoAssinatura).where(PlanoAssinatura.id == plano_id)
        result = await self.session.execute(stmt)
        plano = result.scalar_one_or_none()

        if not plano:
            raise EntityNotFoundError("Plano não encontrado.")

        if not plano.ativo:
            raise BusinessRuleError("Plano indisponível ou inativo.")

        # Validar limites
        if quantidade_usuarios < plano.limite_usuarios_minimo:
            raise BusinessRuleError(
                f"Este plano requer no mínimo {plano.limite_usuarios_minimo} usuário(s). "
                f"Quantidade informada: {quantidade_usuarios}."
            )

        if plano.limite_usuarios_maximo and quantidade_usuarios > plano.limite_usuarios_maximo:
            raise BusinessRuleError(
                f"Plano {plano.nome} suporta no máximo {plano.limite_usuarios_maximo} usuários. "
                f"Solicitado: {quantidade_usuarios}. Para mais usuários, entre em contato."
            )

        return plano

    def _calcular_usuarios_na_faixa(
        self,
        usuarios_restantes: int,
        faixa_inicio: int,
        faixa_fim: Optional[int],
        quantidade_total: int
    ) -> int:
        """Calcula quantos usuários cabem em uma faixa específica."""
        # Se quantidade total for menor que início da faixa, não usa esta faixa
        if quantidade_total < faixa_inicio:
            return 0

        # Usuários que começam nesta faixa
        usuarios_inicio_faixa = max(0, quantidade_total - usuarios_restantes + 1)

        # Se início já passou desta faixa, calcular quantos cabem
        if usuarios_inicio_faixa > faixa_inicio:
            # Já passamos do início desta faixa
            if faixa_fim is None:
                # Faixa ilimitada, todos os restantes cabem
                return usuarios_restantes
            elif usuarios_inicio_faixa > faixa_fim:
                # Já passamos do fim desta faixa
                return 0
            else:
                # Estamos no meio da faixa
                return min(usuarios_restantes, faixa_fim - usuarios_inicio_faixa + 1)
        else:
            # Começamos nesta faixa
            if faixa_fim is None:
                # Faixa ilimitada
                return usuarios_restantes
            else:
                # Faixa limitada
                max_usuarios_faixa = faixa_fim - faixa_inicio + 1
                return min(usuarios_restantes, max_usuarios_faixa)

    async def _validar_overlap_faixas(
        self,
        plano_id: UUID,
        faixa_inicio: int,
        faixa_fim: Optional[int]
    ) -> None:
        """Valida se nova faixa não sobrepõe faixas existentes."""
        stmt = (
            select(PlanoPricing)
            .where(PlanoPricing.plano_id == plano_id)
            .where(PlanoPricing.ativo == True)
        )
        result = await self.session.execute(stmt)
        faixas_existentes = result.scalars().all()

        for faixa in faixas_existentes:
            # Verificar overlap
            if faixa_fim is None:
                # Nova faixa é ilimitada, só pode se não houver faixas acima
                if faixa.faixa_inicio >= faixa_inicio:
                    raise BusinessRuleError(
                        f"Faixa ilimitada ({faixa_inicio}+) conflita com faixa "
                        f"existente ({faixa.faixa_inicio}-{faixa.faixa_fim or '∞'})"
                    )
            elif faixa.faixa_fim is None:
                # Faixa existente é ilimitada
                if faixa_inicio >= faixa.faixa_inicio:
                    raise BusinessRuleError(
                        f"Nova faixa ({faixa_inicio}-{faixa_fim}) conflita com "
                        f"faixa ilimitada existente ({faixa.faixa_inicio}+)"
                    )
            else:
                # Ambas são limitadas, verificar overlap
                if not (faixa_fim < faixa.faixa_inicio or faixa_inicio > faixa.faixa_fim):
                    raise BusinessRuleError(
                        f"Nova faixa ({faixa_inicio}-{faixa_fim}) conflita com "
                        f"faixa existente ({faixa.faixa_inicio}-{faixa.faixa_fim})"
                    )
