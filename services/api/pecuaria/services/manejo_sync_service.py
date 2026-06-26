from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from core.cadastros.produtos.models import Produto, TipoProduto
from alert_engine.models import Domain
from events import DomainEvent, publish_domain_event_safe
from campo.models import TarefaCampo
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from operacional.models.estoque import EstoqueMovimento
from operacional.services.estoque_service import EstoqueService
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal


class ManejoSyncResult(BaseModel):
    status: str
    total_recebido: int
    total_processado: int
    total_ignorados: int
    erros: list[str]
    tarefa_campo_id: UUID

    model_config = ConfigDict(from_attributes=True)


class ManejoSyncService(BaseService[EventoAnimal]):
    ORIGEM_ESTOQUE_VACINACAO = "PECUARIA_VACINACAO"
    IDENTIFICADOR_ESTOQUE_VACINACAO = "PECUARIA_VACINACAO"

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        super().__init__(EventoAnimal, db, tenant_id)

    async def processar_tarefa_campo(self, tarefa_campo_id: UUID) -> ManejoSyncResult:
        tarefa = await self._buscar_tarefa(tarefa_campo_id)
        if not tarefa:
            return self._resultado_ignorado(tarefa_campo_id, "Tarefa não encontrada ou não pertence ao tenant.")
        if tarefa.module != "pecuaria":
            return self._resultado_ignorado(tarefa_campo_id, f"Módulo '{tarefa.module}' ignorado pelo ManejoSyncService.")
        if tarefa.status_execucao != "CONCLUIDA" and tarefa.status != "CONCLUIDA":
            return self._resultado_ignorado(tarefa_campo_id, "A tarefa não está com status CONCLUIDA.")
        if tarefa.type == "PESAGEM":
            res = await self._processar_pesagem(tarefa)
        elif tarefa.type == "VACINACAO":
            res = await self._processar_vacinacao(tarefa)
        else:
            return self._resultado_ignorado(tarefa_campo_id, f"Tipo '{tarefa.type}' não suportado nesta execução.")
        await self._persistir_resultado(tarefa_campo_id, res)
        if res.status == "ERROR":
            await self._publish_sync_failure_event(
                tarefa=tarefa,
                erro=res.erros[0] if res.erros else "Falha não especificada.",
                origem="processar_tarefa_campo",
                status=res.status,
            )
        return res

    async def _buscar_tarefa(self, tarefa_campo_id: UUID) -> TarefaCampo | None:
        stmt = select(TarefaCampo).where(TarefaCampo.id == tarefa_campo_id, TarefaCampo.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _resultado_ignorado(self, tarefa_campo_id: UUID, erro: str) -> ManejoSyncResult:
        return ManejoSyncResult(
            status="IGNORED",
            total_recebido=0,
            total_processado=0,
            total_ignorados=0,
            erros=[erro],
            tarefa_campo_id=tarefa_campo_id,
        )

    async def _processar_pesagem(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        tarefa_id = tarefa.id
        dados = tarefa.dados or {}
        animais_payload = dados.get("animais", [])
        if not animais_payload:
            return self._resultado_ignorado(tarefa_id, "A tarefa não contém a chave 'animais' ou a lista está vazia.")

        validacao = self._validar_animais_payload_pesagem(animais_payload, dados)
        if validacao["erros"]:
            await self.session.rollback()
            return self._resultado_erro(tarefa_id, validacao["total_recebido"], validacao["erros"])

        try:
            animais_banco = await self._buscar_animais(validacao["animal_ids"])
            erros = self._validar_animais_no_lote(animais_banco, validacao["animal_ids"], validacao["lote_id"])
            if erros:
                await self.session.rollback()
                return self._resultado_erro(tarefa_id, validacao["total_recebido"], erros)
            animais_ja_processados = await self._animais_ja_processados(tarefa.id, "PESAGEM", validacao["animal_ids"])
            eventos, total_processado = self._montar_eventos_pesagem(tarefa, dados, animais_banco, validacao["parsed_animais"], animais_ja_processados)
            total_ignorados = len(animais_ja_processados)
            if eventos:
                self.session.add_all(eventos)
            await self.session.commit()
            return ManejoSyncResult(
                status="SUCCESS",
                total_recebido=validacao["total_recebido"],
                total_processado=total_processado,
                total_ignorados=total_ignorados,
                erros=[],
                tarefa_campo_id=tarefa_id,
            )
        except Exception as exc:
            await self.session.rollback()
            erro = str(exc) if not isinstance(exc, ValueError) else "Erros de validação (veja os erros da lista)"
            erros = validacao.get("erros", []).copy() if "validacao" in locals() else []
            if not erros:
                erros.append(erro)
            return self._resultado_erro(tarefa_id, validacao["total_recebido"], erros)

    async def _processar_vacinacao(self, tarefa: TarefaCampo) -> ManejoSyncResult:
        tarefa_id = tarefa.id
        dados = tarefa.dados or {}
        animais_ids = self._normalizar_animais_ids(dados.get("animais_ids"))
        if not animais_ids:
            return self._resultado_ignorado(tarefa_id, "A tarefa não contém a chave 'animais_ids' ou a lista está vazia.")

        try:
            lote_id = self._uuid_from_value(dados.get("lote_id"))
            if not lote_id:
                raise ValueError("lote_id é obrigatório para vacinação.")
            await self._validar_lote_vacinacao(lote_id)
            produto = await self._validar_produto_vacina(dados.get("produto_id"))
            dose = self._validar_dose_vacinacao(dados.get("dose"))
            if not dados.get("unidade_medida"):
                raise ValueError("unidade_medida é obrigatória para vacinação.")
            animais_banco = await self._buscar_animais(animais_ids)
            erros = self._validar_animais_no_lote(animais_banco, animais_ids, lote_id)
            if erros:
                await self.session.rollback()
                return self._resultado_erro(tarefa_id, len(animais_ids), erros)
            animais_ja_processados = await self._animais_ja_processados(tarefa_id, "VACINACAO", animais_ids)
            eventos = self._montar_eventos_vacinacao(tarefa, dados, animais_banco, produto, dose, animais_ja_processados)
            total_processado = len(eventos)
            total_ignorados = len(animais_ja_processados)
            if eventos:
                self.session.add_all(eventos)
                await self.session.flush()
            movimento = await self._registrar_estoque_vacinacao(
                tarefa=tarefa,
                produto=produto,
                dose=dose,
                unidade_medida=str(dados.get("unidade_medida")),
                quantidade_animais=total_processado,
            )
            await self._registrar_custo_vacinacao(tarefa, movimento, total_processado)
            await self.session.commit()
            await self._publish_vacinacao_registrada_event(
                tarefa=tarefa,
                dados=dados,
                animais_ids=animais_ids,
                produto=produto,
                dose=dose,
            )
            return ManejoSyncResult(
                status="SUCCESS",
                total_recebido=len(animais_ids),
                total_processado=total_processado,
                total_ignorados=total_ignorados,
                erros=[],
                tarefa_campo_id=tarefa_id,
            )
        except Exception as exc:
            await self.session.rollback()
            erros = [str(exc)]
            return self._resultado_erro(tarefa_id, len(animais_ids), erros)

    def _validar_animais_payload_pesagem(self, animais_payload: list[dict], dados: dict) -> dict:
        erros: list[str] = []
        animal_ids: list[UUID] = []
        parsed_animais: dict[UUID, dict] = {}
        lote_id = self._uuid_from_value(dados.get("lote_id"))
        for index, item in enumerate(animais_payload):
            try:
                a_id = self._uuid_from_value(item.get("animal_id"))
                if not a_id:
                    erros.append(f"Item índice {index}: animal_id ausente.")
                    continue
                peso = float(item.get("peso_kg", 0))
                if peso <= 0:
                    erros.append(f"Animal {a_id}: Peso inválido ({peso}). Deve ser > 0.")
                animal_ids.append(a_id)
                parsed_animais[a_id] = {
                    "peso_kg": peso,
                    "observacao": item.get("observacao"),
                    "data_evento": item.get("data_evento"),
                }
            except (ValueError, TypeError):
                erros.append(f"Item índice {index}: Falha no parsing de UUID ou Float.")
        return {
            "erros": erros,
            "animal_ids": list(dict.fromkeys(animal_ids)),
            "parsed_animais": parsed_animais,
            "total_recebido": len(animais_payload),
            "lote_id": lote_id,
        }

    async def _buscar_animais(self, animal_ids: list[UUID]) -> dict[UUID, Animal]:
        stmt_animais = select(Animal).where(Animal.id.in_(animal_ids), Animal.tenant_id == self.tenant_id)
        res_animais = await self.session.execute(stmt_animais)
        return {animal.id: animal for animal in res_animais.scalars().all()}

    def _validar_animais_no_lote(self, animais_banco: dict[UUID, Animal], animal_ids: list[UUID], lote_id: UUID | None) -> list[str]:
        erros: list[str] = []
        for a_id in animal_ids:
            animal_obj = animais_banco.get(a_id)
            if not animal_obj:
                erros.append(f"Animal {a_id} não encontrado neste tenant.")
                continue
            if lote_id and animal_obj.lote_id != lote_id:
                erros.append(f"Animal {a_id} não pertence ao lote {lote_id}.")
        return erros

    async def _animais_ja_processados(self, tarefa_campo_id: UUID, tipo: str, animal_ids: list[UUID]) -> set[UUID]:
        stmt_eventos = select(EventoAnimal.animal_id).where(
            EventoAnimal.tarefa_campo_id == tarefa_campo_id,
            EventoAnimal.tipo == tipo,
            EventoAnimal.animal_id.in_(animal_ids),
            EventoAnimal.tenant_id == self.tenant_id,
        )
        res_evt = await self.session.execute(stmt_eventos)
        return set(res_evt.scalars().all())

    def _montar_eventos_pesagem(
        self,
        tarefa: TarefaCampo,
        dados: dict,
        animais_banco: dict[UUID, Animal],
        parsed_animais: dict[UUID, dict],
        animais_ja_processados: set[UUID],
    ) -> tuple[list[EventoAnimal], int]:
        eventos: list[EventoAnimal] = []
        total_processado = 0
        for a_id, p_data in parsed_animais.items():
            if a_id in animais_ja_processados:
                continue
            animal_obj = animais_banco[a_id]
            data_evt = self._resolver_data_evento(p_data.get("data_evento") or dados.get("data_evento"), tarefa.concluida_em)
            eventos.append(
                EventoAnimal(
                    tenant_id=self.tenant_id,
                    animal_id=a_id,
                    tarefa_campo_id=tarefa.id,
                    operador_id=tarefa.operador_id,
                    tipo="PESAGEM",
                    data_evento=data_evt,
                    peso_kg=p_data["peso_kg"],
                    observacoes=p_data["observacao"],
                )
            )
            if animal_obj.data_ultima_pesagem is None or data_evt >= animal_obj.data_ultima_pesagem:
                animal_obj.peso_atual_kg = p_data["peso_kg"]
                animal_obj.data_ultima_pesagem = data_evt
            total_processado += 1
        return eventos, total_processado

    async def _validar_produto_vacina(self, produto_id: object) -> Produto:
        produto_uuid = self._uuid_from_value(produto_id)
        if not produto_uuid:
            raise ValueError("produto_id é obrigatório para vacinação.")
        stmt = select(Produto).where(
            Produto.id == produto_uuid,
            Produto.tenant_id == self.tenant_id,
            Produto.ativo == True,
        )
        produto = (await self.session.execute(stmt)).scalars().first()
        if not produto:
            raise ValueError(f"Produto {produto_uuid} não encontrado neste tenant.")
        if produto.tipo != TipoProduto.VACINA.value:
            raise ValueError("O produto informado para vacinação deve ser do tipo VACINA.")
        return produto

    async def _validar_lote_vacinacao(self, lote_id: UUID) -> LoteAnimal:
        stmt = select(LoteAnimal).where(
            LoteAnimal.id == lote_id,
            LoteAnimal.tenant_id == self.tenant_id,
            LoteAnimal.ativo == True,
        )
        lote = (await self.session.execute(stmt)).scalars().first()
        if not lote:
            raise ValueError(f"Lote {lote_id} não encontrado neste tenant.")
        return lote

    def _montar_eventos_vacinacao(
        self,
        tarefa: TarefaCampo,
        dados: dict,
        animais_banco: dict[UUID, Animal],
        produto: Produto,
        dose: float,
        animais_ja_processados: set[UUID],
    ) -> list[EventoAnimal]:
        eventos: list[EventoAnimal] = []
        lote_id = self._uuid_from_value(dados.get("lote_id"))
        area_id = self._uuid_from_value(dados.get("area_id"))
        data_evento = self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em)
        for animal_id in self._normalizar_animais_ids(dados.get("animais_ids")):
            if animal_id in animais_ja_processados:
                continue
            animal_obj = animais_banco[animal_id]
            eventos.append(
                EventoAnimal(
                    tenant_id=self.tenant_id,
                    animal_id=animal_id,
                    tarefa_campo_id=tarefa.id,
                    operador_id=tarefa.operador_id,
                    tipo="VACINACAO",
                    data_evento=data_evento,
                    produto_id=produto.id,
                    observacoes=dados.get("observacoes"),
                    dados_extras={
                        "lote_id": str(lote_id) if lote_id else None,
                        "area_id": str(area_id) if area_id else None,
                        "dose": dose,
                        "unidade_medida": dados.get("unidade_medida"),
                        "via_aplicacao": dados.get("via_aplicacao"),
                    },
                )
            )
        return eventos

    def _normalizar_animais_ids(self, animais_ids: object) -> list[UUID]:
        if not isinstance(animais_ids, list):
            return []
        resultado: list[UUID] = []
        for item in animais_ids:
            valor = self._uuid_from_value(item)
            if valor:
                resultado.append(valor)
        return list(dict.fromkeys(resultado))

    def _uuid_from_value(self, value: object) -> UUID | None:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    def _validar_dose_vacinacao(self, value: object) -> float:
        try:
            dose = float(cast(Any, value))
        except (TypeError, ValueError):
            raise ValueError("dose é obrigatória para vacinação.")
        if dose <= 0:
            raise ValueError("Dose inválida. Deve ser maior que zero.")
        return dose

    async def _registrar_estoque_vacinacao(
        self,
        *,
        tarefa: TarefaCampo,
        produto: Produto,
        dose: float,
        unidade_medida: str,
        quantidade_animais: int,
    ) -> EstoqueMovimento | None:
        existente = await self._buscar_movimento_estoque_vacinacao(tarefa.id, produto.id)
        if existente:
            return existente
        if quantidade_animais <= 0:
            quantidade_animais = await self._contar_eventos_vacinacao(tarefa.id, produto.id)
        if quantidade_animais <= 0:
            return None
        if not tarefa.unidade_produtiva_id:
            raise BusinessRuleError("Tarefa de vacinação sem unidade produtiva para baixa de estoque.")
        self._validar_unidade_medida_vacinacao(produto, unidade_medida)
        quantidade_total = self._calcular_quantidade_consumida(dose, quantidade_animais)
        estoque_service = EstoqueService(self.session, self.tenant_id)
        production_unit = await self._resolver_production_unit_vacinacao(tarefa)
        motivo = f"{self.IDENTIFICADOR_ESTOQUE_VACINACAO} - tarefa {tarefa.id}"
        return await estoque_service.registrar_saida_insumo(
            produto_id=produto.id,
            quantidade=quantidade_total,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            origem_id=tarefa.id,
            origem_tipo=self.ORIGEM_ESTOQUE_VACINACAO,
            motivo=motivo,
            production_unit_id=production_unit.id if production_unit else None,
        )

    async def _registrar_custo_vacinacao(
        self,
        tarefa: TarefaCampo,
        movimento: EstoqueMovimento | None,
        quantidade_animais: int,
    ) -> CostAllocation | None:
        """Registra a apropriação econômica da vacinação quando houver contexto válido.

        Args:
            tarefa: Tarefa de campo materializada.
            movimento: Movimento de estoque gerado pela vacinação.
            quantidade_animais: Quantidade efetivamente processada.

        Returns:
            CostAllocation criada ou `None` quando a apropriação não puder ser resolvida.
        """
        if movimento is None or quantidade_animais <= 0:
            return None
        if movimento.custo_total is None and movimento.custo_unitario is None:
            return None
        production_unit = await self._resolver_production_unit_vacinacao(tarefa)
        if production_unit is None:
            return None
        if await self._custo_vacinacao_existente(tarefa.id, production_unit.id):
            return None
        amount = self._calcular_custo_vacinacao(movimento)
        if amount <= 0:
            return None
        return await registrar_cost_allocation(
            self.session,
            tenant_id=self.tenant_id,
            production_unit_id=production_unit.id,
            source=self.ORIGEM_ESTOQUE_VACINACAO,
            source_id=tarefa.id,
            inventory_movement_id=movimento.id,
            cost_category="SANITARIO",
            amount=amount,
            allocation_date=(tarefa.concluida_em or datetime.utcnow()).date(),
            allocation_method="DIRECT",
            allocation_basis=float(quantidade_animais),
        )

    async def _resolver_production_unit_vacinacao(self, tarefa: TarefaCampo) -> ProductionUnit | None:
        """Resolve a unidade de produção elegível para a apropriação da vacinação.

        Args:
            tarefa: Tarefa de campo sincronizada.

        Returns:
            ProductionUnit correspondente ao contexto da tarefa ou `None`.
        """
        area_id = tarefa.area_rural_id or self._uuid_from_value((tarefa.dados or {}).get("area_id"))
        if area_id is None:
            return None
        stmt = (
            select(ProductionUnit)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.area_id == area_id,
                ProductionUnit.status != "CANCELADA",
            )
            .order_by(ProductionUnit.data_inicio.desc().nullslast(), ProductionUnit.created_at.desc())
        )
        return (await self.session.execute(stmt.limit(1))).scalars().first()

    async def _custo_vacinacao_existente(self, tarefa_campo_id: UUID, production_unit_id: UUID) -> bool:
        stmt = select(CostAllocation.id).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source == self.ORIGEM_ESTOQUE_VACINACAO,
            CostAllocation.source_id == tarefa_campo_id,
            CostAllocation.production_unit_id == production_unit_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    def _calcular_custo_vacinacao(self, movimento: EstoqueMovimento) -> float:
        custo_total = movimento.custo_total
        if custo_total is not None and float(custo_total) > 0:
            return round(abs(float(custo_total)), 2)
        if movimento.custo_unitario is None:
            return 0.0
        return round(abs(float(movimento.quantidade)) * float(movimento.custo_unitario), 2)

    async def _buscar_movimento_estoque_vacinacao(
        self,
        tarefa_campo_id: UUID,
        produto_id: UUID,
    ) -> EstoqueMovimento | None:
        stmt = select(EstoqueMovimento).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.origem_id == tarefa_campo_id,
            EstoqueMovimento.produto_id == produto_id,
            (
                (EstoqueMovimento.origem == self.ORIGEM_ESTOQUE_VACINACAO)
                | (
                    (EstoqueMovimento.origem == "MANUAL")
                    & (EstoqueMovimento.observacoes.ilike(f"%{self.IDENTIFICADOR_ESTOQUE_VACINACAO}%"))
                )
            ),
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _contar_eventos_vacinacao(self, tarefa_campo_id: UUID, produto_id: UUID) -> int:
        stmt = select(func.count(EventoAnimal.id)).where(
            EventoAnimal.tenant_id == self.tenant_id,
            EventoAnimal.tarefa_campo_id == tarefa_campo_id,
            EventoAnimal.tipo == "VACINACAO",
            EventoAnimal.produto_id == produto_id,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    def _validar_unidade_medida_vacinacao(self, produto: Produto, unidade_medida: str) -> None:
        informada = (unidade_medida or "").strip().upper()
        if not informada:
            raise ValueError("unidade_medida é obrigatória para vacinação.")
        produto_uom = (produto.unidade_medida or "").strip().upper()
        if produto_uom and produto_uom != informada:
            raise ValueError(
                f"unidade_medida '{informada}' divergente da unidade do produto '{produto.unidade_medida}'."
            )

    def _calcular_quantidade_consumida(self, dose: float, quantidade_animais: int) -> float:
        return round(dose * quantidade_animais, 6)

    def _resolver_data_evento(self, valor: object, fallback: datetime | None) -> date:
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str):
            try:
                return datetime.fromisoformat(valor[:10]).date()
            except ValueError:
                pass
        if fallback:
            return fallback.date()
        return date.today()

    async def _publish_sync_failure_event(
        self,
        *,
        tarefa: TarefaCampo,
        erro: str,
        origem: str,
        status: str,
    ) -> None:
        evento = DomainEvent(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            domain=Domain.FIELD,
            event_type="campo.sync.falha",
            source_type="CAMPO_SYNC_FALHA",
            entity_type="sync_campo",
            entity_id=tarefa.id,
            correlation_id=self._uuid_from_value(tarefa.client_id),
            metadata={
                "error_type": "SYNC_PROCESSING_ERROR",
                "error_message": erro,
                "origin": origem,
                "local_id": str(tarefa.id),
                "status": status,
            },
        )
        await publish_domain_event_safe(
            evento,
            session=self.session,
            logger_context={"component": "pecuaria_sync_service"},
        )

    async def _publish_vacinacao_registrada_event(
        self,
        *,
        tarefa: TarefaCampo,
        dados: dict,
        animais_ids: list[UUID],
        produto: Produto,
        dose: float,
    ) -> None:
        evento = DomainEvent(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=tarefa.unidade_produtiva_id,
            domain=Domain.LIVESTOCK,
            event_type="pecuaria.vacinacao.registrada",
            source_type="PECUARIA_VACINACAO_REGISTRADA",
            entity_type="tarefa_campo",
            entity_id=tarefa.id,
            correlation_id=self._uuid_from_value(tarefa.client_id),
            metadata={
                "tarefa_campo_id": str(tarefa.id),
                "lote_id": str(self._uuid_from_value(dados.get("lote_id"))) if self._uuid_from_value(dados.get("lote_id")) else None,
                "animal_id": str(animais_ids[0]) if animais_ids else None,
                "animal_count": len(animais_ids),
                "produto_id": str(produto.id),
                "produto_nome": getattr(produto, "nome", None),
                "dose": dose,
                "unidade_medida": dados.get("unidade_medida"),
                "via_aplicacao": dados.get("via_aplicacao"),
                "data_aplicacao": self._resolver_data_evento(dados.get("data_evento"), tarefa.concluida_em).isoformat(),
            },
        )
        await publish_domain_event_safe(
            evento,
            session=self.session,
            logger_context={"component": "pecuaria_sync_service"},
        )

    def _resultado_erro(self, tarefa_campo_id: UUID, total_recebido: int, erros: list[str]) -> ManejoSyncResult:
        return ManejoSyncResult(
            status="ERROR",
            total_recebido=total_recebido,
            total_processado=0,
            total_ignorados=0,
            erros=erros,
            tarefa_campo_id=tarefa_campo_id,
        )

    async def _persistir_resultado(self, tarefa_campo_id: UUID, res: ManejoSyncResult) -> None:
        try:
            tarefa_banco = await self.session.get(TarefaCampo, tarefa_campo_id)
            if tarefa_banco:
                d = dict(tarefa_banco.dados or {})
                d["sync_pecuaria"] = {
                    "status": res.status,
                    "total_processado": res.total_processado,
                    "erros": res.erros,
                    "data_processamento": datetime.utcnow().isoformat(),
                }
                tarefa_banco.dados = d
                await self.session.commit()
        except Exception:
            await self.session.rollback()
