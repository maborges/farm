from uuid import UUID
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text, delete, or_
from loguru import logger
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.base_service import BaseService

from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao, InsumoOperacao
from agricola.operacoes.schemas import (
    InsumoOperacaoCreate,
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
from agricola.caderno.service import CadernoCampoService, ORIGEM_EVENTO_OPERACAO
from operacional.services import EstoqueService
from operacional.services.estoque_fifo import consumir_lotes_fifo, atualizar_saldo_apos_consumo
from operacional.services.estoque_ledger import registrar_ledger_estoque
from operacional.models.estoque import EstoqueMovimento, LoteEstoque
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.alertas.service import AlertasAgricolasService, WorkflowGovernanceEvent
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

    async def _get_unidade_produtiva_id_for_talhao(self, talhao_id: UUID) -> UUID:
        area = await self.session.get(AreaRural, talhao_id)
        if not area or area.tenant_id != self.tenant_id:
            raise BusinessRuleError("Talhão não localizado ou inacessível para o tenant.")
        return area.unidade_produtiva_id

    async def _validar_area_aplicada(self, talhao_id: UUID, area_aplicada_ha: float | None) -> float:
        if area_aplicada_ha is None:
            raise BusinessRuleError("Área aplicada é obrigatória.")

        area_aplicada = float(area_aplicada_ha)
        if area_aplicada <= 0:
            raise BusinessRuleError("Área aplicada deve ser maior que zero.")

        area = await self.session.get(AreaRural, talhao_id)
        if not area or area.tenant_id != self.tenant_id:
            raise BusinessRuleError("Talhão não localizado ou inacessível para o tenant.")

        area_talhao = area.area_hectares if area.area_hectares is not None else area.area_hectares_manual
        if area_talhao is None:
            raise BusinessRuleError("Talhão não possui área calculada ou informada cadastrada.")

        area_talhao_float = float(area_talhao)
        if area_aplicada > area_talhao_float:
            raise BusinessRuleError(
                f"Área aplicada ({area_aplicada:.4f} ha) não pode ser maior que a área do talhão "
                f"({area_talhao_float:.4f} ha)."
            )

        return area_aplicada

    MENSAGEM_PRODUCTION_UNIT_AUSENTE = (
        "Não é possível concluir a operação com custo sem uma unidade produtiva "
        "econômica válida. Cadastre ou vincule a ProductionUnit da safra e do talhão."
    )
    MENSAGEM_PRODUCTION_UNIT_AMBIGUA = (
        "Existem múltiplas ProductionUnit válidas para esta safra/talhão/cultivo. "
        "Informe explicitamente a production_unit_id para evitar ambiguidade."
    )

    async def _resolve_production_unit_id(self, dados: OperacaoAgricolaCreate) -> UUID | None:
        """Resolve deterministicamente a ProductionUnit para a safra/talhão/cultivo atual.

        Legacy `AreaRural.unidade_produtiva_id` points to `unidades_produtivas`,
        which is not compatible with the FK expected by `operacoes_agricolas`.

        Caso A (production_unit_id informado): validação estrita via
        `validate_production_unit_context` (tenant/safra/área/cultivo) — sem fallback.

        Caso B (ausente): busca por chave de domínio. Prioridade: 1) correspondência
        exata (inclui cultivo, quando informado); 2) unidade ATIVA; 3) apenas uma
        candidata válida. Duas ou mais candidatas igualmente válidas => ambiguidade.

        Bloqueio: quando a operação será persistida como REALIZADA com custo>0 e
        nenhuma candidata (ou mais de uma candidata ambígua) for encontrada, lança
        `BusinessRuleError` — não persiste com NULL nesse cenário.
        """
        cultivo_id = getattr(dados, "cultivo_id", None)
        status_final = getattr(dados, "status", None)
        custo = float(getattr(dados, "custo_total", None) or 0.0)
        exige_bloqueio = status_final == "REALIZADA" and custo > 0

        if dados.production_unit_id:
            pu = await validate_production_unit_context(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=dados.production_unit_id,
                safra_id=dados.safra_id,
                area_id=dados.talhao_id,
                cultivo_id=cultivo_id,
            )
            return pu.id

        stmt = select(ProductionUnit.id, ProductionUnit.status).where(
            ProductionUnit.tenant_id == self.tenant_id,
            ProductionUnit.safra_id == dados.safra_id,
            ProductionUnit.area_id == dados.talhao_id,
        )
        if cultivo_id:
            stmt = stmt.where(ProductionUnit.cultivo_id == cultivo_id)
        candidatos = (await self.session.execute(stmt)).all()

        if not candidatos:
            if exige_bloqueio:
                raise BusinessRuleError(self.MENSAGEM_PRODUCTION_UNIT_AUSENTE)
            logger.warning(
                "No production_unit found for operacao; persisting with NULL",
                safra_id=str(dados.safra_id),
                talhao_id=str(dados.talhao_id),
                tenant_id=str(self.tenant_id),
            )
            return None

        if len(candidatos) == 1:
            return candidatos[0].id

        ativas = [c for c in candidatos if c.status == "ATIVA"]
        if len(ativas) == 1:
            return ativas[0].id

        # Ambiguidade real: mais de uma candidata igualmente válida (não decidir por
        # first()/created_at — regra explícita do programa 04K).
        if exige_bloqueio:
            raise BusinessRuleError(self.MENSAGEM_PRODUCTION_UNIT_AMBIGUA)
        logger.warning(
            "Ambiguous production_unit candidates for operacao; persisting with NULL",
            safra_id=str(dados.safra_id),
            talhao_id=str(dados.talhao_id),
            tenant_id=str(self.tenant_id),
            candidatos=len(candidatos),
        )
        return None

    async def _buscar_execucao_existente(self, operacao_id: UUID) -> OperacaoExecucao | None:
        stmt = (
            select(OperacaoExecucao)
            .where(
                OperacaoExecucao.operacao_id == operacao_id,
                OperacaoExecucao.tenant_id == self.tenant_id,
            )
            .order_by(OperacaoExecucao.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _buscar_execucoes_da_operacao(self, operacao_id: UUID) -> list[OperacaoExecucao]:
        stmt = select(OperacaoExecucao).where(
            OperacaoExecucao.operacao_id == operacao_id,
            OperacaoExecucao.tenant_id == self.tenant_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _reverter_efeitos_economicos_operacao(
        self,
        operacao_id: UUID,
        *,
        remover_execucoes: bool = True,
    ) -> None:
        """Reverte, na mesma transação, estoque, CostAllocation e Despesa de uma operação.

        `remover_execucoes=False` é usado quando a própria OperacaoAgricola será excluída
        em seguida (hard_delete): o cascade "all, delete-orphan" já remove as execuções,
        e apagá-las aqui duplicaria o DELETE. Para transições de status (operação
        permanece viva), `remover_execucoes=True` remove a execução para que uma futura
        reexecução não reutilize um registro obsoleto.

        Idempotente por natureza dos vínculos: uma segunda chamada não encontra mais
        execuções, allocations ou despesa ativa para reverter (já foram removidas/
        neutralizadas na primeira execução), portanto não produz efeito adicional.
        """
        execucoes = await self._buscar_execucoes_da_operacao(operacao_id)
        execucao_ids = [execucao.id for execucao in execucoes]

        for execucao in execucoes:
            await self._reverter_movimentos_estoque_operacao(execucao, motivo="cancelamento")

        if execucao_ids:
            alloc_stmt = select(CostAllocation).where(
                CostAllocation.tenant_id == self.tenant_id,
                or_(
                    CostAllocation.operation_execution_id.in_(execucao_ids),
                    CostAllocation.source_id.in_(execucao_ids),
                ),
            )
            allocations = list((await self.session.execute(alloc_stmt)).scalars().all())
            for allocation in allocations:
                await self.session.delete(allocation)

        despesa = await self._buscar_despesa_existente(operacao_id)
        if despesa is not None:
            despesa.ativo = False
            despesa.status = "CANCELADO"
            self.session.add(despesa)

        if remover_execucoes:
            for execucao in execucoes:
                await self.session.delete(execucao)

        if execucoes or despesa is not None:
            await self.session.flush()

    async def _buscar_despesa_existente(self, operacao_id: UUID) -> Despesa | None:
        stmt = (
            select(Despesa)
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.origem_tipo == "OPERACAO_AGRICOLA",
                Despesa.origem_id == operacao_id,
                Despesa.ativo == True,
            )
            .order_by(Despesa.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _buscar_entrada_caderno_existente(self, operacao_id: UUID) -> CadernoCampoEntrada | None:
        stmt = (
            select(CadernoCampoEntrada)
            .where(
                CadernoCampoEntrada.tenant_id == self.tenant_id,
                (
                    (CadernoCampoEntrada.operacao_id == operacao_id)
                    | (
                        (CadernoCampoEntrada.origem_evento == ORIGEM_EVENTO_OPERACAO)
                        & (CadernoCampoEntrada.origem_id == str(operacao_id))
                    )
                ),
            )
            .order_by(CadernoCampoEntrada.data_registro.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    def _montar_descricao_caderno(self, operacao: OperacaoAgricola) -> str:
        descricao = operacao.tipo
        if operacao.area_aplicada_ha:
            descricao += f"\nÁrea: {operacao.area_aplicada_ha} ha"
        if operacao.custo_total:
            descricao += f"\nCusto: R$ {operacao.custo_total:.2f}"
        return descricao

    async def _aplicar_insumos_na_operacao(
        self,
        operacao: OperacaoAgricola,
        insumos_data: list[InsumoOperacaoCreate],
        *,
        unidade_produtiva_id: UUID,
        area_base_ha: float,
    ) -> tuple[float, list[dict]]:
        custo_total_insumos = 0.0
        ledger_consumos: list[dict] = []

        for insumo in insumos_data:
            quantidade_total = insumo.dose_por_ha * (insumo.area_aplicada or area_base_ha)
            custo_item = 0.0
            custo_unitario = 0.0

            produto = await self.session.get(Produto, insumo.produto_id)
            if not produto or (produto.tenant_id is not None and produto.tenant_id != self.tenant_id):
                logger.warning(
                    "multi_up_tenant_mismatch",
                    resource="produto",
                    tenant_id=str(self.tenant_id),
                    produto_id=str(insumo.produto_id),
                )
                raise EntityNotFoundError("Produto/Insumo", insumo.produto_id)

            if operacao.status == "REALIZADA":
                consumo = await consumir_lotes_fifo(
                    session=self.session,
                    produto_id=insumo.produto_id,
                    quantidade_necessaria=quantidade_total,
                    tenant_id=self.tenant_id,
                )

                custo_item = consumo.custo_total
                custo_unitario = consumo.custo_total / quantidade_total if quantidade_total > 0 else 0.0

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

                await atualizar_saldo_apos_consumo(
                    session=self.session,
                    produto_id=insumo.produto_id,
                    quantidade_total=quantidade_total,
                )

            insumo_op = InsumoOperacao(
                id=uuid.uuid4(),
                operacao_id=operacao.id,
                tenant_id=self.tenant_id,
                produto_id=insumo.produto_id,
                lote_insumo=insumo.lote_insumo,
                lote_estoque_id=insumo.lote_estoque_id,
                unidade_medida_id=insumo.unidade_medida_id,
                dose_por_ha=insumo.dose_por_ha,
                unidade=insumo.unidade,
                area_aplicada=insumo.area_aplicada,
                quantidade_total=quantidade_total,
                custo_unitario=custo_unitario,
                custo_total=custo_item,
            )
            self.session.add(insumo_op)
            custo_total_insumos += custo_item

        return custo_total_insumos, ledger_consumos

    async def _reverter_movimentos_estoque_operacao(
        self,
        operacao_execucao: OperacaoExecucao | None,
        *,
        motivo: str = "edição",
    ) -> None:
        if operacao_execucao is None:
            return

        stmt = (
            select(EstoqueMovimento)
            .where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.operacao_execucao_id == operacao_execucao.id,
                EstoqueMovimento.tipo_movimento == "SAIDA",
            )
            .order_by(EstoqueMovimento.created_at.asc())
        )
        movimentos = list((await self.session.execute(stmt)).scalars().all())
        produtos_recalculados: set[UUID] = set()

        for movimento in movimentos:
            if movimento.lote_id:
                lote = await self.session.get(LoteEstoque, movimento.lote_id)
                if lote:
                    lote.quantidade_atual += abs(float(movimento.quantidade))
                    if lote.status == "ESGOTADO" and lote.quantidade_atual > 0:
                        lote.status = "ATIVO"
                    self.session.add(lote)

            await registrar_ledger_estoque(
                self.session,
                tenant_id=self.tenant_id,
                tipo_movimento="DEVOLUCAO",
                origem="OPERACAO_EXECUCAO",
                origem_id=operacao_execucao.id,
                operacao_execucao_id=operacao_execucao.id,
                production_unit_id=movimento.production_unit_id,
                produto_id=movimento.produto_id,
                deposito_id=movimento.deposito_id,
                lote_id=movimento.lote_id,
                quantidade=abs(float(movimento.quantidade)),
                custo_unitario=float(movimento.custo_unitario or 0.0),
                custo_total=float(movimento.custo_total or 0.0),
                ajuste_de=movimento.id,
                observacoes=f"Estorno por {motivo} da operação agrícola {operacao_execucao.operacao_id}",
            )
            produtos_recalculados.add(movimento.produto_id)

        for produto_id in produtos_recalculados:
            await atualizar_saldo_apos_consumo(
                session=self.session,
                produto_id=produto_id,
                quantidade_total=0,
            )

    async def _sincronizar_efeitos_operacao(
        self,
        operacao: OperacaoAgricola,
        *,
        unidade_produtiva_id: UUID,
        safra_desc: str,
    ) -> None:
        operacao_execucao = await self._buscar_execucao_existente(operacao.id)
        allocation = None
        if operacao.status == "REALIZADA":
            operacao_execucao, allocation = await self._garantir_execucao_e_allocation_leves(
                operacao,
                allow_create_execucao=True,
            )
        if operacao_execucao is not None:
            operacao_execucao.data_execucao = operacao.data_realizada
            operacao_execucao.hora_execucao = operacao.hora_inicio
            operacao_execucao.quantidade_planejada = operacao.area_aplicada_ha
            operacao_execucao.quantidade_executada = operacao.area_aplicada_ha or 1
            operacao_execucao.custo_real = float(operacao.custo_total or 0.0)
            operacao_execucao.area_ha_executada = operacao.area_aplicada_ha
            operacao_execucao.operador_id = operacao.operador_id
            operacao_execucao.observacoes = operacao.observacoes
            self.session.add(operacao_execucao)

        allocation = allocation or await self._buscar_allocation_existente(
            operacao_execucao_id=operacao_execucao.id if operacao_execucao else None,
            production_unit_id=operacao.production_unit_id,
        )
        if allocation is not None:
            allocation.amount = float(operacao.custo_total or 0.0)
            allocation.allocation_basis = float(operacao.area_aplicada_ha or 0.0) or None
            allocation.allocation_date = operacao.data_realizada
            self.session.add(allocation)

        # Despesa(OPERACAO_AGRICOLA) não é mais criada nem sincronizada (SOIL-PLAN-EXEC-04I).
        # Registros históricos permanecem intocados; a única operação suportada sobre eles é a
        # neutralização em `_reverter_efeitos_economicos_operacao`.

        if operacao.status == "REALIZADA":
            caderno_svc = CadernoCampoService(self.session, self.tenant_id)
            entrada = await caderno_svc.garantir_evento_operacao(operacao)
            entrada.safra_id = operacao.safra_id
            entrada.talhao_id = operacao.talhao_id
            self.session.add(entrada)

    async def _buscar_allocation_existente(
        self,
        *,
        operacao_execucao_id: UUID | None,
        production_unit_id: UUID | None,
    ) -> CostAllocation | None:
        stmt = select(CostAllocation).where(CostAllocation.tenant_id == self.tenant_id)
        if operacao_execucao_id is not None:
            stmt = stmt.where(CostAllocation.operation_execution_id == operacao_execucao_id)
        elif production_unit_id is not None:
            stmt = stmt.where(
                CostAllocation.source == "OPERATION_EXECUTION",
                CostAllocation.production_unit_id == production_unit_id,
            )
        else:
            return None
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def _garantir_execucao_e_allocation_leves(
        self,
        operacao: OperacaoAgricola,
        *,
        allow_create_execucao: bool,
    ) -> tuple[OperacaoExecucao | None, CostAllocation | None]:
        if operacao.status != "REALIZADA":
            return None, None

        alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
        regra = alertas_svc.classificar_origem_operacao(operacao.tipo)
        operacao_execucao = await self._buscar_execucao_existente(operacao.id)
        allocation = None

        if operacao_execucao is None and allow_create_execucao:
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
                    custo_real=float(operacao.custo_total or 0.0),
                    area_ha_executada=operacao.area_aplicada_ha,
                    status="REALIZADA",
                    operador_id=operacao.operador_id,
                    observacoes=operacao.observacoes,
                )
                self.session.add(operacao_execucao)
                await self.session.flush()

        if operacao_execucao is None:
            finding = alertas_svc.build_finding(
                codigo="OPERACAO_REALIZADA_SEM_EXECUCAO_NOVO_FLUXO",
                titulo="Operação realizada sem execução no novo fluxo",
                severidade="INCONSISTENCIA_MODERADA",
                origem="operacoes_agricolas",
                total=1,
                mensagem=(
                    "Operação marcada como realizada no novo fluxo não possui "
                    "OperacaoExecucao criada automaticamente."
                ),
                amostras=[str(operacao.id)],
                meta={"operacao_id": str(operacao.id), "tipo_operacao": operacao.tipo},
            )
            await alertas_svc.registrar_e_aplicar_enforcement(
                WorkflowGovernanceEvent(
                    finding=finding,
                    resource_id=str(operacao.id),
                    action="lv_missing_exec",
                    notify=True,
                    audit=True,
                    origem_id=f"operacao:{operacao.id}:missing_execution",
                ),
                allow_block=True,
            )
            return None, None

        custo_operacional = float(operacao.custo_total or 0.0)
        if custo_operacional <= 0 or operacao.production_unit_id is None:
            if custo_operacional > 0 and operacao.production_unit_id is None and regra.exige_cost_allocation:
                finding = alertas_svc.build_finding(
                    codigo="OPERACAO_COM_CUSTO_SEM_CONTEXTO_ALLOCATION",
                    titulo="Operação com custo sem contexto suficiente para apropriação",
                    severidade="RISCO_ECONOMICO",
                    origem="operacoes_agricolas",
                    total=1,
                    mensagem=(
                        "Operação possui custo, mas ainda não foi possível resolver "
                        "production_unit para gerar CostAllocation."
                    ),
                    amostras=[str(operacao.id)],
                    meta={"operacao_id": str(operacao.id), "tipo_operacao": operacao.tipo},
                )
                await alertas_svc.registrar_e_aplicar_enforcement(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(operacao.id),
                        action="lv_alloc_ctx",
                        notify=True,
                        audit=True,
                        origem_id=f"operacao:{operacao.id}:missing_allocation_context",
                    ),
                    allow_block=True,
                    error_message=(
                        "Nao e possivel concluir a operacao com custo sem apropriacao economica. "
                        "Revise ProductionUnit ou o contexto operacional da safra."
                    ),
                )
                # Bloqueio direcionado (SOIL-PLAN-EXEC-04K): independente do modo global
                # WORKFLOW_ENFORCEMENT_MODE (que permanece WARNING_ONLY), operação REALIZADA
                # com custo>0 e sem ProductionUnit resolvida NUNCA pode ficar sem allocation
                # quando o tipo exige. O finding acima permanece como evidência/observabilidade.
                raise BusinessRuleError(self.MENSAGEM_PRODUCTION_UNIT_AUSENTE)
            elif custo_operacional <= 0 and regra.origem == "AGRICOLA_OPERACIONAL":
                finding = alertas_svc.build_finding(
                    codigo="OPERACAO_AGRICOLA_SEM_CUSTO_NOVO_FLUXO",
                    titulo="Operação agrícola realizada sem custo direto",
                    severidade="WARNING_LEVE",
                    origem="operacoes_agricolas",
                    total=1,
                    mensagem=(
                        "Operação agrícola foi marcada como realizada sem custo direto. "
                        "O fluxo é permitido, mas não é o caminho recomendado sem evidência complementar."
                    ),
                    amostras=[str(operacao.id)],
                    meta={"operacao_id": str(operacao.id), "tipo_operacao": operacao.tipo, "classificacao_origem": regra.origem},
                )
                await alertas_svc.registrar_e_aplicar_enforcement(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(operacao.id),
                        action="op_no_cost",
                        notify=True,
                        audit=True,
                        origem_id=f"operacao:{operacao.id}:no_cost",
                    ),
                    allow_block=True,
                )
            return operacao_execucao, None

        allocation = await self._buscar_allocation_existente(
            operacao_execucao_id=operacao_execucao.id,
            production_unit_id=operacao.production_unit_id,
        )
        if allocation is not None:
            return operacao_execucao, allocation

        try:
            allocation = await registrar_cost_allocation(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=operacao.production_unit_id,
                source="OPERATION_EXECUTION",
                source_id=operacao_execucao.id,
                operation_execution_id=operacao_execucao.id,
                cost_category="OUTROS",
                amount=custo_operacional,
                allocation_date=operacao_execucao.data_execucao,
                allocation_method="DIRECT",
                allocation_basis=operacao_execucao.area_ha_executada,
            )
            await self.session.flush()
        except Exception as exc:
            logger.warning(
                "light_validation_allocation_failed",
                tenant_id=str(self.tenant_id),
                operacao_id=str(operacao.id),
                error=str(exc),
            )
            finding = alertas_svc.build_finding(
                codigo="OPERACAO_COM_CUSTO_SEM_ALLOCATION_NOVO_FLUXO",
                titulo="Operação com custo sem allocation no novo fluxo",
                severidade="RISCO_ECONOMICO",
                origem="operacoes_agricolas",
                total=1,
                mensagem=(
                    "Operação realizada com custo direto não conseguiu gerar "
                    "CostAllocation automaticamente no novo fluxo."
                ),
                amostras=[str(operacao.id)],
                meta={"operacao_id": str(operacao.id), "tipo_operacao": operacao.tipo},
            )
            await alertas_svc.registrar_e_aplicar_enforcement(
                WorkflowGovernanceEvent(
                    finding=finding,
                    resource_id=str(operacao.id),
                    action="lv_alloc_fail",
                    notify=True,
                    audit=True,
                    origem_id=f"operacao:{operacao.id}:allocation_failed",
                ),
                allow_block=True,
                error_message=(
                    "Nao e possivel concluir a operacao com custo sem apropriacao economica. "
                    "Revise ProductionUnit, execucao e insumos antes de marcar como realizada."
                ),
            )
            # Bloqueio direcionado (SOIL-PLAN-EXEC-04K): falha ao criar CostAllocation
            # obrigatória nunca pode deixar a operação REALIZADA silenciosamente sem
            # apropriação econômica — a transação inteira deve falhar (rollback total).
            raise BusinessRuleError(
                "Não foi possível registrar a apropriação econômica (CostAllocation) da "
                "operação. Revise ProductionUnit, execução e insumos antes de concluir."
            ) from exc

        return operacao_execucao, allocation

    async def _validar_calibracao_e_sanitario(
        self, maquina_id: UUID | None, data_realizada: date
    ) -> None:
        if not maquina_id:
            return

        from core.cadastros.equipamentos.models import Equipamento, EquipamentoCalibracao
        from operacional.models.checklist import ChecklistRealizado, ChecklistModelo
        from sqlalchemy import func, Date

        equipamento = await self.session.get(Equipamento, maquina_id)
        if not equipamento or equipamento.tenant_id != self.tenant_id:
            raise BusinessRuleError("Equipamento não localizado ou inacessível para o tenant.")

        if equipamento.tipo == "PULVERIZADOR":
            # 1. Verifica calibração vigente
            calib_stmt = (
                select(EquipamentoCalibracao)
                .where(
                    EquipamentoCalibracao.equipamento_id == maquina_id,
                    EquipamentoCalibracao.tenant_id == self.tenant_id,
                    EquipamentoCalibracao.data_calibracao <= data_realizada,
                    EquipamentoCalibracao.validade_ate >= data_realizada,
                )
            )
            calib_existe = (await self.session.execute(calib_stmt)).scalars().first()
            if not calib_existe:
                raise BusinessRuleError("Equipamento sem calibração válida.")

            # 2. Verifica liberação sanitária aprovada no mesmo dia
            chk_stmt = (
                select(ChecklistRealizado)
                .join(ChecklistModelo)
                .where(
                    ChecklistRealizado.equipamento_id == maquina_id,
                    ChecklistRealizado.tenant_id == self.tenant_id,
                    ChecklistRealizado.liberado_para_uso == True,
                    func.cast(ChecklistRealizado.data_hora, Date) == data_realizada,
                    (ChecklistModelo.nome.ilike("%sanit%") | ChecklistModelo.nome.ilike("%limpez%") | ChecklistModelo.nome.ilike("%higien%")),
                )
            )
            chk_existe = (await self.session.execute(chk_stmt)).scalars().first()
            if not chk_existe:
                raise BusinessRuleError("Liberação sanitária pendente.")

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
            await self._validar_calibracao_e_sanitario(dados.maquina_id, dados.data_realizada)
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
        area_aplicada_validada = await self._validar_area_aplicada(dados.talhao_id, dados.area_aplicada_ha)

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

        # 2.6. VALIDAÇÃO: Data não pode ser futura apenas se a operação já estiver realizada
        if dados.status == "REALIZADA" and dados.data_realizada > date.today():
            raise BusinessRuleError(
                f"Data da operação não pode ser futura. "
                f"Informe a data em que a operação foi realmente realizada."
            )

        # 3. Extrai insumos
        insumos_data = dados.insumos
        dados_dict = dados.model_dump(exclude={"insumos"})
        dados_dict["fase_safra"] = fase_safra
        dados_dict["production_unit_id"] = await self._resolve_production_unit_id(dados)
        dados_dict["area_aplicada_ha"] = area_aplicada_validada

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
                custo_item = 0.0
                custo_unitario = 0.0

                produto = await self.session.get(Produto, insumo.produto_id)
                if not produto or (produto.tenant_id is not None and produto.tenant_id != self.tenant_id):
                    logger.warning(
                        "multi_up_tenant_mismatch",
                        resource="produto",
                        tenant_id=str(self.tenant_id),
                        produto_id=str(insumo.produto_id),
                    )
                    raise EntityNotFoundError("Produto/Insumo", insumo.produto_id)

                if operacao.status == "REALIZADA":
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
                    custo_unitario = consumo.custo_total / quantidade_total if quantidade_total > 0 else 0.0

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

                    # Update SaldoEstoque after FIFO consumption (required for UI accuracy)
                    await atualizar_saldo_apos_consumo(
                        session=self.session,
                        produto_id=insumo.produto_id,
                        quantidade_total=quantidade_total,
                    )

                # Record InsumoOperacao
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
                    custo_unitario=custo_unitario,
                    custo_total=custo_item,
                )

                self.session.add(insumo_op)
                custo_total_operacao += custo_item

            # All insumos processed successfully - finalize operacao.
            # Manual-only launches (common in "Execução por Fase") do not send
            # insumos, so we preserve the informed total instead of forcing zero.
            operacao.custo_total = custo_total_operacao
            if operacao.area_aplicada_ha and operacao.area_aplicada_ha > 0:
                operacao.custo_por_ha = custo_total_operacao / operacao.area_aplicada_ha

            operacao_execucao = None
            if operacao.status == "REALIZADA":
                operacao_execucao, _ = await self._garantir_execucao_e_allocation_leves(
                    operacao,
                    allow_create_execucao=True,
                )
                if operacao_execucao is not None:
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

            # 4. Sincroniza custo na Safra
            safra = await self.session.get(Safra, operacao.safra_id)
            if safra:
                # Re-calcula custo realizado por ha baseado em todas as operações REALIZADAS
                stmt_sum = select(func.sum(OperacaoAgricola.custo_total)).where(
                    OperacaoAgricola.safra_id == safra.id,
                    OperacaoAgricola.status == "REALIZADA"
                )
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

            # Commit only if ALL operations succeeded (atomicity)
            # 6. TRIGGER: Se operação foi criada com status REALIZADA, cria evento canônico no caderno
            if operacao.status == "REALIZADA":
                caderno_svc = CadernoCampoService(self.session, self.tenant_id)
                entrada = await caderno_svc.garantir_evento_operacao(operacao)
                logger.info(
                    f"Entrada canônica no caderno (criação): {operacao.tipo} → safra {operacao.safra_id}",
                    entrada_id=str(entrada.id),
                )

            # 7. Conclui a tarefa vinculada automaticamente se a operação for REALIZADA
            if dados.tarefa_id and operacao.status == "REALIZADA":
                from agricola.tarefas.models import SafraTarefa
                tarefa = await self.session.get(SafraTarefa, dados.tarefa_id)
                if tarefa and tarefa.tenant_id == self.tenant_id:
                    tarefa.status = "CONCLUIDA"
                    tarefa.operacao_id = operacao.id
                    tarefa.concluida_em = datetime.utcnow()

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

    async def hard_delete(self, id: UUID) -> None:
        """Cancela a operação: reverte estoque/CostAllocation/Despesa antes de excluir."""
        operacao = await self.get_or_fail(id)
        await self._reverter_efeitos_economicos_operacao(operacao.id, remover_execucoes=False)
        await super().hard_delete(id)

    async def atualizar(self, obj_id: UUID, dados: OperacaoAgricolaUpdate) -> OperacaoAgricola:
        # 1. Busca estado atual antes de atualizar
        operacao_atual = await self.get_or_fail(obj_id)
        status_anterior = operacao_atual.status
        insumos_anteriores = list(operacao_atual.insumos or [])
        custo_insumos_anterior = sum(float(insumo.custo_total or 0.0) for insumo in insumos_anteriores)
        operacao_execucao_existente = await self._buscar_execucao_existente(obj_id)
        unidade_produtiva_id = await self._get_unidade_produtiva_id_for_talhao(operacao_atual.talhao_id)

        # Validar calibração e liberação sanitária para atualização
        dados_dict = dados.model_dump(exclude_unset=True)
        maquina_id_final = dados_dict.get("maquina_id", operacao_atual.maquina_id)
        data_realizada_final = dados_dict.get("data_realizada", operacao_atual.data_realizada)
        await self._validar_calibracao_e_sanitario(maquina_id_final, data_realizada_final)

        # 2. Aplica atualização
        dados_dict = dados.model_dump(exclude_unset=True)
        insumos_payload = dados_dict.pop("insumos", None)
        if "area_aplicada_ha" in dados_dict:
            dados_dict["area_aplicada_ha"] = await self._validar_area_aplicada(
                operacao_atual.talhao_id,
                dados_dict["area_aplicada_ha"],
            )
        if "custo_total" in dados_dict and dados_dict["custo_total"] is not None:
            dados_dict["custo_total"] = float(dados_dict["custo_total"])

        # 2.1 Revalida ProductionUnit quando informada explicitamente na edição
        # (SOIL-PLAN-EXEC-04K): impede vínculo com unidade de outro tenant/contexto
        # incompatível ao trocar a unidade econômica de uma operação existente.
        if "production_unit_id" in dados_dict and dados_dict["production_unit_id"] is not None:
            safra_id_final = dados_dict.get("safra_id", operacao_atual.safra_id)
            talhao_id_final = dados_dict.get("talhao_id", operacao_atual.talhao_id)
            cultivo_id_final = dados_dict.get("cultivo_id", getattr(operacao_atual, "cultivo_id", None))
            pu = await validate_production_unit_context(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=dados_dict["production_unit_id"],
                safra_id=safra_id_final,
                area_id=talhao_id_final,
                cultivo_id=cultivo_id_final,
            )
            dados_dict["production_unit_id"] = pu.id

        # A partir daqui, qualquer BusinessRuleError (ex.: ProductionUnit ausente/ambígua,
        # falha ao criar CostAllocation obrigatória) precisa reverter TUDO nesta chamada
        # (status, estoque, execução, allocation) — nenhum efeito parcial pode sobreviver
        # (SOIL-PLAN-EXEC-04K, ordem transacional §11).
        try:
            operacao = await self._atualizar_efeitos_operacao(
                operacao_id=obj_id,
                dados_dict=dados_dict,
                insumos_payload=insumos_payload,
                insumos_anteriores=insumos_anteriores,
                custo_insumos_anterior=custo_insumos_anterior,
                operacao_execucao_existente=operacao_execucao_existente,
                unidade_produtiva_id=unidade_produtiva_id,
                status_anterior=status_anterior,
                custo_total_anterior=float(operacao_atual.custo_total or 0.0),
            )
        except BusinessRuleError:
            await self.session.rollback()
            raise

        return operacao

    async def _atualizar_efeitos_operacao(
        self,
        *,
        operacao_id: UUID,
        dados_dict: dict,
        insumos_payload,
        insumos_anteriores: list,
        custo_insumos_anterior: float,
        operacao_execucao_existente: OperacaoExecucao | None,
        unidade_produtiva_id: UUID,
        status_anterior: str,
        custo_total_anterior: float = 0.0,
    ) -> OperacaoAgricola:
        operacao = await super().update(operacao_id, dados_dict)

        area_alterada = "area_aplicada_ha" in dados_dict
        novo_status = dados_dict.get("status")
        status_mudou_para_realizada = novo_status == "REALIZADA" and status_anterior != "REALIZADA"
        operacao_saiu_de_realizada = (
            status_anterior == "REALIZADA"
            and novo_status is not None
            and novo_status != "REALIZADA"
        )

        precisa_reprocessar_insumos = (
            insumos_payload is not None
            or (area_alterada and len(insumos_anteriores) > 0)
            or status_mudou_para_realizada
        )

        if operacao_saiu_de_realizada:
            # Operação deixou de ser REALIZADA: reverte estoque, CostAllocation e Despesa
            # em vez de reaplicar insumos.
            await self._reverter_efeitos_economicos_operacao(operacao.id)
        elif precisa_reprocessar_insumos:
            await self._reverter_movimentos_estoque_operacao(operacao_execucao_existente)
            if insumos_anteriores:
                await self.session.execute(delete(InsumoOperacao).where(InsumoOperacao.operacao_id == operacao.id))
                await self.session.flush()

            if insumos_payload is None:
                insumos_reaplicados = [
                    InsumoOperacaoCreate(
                        produto_id=insumo.produto_id,
                        lote_insumo=insumo.lote_insumo,
                        lote_estoque_id=insumo.lote_estoque_id,
                        unidade_medida_id=insumo.unidade_medida_id,
                        dose_por_ha=float(insumo.dose_por_ha),
                        unidade=insumo.unidade,
                        area_aplicada=float(insumo.area_aplicada) if insumo.area_aplicada is not None else None,
                    )
                    for insumo in insumos_anteriores
                ]
            else:
                insumos_reaplicados = [
                    item if isinstance(item, InsumoOperacaoCreate) else InsumoOperacaoCreate(**item)
                    for item in insumos_payload
                ]

            base_manual = (
                float(dados_dict["custo_total"])
                if "custo_total" in dados_dict and dados_dict["custo_total"] is not None
                else max(0.0, float(custo_total_anterior or 0.0) - custo_insumos_anterior)
            )
            custo_insumos_novo, ledger_consumos = await self._aplicar_insumos_na_operacao(
                operacao,
                insumos_reaplicados,
                unidade_produtiva_id=unidade_produtiva_id,
                area_base_ha=float(operacao.area_aplicada_ha or 0.0),
            )
            operacao.custo_total = base_manual + custo_insumos_novo

            operacao_execucao = operacao_execucao_existente
            if operacao.status == "REALIZADA":
                operacao_execucao, _ = await self._garantir_execucao_e_allocation_leves(
                    operacao,
                    allow_create_execucao=True,
                )
                if operacao_execucao is not None:
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

        if "custo_total" in dados_dict or "area_aplicada_ha" in dados_dict or precisa_reprocessar_insumos:
            custo_total = float(operacao.custo_total or 0.0)
            area_aplicada = float(operacao.area_aplicada_ha or 0.0)
            operacao.custo_por_ha = (custo_total / area_aplicada) if area_aplicada > 0 else 0.0
            self.session.add(operacao)
            await self.session.flush()

            # 3. TRIGGER: Se status mudou para REALIZADA, cria evento canônico no caderno de campo
            novo_status = dados_dict.get("status")
            if novo_status == "REALIZADA" and status_anterior != "REALIZADA":
                caderno_svc = CadernoCampoService(self.session, self.tenant_id)
                entrada = await caderno_svc.garantir_evento_operacao(operacao)
                logger.info(
                    f"Entrada canônica no caderno: {operacao.tipo} → safra {operacao.safra_id}",
                    entrada_id=str(entrada.id),
                )

                # 4. Conclui a tarefa vinculada automaticamente (mesmo comportamento de criar()) —
                # fecha o ciclo planejamento->campo para Ordens de Serviço geradas via
                # /tarefas/{id}/planejar-operacao e depois marcadas como REALIZADA aqui.
                if operacao.tarefa_id:
                    from agricola.tarefas.models import SafraTarefa
                    tarefa = await self.session.get(SafraTarefa, operacao.tarefa_id)
                    if tarefa and tarefa.tenant_id == self.tenant_id:
                        tarefa.status = "CONCLUIDA"
                        tarefa.operacao_id = operacao.id
                        tarefa.concluida_em = datetime.utcnow()

        if operacao.status == "REALIZADA":
            await self._garantir_execucao_e_allocation_leves(
                operacao,
                allow_create_execucao=True,
            )

        safra = await self.session.get(Safra, operacao.safra_id)
        safra_desc = (
            f"{safra.cultura} {safra.ano_safra}"
            if safra is not None and getattr(safra, "cultura", None) is not None
            else str(operacao.safra_id)[:8]
        )
        await self._sincronizar_efeitos_operacao(
            operacao,
            unidade_produtiva_id=unidade_produtiva_id,
            safra_desc=safra_desc,
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
