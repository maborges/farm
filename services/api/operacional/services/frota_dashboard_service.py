from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.safras.models import Safra
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.propriedades.models import AreaRural
from core.cadastros.equipamentos.models import Equipamento
from core.models.unidade_produtiva import UnidadeProdutiva
from operacional.models.abastecimento import Abastecimento
from operacional.models.documento_equipamento import DocumentoEquipamento
from operacional.models.frota import JornadaEquipamento, OrdemServico, PlanoManutencao, RegistroManutencao
from operacional.schemas.frota_dashboard import (
    FrotaDashboardEquipamentoItem,
    FrotaDashboardJornadaItem,
    FrotaDashboardRankingItem,
    FrotaDashboardResponse,
    FrotaDashboardResumo,
    FrotaDashboardRiscoItem,
    FrotaDashboardUltimoAbastecimento,
)


@dataclass
class _MaintenanceStatus:
    status: str
    overdue_count: int = 0
    upcoming_count: int = 0


class FrotaDashboardService:
    SEM_ABASTECIMENTO_DIAS = 30
    OS_ABERTA_DIAS = 7
    PROXIMIDADE_MANUTENCAO = 0.1
    PROXIMIDADE_MANUTENCAO_DIAS_MIN = 3
    PROXIMIDADE_MANUTENCAO_DIAS_MAX = 15
    RANKING_LIMIT = 5
    ULTIMOS_ABASTECIMENTOS_LIMIT = 10

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def obter_dashboard(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDashboardResponse:
        agora = datetime.now(timezone.utc)
        hoje = agora.date()

        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        if not equipamentos:
            return FrotaDashboardResponse(
                resumo=FrotaDashboardResumo(
                    total_equipamentos=0,
                    ativos=0,
                    parados=0,
                    em_uso=0,
                    em_manutencao=0,
                    em_risco=0,
                    os_abertas=0,
                    manutencoes_vencidas=0,
                    manutencoes_proximas=0,
                    documentos_vencidos=0,
                    custo_total_acumulado=0.0,
                ),
                equipamentos=[],
                ranking_maior_custo=[],
                alertas_operacionais=[],
                ultimos_abastecimentos=[],
                ultimas_jornadas=[],
                gerado_em=agora,
            )

        equipamento_ids = [equipamento.id for equipamento in equipamentos]

        # SQL-based aggregations for costs and counts
        custo_abastecimento_por_equipamento = await self._obter_custo_abastecimento_sql(equipamento_ids)
        custo_manutencao_por_equipamento = await self._obter_custo_manutencao_sql(equipamento_ids)
        os_abertas_counts = await self._obter_os_abertas_count_sql(equipamento_ids)
        total_os_abertas = sum(os_abertas_counts.values())

        # Fetch only necessary data for complex logic (maintenance status, alerts)
        registros_manutencao = await self._listar_registros_manutencao(equipamento_ids)
        planos = await self._listar_planos(equipamento_ids)
        documentos = await self._listar_documentos(equipamento_ids)
        jornadas = await self._listar_jornadas(equipamento_ids)
        # Fetch only the latest abastecimento per equipment instead of all
        ultimos_abastecimentos_map = await self._obter_ultimos_abastecimentos_sql(equipamento_ids)

        jornadas_abertas_por_equipamento: dict[uuid.UUID, JornadaEquipamento] = {
            j.equipamento_id: j for j in jornadas if j.status == "ABERTA"
        }

        planos_por_equipamento: dict[uuid.UUID, list[PlanoManutencao]] = defaultdict(list)
        for plano in planos:
            planos_por_equipamento[plano.equipamento_id].append(plano)

        documentos_por_equipamento: dict[uuid.UUID, list[DocumentoEquipamento]] = defaultdict(list)
        for documento in documentos:
            documentos_por_equipamento[documento.equipamento_id].append(documento)

        maintenance_status_map: dict[uuid.UUID, _MaintenanceStatus] = {}
        total_manutencoes_vencidas = 0
        total_manutencoes_proximas = 0
        total_documentos_vencidos = 0

        equipamento_items: list[FrotaDashboardEquipamentoItem] = []
        alertas_operacionais: list[FrotaDashboardRiscoItem] = []
        custo_total_acumulado = 0.0
        equipamentos_em_risco = 0
        equipamentos_em_uso = len(jornadas_abertas_por_equipamento)

        custo_total_por_equipamento: dict[uuid.UUID, float] = {}
        for equipamento in equipamentos:
            equipamento_id = equipamento.id
            c_abast = round(custo_abastecimento_por_equipamento.get(equipamento_id, 0.0), 2)
            c_manut = round(custo_manutencao_por_equipamento.get(equipamento_id, 0.0), 2)
            c_total = round(c_abast + c_manut, 2)
            custo_total_por_equipamento[equipamento_id] = c_total
            custo_total_acumulado += c_total

        media_custo = custo_total_acumulado / len(equipamentos) if equipamentos else 0.0

        for equipamento in equipamentos:
            equipamento_id = equipamento.id
            last_abastecimento = ultimos_abastecimentos_map.get(equipamento_id)
            maintenance_status = self._calcular_status_manutencao(
                equipamento=equipamento,
                planos=planos_por_equipamento[equipamento_id],
            )
            maintenance_status_map[equipamento_id] = maintenance_status
            total_manutencoes_vencidas += maintenance_status.overdue_count
            total_manutencoes_proximas += maintenance_status.upcoming_count

            documentos_vencidos = self._contar_documentos_vencidos(
                documentos_por_equipamento[equipamento_id],
                hoje,
            )
            total_documentos_vencidos += documentos_vencidos

            riscos: list[str] = []
            custo_total = custo_total_por_equipamento[equipamento_id]
            dias_sem_abastecimento = self._dias_sem_abastecimento(last_abastecimento, agora)

            if self._tem_risco_sem_abastecimento(equipamento, dias_sem_abastecimento):
                riscos.append("SEM_ABASTECIMENTO_RECENTE")
                alertas_operacionais.append(
                    FrotaDashboardRiscoItem(
                        tipo="SEM_ABASTECIMENTO_RECENTE",
                        titulo="Sem abastecimento recente",
                        severidade="warning",
                        equipamento_id=equipamento_id,
                        equipamento_nome=equipamento.nome,
                        detalhe=(
                            f"Sem registro de abastecimento há {dias_sem_abastecimento} dias."
                            if dias_sem_abastecimento is not None
                            else "Sem registro de abastecimento para o equipamento."
                        ),
                        dias_desde_evento=dias_sem_abastecimento,
                        data_referencia=last_abastecimento.data if last_abastecimento else None,
                    )
                )

            # Check for old open OS (SQL optimized)
            os_abertas_antigas = await self._obter_os_abertas_antigas_sql(equipamento_id, agora)
            for ordem_antiga in os_abertas_antigas:
                riscos.append("OS_ABERTA_ANTIGA")
                dias_aberta = max((agora - ordem_antiga.data_abertura).days, 0)
                alertas_operacionais.append(
                    FrotaDashboardRiscoItem(
                        tipo="OS_ABERTA_ANTIGA",
                        titulo="OS aberta há muitos dias",
                        severidade="danger",
                        equipamento_id=equipamento_id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"OS {ordem_antiga.numero_os} está aberta há {dias_aberta} dias.",
                        dias_desde_evento=dias_aberta,
                        data_referencia=ordem_antiga.data_abertura,
                    )
                )

            if maintenance_status.status == "VENCIDA":
                riscos.append("MANUTENCAO_VENCIDA")
                alertas_operacionais.append(
                    FrotaDashboardRiscoItem(
                        tipo="MANUTENCAO_VENCIDA",
                        titulo="Manutenção vencida",
                        severidade="danger",
                        equipamento_id=equipamento_id,
                        equipamento_nome=equipamento.nome,
                        detalhe="Há plano de manutenção vencido pelo horímetro/km atual.",
                    )
                )

            if documentos_vencidos > 0:
                riscos.append("DOCUMENTO_VENCIDO")
                alertas_operacionais.append(
                    FrotaDashboardRiscoItem(
                        tipo="DOCUMENTO_VENCIDO",
                        titulo="Documento vencido",
                        severidade="danger",
                        equipamento_id=equipamento_id,
                        equipamento_nome=equipamento.nome,
                        detalhe=f"{documentos_vencidos} documento(s) vencido(s) vinculado(s) ao equipamento.",
                    )
                )

            if media_custo > 0 and custo_total > media_custo * 1.2:
                riscos.append("CUSTO_ACIMA_MEDIA")
                alertas_operacionais.append(
                    FrotaDashboardRiscoItem(
                        tipo="CUSTO_ACIMA_MEDIA",
                        titulo="Custo acima da média",
                        severidade="warning",
                        equipamento_id=equipamento_id,
                        equipamento_nome=equipamento.nome,
                        detalhe=(
                            f"Custo acumulado de R$ {custo_total:,.2f} acima da média da frota."
                        ).replace(",", "X").replace(".", ",").replace("X", "."),
                    )
                )

            if riscos:
                equipamentos_em_risco += 1

            equipamento_items.append(
                FrotaDashboardEquipamentoItem(
                    equipamento_id=equipamento_id,
                    nome=equipamento.nome,
                    tipo=equipamento.tipo,
                    status=self._normalizar_status(equipamento.status),
                    marca=equipamento.marca,
                    modelo=equipamento.modelo,
                    unidade_produtiva_id=equipamento.unidade_produtiva_id,
                    horimetro_atual=equipamento.horimetro_atual,
                    km_atual=equipamento.km_atual,
                    custo_total=round(custo_total, 2),
                    custo_abastecimento=round(custo_abastecimento_por_equipamento.get(equipamento_id, 0.0), 2),
                    custo_manutencao=round(custo_manutencao_por_equipamento.get(equipamento_id, 0.0), 2),
                    custo_por_hora=self._calcular_custo_por_hora(custo_total, equipamento.horimetro_atual),
                    custo_por_km=self._calcular_custo_por_km(custo_total, equipamento.km_atual),
                    jornada_aberta=equipamento_id in jornadas_abertas_por_equipamento,
                    os_abertas=os_abertas_counts.get(equipamento_id, 0),
                    manutencao_status=maintenance_status.status,  # type: ignore[arg-type]
                    documentos_vencidos=documentos_vencidos,
                    ultimo_abastecimento_em=last_abastecimento.data if last_abastecimento else None,
                    dias_sem_abastecimento=dias_sem_abastecimento,
                    risco_total=len(riscos),
                    riscos=riscos,  # type: ignore[arg-type]
                )
            )

        ranking = sorted(
            (
                FrotaDashboardRankingItem(
                    equipamento_id=equipamento.id,
                    equipamento_nome=equipamento.nome,
                    tipo=equipamento.tipo,
                    status=self._normalizar_status(equipamento.status),
                    custo_total=round(custo_total_por_equipamento[equipamento.id], 2),
                    custo_abastecimento=round(custo_abastecimento_por_equipamento.get(equipamento.id, 0.0), 2),
                    custo_manutencao=round(custo_manutencao_por_equipamento.get(equipamento.id, 0.0), 2),
                    os_abertas=os_abertas_counts.get(equipamento.id, 0),
                )
                for equipamento in equipamentos
            ),
            key=lambda item: item.custo_total,
            reverse=True,
        )[: self.RANKING_LIMIT]

        ultimos_abastecimentos = [
            FrotaDashboardUltimoAbastecimento(
                id=abastecimento.id,
                equipamento_id=abastecimento.equipamento_id,
                equipamento_nome=next(
                    equipamento.nome
                    for equipamento in equipamentos
                    if equipamento.id == abastecimento.equipamento_id
                ),
                data=abastecimento.data,
                tipo_combustivel=abastecimento.tipo_combustivel,
                litros=float(abastecimento.litros or 0.0),
                custo_total=float(abastecimento.custo_total or 0.0),
                horimetro_na_data=abastecimento.horimetro_na_data,
                km_na_data=abastecimento.km_na_data,
            )
            for abastecimento in (await self._listar_abastecimentos(equipamento_ids))[: self.ULTIMOS_ABASTECIMENTOS_LIMIT]
        ]

        ultimas_jornadas = await self._serializar_dashboard_jornadas(
            jornadas=sorted(jornadas, key=lambda item: item.data_inicio, reverse=True)[: self.ULTIMOS_ABASTECIMENTOS_LIMIT],
            custo_total_por_equipamento=custo_total_por_equipamento,
            equipamentos_map={item.id: item for item in equipamentos},
        )

        resumo = FrotaDashboardResumo(
            total_equipamentos=len(equipamentos),
            ativos=sum(1 for equipamento in equipamentos if self._normalizar_status(equipamento.status) == "ATIVO"),
            parados=sum(1 for equipamento in equipamentos if self._normalizar_status(equipamento.status) in {"INATIVO", "PARADO"}),
            em_uso=equipamentos_em_uso,
            em_manutencao=sum(
                1 for equipamento in equipamentos if self._normalizar_status(equipamento.status) == "EM_MANUTENCAO"
            ),
            em_risco=equipamentos_em_risco,
            os_abertas=total_os_abertas,
            manutencoes_vencidas=total_manutencoes_vencidas,
            manutencoes_proximas=total_manutencoes_proximas,
            documentos_vencidos=total_documentos_vencidos,
            custo_total_acumulado=round(custo_total_acumulado, 2),
        )

        return FrotaDashboardResponse(
            resumo=resumo,
            equipamentos=sorted(
                equipamento_items,
                key=lambda item: (item.risco_total, item.custo_total, item.nome),
                reverse=True,
            ),
            ranking_maior_custo=ranking,
            alertas_operacionais=sorted(
                alertas_operacionais,
                key=lambda item: (
                    1 if item.severidade == "danger" else 0,
                    item.dias_desde_evento or 0,
                ),
                reverse=True,
            ),
            ultimos_abastecimentos=ultimos_abastecimentos,
            ultimas_jornadas=ultimas_jornadas,
            gerado_em=agora,
        )

    async def _listar_equipamentos(
        self,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> list[Equipamento]:
        stmt = select(Equipamento).where(Equipamento.tenant_id == self.tenant_id)
        if unidade_produtiva_id:
            stmt = stmt.where(Equipamento.unidade_produtiva_id == unidade_produtiva_id)
        stmt = stmt.order_by(Equipamento.nome.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_abastecimentos(self, equipamento_ids: list[uuid.UUID]) -> list[Abastecimento]:
        stmt = (
            select(Abastecimento)
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Abastecimento.equipamento_id.in_(equipamento_ids),
            )
            .order_by(Abastecimento.data.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_ordens_servico(self, equipamento_ids: list[uuid.UUID]) -> list[OrdemServico]:
        stmt = (
            select(OrdemServico)
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
            )
            .order_by(OrdemServico.data_abertura.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_registros_manutencao(
        self,
        equipamento_ids: list[uuid.UUID],
    ) -> list[RegistroManutencao]:
        stmt = (
            select(RegistroManutencao)
            .where(RegistroManutencao.equipamento_id.in_(equipamento_ids))
            .order_by(RegistroManutencao.data_realizacao.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_planos(self, equipamento_ids: list[uuid.UUID]) -> list[PlanoManutencao]:
        stmt = select(PlanoManutencao).where(PlanoManutencao.equipamento_id.in_(equipamento_ids))
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_documentos(
        self,
        equipamento_ids: list[uuid.UUID],
    ) -> list[DocumentoEquipamento]:
        stmt = (
            select(DocumentoEquipamento)
            .where(
                DocumentoEquipamento.tenant_id == self.tenant_id,
                DocumentoEquipamento.equipamento_id.in_(equipamento_ids),
                DocumentoEquipamento.ativo == True,
            )
            .order_by(DocumentoEquipamento.data_vencimento.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_jornadas(
        self,
        equipamento_ids: list[uuid.UUID],
        status: str | None = None,
    ) -> list[JornadaEquipamento]:
        if not equipamento_ids:
            return []
        stmt = select(JornadaEquipamento).where(
            JornadaEquipamento.tenant_id == self.tenant_id,
            JornadaEquipamento.equipamento_id.in_(equipamento_ids),
        )
        if status:
            stmt = stmt.where(JornadaEquipamento.status == status)
        stmt = stmt.order_by(JornadaEquipamento.data_inicio.desc(), JornadaEquipamento.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def _obter_custo_abastecimento_sql(self, equipamento_ids: list[uuid.UUID]) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(Abastecimento.equipamento_id, func.sum(Abastecimento.custo_total))
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Abastecimento.equipamento_id.in_(equipamento_ids),
            )
            .group_by(Abastecimento.equipamento_id)
        )
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_custo_manutencao_sql(self, equipamento_ids: list[uuid.UUID]) -> dict[uuid.UUID, float]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(RegistroManutencao.equipamento_id, func.sum(RegistroManutencao.custo_total))
            .where(
                RegistroManutencao.tenant_id == self.tenant_id,
                RegistroManutencao.equipamento_id.in_(equipamento_ids),
            )
            .group_by(RegistroManutencao.equipamento_id)
        )
        result = await self.session.execute(stmt)
        return {row[0]: float(row[1] or 0.0) for row in result.all()}

    async def _obter_os_abertas_count_sql(self, equipamento_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not equipamento_ids:
            return {}
        stmt = (
            select(OrdemServico.equipamento_id, func.count(OrdemServico.id))
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id.in_(equipamento_ids),
                OrdemServico.status.in_({"ABERTA", "EM_EXECUCAO"}),
            )
            .group_by(OrdemServico.equipamento_id)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1] or 0) for row in result.all()}

    async def _obter_ultimos_abastecimentos_sql(self, equipamento_ids: list[uuid.UUID]) -> dict[uuid.UUID, Abastecimento]:
        if not equipamento_ids:
            return {}
        # This is slightly more complex in SQL (Last per group)
        # For simplicity and given small equipment lists (usually < 100), we can use a targeted query
        # But for true scale, we'd use a Window Function
        from sqlalchemy import over
        from sqlalchemy.orm import aliased

        subq = (
            select(
                Abastecimento,
                func.row_number().over(
                    partition_by=Abastecimento.equipamento_id,
                    order_by=Abastecimento.data.desc()
                ).label("rn")
            )
            .where(
                Abastecimento.tenant_id == self.tenant_id,
                Abastecimento.equipamento_id.in_(equipamento_ids)
            )
            .subquery()
        )
        
        abast_alias = aliased(Abastecimento, subq)
        stmt = select(abast_alias).where(subq.c.rn == 1)
        result = await self.session.execute(stmt)
        return {a.equipamento_id: a for a in result.scalars().all()}

    async def _obter_os_abertas_antigas_sql(self, equipamento_id: uuid.UUID, agora: datetime) -> list[OrdemServico]:
        stmt = (
            select(OrdemServico)
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id == equipamento_id,
                OrdemServico.status.in_({"ABERTA", "EM_EXECUCAO"}),
                OrdemServico.data_abertura < agora - timedelta(days=self.OS_ABERTA_DIAS)
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

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

    async def _serializar_dashboard_jornadas(
        self,
        jornadas: list[JornadaEquipamento],
        custo_total_por_equipamento: dict[uuid.UUID, float],
        equipamentos_map: dict[uuid.UUID, Equipamento],
    ) -> list[FrotaDashboardJornadaItem]:
        if not jornadas:
            return []
        pessoas_map = await self._listar_pessoas([item.operador_id for item in jornadas if item.operador_id])
        resposta: list[FrotaDashboardJornadaItem] = []
        for jornada in jornadas:
            equipamento = equipamentos_map.get(jornada.equipamento_id)
            custo_total = custo_total_por_equipamento.get(jornada.equipamento_id, 0.0)
            custo_por_hora = self._calcular_custo_por_hora(custo_total, equipamento.horimetro_atual if equipamento else None)
            custo_por_km = self._calcular_custo_por_km(custo_total, equipamento.km_atual if equipamento else None)
            horas_trabalhadas = self._calcular_delta(jornada.horimetro_inicial, jornada.horimetro_final)
            km_trabalhados = self._calcular_delta(jornada.km_inicial, jornada.km_final)
            custo_estimado, metrica_custo = self._calcular_custo_estimado_jornada(
                horas_trabalhadas,
                km_trabalhados,
                custo_por_hora,
                custo_por_km,
            )
            resposta.append(
                FrotaDashboardJornadaItem(
                    jornada_id=jornada.id,
                    equipamento_id=jornada.equipamento_id,
                    equipamento_nome=equipamento.nome if equipamento else "Equipamento",
                    operador_nome=pessoas_map.get(jornada.operador_id) if jornada.operador_id else None,
                    tipo_operacao=jornada.tipo_operacao,
                    data_inicio=jornada.data_inicio,
                    data_fim=jornada.data_fim,
                    status=jornada.status,  # type: ignore[arg-type]
                    duracao_horas=self._calcular_duracao_horas(jornada.data_inicio, jornada.data_fim),
                    horas_trabalhadas=horas_trabalhadas,
                    km_trabalhados=km_trabalhados,
                    custo_estimado=custo_estimado,
                    metrica_custo=metrica_custo,  # type: ignore[arg-type]
                )
            )
        return resposta

    @staticmethod
    def _normalizar_status(status: str | None) -> str:
        if status in {"EM_MANUTENCAO", "MANUTENCAO"}:
            return "EM_MANUTENCAO"
        if status in {"VENDIDO", "SUCATEADO"}:
            return "PARADO"
        return status or "INATIVO"

    @staticmethod
    def _obter_ultimo_abastecimento(abastecimentos: list[Abastecimento]) -> Abastecimento | None:
        return abastecimentos[0] if abastecimentos else None

    def _dias_sem_abastecimento(
        self,
        abastecimento: Abastecimento | None,
        agora: datetime,
    ) -> int | None:
        if not abastecimento:
            return None
        return max((agora - abastecimento.data).days, 0)

    def _tem_risco_sem_abastecimento(
        self,
        equipamento: Equipamento,
        dias_sem_abastecimento: int | None,
    ) -> bool:
        if self._normalizar_status(equipamento.status) != "ATIVO":
            return False
        if equipamento.combustivel in {"ELETRICO", "NAO_APLICAVEL"}:
            return False
        if dias_sem_abastecimento is None:
            return True
        return dias_sem_abastecimento > self.SEM_ABASTECIMENTO_DIAS

    def _obter_os_aberta_antiga(
        self,
        ordens_servico: list[OrdemServico],
        agora: datetime,
    ) -> OrdemServico | None:
        for ordem in ordens_servico:
            if ordem.status not in {"ABERTA", "EM_EXECUCAO"}:
                continue
            if (agora - ordem.data_abertura).days > self.OS_ABERTA_DIAS:
                return ordem
        return None

    def _calcular_status_manutencao(
        self,
        equipamento: Equipamento,
        planos: list[PlanoManutencao],
    ) -> _MaintenanceStatus:
        if not planos:
            return _MaintenanceStatus(status="SEM_PLANO")

        overdue_count = 0
        upcoming_count = 0

        for plano in planos:
            if plano.frequencia_dias and plano.frequencia_dias > 0:
                base_data = plano.ultimo_registro_data or plano.created_at
                if base_data is not None:
                    dias_restantes = (
                        base_data + timedelta(days=int(plano.frequencia_dias)) - datetime.now(timezone.utc)
                    ).total_seconds() / 86400
                    proximidade_dias = min(
                        max(int(round(float(plano.frequencia_dias) * self.PROXIMIDADE_MANUTENCAO)), self.PROXIMIDADE_MANUTENCAO_DIAS_MIN),
                        self.PROXIMIDADE_MANUTENCAO_DIAS_MAX,
                    )
                    if dias_restantes <= 0:
                        overdue_count += 1
                    elif dias_restantes <= proximidade_dias:
                        upcoming_count += 1

            if plano.frequencia_horas and plano.frequencia_horas > 0:
                usado_horas = float(equipamento.horimetro_atual or 0.0) - float(plano.ultimo_registro_horas or 0.0)
                restante_horas = float(plano.frequencia_horas) - usado_horas
                if restante_horas <= 0:
                    overdue_count += 1
                elif restante_horas <= float(plano.frequencia_horas) * self.PROXIMIDADE_MANUTENCAO:
                    upcoming_count += 1

            if plano.frequencia_km and plano.frequencia_km > 0:
                usado_km = float(equipamento.km_atual or 0.0) - float(plano.ultimo_registro_km or 0.0)
                restante_km = float(plano.frequencia_km) - usado_km
                if restante_km <= 0:
                    overdue_count += 1
                elif restante_km <= float(plano.frequencia_km) * self.PROXIMIDADE_MANUTENCAO:
                    upcoming_count += 1

        if overdue_count > 0:
            return _MaintenanceStatus(status="VENCIDA", overdue_count=overdue_count)
        if upcoming_count > 0:
            return _MaintenanceStatus(status="PROXIMA", upcoming_count=upcoming_count)
        return _MaintenanceStatus(status="OK")

    @staticmethod
    def _contar_documentos_vencidos(
        documentos: list[DocumentoEquipamento],
        hoje: date,
    ) -> int:
        return sum(
            1
            for documento in documentos
            if documento.data_vencimento is not None and documento.data_vencimento < hoje
        )

    @staticmethod
    def _calcular_custo_por_hora(custo_total: float, horimetro_atual: float | None) -> float | None:
        if horimetro_atual is None or horimetro_atual <= 0:
            return None
        return round(custo_total / horimetro_atual, 2)

    @staticmethod
    def _calcular_custo_por_km(custo_total: float, km_atual: float | None) -> float | None:
        if km_atual is None or km_atual <= 0:
            return None
        return round(custo_total / km_atual, 2)

    @staticmethod
    def _calcular_delta(inicial: float | None, final: float | None) -> float | None:
        if inicial is None or final is None or final < inicial:
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
