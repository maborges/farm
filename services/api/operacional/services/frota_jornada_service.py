from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo, CultivoArea
from agricola.safras.models import Safra
from agricola.safras.models import SafraTalhao
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from operacional.models.frota import JornadaEquipamento
from operacional.schemas.frota_jornada import (
    FrotaJornadaCancelarRequest,
    FrotaJornadaCreate,
    FrotaJornadaDetailResponse,
    FrotaJornadaFinalizarRequest,
    FrotaJornadaItem,
    FrotaJornadaListResponse,
    FrotaJornadaResumo,
    FrotaJornadaUpdate,
)
from operacional.services.frota_custo_service import FrotaCustoService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from operacional.services.frota_disponibilidade_service import FrotaDisponibilidadeService


class FrotaJornadaService(FrotaDashboardService):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(session, tenant_id)

    async def listar_jornadas(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        equipamento_id: uuid.UUID | None = None,
        status: str | None = None,
        periodo_dias: int | None = None,
    ) -> FrotaJornadaListResponse:
        agora = datetime.now(timezone.utc)
        jornadas = await self._buscar_jornadas(
            unidade_produtiva_id=unidade_produtiva_id,
            equipamento_id=equipamento_id,
            status=status,
            periodo_dias=periodo_dias,
        )
        itens = await self._serializar_jornadas(jornadas, unidade_produtiva_id)
        return FrotaJornadaListResponse(
            resumo=FrotaJornadaResumo(
                total=len(itens),
                abertas=sum(1 for item in itens if item.status == "ABERTA"),
                finalizadas=sum(1 for item in itens if item.status == "FINALIZADA"),
                canceladas=sum(1 for item in itens if item.status == "CANCELADA"),
                em_uso=sum(1 for item in itens if item.status == "ABERTA"),
                horas_trabalhadas=round(
                    sum(float(item.horas_trabalhadas or 0.0) for item in itens if item.status == "FINALIZADA"),
                    2,
                ),
                km_trabalhados=round(
                    sum(float(item.km_trabalhados or 0.0) for item in itens if item.status == "FINALIZADA"),
                    2,
                ),
            ),
            jornadas=itens,
            gerado_em=agora,
        )

    async def criar_jornada(self, dados: FrotaJornadaCreate) -> FrotaJornadaDetailResponse:
        equipamento = await self._obter_equipamento(dados.equipamento_id, dados.unidade_produtiva_id)
        await self._validar_abertura(equipamento.id, dados.unidade_produtiva_id)
        unidade_produtiva_id = dados.unidade_produtiva_id or equipamento.unidade_produtiva_id
        await self._validar_contexto_agricola(
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
        )

        jornada = JornadaEquipamento(
            tenant_id=self.tenant_id,
            equipamento_id=equipamento.id,
            operador_id=dados.operador_id,
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            tipo_operacao=dados.tipo_operacao.strip(),
            data_inicio=dados.data_inicio,
            horimetro_inicial=dados.horimetro_inicial if dados.horimetro_inicial is not None else equipamento.horimetro_atual,
            km_inicial=dados.km_inicial if dados.km_inicial is not None else equipamento.km_atual,
            status="ABERTA",
            observacoes=dados.observacoes,
        )
        self.session.add(jornada)
        await self.session.commit()
        await self.session.refresh(jornada)
        return await self.obter_jornada(jornada.id)

    async def obter_jornada(self, jornada_id: uuid.UUID) -> FrotaJornadaDetailResponse:
        jornada = await self._get_or_fail(jornada_id)
        itens = await self._serializar_jornadas([jornada], jornada.unidade_produtiva_id)
        return FrotaJornadaDetailResponse(jornada=itens[0], gerado_em=datetime.now(timezone.utc))

    async def atualizar_jornada(self, jornada_id: uuid.UUID, dados: FrotaJornadaUpdate) -> FrotaJornadaDetailResponse:
        jornada = await self._get_or_fail(jornada_id)
        if jornada.status != "ABERTA":
            raise BusinessRuleError("Somente jornadas abertas podem ser atualizadas.")

        if dados.unidade_produtiva_id is not None:
            await self._obter_equipamento(jornada.equipamento_id, dados.unidade_produtiva_id)
            jornada.unidade_produtiva_id = dados.unidade_produtiva_id
        if dados.operador_id is not None:
            jornada.operador_id = dados.operador_id
        if dados.safra_id is not None:
            jornada.safra_id = dados.safra_id
        if dados.talhao_id is not None:
            jornada.talhao_id = dados.talhao_id
        if dados.tipo_operacao is not None:
            jornada.tipo_operacao = dados.tipo_operacao.strip()
        if dados.data_inicio is not None:
            if jornada.data_fim is not None and dados.data_inicio > jornada.data_fim:
                raise BusinessRuleError("data_inicio não pode ser posterior a data_fim.")
            jornada.data_inicio = dados.data_inicio
        if dados.horimetro_inicial is not None:
            jornada.horimetro_inicial = dados.horimetro_inicial
        if dados.km_inicial is not None:
            jornada.km_inicial = dados.km_inicial
        if dados.observacoes is not None:
            jornada.observacoes = dados.observacoes

        await self._validar_contexto_agricola(
            unidade_produtiva_id=jornada.unidade_produtiva_id,
            safra_id=jornada.safra_id,
            talhao_id=jornada.talhao_id,
        )
        self._validar_leituras(
            jornada.horimetro_inicial,
            jornada.horimetro_final,
            jornada.km_inicial,
            jornada.km_final,
        )
        await self.session.commit()
        await self.session.refresh(jornada)
        return await self.obter_jornada(jornada.id)

    async def finalizar_jornada(
        self,
        jornada_id: uuid.UUID,
        dados: FrotaJornadaFinalizarRequest,
    ) -> FrotaJornadaDetailResponse:
        jornada = await self._get_or_fail(jornada_id)
        if jornada.status != "ABERTA":
            raise BusinessRuleError("Somente jornadas abertas podem ser finalizadas.")
        if dados.data_fim < jornada.data_inicio:
            raise BusinessRuleError("data_fim deve ser maior ou igual a data_inicio.")

        jornada.data_fim = dados.data_fim
        jornada.horimetro_final = dados.horimetro_final if dados.horimetro_final is not None else jornada.horimetro_final
        jornada.km_final = dados.km_final if dados.km_final is not None else jornada.km_final
        jornada.status = "FINALIZADA"
        if dados.observacoes is not None:
            jornada.observacoes = dados.observacoes

        self._validar_leituras(
            jornada.horimetro_inicial,
            jornada.horimetro_final,
            jornada.km_inicial,
            jornada.km_final,
        )

        equipamento = await self._obter_equipamento(jornada.equipamento_id, jornada.unidade_produtiva_id)
        if jornada.horimetro_final is not None:
            equipamento.horimetro_atual = jornada.horimetro_final
        if jornada.km_final is not None:
            equipamento.km_atual = jornada.km_final

        await self.session.commit()
        await self.session.refresh(jornada)
        return await self.obter_jornada(jornada.id)

    async def cancelar_jornada(
        self,
        jornada_id: uuid.UUID,
        dados: FrotaJornadaCancelarRequest | None = None,
    ) -> FrotaJornadaDetailResponse:
        jornada = await self._get_or_fail(jornada_id)
        if jornada.status != "ABERTA":
            raise BusinessRuleError("Somente jornadas abertas podem ser canceladas.")
        jornada.status = "CANCELADA"
        jornada.data_fim = datetime.now(timezone.utc)
        if dados and dados.observacoes:
            jornada.observacoes = dados.observacoes
        await self.session.commit()
        await self.session.refresh(jornada)
        return await self.obter_jornada(jornada.id)

    async def _validar_abertura(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> None:
        aberta = await self._buscar_jornada_aberta_por_equipamento(equipamento_id)
        if aberta:
            raise BusinessRuleError("Já existe uma jornada aberta para este equipamento.")

        disponibilidade = await FrotaDisponibilidadeService(self.session, self.tenant_id).obter_disponibilidade_equipamento(
            equipamento_id=equipamento_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        if disponibilidade.equipamento.status_operacional != "DISPONIVEL":
            raise BusinessRuleError(
                disponibilidade.equipamento.motivo_status
                or "Equipamento indisponível para abertura de jornada."
            )

    async def _buscar_jornadas(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
        equipamento_id: uuid.UUID | None = None,
        status: str | None = None,
        periodo_dias: int | None = None,
    ) -> list[JornadaEquipamento]:
        stmt = select(JornadaEquipamento).where(JornadaEquipamento.tenant_id == self.tenant_id)
        if unidade_produtiva_id:
            stmt = stmt.where(JornadaEquipamento.unidade_produtiva_id == unidade_produtiva_id)
        if equipamento_id:
            stmt = stmt.where(JornadaEquipamento.equipamento_id == equipamento_id)
        if status:
            stmt = stmt.where(JornadaEquipamento.status == status)
        if periodo_dias:
            data_corte = datetime.now(timezone.utc) - timedelta(days=periodo_dias)
            stmt = stmt.where(JornadaEquipamento.data_inicio >= data_corte)
        stmt = stmt.order_by(JornadaEquipamento.data_inicio.desc(), JornadaEquipamento.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _buscar_jornada_aberta_por_equipamento(self, equipamento_id: uuid.UUID) -> JornadaEquipamento | None:
        stmt = select(JornadaEquipamento).where(
            JornadaEquipamento.tenant_id == self.tenant_id,
            JornadaEquipamento.equipamento_id == equipamento_id,
            JornadaEquipamento.status == "ABERTA",
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _obter_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> Equipamento:
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        for equipamento in equipamentos:
            if equipamento.id == equipamento_id:
                return equipamento
        raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")

    async def _get_or_fail(self, jornada_id: uuid.UUID) -> JornadaEquipamento:
        stmt = select(JornadaEquipamento).where(
            JornadaEquipamento.id == jornada_id,
            JornadaEquipamento.tenant_id == self.tenant_id,
        )
        jornada = (await self.session.execute(stmt)).scalar_one_or_none()
        if jornada is None:
            raise EntityNotFoundError("Jornada não encontrada para o tenant informado.")
        return jornada

    async def _serializar_jornadas(
        self,
        jornadas: list[JornadaEquipamento],
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[FrotaJornadaItem]:
        if not jornadas:
            return []

        equipamento_ids = [item.equipamento_id for item in jornadas]
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        equipamentos_map = {item.id: item for item in equipamentos if item.id in equipamento_ids}

        pessoas_ids = [item.operador_id for item in jornadas if item.operador_id]
        unidades_ids = [item.unidade_produtiva_id for item in jornadas if item.unidade_produtiva_id]
        safra_ids = [item.safra_id for item in jornadas if item.safra_id]
        talhao_ids = [item.talhao_id for item in jornadas if item.talhao_id]

        pessoas_map = await self._listar_pessoas(pessoas_ids)
        unidades_map = await self._listar_unidades(unidades_ids)
        safras_map = await self._listar_safras(safra_ids)
        talhoes_map = await self._listar_talhoes(talhao_ids)

        custos = await FrotaCustoService(self.session, self.tenant_id).obter_custos(
            unidade_produtiva_id=unidade_produtiva_id,
        )
        custos_map = {item.equipamento_id: item for item in custos.equipamentos}

        resposta: list[FrotaJornadaItem] = []
        for jornada in jornadas:
            equipamento = equipamentos_map.get(jornada.equipamento_id)
            custo_item = custos_map.get(jornada.equipamento_id)
            duracao_horas = self._calcular_duracao_horas(jornada.data_inicio, jornada.data_fim)
            horas_trabalhadas = self._calcular_delta(jornada.horimetro_inicial, jornada.horimetro_final)
            km_trabalhados = self._calcular_delta(jornada.km_inicial, jornada.km_final)
            custo_estimado, metrica_custo = self._calcular_custo_estimado_jornada(
                horas_trabalhadas,
                km_trabalhados,
                custo_item.custo_por_hora if custo_item else None,
                custo_item.custo_por_km if custo_item else None,
            )

            resposta.append(
                FrotaJornadaItem(
                    id=jornada.id,
                    equipamento_id=jornada.equipamento_id,
                    equipamento_nome=equipamento.nome if equipamento else "Equipamento",
                    equipamento_tipo=equipamento.tipo if equipamento else "N/D",
                    operador_id=jornada.operador_id,
                    operador_nome=pessoas_map.get(jornada.operador_id) if jornada.operador_id else None,
                    unidade_produtiva_id=jornada.unidade_produtiva_id,
                    unidade_produtiva_nome=unidades_map.get(jornada.unidade_produtiva_id) if jornada.unidade_produtiva_id else None,
                    safra_id=jornada.safra_id,
                    safra_nome=safras_map.get(jornada.safra_id) if jornada.safra_id else None,
                    talhao_id=jornada.talhao_id,
                    talhao_nome=talhoes_map.get(jornada.talhao_id) if jornada.talhao_id else None,
                    tipo_operacao=jornada.tipo_operacao,
                    data_inicio=jornada.data_inicio,
                    data_fim=jornada.data_fim,
                    horimetro_inicial=jornada.horimetro_inicial,
                    horimetro_final=jornada.horimetro_final,
                    km_inicial=jornada.km_inicial,
                    km_final=jornada.km_final,
                    status=jornada.status,  # type: ignore[arg-type]
                    observacoes=jornada.observacoes,
                    duracao_horas=duracao_horas,
                    horas_trabalhadas=horas_trabalhadas,
                    km_trabalhados=km_trabalhados,
                    custo_estimado=custo_estimado,
                    metrica_custo=metrica_custo,
                    created_at=jornada.created_at,
                    updated_at=jornada.updated_at,
                )
            )
        return resposta

    async def _listar_pessoas(self, pessoa_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not pessoa_ids:
            return {}
        stmt = select(Pessoa).where(Pessoa.tenant_id == self.tenant_id, Pessoa.id.in_(pessoa_ids))
        pessoas = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item.nome_exibicao for item in pessoas}

    async def _listar_unidades(self, unidade_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not unidade_ids:
            return {}
        stmt = select(UnidadeProdutiva).where(
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.id.in_(unidade_ids),
        )
        unidades = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item.nome for item in unidades}

    async def _listar_safras(self, safra_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not safra_ids:
            return {}
        stmt = select(Safra).where(Safra.tenant_id == self.tenant_id, Safra.id.in_(safra_ids))
        safras = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: " / ".join(part for part in [item.ano_safra, item.cultura] if part) for item in safras}

    async def _listar_talhoes(self, talhao_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not talhao_ids:
            return {}
        stmt = select(AreaRural).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.id.in_(talhao_ids),
        )
        talhoes = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item.nome for item in talhoes}

    async def _validar_contexto_agricola(
        self,
        unidade_produtiva_id: uuid.UUID | None,
        safra_id: uuid.UUID | None,
        talhao_id: uuid.UUID | None,
    ) -> None:
        if safra_id is not None:
            stmt_safra = select(Safra.id).where(
                Safra.id == safra_id,
                Safra.tenant_id == self.tenant_id,
            )
            safra_existe = (await self.session.execute(stmt_safra)).scalar_one_or_none()
            if safra_existe is None:
                raise BusinessRuleError("Safra não encontrada para o tenant informado.")

        talhao: AreaRural | None = None
        if talhao_id is not None:
            stmt_talhao = select(AreaRural).where(
                AreaRural.id == talhao_id,
                AreaRural.tenant_id == self.tenant_id,
            )
            talhao = (await self.session.execute(stmt_talhao)).scalar_one_or_none()
            if talhao is None:
                raise BusinessRuleError("Talhão não encontrado para o tenant informado.")
            if unidade_produtiva_id is not None and talhao.unidade_produtiva_id != unidade_produtiva_id:
                raise BusinessRuleError("Talhão informado não pertence à unidade produtiva da jornada.")

        if safra_id is None or talhao_id is None:
            return

        stmt_safra_talhao = select(SafraTalhao.id).where(
            SafraTalhao.tenant_id == self.tenant_id,
            SafraTalhao.safra_id == safra_id,
            SafraTalhao.area_id == talhao_id,
        )
        vinculo_legado = (await self.session.execute(stmt_safra_talhao)).scalar_one_or_none()
        if vinculo_legado is not None:
            return

        stmt_cultivo_area = (
            select(CultivoArea.id)
            .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
            .where(
                CultivoArea.tenant_id == self.tenant_id,
                Cultivo.tenant_id == self.tenant_id,
                Cultivo.safra_id == safra_id,
                CultivoArea.area_id == talhao_id,
            )
        )
        vinculo_cultivo = (await self.session.execute(stmt_cultivo_area)).scalar_one_or_none()
        if vinculo_cultivo is None:
            raise BusinessRuleError("Talhão informado não está vinculado à safra selecionada.")

    @staticmethod
    def _validar_leituras(
        horimetro_inicial: float | None,
        horimetro_final: float | None,
        km_inicial: float | None,
        km_final: float | None,
    ) -> None:
        if horimetro_inicial is not None and horimetro_final is not None and horimetro_final < horimetro_inicial:
            raise BusinessRuleError("Horímetro final deve ser maior ou igual ao inicial.")
        if km_inicial is not None and km_final is not None and km_final < km_inicial:
            raise BusinessRuleError("KM final deve ser maior ou igual ao inicial.")

    @staticmethod
    def _calcular_delta(inicial: float | None, final: float | None) -> float | None:
        if inicial is None or final is None:
            return None
        if final < inicial:
            return None
        return round(final - inicial, 2)

    @staticmethod
    def _calcular_duracao_horas(data_inicio: datetime, data_fim: datetime | None) -> float | None:
        if data_fim is None:
            return None
        return round(max((data_fim - data_inicio).total_seconds(), 0) / 3600, 2)

    @staticmethod
    def _calcular_custo_estimado_jornada(
        horas_trabalhadas: float | None,
        km_trabalhados: float | None,
        custo_por_hora: float | None,
        custo_por_km: float | None,
    ) -> tuple[float | None, str]:
        if horas_trabalhadas is not None and horas_trabalhadas > 0 and custo_por_hora is not None:
            return round(horas_trabalhadas * custo_por_hora, 2), "HORA"
        if km_trabalhados is not None and km_trabalhados > 0 and custo_por_km is not None:
            return round(km_trabalhados * custo_por_km, 2), "KM"
        return None, "INDISPONIVEL"
