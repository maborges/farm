"""
Service para gerenciamento de pricing dinâmico de planos.

Implementa cálculo de preços por faixa de usuários com preços progressivos.
"""
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.constants import (
    ALL_MODULES,
    FATOR_HEQ_POR_CABECA_EXCEDENTE,
    LOTACAO_PADRAO_CABECAS_POR_HA,
    TIPOS_AREA_ISENTOS_FRANQUIA,
    obter_fator_intensidade_cultura,
)
from core.models.plan_changes import PlanoPricing
from core.models.billing import PlanoAssinatura
from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError


# Tabela progressiva oficial por perfil de pacote (20% de desconto nas licenças adicionais no ciclo ANUAL)
FAIXAS_PADRAO_POR_PLANO: dict[str, list[dict]] = {
    "Familiar": [
        {"faixa_inicio": 1, "faixa_fim": 2, "preco_por_usuario_mensal": Decimal("89.00"), "preco_por_usuario_anual": Decimal("854.40")},
    ],
    "Pequeno Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 2, "preco_por_usuario_mensal": Decimal("99.00"), "preco_por_usuario_anual": Decimal("950.40")},
        {"faixa_inicio": 3, "faixa_fim": 4, "preco_por_usuario_mensal": Decimal("85.00"), "preco_por_usuario_anual": Decimal("816.00")},
    ],
    "Médio Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 5, "preco_por_usuario_mensal": Decimal("110.00"), "preco_por_usuario_anual": Decimal("1056.00")},
        {"faixa_inicio": 6, "faixa_fim": 10, "preco_por_usuario_mensal": Decimal("90.00"), "preco_por_usuario_anual": Decimal("864.00")},
    ],
    "Grande Produtor": [
        {"faixa_inicio": 1, "faixa_fim": 10, "preco_por_usuario_mensal": Decimal("120.00"), "preco_por_usuario_anual": Decimal("1152.00")},
        {"faixa_inicio": 11, "faixa_fim": 20, "preco_por_usuario_mensal": Decimal("95.00"), "preco_por_usuario_anual": Decimal("912.00")},
    ],
    "Grupo": [
        {"faixa_inicio": 1, "faixa_fim": 15, "preco_por_usuario_mensal": Decimal("110.00"), "preco_por_usuario_anual": Decimal("1056.00")},
        {"faixa_inicio": 16, "faixa_fim": 30, "preco_por_usuario_mensal": Decimal("90.00"), "preco_por_usuario_anual": Decimal("864.00")},
        {"faixa_inicio": 31, "faixa_fim": None, "preco_por_usuario_mensal": Decimal("75.00"), "preco_por_usuario_anual": Decimal("720.00")},
    ],
}


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
            faixas_padrao = FAIXAS_PADRAO_POR_PLANO.get(plano.nome, [])
            if faixas_padrao:
                faixas = [SimpleNamespace(**f) for f in faixas_padrao]
            else:
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

    # ========================================================================
    # Hectares Equivalentes (HEq), Multi-Cultura, ILP e Simulador Transparente
    # ========================================================================

    @staticmethod
    def calcular_hectares_equivalentes_operacao(
        parametros: dict,
    ) -> dict:
        """
        Calcula a capacidade consumida em Hectares Equivalentes (HEq) considerando:
        1. Isenção total (fator 0.0x) de áreas ambientais (APP e Reserva Legal).
        2. Múltiplas culturas em talhões distintos ponderadas por intensidade operacional.
        3. Duas ou mais culturas no mesmo talhão e mesma safra (consórcio ou sucessão Safra + Safrinha):
           - Não duplica a área física do talhão (usa o maior fator de intensidade do talhão na safra).
           - Apenas a partir do 3º ciclo intensivo na mesma safra adiciona +0.25x por ciclo extra.
        4. Fazenda mista (Agricultura + Pecuária / ILP):
           - Suporta até 2,0 cabeças por hectare produtivo inclusas sem acréscimo de área.
           - Cabeças excedentes (confinamento/semi-intensivo) convertem na razão de 2 cabeças = 1 HEq.

        Args:
            parametros: Dicionário com area_total_ha, area_ambiental_ha, vocacao_predominante,
                cabecas_pecuaria e talhoes_culturas (opcional).

        Returns:
            dict: Detalhamento completo de hectares físicos, isentos e equivalentes (HEq).
        """
        area_total = max(Decimal("0.00"), Decimal(str(parametros.get("area_total_ha") or 0)))
        area_ambiental = max(Decimal("0.00"), Decimal(str(parametros.get("area_ambiental_ha") or 0)))
        area_ambiental = min(area_total, area_ambiental)
        area_produtiva_liquida = max(Decimal("0.00"), area_total - area_ambiental)

        vocacao = str(parametros.get("vocacao_predominante") or "GRAOS")
        cabecas = max(0, int(parametros.get("cabecas_pecuaria") or 0))
        talhoes_culturas: list[dict] = list(parametros.get("talhoes_culturas") or [])

        heq_agricola = Decimal("0.00")
        area_coberta_por_talhoes = Decimal("0.00")

        if talhoes_culturas:
            # Agrupar por (talhao_id, safra_id) para aplicar regra justa de Consórcio e Safrinha
            grupos_talhao: dict[tuple[str, str], list[dict]] = {}
            for item in talhoes_culturas:
                tid = str(item.get("talhao_id") or item.get("area_id") or "default")
                sid = str(item.get("safra_id") or "safra_atual")
                grupos_talhao.setdefault((tid, sid), []).append(item)

            areas_fisicas_por_talhao: dict[str, Decimal] = {}
            heq_por_talhao: dict[str, Decimal] = {}

            for (tid, _sid), cultivos in grupos_talhao.items():
                area_talhao = max(
                    Decimal(str(c.get("area_ha") or 0)) for c in cultivos
                )
                fatores = [
                    Decimal(str(obter_fator_intensidade_cultura(c.get("cultura"))))
                    for c in cultivos
                ]
                fator_base_talhao = max(fatores) if fatores else Decimal("1.0")

                # Ciclos não-consorciados além da 2ª safra (ex: 3ª safra irrigada no mesmo ano)
                ciclos_sucessao = sum(1 for c in cultivos if not c.get("consorciado", False))
                adicional_terceira_safra = (
                    Decimal("0.25") * Decimal(str(ciclos_sucessao - 2))
                    if ciclos_sucessao > 2
                    else Decimal("0.00")
                )
                fator_efetivo = fator_base_talhao + adicional_terceira_safra
                heq_safra = area_talhao * fator_efetivo

                areas_fisicas_por_talhao[tid] = max(
                    areas_fisicas_por_talhao.get(tid, Decimal("0.00")), area_talhao
                )
                heq_por_talhao[tid] = max(
                    heq_por_talhao.get(tid, Decimal("0.00")), heq_safra
                )

            area_coberta_por_talhoes = sum(areas_fisicas_por_talhao.values(), Decimal("0.00"))
            heq_agricola = sum(heq_por_talhao.values(), Decimal("0.00"))

        area_restante = max(Decimal("0.00"), area_produtiva_liquida - area_coberta_por_talhoes)
        if area_restante > 0:
            fator_vocacao = Decimal(str(obter_fator_intensidade_cultura(vocacao)))
            heq_agricola += area_restante * fator_vocacao

        base_produtiva_ilp = max(area_produtiva_liquida, area_coberta_por_talhoes)
        cabecas_isentas = int(float(base_produtiva_ilp) * LOTACAO_PADRAO_CABECAS_POR_HA)
        cabecas_excedentes = max(0, cabecas - cabecas_isentas)
        heq_pecuaria_excedente = Decimal(str(cabecas_excedentes)) * Decimal(
            str(FATOR_HEQ_POR_CABECA_EXCEDENTE)
        )

        heq_total = (heq_agricola + heq_pecuaria_excedente).quantize(Decimal("0.01"))
        fator_medio = (
            float((heq_agricola / base_produtiva_ilp).quantize(Decimal("0.01")))
            if base_produtiva_ilp > 0
            else obter_fator_intensidade_cultura(vocacao)
        )

        return {
            "hectares_fisicos_total": float(area_total),
            "hectares_ambientais_isentos": float(area_ambiental),
            "hectares_produtivos_liquidos": float(base_produtiva_ilp),
            "hectares_equivalentes_agricola": float(heq_agricola.quantize(Decimal("0.01"))),
            "cabecas_pecuaria_total": cabecas,
            "cabecas_isentas_ilp": cabecas_isentas,
            "cabecas_excedentes": cabecas_excedentes,
            "hectares_equivalentes_pecuaria_excedente": float(
                heq_pecuaria_excedente.quantize(Decimal("0.01"))
            ),
            "hectares_equivalentes_total": float(heq_total),
            "fator_medio_aplicado": fator_medio,
        }

    async def simular_orcamento_publico(
        self,
        parametros: dict,
    ) -> dict:
        """
        Simula de forma transparente o pacote ideal e o valor exato mensal e anual
        (com 2 meses grátis no pacote base + 20% OFF nas licenças adicionais no plano anual).

        Args:
            parametros: Dicionário contendo area_total_ha, area_ambiental_ha,
                vocacao_predominante, cabecas_pecuaria, quantidade_usuarios,
                dispositivos_campo, plano_id (opcional) e talhoes_culturas (opcional).

        Returns:
            dict: Simulação completa com capacidade equivalente, pacote recomendado,
                orçamento mensal, orçamento anual e economia detalhada.
        """
        capacidade = self.calcular_hectares_equivalentes_operacao(parametros)
        heq_necessarios = Decimal(str(capacidade["hectares_equivalentes_total"]))
        usuarios_solicitados = max(1, int(parametros.get("quantidade_usuarios") or 1))
        dispositivos_campo = max(0, int(parametros.get("dispositivos_campo") or 0))
        plano_id_informado = parametros.get("plano_id")

        stmt = (
            select(PlanoAssinatura)
            .where(PlanoAssinatura.ativo == True)
            .order_by(PlanoAssinatura.preco_mensal.asc())
        )
        result = await self.session.execute(stmt)
        planos = list(result.scalars().all())

        if not planos:
            from scripts.initial_load.seed_plans import PLANOS_INICIAIS
            planos = [PlanoAssinatura(**p) for p in PLANOS_INICIAIS]

        plano_escolhido = None
        if plano_id_informado:
            plano_uuid = UUID(str(plano_id_informado)) if not isinstance(plano_id_informado, UUID) else plano_id_informado
            plano_escolhido = next((p for p in planos if p.id == plano_uuid), None)

        if plano_escolhido is None:
            for candidato in planos:
                atende_area = (
                    candidato.limite_hectares is None
                    or Decimal(str(candidato.limite_hectares)) >= heq_necessarios
                )
                atende_usuarios = (
                    candidato.limite_usuarios_maximo is None
                    or int(candidato.limite_usuarios_maximo) >= usuarios_solicitados
                )
                if atende_area and atende_usuarios:
                    plano_escolhido = candidato
                    break

        if plano_escolhido is None:
            plano_escolhido = planos[-1]

        usuarios_efetivos = max(
            usuarios_solicitados, int(plano_escolhido.limite_usuarios_minimo or 1)
        )
        if (
            plano_escolhido.limite_usuarios_maximo is not None
            and usuarios_efetivos > int(plano_escolhido.limite_usuarios_maximo)
        ):
            usuarios_efetivos = int(plano_escolhido.limite_usuarios_maximo)

        valor_mensal, det_mensal = await self._calcular_preco_instancia_plano(
            plano_escolhido, usuarios_efetivos, "MENSAL"
        )
        valor_anual, det_anual = await self._calcular_preco_instancia_plano(
            plano_escolhido, usuarios_efetivos, "ANUAL"
        )

        base_mensal = Decimal(str(plano_escolhido.preco_mensal or 0))
        base_anual = Decimal(str(plano_escolhido.preco_anual or (base_mensal * 10)))
        adicionais_mensal = valor_mensal - base_mensal
        adicionais_anual = valor_anual - base_anual

        custo_12x_mensal = valor_mensal * Decimal("12")
        economia_pacote_anual = (base_mensal * Decimal("12")) - base_anual
        economia_usuarios_anual = (adicionais_mensal * Decimal("12")) - adicionais_anual
        economia_total_anual = custo_12x_mensal - valor_anual
        percentual_economia = (
            float((economia_total_anual / custo_12x_mensal * Decimal("100")).quantize(Decimal("0.1")))
            if custo_12x_mensal > 0
            else 0.0
        )

        from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

        overrides_catalogo = await carregar_overrides_catalogo_modulos(self.session)
        modulos_liberados = ModuloMetadata.filtrar_modulos_ativos(
            plano_escolhido.modulos_inclusos or ALL_MODULES, overrides_catalogo
        )

        return {
            "capacidade": {
                **capacidade,
                "acessos_web_simultaneos": usuarios_efetivos,
                "dispositivos_campo_isentos": dispositivos_campo,
                "custo_adicional_app_campo": 0.0,
            },
            "plano_recomendado": {
                "id": str(plano_escolhido.id),
                "nome": plano_escolhido.nome,
                "descricao": plano_escolhido.descricao,
                "limite_hectares": float(plano_escolhido.limite_hectares) if plano_escolhido.limite_hectares is not None else None,
                "max_fazendas": plano_escolhido.max_fazendas,
                "usuarios_inclusos": int(plano_escolhido.limite_usuarios_minimo or 1),
                "limite_usuarios_maximo": plano_escolhido.limite_usuarios_maximo,
                "usuarios_adicionais_contratados": max(0, usuarios_efetivos - int(plano_escolhido.limite_usuarios_minimo or 1)),
                "todos_modulos_inclusos": True,
                "total_modulos_liberados": len(modulos_liberados),
            },
            "orcamento_mensal": {
                "ciclo": "MENSAL",
                "valor_pacote_base": float(base_mensal),
                "valor_usuarios_adicionais": float(adicionais_mensal),
                "valor_total_mensal": float(valor_mensal),
                "equivalente_12_meses": float(custo_12x_mensal),
                "detalhamento": det_mensal,
            },
            "orcamento_anual": {
                "ciclo": "ANUAL",
                "valor_pacote_base_anual": float(base_anual),
                "valor_usuarios_adicionais_anual": float(adicionais_anual),
                "valor_total_anual": float(valor_anual),
                "equivalente_mensal": float((valor_anual / Decimal("12")).quantize(Decimal("0.01"))),
                "economia_pacote_anual": float(economia_pacote_anual),
                "economia_usuarios_anual": float(economia_usuarios_anual),
                "economia_total_anual": float(economia_total_anual),
                "percentual_economia_total": percentual_economia,
                "desconto_licencas_adicionais_percentual": 20.0,
                "detalhamento": det_anual,
            },
        }

    async def _calcular_preco_instancia_plano(
        self,
        plano: PlanoAssinatura,
        quantidade_usuarios: int,
        ciclo: str,
    ) -> tuple[Decimal, list[dict]]:
        """
        Calcula o preço composto a partir de uma instância de PlanoAssinatura já carregada.

        Args:
            plano: Objeto PlanoAssinatura.
            quantidade_usuarios: Quantidade total de acessos simultâneos.
            ciclo: MENSAL ou ANUAL.

        Returns:
            tuple[Decimal, list[dict]]: Valor total e detalhamento por faixa.
        """
        preco_base_raw = plano.preco_anual if ciclo == "ANUAL" else plano.preco_mensal
        preco_pacote = Decimal(str(preco_base_raw or 0))
        usuarios_inclusos = max(1, int(plano.limite_usuarios_minimo or 1))
        usuarios_adicionais = max(0, quantidade_usuarios - usuarios_inclusos)

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
            return preco_pacote, detalhamento

        faixas = await self.obter_faixas_plano(plano.id)
        if not faixas:
            faixas = [SimpleNamespace(**f) for f in FAIXAS_PADRAO_POR_PLANO.get(plano.nome, [])]

        valor_total = preco_pacote
        usuarios_restantes = usuarios_adicionais
        for faixa in faixas:
            if usuarios_restantes <= 0:
                break
            usuarios_nesta_faixa = self._calcular_usuarios_na_faixa(
                usuarios_restantes, faixa.faixa_inicio, faixa.faixa_fim, usuarios_adicionais
            )
            if usuarios_nesta_faixa <= 0:
                continue
            preco_unitario = Decimal(
                str(faixa.preco_por_usuario_anual if ciclo == "ANUAL" else faixa.preco_por_usuario_mensal)
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

        return valor_total, detalhamento

    async def calcular_consumo_capacidade_tenant(self, tenant_id: UUID) -> dict:
        """
        Apura em tempo real o consumo de capacidade do tenant:
        - Área física total das propriedades ativas
        - Área ambiental isenta (APP e Reserva Legal)
        - Hectares Equivalentes (HEq) considerando cultivos/safras/consórcio e rebanho ativo
        - Dispositivos ativos no aplicativo Campo (isentos de acesso simultâneo)

        Args:
            tenant_id: UUID do tenant.

        Returns:
            dict: Métricas consolidadas de capacidade e isenções do tenant.
        """
        from core.cadastros.propriedades.models import AreaRural, TIPOS_AREA_AMBIENTAL
        from core.models.unidade_produtiva import UnidadeProdutiva
        from agricola.cultivos.models import Cultivo, CultivoArea
        from pecuaria.animal.models import Animal
        from campo.models import DispositivoCampo

        area_expr = func.coalesce(
            UnidadeProdutiva.area_total_calculada_ha,
            UnidadeProdutiva.area_total_ha,
            0,
        )
        res_up = await self.session.execute(
            select(func.coalesce(func.sum(area_expr), 0)).where(
                UnidadeProdutiva.tenant_id == tenant_id,
                UnidadeProdutiva.ativo == True,
            )
        )
        area_fisica_total = Decimal(str(res_up.scalar_one() or 0))

        tipos_ambientais = [t.value if hasattr(t, "value") else str(t) for t in TIPOS_AREA_AMBIENTAL]
        res_amb = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(func.coalesce(AreaRural.area_hectares_manual, AreaRural.area_hectares, 0)),
                    0,
                )
            ).where(
                AreaRural.tenant_id == tenant_id,
                AreaRural.ativo == True,
                AreaRural.tipo.in_(tipos_ambientais),
            )
        )
        area_ambiental_isenta = Decimal(str(res_amb.scalar_one() or 0))

        stmt_cultivos = (
            select(
                CultivoArea.area_id,
                Cultivo.safra_id,
                CultivoArea.area_ha,
                Cultivo.cultura,
                Cultivo.consorciado,
            )
            .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
            .where(
                CultivoArea.tenant_id == tenant_id,
                Cultivo.status.notin_(["CANCELADO", "ENCERRADO"]),
            )
        )
        res_cultivos = await self.session.execute(stmt_cultivos)
        talhoes_culturas = [
            {
                "talhao_id": str(row[0]),
                "safra_id": str(row[1]),
                "area_ha": float(row[2] or 0),
                "cultura": str(row[3] or "GRAOS"),
                "consorciado": bool(row[4]),
            }
            for row in res_cultivos.all()
        ]

        res_animais = await self.session.execute(
            select(func.count(Animal.id)).where(
                Animal.tenant_id == tenant_id,
                Animal.status == "ATIVO",
            )
        )
        cabecas_ativas = int(res_animais.scalar_one() or 0)

        res_campo = await self.session.execute(
            select(func.count(DispositivoCampo.id)).where(
                DispositivoCampo.tenant_id == tenant_id,
                DispositivoCampo.status == "ATIVO",
            )
        )
        dispositivos_campo_ativos = int(res_campo.scalar_one() or 0)

        capacidade = self.calcular_hectares_equivalentes_operacao(
            {
                "area_total_ha": area_fisica_total,
                "area_ambiental_ha": area_ambiental_isenta,
                "vocacao_predominante": "GRAOS",
                "cabecas_pecuaria": cabecas_ativas,
                "talhoes_culturas": talhoes_culturas,
            }
        )
        capacidade["dispositivos_campo_ativos_isentos"] = dispositivos_campo_ativos
        return capacidade
