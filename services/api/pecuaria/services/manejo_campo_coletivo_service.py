"""Materialização híbrida (POR_LOTE e INDIVIDUAL) de manejos enviados pelo App Campo."""

from __future__ import annotations

from datetime import date, datetime
from typing import Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from campo.models import TarefaCampo
from core.cadastros.produtos.models import Produto
from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.schemas.campo_sync_schema import ManejoSyncResult
from pecuaria.schemas.manejo_schema import ManejoLoteCreate
from pecuaria.services.manejo_service import ManejoLoteService


class ManejoCampoColetivoService:
    """Processa tarefas pecuárias coletivas (POR_LOTE) e eventos físicos de campo."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    @staticmethod
    def ja_processado_com_sucesso(tarefa: TarefaCampo) -> bool:
        """Indica se a tarefa já possui registro concluído em `sync_pecuaria`."""
        meta = (tarefa.dados or {}).get("sync_pecuaria")
        return isinstance(meta, dict) and meta.get("status") == "SUCCESS"

    async def buscar_lote_coletivo_elegivel(self, lote_id: UUID | None) -> LoteAnimal | None:
        """Retorna o lote quando ativo no tenant, em modo POR_LOTE e sem animais individuais.

        Args:
            lote_id: Identificador do lote informado na tarefa.

        Returns:
            LoteAnimal elegível para fluxo coletivo ou None.
        """
        if lote_id is None:
            return None
        lote = await self._buscar_lote(lote_id)
        if not lote or not lote.ativo or lote.modo_gestao != "POR_LOTE":
            return None
        if await self._contar_animais_individuais(lote.id) > 0:
            return None
        return lote

    async def processar_pesagem_por_lote(
        self, tarefa: TarefaCampo, lote: LoteAnimal
    ) -> ManejoSyncResult:
        """Registra pesagem coletiva no ManejoLote e atualiza o peso médio do lote."""
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa.id, "Pesagem coletiva já processada.")

        dados = tarefa.dados or {}
        qtd = self._safe_int(dados.get("quantidade_animais")) or int(lote.quantidade_cabecas or 0)
        peso_medio = self._safe_float(dados.get("peso_medio_kg"))
        peso_total = self._safe_float(dados.get("peso_total_kg") or dados.get("peso_total_estimado"))
        if peso_total is None or peso_total <= 0:
            peso_total = round(peso_medio * qtd, 2) if (peso_medio and peso_medio > 0 and qtd > 0) else 0.0

        if qtd <= 0 or peso_total <= 0:
            return self._resultado_erro(
                tarefa.id,
                max(qtd, 1),
                ["Informe quantidade de cabeças e peso médio/total válidos para pesagem coletiva."],
            )

        data_ev = self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em)
        manejo = ManejoLote(
            tenant_id=self.tenant_id,
            lote_id=lote.id,
            tipo_evento="PESAGEM",
            data_evento=data_ev,
            quantidade_cabecas=qtd,
            peso_total_kg=round(peso_total, 2),
            observacoes=self._obs(dados),
        )
        self.session.add(manejo)
        peso_medio_calc = round(peso_total / qtd, 2)
        lote.peso_medio_kg = peso_medio_calc
        if lote.peso_inicial_medio_kg is None:
            lote.peso_inicial_medio_kg = peso_medio_calc
        self.session.add(lote)
        await self.session.flush()
        return self._resultado_sucesso(tarefa.id, qtd, qtd)

    async def processar_vacinacao_por_lote(
        self,
        *,
        tarefa: TarefaCampo,
        lote: LoteAnimal,
        produto: Produto,
        dose: float,
        unidade_medida: str,
        registrar_estoque_fn: Callable[..., Awaitable[EstoqueMovimento | None]],
        registrar_custo_fn: Callable[..., Awaitable[CostAllocation | None]],
    ) -> ManejoSyncResult:
        """Executa vacinação coletiva em lote POR_LOTE com baixa proporcional no estoque."""
        tarefa_id = tarefa.id
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa_id, "Vacinação coletiva já processada.")

        dados = tarefa.dados or {}
        qtd = self._safe_int(dados.get("quantidade_animais")) or int(lote.quantidade_cabecas or 0)
        if qtd <= 0:
            return self._resultado_erro(tarefa_id, 1, ["Lote sem saldo de cabeças para vacinação."])

        try:
            movimento = await registrar_estoque_fn(
                tarefa=tarefa,
                produto=produto,
                dose=dose,
                unidade_medida=unidade_medida,
                quantidade_animais=qtd,
            )
            cost_alloc = await registrar_custo_fn(tarefa, movimento, qtd)
            custo_manejo = self._resolver_custo_manejo_sem_duplicar(movimento, cost_alloc)
            manejo = ManejoLote(
                tenant_id=self.tenant_id,
                lote_id=lote.id,
                tipo_evento="VACINACAO",
                data_evento=self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em),
                quantidade_cabecas=qtd,
                produto_id=produto.id,
                custo_total=custo_manejo,
                observacoes=self._obs(dados),
            )
            self.session.add(manejo)
            await self.session.flush()
            return self._resultado_sucesso(tarefa_id, qtd, qtd)
        except Exception as exc:
            await self.session.rollback()
            return self._resultado_erro(tarefa_id, qtd, [str(exc)])

    async def processar_morte(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        """Registra ocorrência de morte (individual ou coletiva em lote POR_LOTE)."""
        tarefa_id = tarefa.id
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa_id, "Morte já processada anteriormente.")

        dados = tarefa.dados or {}
        animal_id = self._uuid_val(dados.get("animal_id"))
        causa = str(dados.get("causa_morte") or "").strip() or None
        obs = self._montar_obs_com_prefixo(causa and f"Causa: {causa}", self._obs(dados))
        data_ev = self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em)

        if animal_id:
            return await self._processar_morte_individual(tarefa, animal_id, data_ev, causa, obs)

        lote_id = self._uuid_val(dados.get("lote_id") or tarefa.lote_id)
        qtd = self._safe_int(dados.get("quantidade_cabecas") or dados.get("quantidade_animais")) or 0
        if not lote_id or qtd <= 0:
            return self._resultado_erro(
                tarefa_id, 1, ["Informe o lote e a quantidade de cabeças (ou animal_id)."]
            )
        lote = await self._buscar_lote(lote_id)
        if not lote:
            return self._resultado_erro(tarefa_id, qtd, [f"Lote {lote_id} não encontrado."])
        if lote.modo_gestao == "INDIVIDUAL" or await self._contar_animais_individuais(lote.id) > 0:
            return self._resultado_erro(
                tarefa_id, qtd, ["Lote individual: selecione o animal que sofreu a baixa."]
            )
        try:
            await ManejoLoteService(self.tenant_id).registrar_evento(
                self.session,
                obj_in=ManejoLoteCreate(
                    lote_id=lote.id,
                    tipo_evento="MORTE",
                    data_evento=data_ev,
                    quantidade_cabecas=qtd,
                    observacoes=obs,
                ),
            )
            await self.session.flush()
            return self._resultado_sucesso(tarefa_id, qtd, qtd)
        except (BusinessRuleError, EntityNotFoundError) as exc:
            await self.session.rollback()
            return self._resultado_erro(tarefa_id, qtd, [str(exc)])

    async def processar_nascimento_lote(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        """Incrementa saldo de nascimentos coletivos em lote POR_LOTE."""
        tarefa_id = tarefa.id
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa_id, "Nascimento coletivo já processado.")

        dados = tarefa.dados or {}
        lote_id = self._uuid_val(dados.get("lote_id") or tarefa.lote_id)
        qtd = self._safe_int(dados.get("quantidade_cabecas") or dados.get("quantidade_animais")) or 0
        if not lote_id or qtd <= 0:
            return self._resultado_erro(tarefa_id, 1, ["Informe lote_id e quantidade_cabecas > 0."])
        lote = await self._buscar_lote(lote_id)
        if not lote:
            return self._resultado_erro(tarefa_id, qtd, [f"Lote {lote_id} não encontrado."])
        if lote.modo_gestao == "INDIVIDUAL" or await self._contar_animais_individuais(lote.id) > 0:
            return self._resultado_erro(
                tarefa_id,
                qtd,
                ["Lote em modo INDIVIDUAL; registre nascimentos individuais pela tela de Parto."],
            )
        try:
            await ManejoLoteService(self.tenant_id).registrar_evento(
                self.session,
                obj_in=ManejoLoteCreate(
                    lote_id=lote.id,
                    tipo_evento="NASCIMENTO",
                    data_evento=self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em),
                    quantidade_cabecas=qtd,
                    observacoes=self._obs(dados),
                ),
            )
            await self.session.flush()
            return self._resultado_sucesso(tarefa_id, qtd, qtd)
        except (BusinessRuleError, EntityNotFoundError) as exc:
            await self.session.rollback()
            return self._resultado_erro(tarefa_id, qtd, [str(exc)])

    async def processar_movimentacao_lote(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        """Executa troca de piquete do lote ou transferência de animal entre lotes."""
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa.id, "Movimentação já processada.")

        dados = tarefa.dados or {}
        animal_id = self._uuid_val(dados.get("animal_id"))
        lote_destino_id = self._uuid_val(dados.get("lote_destino_id"))
        data_ev = self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em)

        if animal_id and lote_destino_id:
            return await self._transferir_animal_entre_lotes(
                tarefa, animal_id, lote_destino_id, data_ev
            )

        lote_id = self._uuid_val(dados.get("lote_id") or tarefa.lote_id)
        area_destino_id = self._uuid_val(dados.get("area_destino_id") or tarefa.area_rural_id)
        if not lote_id or not area_destino_id:
            return self._resultado_erro(
                tarefa.id, 1, ["Informe lote_id e piquete destino para movimentação."]
            )

        lote = await self._buscar_lote(lote_id)
        if not lote:
            return self._resultado_erro(tarefa.id, 1, [f"Lote {lote_id} não encontrado."])

        piquete = await self._buscar_piquete(area_destino_id, lote.unidade_produtiva_id)
        if not piquete:
            return self._resultado_erro(
                tarefa.id,
                1,
                ["Piquete destino inválido, inativo ou pertence a outra fazenda/tenant."],
            )

        lote.area_id = piquete.id
        self.session.add(lote)
        manejo = ManejoLote(
            tenant_id=self.tenant_id,
            lote_id=lote.id,
            tipo_evento="TRANSFERENCIA",
            data_evento=data_ev,
            quantidade_cabecas=int(lote.quantidade_cabecas or 0),
            observacoes=self._obs(dados) or f"Movimentado para piquete {piquete.nome}",
        )
        self.session.add(manejo)
        await self.session.flush()
        return self._resultado_sucesso(tarefa.id, 1, 1)

    async def processar_medicacao(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        """Registra tratamento medicamentoso em animal individual ou coletivo no lote."""
        if self.ja_processado_com_sucesso(tarefa):
            return self._resultado_ignorado(tarefa.id, "Medicação já processada.")

        dados = tarefa.dados or {}
        produto_id = self._uuid_val(dados.get("produto_id"))
        produto: Produto | None = None
        if produto_id:
            produto = await self._buscar_produto_ativo(produto_id)
            if not produto:
                return self._resultado_erro(tarefa.id, 1, ["Medicamento não encontrado no tenant."])

        custo_total = self._safe_float(dados.get("custo_total"))
        if custo_total is not None and custo_total < 0:
            return self._resultado_erro(tarefa.id, 1, ["Custo total da medicação não pode ser negativo."])

        dose = self._safe_float(dados.get("dose") or dados.get("dose_ml"))
        data_ev = self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em)
        animal_id = self._uuid_val(dados.get("animal_id"))

        if animal_id:
            animal = await self._buscar_animal(animal_id)
            if not animal:
                return self._resultado_erro(tarefa.id, 1, [f"Animal {animal_id} não encontrado."])
            if await self._evento_animal_existente(tarefa.id, animal.id, "MEDICACAO"):
                return self._resultado_ignorado(tarefa.id, "Evento de medicação já registrado.")
            self.session.add(
                EventoAnimal(
                    tenant_id=self.tenant_id,
                    animal_id=animal.id,
                    tarefa_campo_id=tarefa.id,
                    operador_id=tarefa.operador_id,
                    tipo="MEDICACAO",
                    data_evento=data_ev,
                    produto_id=produto.id if produto else None,
                    valor=custo_total,
                    observacoes=self._obs(dados),
                    dados_extras={
                        "dose": dose,
                        "unidade_medida": dados.get("unidade_medida"),
                    },
                )
            )
            await self.session.flush()
            return self._resultado_sucesso(tarefa.id, 1, 1)

        lote_id = self._uuid_val(dados.get("lote_id") or tarefa.lote_id)
        if not lote_id:
            return self._resultado_erro(tarefa.id, 1, ["Informe lote_id ou animal_id para medicação."])
        lote = await self._buscar_lote(lote_id)
        if not lote:
            return self._resultado_erro(tarefa.id, 1, [f"Lote {lote_id} não encontrado."])
        qtd = self._safe_int(dados.get("quantidade_animais") or dados.get("quantidade_cabecas")) or int(
            lote.quantidade_cabecas or 0
        )
        self.session.add(
            ManejoLote(
                tenant_id=self.tenant_id,
                lote_id=lote.id,
                tipo_evento="MEDICACAO",
                data_evento=data_ev,
                quantidade_cabecas=qtd,
                produto_id=produto.id if produto else None,
                custo_total=custo_total,
                observacoes=self._obs(dados),
            )
        )
        await self.session.flush()
        return self._resultado_sucesso(tarefa.id, max(qtd, 1), max(qtd, 1))

    async def _processar_morte_individual(
        self,
        tarefa: TarefaCampo,
        animal_id: UUID,
        data_ev: date,
        causa: str | None,
        obs: str | None,
    ) -> ManejoSyncResult:
        animal = await self._buscar_animal(animal_id)
        if not animal:
            return self._resultado_erro(tarefa.id, 1, [f"Animal {animal_id} não encontrado."])
        if await self._evento_animal_existente(tarefa.id, animal.id, "MORTE"):
            return self._resultado_ignorado(tarefa.id, "Morte do animal já registrada.")
        if animal.status == "MORTO":
            return self._resultado_erro(tarefa.id, 1, ["Animal já está marcado como MORTO."])

        animal.status = "MORTO"
        self.session.add(animal)
        self.session.add(
            EventoAnimal(
                tenant_id=self.tenant_id,
                animal_id=animal.id,
                tarefa_campo_id=tarefa.id,
                operador_id=tarefa.operador_id,
                tipo="MORTE",
                data_evento=data_ev,
                observacoes=obs,
                dados_extras={
                    "causa_morte": causa,
                    "latitude": float(tarefa.latitude) if tarefa.latitude is not None else None,
                    "longitude": float(tarefa.longitude) if tarefa.longitude is not None else None,
                },
            )
        )
        await self.session.flush()
        await self._rematerializar_lote(animal.lote_id)
        await self.session.flush()
        return self._resultado_sucesso(tarefa.id, 1, 1)

    async def _transferir_animal_entre_lotes(
        self,
        tarefa: TarefaCampo,
        animal_id: UUID,
        lote_destino_id: UUID,
        data_ev: date,
    ) -> ManejoSyncResult:
        animal = await self._buscar_animal(animal_id)
        if not animal:
            return self._resultado_erro(tarefa.id, 1, [f"Animal {animal_id} não encontrado."])
        lote_destino = await self._buscar_lote(lote_destino_id)
        if not lote_destino or lote_destino.unidade_produtiva_id != animal.unidade_produtiva_id:
            return self._resultado_erro(
                tarefa.id, 1, ["Lote destino inválido ou pertence a outra fazenda/tenant."]
            )
        if await self._evento_animal_existente(tarefa.id, animal.id, "TRANSFERENCIA_LOTE"):
            return self._resultado_ignorado(tarefa.id, "Transferência individual já processada.")

        lote_origem_id = animal.lote_id
        animal.lote_id = lote_destino.id
        self.session.add(animal)
        self.session.add(
            EventoAnimal(
                tenant_id=self.tenant_id,
                animal_id=animal.id,
                tarefa_campo_id=tarefa.id,
                operador_id=tarefa.operador_id,
                tipo="TRANSFERENCIA_LOTE",
                data_evento=data_ev,
                lote_destino_id=lote_destino.id,
                area_destino_id=lote_destino.area_id,
                observacoes=self._obs(tarefa.dados or {}),
            )
        )
        await self.session.flush()
        await self._rematerializar_lote(lote_origem_id)
        await self._rematerializar_lote(lote_destino.id)
        await self.session.flush()
        return self._resultado_sucesso(tarefa.id, 1, 1)

    async def _rematerializar_lote(self, lote_id: UUID | None) -> None:
        if lote_id is None:
            return
        row = (
            await self.session.execute(
                select(
                    func.count(Animal.id),
                    func.coalesce(func.sum(Animal.peso_atual_kg), 0),
                    func.count(Animal.peso_atual_kg),
                ).where(
                    Animal.tenant_id == self.tenant_id,
                    Animal.lote_id == lote_id,
                    Animal.status == "ATIVO",
                )
            )
        ).one()
        lote = await self._buscar_lote(lote_id)
        if not lote:
            return
        total = int(row[0] or 0)
        peso_total = float(row[1] or 0)
        com_peso = int(row[2] or 0)
        lote.quantidade_cabecas = total
        lote.peso_medio_kg = round(peso_total / com_peso, 2) if com_peso else 0.0
        if total > 0 and lote.modo_gestao == "POR_LOTE":
            lote.modo_gestao = "INDIVIDUAL"
        self.session.add(lote)

    async def _buscar_lote(self, lote_id: UUID) -> LoteAnimal | None:
        return await self.session.scalar(
            select(LoteAnimal).where(
                LoteAnimal.id == lote_id,
                LoteAnimal.tenant_id == self.tenant_id,
            )
        )

    async def _buscar_animal(self, animal_id: UUID) -> Animal | None:
        return await self.session.scalar(
            select(Animal).where(Animal.id == animal_id, Animal.tenant_id == self.tenant_id)
        )

    async def _buscar_piquete(
        self, area_id: UUID, unidade_produtiva_id: UUID
    ) -> AreaRural | None:
        return await self.session.scalar(
            select(AreaRural).where(
                AreaRural.id == area_id,
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                AreaRural.tipo == TipoArea.PIQUETE.value,
                AreaRural.ativo == True,  # noqa: E712
            )
        )

    async def _buscar_produto_ativo(self, produto_id: UUID) -> Produto | None:
        return await self.session.scalar(
            select(Produto).where(
                Produto.id == produto_id,
                Produto.tenant_id == self.tenant_id,
                Produto.ativo == True,  # noqa: E712
            )
        )

    async def _contar_animais_individuais(self, lote_id: UUID) -> int:
        val = await self.session.scalar(
            select(func.count(Animal.id)).where(
                Animal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
            )
        )
        return int(val or 0)

    async def _evento_animal_existente(
        self, tarefa_id: UUID, animal_id: UUID, tipo: str
    ) -> bool:
        found = await self.session.scalar(
            select(EventoAnimal.id).where(
                EventoAnimal.tenant_id == self.tenant_id,
                EventoAnimal.tarefa_campo_id == tarefa_id,
                EventoAnimal.animal_id == animal_id,
                EventoAnimal.tipo == tipo,
            )
        )
        return found is not None

    @staticmethod
    def _resolver_custo_manejo_sem_duplicar(
        movimento: EstoqueMovimento | None,
        cost_alloc: CostAllocation | None,
    ) -> float | None:
        if cost_alloc is not None or movimento is None:
            return None
        if movimento.custo_total is not None and float(movimento.custo_total) != 0:
            return round(abs(float(movimento.custo_total)), 2)
        if movimento.custo_unitario is not None and float(movimento.custo_unitario) > 0:
            return round(abs(float(movimento.quantidade)) * float(movimento.custo_unitario), 2)
        return None

    @staticmethod
    def _resolver_data_evento(valor: object, fallback: datetime | None) -> date:
        if isinstance(valor, date) and not isinstance(valor, datetime):
            return valor
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, str):
            try:
                return datetime.fromisoformat(valor[:10]).date()
            except ValueError:
                pass
        return fallback.date() if fallback else date.today()

    @staticmethod
    def _obs(dados: dict) -> str | None:
        val = dados.get("observacoes") or dados.get("obs_execucao") or dados.get("obs")
        return str(val).strip() if val else None

    @staticmethod
    def _montar_obs_com_prefixo(prefixo: str | None, obs: str | None) -> str | None:
        partes = [p for p in (prefixo, obs) if p]
        return " · ".join(partes) if partes else None

    @staticmethod
    def _uuid_val(value: object) -> UUID | None:
        if isinstance(value, UUID):
            return value
        if value in (None, ""):
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: object) -> float | None:
        try:
            return None if value in (None, "") else float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: object) -> int | None:
        try:
            return None if value in (None, "") else int(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _resultado_sucesso(tarefa_id: UUID, recebido: int, processado: int) -> ManejoSyncResult:
        return ManejoSyncResult(
            status="SUCCESS",
            total_recebido=recebido,
            total_processado=processado,
            total_ignorados=0,
            erros=[],
            tarefa_campo_id=tarefa_id,
        )

    @staticmethod
    def _resultado_ignorado(tarefa_id: UUID, motivo: str) -> ManejoSyncResult:
        return ManejoSyncResult(
            status="IGNORED",
            total_recebido=0,
            total_processado=0,
            total_ignorados=0,
            erros=[motivo],
            tarefa_campo_id=tarefa_id,
        )

    @staticmethod
    def _resultado_erro(tarefa_id: UUID, recebido: int, erros: list[str]) -> ManejoSyncResult:
        return ManejoSyncResult(
            status="ERROR",
            total_recebido=recebido,
            total_processado=0,
            total_ignorados=0,
            erros=erros,
            tarefa_campo_id=tarefa_id,
        )
