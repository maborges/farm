from uuid import UUID
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text
from loguru import logger
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.base_service import BaseService

from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao, InsumoOperacao
from agricola.operacoes.schemas import (
    OperacaoAgricolaCreate,
    OperacaoAgricolaUpdate,
    OperacaoPorFaseKPI,
    OperacaoTipoFaseCreate,
    OperacaoTipoFaseUpdate,
    SafraOperacoesPorFaseResponse,
)
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import SAFRA_FASES_ORDEM
from core.cadastros.propriedades.models import AreaRural
from agricola.safras.models import Safra
from agricola.models import OperacaoTipoFase
from core.cadastros.produtos.models import Produto
from core.cadastros.equipamentos.models import Equipamento
from operacional.services import EstoqueService
from operacional.services.estoque_fifo import consumir_lotes_fifo, atualizar_saldo_apos_consumo
from operacional.services.estoque_ledger import registrar_ledger_estoque
from agricola.custos.allocation_service import registrar_cost_allocation
from financeiro.models.despesa import Despesa
from agricola.caderno.models import CadernoCampoEntrada
from core.operational_context import (
    validate_area_in_tenant,
    validate_cultivo_context,
    validate_deposito_context,
    validate_pessoa_tenant,
    validate_production_unit_context,
    validate_safra_area_link,
    validate_safra_in_tenant,
)

DEFAULT_TIPO_FASES: dict[str, list[str]] = {
    "PLANTIO": ["PLANTIO", "DESENVOLVIMENTO"],
    "ADUBAÇÃO": ["PREPARO_SOLO", "DESENVOLVIMENTO"],
    "PULVERIZAÇÃO": ["PLANEJADA", "DESENVOLVIMENTO", "COLHEITA"],
    "COLHEITA": ["COLHEITA"],
    "OPERAÇÃO_MECANIZADA": ["PLANTIO", "DESENVOLVIMENTO"],
    "PREPARO_SOLO": ["PREPARO_SOLO"],
    "CALAGEM": ["PREPARO_SOLO"],
    "IRRIGAÇÃO": ["DESENVOLVIMENTO", "COLHEITA"],
    "OUTROS": ["PLANEJADA", "PREPARO_SOLO", "PLANTIO", "DESENVOLVIMENTO", "COLHEITA", "POS_COLHEITA"],
}

DEFAULT_TIPO_DESCRICOES: dict[str, str] = {
    "PLANTIO": "Semeadura e plantio",
    "ADUBAÇÃO": "Adubação de base ou cobertura",
    "PULVERIZAÇÃO": "Aplicação de defensivos ou bioinsumos",
    "COLHEITA": "Colheita manual ou mecanizada",
    "OPERAÇÃO_MECANIZADA": "Operações gerais com máquinas e implementos",
    "PREPARO_SOLO": "Aração, gradagem, subsolagem e preparo de área",
    "CALAGEM": "Aplicação de calcário",
    "IRRIGAÇÃO": "Operações de irrigação",
    "OUTROS": "Outras operações de campo",
}


class OperacaoTipoFaseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_defaults(self) -> None:
        existentes = {
            item.tipo_operacao: item
            for item in (
                await self.session.execute(select(OperacaoTipoFase))
            ).scalars().all()
        }

        for tipo_operacao, fases_permitidas in DEFAULT_TIPO_FASES.items():
            item = existentes.get(tipo_operacao)
            if item is None:
                self.session.add(
                    OperacaoTipoFase(
                        id=uuid.uuid4(),
                        tipo_operacao=tipo_operacao,
                        fases_permitidas=fases_permitidas,
                        descricao=DEFAULT_TIPO_DESCRICOES.get(tipo_operacao),
                    )
                )
                continue

            if not item.fases_permitidas:
                item.fases_permitidas = fases_permitidas
            if not item.descricao:
                item.descricao = DEFAULT_TIPO_DESCRICOES.get(tipo_operacao)
            self.session.add(item)
        await self.session.flush()

    async def listar(self) -> list[OperacaoTipoFase]:
        await self.ensure_defaults()
        stmt = select(OperacaoTipoFase).order_by(OperacaoTipoFase.tipo_operacao)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, dados: OperacaoTipoFaseCreate) -> OperacaoTipoFase:
        await self.ensure_defaults()
        tipo_operacao = dados.tipo_operacao.strip().upper()
        existente = (
            await self.session.execute(
                select(OperacaoTipoFase).where(OperacaoTipoFase.tipo_operacao == tipo_operacao)
            )
        ).scalar_one_or_none()
        if existente:
            raise BusinessRuleError(f"Tipo de operação '{tipo_operacao}' já está cadastrado.")

        obj = OperacaoTipoFase(
            id=uuid.uuid4(),
            tipo_operacao=tipo_operacao,
            fases_permitidas=[fase.upper() for fase in dados.fases_permitidas],
            descricao=dados.descricao,
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def atualizar(self, tipo_id: UUID, dados: OperacaoTipoFaseUpdate) -> OperacaoTipoFase:
        obj = await self.get_or_fail(tipo_id)
        tipo_anterior = obj.tipo_operacao
        if dados.tipo_operacao is not None:
            novo_tipo = dados.tipo_operacao.strip().upper()
            existente = (
                await self.session.execute(
                    select(OperacaoTipoFase).where(
                        OperacaoTipoFase.tipo_operacao == novo_tipo,
                        OperacaoTipoFase.id != tipo_id,
                    )
                )
            ).scalar_one_or_none()
            if existente:
                raise BusinessRuleError(f"Tipo de operação '{novo_tipo}' já está cadastrado.")
            obj.tipo_operacao = novo_tipo
            if novo_tipo != tipo_anterior:
                operacoes = (
                    await self.session.execute(
                        select(OperacaoAgricola).where(OperacaoAgricola.tipo == tipo_anterior)
                    )
                ).scalars().all()
                for operacao in operacoes:
                    operacao.tipo = novo_tipo
                    self.session.add(operacao)

        if dados.fases_permitidas is not None:
            obj.fases_permitidas = [fase.upper() for fase in dados.fases_permitidas]

        if "descricao" in dados.model_dump(exclude_unset=True):
            obj.descricao = dados.descricao

        self.session.add(obj)
        await self.session.flush()
        return obj

    async def excluir(self, tipo_id: UUID) -> None:
        obj = await self.get_or_fail(tipo_id)
        uso = (
            await self.session.execute(
                select(func.count()).select_from(OperacaoAgricola).where(OperacaoAgricola.tipo == obj.tipo_operacao)
            )
        ).scalar_one()
        if uso:
            raise BusinessRuleError(
                f"Tipo de operação '{obj.tipo_operacao}' não pode ser excluído porque já possui operações vinculadas."
            )
        await self.session.delete(obj)
        await self.session.flush()

    async def get_or_fail(self, tipo_id: UUID) -> OperacaoTipoFase:
        obj = (
            await self.session.execute(
                select(OperacaoTipoFase).where(OperacaoTipoFase.id == tipo_id)
            )
        ).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Tipo de operação", str(tipo_id))
        return obj

class OperacaoService(BaseService[OperacaoAgricola]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(OperacaoAgricola, session, tenant_id)
        self.estoque_svc = EstoqueService(session, tenant_id)

    async def _get_area_unit_id(self) -> UUID | None:
        """Resolve the canonical hectare unit when available.

        Some local/dev databases may not have the global HA seed loaded yet.
        Operation creation should still succeed in that case, even if we skip the
        derived execution record.
        """
        unidade_ha_stmt = text("""
            SELECT id
              FROM unidades_medida
             WHERE ativo = true
               AND codigo = 'HA'
               AND (tenant_id IS NULL OR tenant_id = :tenant_id)
             ORDER BY CASE WHEN tenant_id IS NULL THEN 0 ELSE 1 END
             LIMIT 1
        """)
        unidade_ha_id = (
            await self.session.execute(unidade_ha_stmt, {"tenant_id": self.tenant_id})
        ).scalar_one_or_none()
        if unidade_ha_id is None:
            logger.warning(
                "Skipping operacao_execucao creation because HA unit is missing",
                tenant_id=str(self.tenant_id),
            )
        return unidade_ha_id

    async def _resolve_production_unit_id(self, dados: OperacaoAgricolaCreate) -> UUID | None:
        """Resolve a valid production unit for the current safra/talhao.

        Legacy `AreaRural.unidade_produtiva_id` points to `unidades_produtivas`,
        which is not compatible with the FK expected by `operacoes_agricolas`.
        """
        if dados.production_unit_id:
            cultivo_id = getattr(dados, "cultivo_id", None)
            pu = await validate_production_unit_context(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=dados.production_unit_id,
                safra_id=dados.safra_id,
                area_id=dados.talhao_id,
                cultivo_id=cultivo_id,
            )
            return pu.id

        stmt = (
            select(ProductionUnit.id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == dados.safra_id,
                ProductionUnit.area_id == dados.talhao_id,
            )
            .order_by(
                (ProductionUnit.status == "ATIVA").desc(),
                ProductionUnit.created_at.desc(),
            )
        )
        production_unit_id = (await self.session.execute(stmt)).scalars().first()
        if production_unit_id is None:
            logger.warning(
                "No production_unit found for operacao; persisting with NULL",
                safra_id=str(dados.safra_id),
                talhao_id=str(dados.talhao_id),
                tenant_id=str(self.tenant_id),
            )
        return production_unit_id

    async def criar(self, dados: OperacaoAgricolaCreate) -> OperacaoAgricola:
        await OperacaoTipoFaseService(self.session).ensure_defaults()
        # 1. Valida tenant e contexto operacional das entidades base.
        talhao = await validate_area_in_tenant(
            self.session,
            tenant_id=self.tenant_id,
            area_id=dados.talhao_id,
        )
        unidade_produtiva_id = talhao.unidade_produtiva_id

        # 2. Auto-preenche fase_safra com fase atual da safra (override permitido)
        safra_atual = await validate_safra_in_tenant(
            self.session,
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
        )
        cultivo_id = getattr(dados, "cultivo_id", None)
        if cultivo_id:
            await validate_cultivo_context(
                self.session,
                tenant_id=self.tenant_id,
                cultivo_id=cultivo_id,
                safra_id=dados.safra_id,
            )
        await validate_safra_area_link(
            self.session,
            tenant_id=self.tenant_id,
            safra_id=dados.safra_id,
            area_id=dados.talhao_id,
            cultivo_id=cultivo_id,
        )
        if dados.operador_id:
            await validate_pessoa_tenant(self.session, tenant_id=self.tenant_id, pessoa_id=dados.operador_id)
        if dados.maquina_id:
            equipamento = (
                await self.session.execute(
                    select(Equipamento).where(Equipamento.id == dados.maquina_id, Equipamento.tenant_id == self.tenant_id)
                )
            ).scalars().first()
            if not equipamento:
                logger.warning(
                    "multi_up_tenant_mismatch",
                    resource="equipamento",
                    tenant_id=str(self.tenant_id),
                    equipamento_id=str(dados.maquina_id),
                )
                raise BusinessRuleError("Equipamento não localizado ou inacessível para o tenant.")
            if equipamento.unidade_produtiva_id and equipamento.unidade_produtiva_id != unidade_produtiva_id:
                logger.warning(
                    "multi_up_equipment_operating_outside_home_unit",
                    tenant_id=str(self.tenant_id),
                    equipamento_id=str(equipamento.id),
                    equipamento_unidade_produtiva_id=str(equipamento.unidade_produtiva_id),
                    operacao_unidade_produtiva_id=str(unidade_produtiva_id),
                )
        fase_safra = dados.fase_safra or safra_atual.status

        # 2.5. VALIDAÇÃO: Operação só permitida em fases específicas
        # Busca lookup table para tipo de operação
        tipo_fase_stmt = select(OperacaoTipoFase).where(
            OperacaoTipoFase.tipo_operacao == dados.tipo
        )
        tipo_fase = (await self.session.execute(tipo_fase_stmt)).scalars().first()
        if not tipo_fase:
            fases_padrao = DEFAULT_TIPO_FASES.get(dados.tipo)
            if not fases_padrao:
                logger.warning(f"Tipo de operação '{dados.tipo}' não cadastrado em lookup table")
                raise BusinessRuleError(
                    f"Tipo de operação '{dados.tipo}' não está cadastrado no sistema. "
                    f"Tipos permitidos: {', '.join(DEFAULT_TIPO_FASES.keys())}."
                )
            logger.warning(
                "Tipo de operação ausente na lookup table; usando fallback padrão",
                tipo_operacao=dados.tipo,
                tenant_id=str(self.tenant_id),
            )
            fases_permitidas = fases_padrao
        else:
            fases_permitidas = tipo_fase.fases_permitidas

        # Validar se fase atual está permitida para este tipo
        if fase_safra not in fases_permitidas:
            raise BusinessRuleError(
                f"Operação '{dados.tipo}' não é permitida na fase '{fase_safra}'. "
                f"Fases permitidas: {', '.join(fases_permitidas)}"
            )

        # 2.6. VALIDAÇÃO: Data não pode ser futura
        if dados.data_realizada > date.today():
            raise BusinessRuleError(
                f"Data da operação não pode ser futura. "
                f"Informe a data em que a operação foi realmente realizada."
            )

        # 3. Extrai insumos
        insumos_data = dados.insumos
        dados_dict = dados.model_dump(exclude={"insumos"})
        dados_dict["fase_safra"] = fase_safra
        dados_dict["production_unit_id"] = await self._resolve_production_unit_id(dados)

        custo_manual_informado = float(dados.custo_total or 0.0)
        custo_total_operacao = custo_manual_informado

        # Create operacao in memory (NOT flushed yet)
        operacao = OperacaoAgricola(
            tenant_id=self.tenant_id,
            **dados_dict
        )
        self.session.add(operacao)
        await self.session.flush()

        # 3. Processa insumos e baixa estoque (FIFO). Se falhar, a transação inteira é revertida.
        ledger_consumos = []
        try:
            for insumo in insumos_data:
                quantidade_total = insumo.dose_por_ha * (insumo.area_aplicada or dados.area_aplicada_ha or 1.0)

                # Busca produto
                produto = await self.session.get(Produto, insumo.produto_id)
                if not produto or (produto.tenant_id is not None and produto.tenant_id != self.tenant_id):
                    logger.warning(
                        "multi_up_tenant_mismatch",
                        resource="produto",
                        tenant_id=str(self.tenant_id),
                        produto_id=str(insumo.produto_id),
                    )
                    raise EntityNotFoundError("Produto/Insumo", insumo.produto_id)

                # FIFO: Consume oldest batches first
                try:
                    consumo = await consumir_lotes_fifo(
                        session=self.session,
                        produto_id=insumo.produto_id,
                        quantidade_necessaria=quantidade_total,
                        tenant_id=self.tenant_id,
                    )
                except BusinessRuleError as e:
                    logger.warning(f"FIFO consumption failed for {insumo.produto_id}: {e}")
                    raise

                # Custo real vem do FIFO (lotes históricos), não do preço médio
                custo_item = consumo.custo_total

                for lote_consumido in consumo.lotes_consumidos:
                    await validate_deposito_context(
                        self.session,
                        tenant_id=self.tenant_id,
                        deposito_id=lote_consumido["deposito_id"],
                        expected_unidade_produtiva_id=unidade_produtiva_id,
                    )
                    ledger_consumos.append({
                        "produto_id": insumo.produto_id,
                        "deposito_id": lote_consumido["deposito_id"],
                        "lote_id": lote_consumido["lote_id"],
                        "quantidade": lote_consumido["quantidade"],
                        "custo_unitario": lote_consumido["custo_unitario"],
                        "custo_total": lote_consumido["custo"],
                        "observacoes": f"Aplicação em operação agrícola ({operacao.tipo})",
                    })
                    logger.info(
                        f"Batch consumed via FIFO: {lote_consumido['numero_lote']} × {lote_consumido['quantidade']}",
                        lote_id=str(lote_consumido["lote_id"]),
                        deposito_id=str(lote_consumido["deposito_id"]),
                        quantidade=lote_consumido["quantidade"],
                        custo=lote_consumido["custo"],
                    )

                # Record InsumoOperacao with actual FIFO cost
                # custo_unitario = weighted average of all consumed batches
                insumo_op = InsumoOperacao(
                    id=uuid.uuid4(),
                    operacao_id=operacao.id,
                    tenant_id=self.tenant_id,
                    produto_id=insumo.produto_id,
                    lote_insumo=insumo.lote_insumo,
                    dose_por_ha=insumo.dose_por_ha,
                    unidade=insumo.unidade,
                    area_aplicada=insumo.area_aplicada,
                    quantidade_total=quantidade_total,
                    custo_unitario=consumo.custo_total / quantidade_total if quantidade_total > 0 else 0.0,  # Weighted avg
                    custo_total=custo_item,
                )

                self.session.add(insumo_op)
                custo_total_operacao += custo_item

                # Update SaldoEstoque after FIFO consumption (required for UI accuracy)
                await atualizar_saldo_apos_consumo(
                    session=self.session,
                    produto_id=insumo.produto_id,
                    quantidade_total=quantidade_total,
                )

            # All insumos processed successfully - finalize operacao.
            # Manual-only launches (common in "Execução por Fase") do not send
            # insumos, so we preserve the informed total instead of forcing zero.
            operacao.custo_total = custo_total_operacao
            if operacao.area_aplicada_ha and operacao.area_aplicada_ha > 0:
                operacao.custo_por_ha = custo_total_operacao / operacao.area_aplicada_ha

            operacao_execucao = None
            if operacao.status == "REALIZADA":
                unidade_ha_id = await self._get_area_unit_id()
                if unidade_ha_id is not None:
                    operacao_execucao = OperacaoExecucao(
                        tenant_id=self.tenant_id,
                        operacao_id=operacao.id,
                        production_unit_id=operacao.production_unit_id,
                        data_execucao=operacao.data_realizada,
                        hora_execucao=operacao.hora_inicio,
                        quantidade_planejada=operacao.area_aplicada_ha,
                        quantidade_executada=operacao.area_aplicada_ha or 1,
                        quantidade_devolvida=0,
                        unidade_medida_id=unidade_ha_id,
                        custo_real=custo_total_operacao,
                        area_ha_executada=operacao.area_aplicada_ha,
                        status="REALIZADA",
                        operador_id=operacao.operador_id,
                        observacoes=operacao.observacoes,
                    )
                    self.session.add(operacao_execucao)
                    await self.session.flush()

                    for consumo_ledger in ledger_consumos:
                        await registrar_ledger_estoque(
                            self.session,
                            tenant_id=self.tenant_id,
                            tipo_movimento="SAIDA",
                            origem="OPERACAO_EXECUCAO",
                            origem_id=operacao_execucao.id,
                            operacao_execucao_id=operacao_execucao.id,
                            production_unit_id=operacao.production_unit_id,
                            **consumo_ledger,
                        )

                    if custo_total_operacao and operacao.production_unit_id:
                        await registrar_cost_allocation(
                            self.session,
                            tenant_id=self.tenant_id,
                            production_unit_id=operacao.production_unit_id,
                            source="OPERATION_EXECUTION",
                            source_id=operacao_execucao.id,
                            operation_execution_id=operacao_execucao.id,
                            cost_category="OUTROS",
                            amount=custo_total_operacao,
                            allocation_date=operacao_execucao.data_execucao,
                            allocation_method="DIRECT",
                            allocation_basis=operacao_execucao.area_ha_executada,
                        )

            # 4. Sincroniza custo na Safra
            safra = await self.session.get(Safra, operacao.safra_id)
            if safra:
                # Re-calcula custo realizado por ha baseado em todas as operações (simplificado para fins de refino)
                stmt_sum = select(func.sum(OperacaoAgricola.custo_total)).where(OperacaoAgricola.safra_id == safra.id)
                total_acumulado = (await self.session.execute(stmt_sum)).scalar() or 0.0
                area_plantada_ha = getattr(safra, "area_plantada_ha", None)
                if (
                    area_plantada_ha
                    and area_plantada_ha > 0
                    and hasattr(safra, "custo_realizado_ha")
                ):
                    safra.custo_realizado_ha = (
                        (float(total_acumulado) + custo_total_operacao)
                        / float(area_plantada_ha)
                    )

            # 5. Registra Despesa no Financeiro (Módulo Integrado)
            if custo_total_operacao > 0:
                from financeiro.models.plano_conta import PlanoConta
                # Tenta conta analítica de custeio; fallback para qualquer conta de custeio ativa
                stmt_pc = (
                    select(PlanoConta.id)
                    .where(
                        PlanoConta.tenant_id == self.tenant_id,
                        PlanoConta.categoria_rfb == "CUSTEIO",
                        PlanoConta.ativo == True,
                    )
                    .order_by(PlanoConta.natureza)  # ANALITICA < SINTETICA alfabeticamente
                    .limit(1)
                )
                plano_id = (await self.session.execute(stmt_pc)).scalar()

                if plano_id:
                    safra_desc = f"{safra_atual.cultura} {safra_atual.ano_safra}" if safra_atual else str(dados.safra_id)[:8]
                    descricao = f"{operacao.tipo} — {safra_desc} (fase {fase_safra})"
                    despesa = Despesa(
                        id=uuid.uuid4(),
                        tenant_id=self.tenant_id,
                        unidade_produtiva_id=unidade_produtiva_id,
                        plano_conta_id=plano_id,
                        descricao=descricao[:255],
                        valor_total=float(custo_total_operacao),
                        data_emissao=operacao.data_realizada,
                        data_vencimento=operacao.data_realizada,
                        data_pagamento=operacao.data_realizada,
                        status="PAGO",
                        origem_id=operacao.id,
                        origem_tipo="OPERACAO_AGRICOLA",
                    )
                    self.session.add(despesa)

            # Commit only if ALL operations succeeded (atomicity)
            # 6. TRIGGER: Se operação foi criada com status REALIZADA, cria entrada no caderno
            if operacao.status == "REALIZADA":
                SYSTEM_USER = UUID("00000000-0000-0000-0000-000000000000")
                descricao = operacao.tipo
                if operacao.area_aplicada_ha:
                    descricao += f"\nÁrea: {operacao.area_aplicada_ha} ha"
                if operacao.custo_total:
                    descricao += f"\nCusto: R$ {operacao.custo_total:.2f}"

                from agricola.caderno.models import CadernoCampoEntrada
                entrada = CadernoCampoEntrada(
                    tenant_id=self.tenant_id,
                    safra_id=operacao.safra_id,
                    talhao_id=operacao.talhao_id,
                    tipo="OPERACAO_AUTO",
                    descricao=descricao,
                    data_registro=operacao.data_realizada,
                    usuario_id=SYSTEM_USER,
                    operacao_id=operacao.id,
                )
                self.session.add(entrada)
                logger.info(
                    f"Entrada automática no caderno (criação): {operacao.tipo} → safra {operacao.safra_id}",
                    entrada_id=str(entrada.id),
                )

            # 7. Conclui a tarefa vinculada automaticamente
            if dados.tarefa_id:
                from agricola.tarefas.models import SafraTarefa
                tarefa = await self.session.get(SafraTarefa, dados.tarefa_id)
                if tarefa and tarefa.tenant_id == self.tenant_id:
                    tarefa.status = "CONCLUIDA"
                    tarefa.operacao_id = operacao.id
                    tarefa.concluida_em = datetime.now(timezone.utc)

            await self.session.commit()

        except BusinessRuleError as e:
            # FIFO failed - rollback entire transaction (operacao never persisted)
            await self.session.rollback()
            logger.error(
                f"Operation creation rolled back due to FIFO failure",
                operacao_tipo=operacao.tipo,
                safra_id=str(operacao.safra_id),
                error=str(e),
            )
            raise

        await self.session.refresh(operacao)

        return operacao

    async def buscar_condicoes_clima(self, lat: float, lng: float, data_op: date) -> dict:
        return {
            "temperatura_c": 25.0,
            "umidade_rel": 60.0,
            "vento_kmh": 10.0,
            "condicao_clima": "sol"
        }

    async def atualizar(self, obj_id: UUID, dados: OperacaoAgricolaUpdate) -> OperacaoAgricola:
        # 1. Busca estado atual antes de atualizar
        operacao_atual = await self.get_or_fail(obj_id)
        status_anterior = operacao_atual.status

        # 2. Aplica atualização
        dados_dict = dados.model_dump(exclude_unset=True)
        if "custo_total" in dados_dict and dados_dict["custo_total"] is not None:
            dados_dict["custo_total"] = float(dados_dict["custo_total"])
        operacao = await super().update(obj_id, dados_dict)

        if "custo_total" in dados_dict or "area_aplicada_ha" in dados_dict:
            custo_total = float(operacao.custo_total or 0.0)
            area_aplicada = float(operacao.area_aplicada_ha or 0.0)
            operacao.custo_por_ha = (custo_total / area_aplicada) if area_aplicada > 0 else 0.0
            self.session.add(operacao)
            await self.session.flush()

        # 3. TRIGGER: Se status mudou para REALIZADA, cria entrada no caderno de campo
        novo_status = dados_dict.get("status")
        if novo_status == "REALIZADA" and status_anterior != "REALIZADA":
            descricao = operacao.tipo
            if operacao.area_aplicada_ha:
                descricao += f"\nÁrea: {operacao.area_aplicada_ha} ha"
            if operacao.custo_total:
                descricao += f"\nCusto: R$ {operacao.custo_total:.2f}"

            # UUID "zero" para indicar origem automática do sistema
            SYSTEM_USER = UUID("00000000-0000-0000-0000-000000000000")

            entrada = CadernoCampoEntrada(
                tenant_id=self.tenant_id,
                safra_id=operacao.safra_id,
                talhao_id=operacao.talhao_id,
                tipo="OPERACAO_AUTO",
                descricao=descricao,
                data_registro=operacao.data_realizada,
                usuario_id=SYSTEM_USER,
                operacao_id=operacao.id,
            )
            self.session.add(entrada)
            logger.info(
                f"Entrada automática no caderno: {operacao.tipo} → safra {operacao.safra_id}",
                entrada_id=str(entrada.id),
            )

        return operacao

    async def listar_por_safra_e_fase(
        self, safra_id: UUID, fase: str | None = None
    ) -> list[OperacaoAgricola]:
        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.tenant_id == self.tenant_id,
        ).order_by(OperacaoAgricola.data_realizada.desc())
        if fase:
            stmt = stmt.where(OperacaoAgricola.fase_safra == fase)
        return list((await self.session.execute(stmt)).scalars().all())

    async def resumo_por_fase(self, safra_id: UUID) -> SafraOperacoesPorFaseResponse:
        stmt = select(
            OperacaoAgricola.fase_safra,
            func.count(OperacaoAgricola.id).label("total"),
            func.coalesce(func.sum(OperacaoAgricola.custo_total), 0).label("custo_total"),
            func.coalesce(func.sum(OperacaoAgricola.area_aplicada_ha), 0).label("area_total"),
        ).where(
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.tenant_id == self.tenant_id,
        ).group_by(OperacaoAgricola.fase_safra)

        rows = (await self.session.execute(stmt)).all()
        por_fase: dict[str, OperacaoPorFaseKPI] = {}
        for row in rows:
            fase = row.fase_safra or "SEM_FASE"
            area = float(row.area_total or 0)
            custo = float(row.custo_total or 0)
            por_fase[fase] = OperacaoPorFaseKPI(
                fase=fase,
                total_operacoes=row.total,
                custo_total=custo,
                custo_por_ha=round(custo / area, 2) if area > 0 else 0.0,
                area_total_ha=area,
            )

        # Ordena pelas fases do ciclo
        fases_ordenadas = [
            por_fase[f] for f in SAFRA_FASES_ORDEM if f in por_fase
        ]
        # Fases fora do ciclo padrão (SEM_FASE, etc.)
        extras = [v for k, v in por_fase.items() if k not in SAFRA_FASES_ORDEM]
        fases_ordenadas.extend(extras)

        custo_total = sum(f.custo_total for f in fases_ordenadas)
        return SafraOperacoesPorFaseResponse(
            safra_id=safra_id,
            fases=fases_ordenadas,
            custo_total_safra=custo_total,
        )

    async def gerar_receituario_agronomico(self, operacao_id: UUID) -> bytes:
        return b"%PDF-1.4\n..."
