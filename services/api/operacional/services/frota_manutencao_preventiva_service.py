from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import EntityNotFoundError
from operacional.models.frota import OrdemServico, PlanoManutencao
from operacional.schemas.frota_preventiva import (
    FrotaPreventivaEquipamentoResponse,
    FrotaPreventivaListResponse,
    FrotaPreventivaPlanoItem,
    FrotaPreventivaRegraStatus,
    FrotaPreventivaStatusResumo,
    GerarOsPreventivaResponse,
)
from operacional.services.frota_dashboard_service import FrotaDashboardService


@dataclass
class _PlanoContexto:
    plano: PlanoManutencao
    equipamento: Equipamento
    regras: list[FrotaPreventivaRegraStatus]
    status: str
    os_aberta: OrdemServico | None


class FrotaManutencaoPreventivaService(FrotaDashboardService):
    DIAS_PROXIMIDADE_MIN = 3
    DIAS_PROXIMIDADE_MAX = 15

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(session, tenant_id)

    async def listar_planos_preventivos(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaPreventivaListResponse:
        agora = datetime.now(timezone.utc)
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        if not equipamentos:
            return FrotaPreventivaListResponse(
                resumo=FrotaPreventivaStatusResumo(
                    planos_em_dia=0,
                    planos_proximos_vencimento=0,
                    planos_vencidos=0,
                    os_preventivas_abertas=0,
                ),
                itens=[],
                gerado_em=agora,
            )

        contextos = await self._montar_contextos(equipamentos)
        itens = [self._serializar_plano(contexto) for contexto in contextos]
        return FrotaPreventivaListResponse(
            resumo=self._montar_resumo(contextos),
            itens=sorted(itens, key=self._sort_key_item),
            gerado_em=agora,
        )

    async def listar_planos_preventivos_por_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaPreventivaEquipamentoResponse:
        equipamento = await self._obter_equipamento(equipamento_id, unidade_produtiva_id)
        agora = datetime.now(timezone.utc)
        contextos = await self._montar_contextos([equipamento])
        itens = [self._serializar_plano(contexto) for contexto in contextos]
        return FrotaPreventivaEquipamentoResponse(
            equipamento_id=equipamento.id,
            equipamento_nome=equipamento.nome,
            equipamento_tipo=equipamento.tipo,
            equipamento_status=self._normalizar_status(equipamento.status),
            planos=sorted(itens, key=self._sort_key_item),
            resumo=self._montar_resumo(contextos),
            gerado_em=agora,
        )

    async def gerar_os_preventiva(
        self,
        plano_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> GerarOsPreventivaResponse:
        plano, equipamento = await self._obter_plano_com_equipamento(plano_id, unidade_produtiva_id)
        existente = await self._buscar_os_preventiva_aberta(plano.id, equipamento.id)
        if existente:
            return self._serializar_resposta_os(existente, criada=False, plano_id=plano.id)

        agora = datetime.now(timezone.utc)
        numero_os = f"PR{agora:%m%d%H%M%S}{str(plano.id).replace('-', '')[:4]}".upper()
        descricao = f"Executar manutenção preventiva: {plano.descricao}"
        os = OrdemServico(
            tenant_id=self.tenant_id,
            equipamento_id=equipamento.id,
            plano_manutencao_id=plano.id,
            numero_os=numero_os,
            tipo="PREVENTIVA",
            status="ABERTA",
            descricao_problema=descricao,
            data_abertura=agora,
            horimetro_na_abertura=float(equipamento.horimetro_atual or 0.0),
            km_na_abertura=equipamento.km_atual,
        )
        if self._normalizar_status(equipamento.status) == "ATIVO":
            equipamento.status = "EM_MANUTENCAO"

        self.session.add(os)
        await self.session.commit()
        await self.session.refresh(os)
        return self._serializar_resposta_os(os, criada=True, plano_id=plano.id)

    async def _montar_contextos(self, equipamentos: list[Equipamento]) -> list[_PlanoContexto]:
        if not equipamentos:
            return []

        equipamento_ids = [equipamento.id for equipamento in equipamentos]
        planos = await self._listar_planos(equipamento_ids)
        ordens = await self._listar_ordens_servico(equipamento_ids)
        ordens_abertas_por_plano: dict[uuid.UUID, OrdemServico] = {}
        for ordem in ordens:
            if (
                ordem.plano_manutencao_id
                and ordem.tipo == "PREVENTIVA"
                and ordem.status in {"ABERTA", "EM_EXECUCAO"}
                and ordem.plano_manutencao_id not in ordens_abertas_por_plano
            ):
                ordens_abertas_por_plano[ordem.plano_manutencao_id] = ordem

        equipamentos_map = {equipamento.id: equipamento for equipamento in equipamentos}
        contextos: list[_PlanoContexto] = []
        agora = datetime.now(timezone.utc)

        for plano in planos:
            equipamento = equipamentos_map.get(plano.equipamento_id)
            if not equipamento:
                continue
            regras = self._calcular_regras_plano(plano, equipamento, agora)
            status = self._agrupar_status_regras(regras)
            contextos.append(
                _PlanoContexto(
                    plano=plano,
                    equipamento=equipamento,
                    regras=regras,
                    status=status,
                    os_aberta=ordens_abertas_por_plano.get(plano.id),
                )
            )
        return contextos

    def _calcular_regras_plano(
        self,
        plano: PlanoManutencao,
        equipamento: Equipamento,
        agora: datetime,
    ) -> list[FrotaPreventivaRegraStatus]:
        regras: list[FrotaPreventivaRegraStatus] = []

        if plano.frequencia_dias and plano.frequencia_dias > 0:
            base = plano.ultimo_registro_data or plano.created_at or agora
            proxima_execucao = base + timedelta(days=int(plano.frequencia_dias))
            restante = (proxima_execucao - agora).total_seconds() / 86400
            status = self._status_por_restante(
                restante=restante,
                proximidade=self._proximidade_dias(int(plano.frequencia_dias)),
            )
            regras.append(
                FrotaPreventivaRegraStatus(
                    tipo="DIAS",
                    limite=float(plano.frequencia_dias),
                    leitura_atual=agora,
                    ultimo_registro=base,
                    proxima_execucao=proxima_execucao,
                    restante=round(max(restante, 0), 2) if restante > 0 else None,
                    vencido_por=round(abs(restante), 2) if restante < 0 else None,
                    status=status,  # type: ignore[arg-type]
                )
            )

        if plano.frequencia_horas and plano.frequencia_horas > 0:
            ultimo = float(plano.ultimo_registro_horas or 0.0)
            atual = float(equipamento.horimetro_atual or 0.0)
            proxima_execucao = ultimo + float(plano.frequencia_horas)
            restante = proxima_execucao - atual
            status = self._status_por_restante(
                restante=restante,
                proximidade=max(float(plano.frequencia_horas) * self.PROXIMIDADE_MANUTENCAO, 1.0),
            )
            regras.append(
                FrotaPreventivaRegraStatus(
                    tipo="HORAS",
                    limite=float(plano.frequencia_horas),
                    leitura_atual=atual,
                    ultimo_registro=ultimo,
                    proxima_execucao=round(proxima_execucao, 2),
                    restante=round(max(restante, 0), 2) if restante > 0 else None,
                    vencido_por=round(abs(restante), 2) if restante < 0 else None,
                    status=status,  # type: ignore[arg-type]
                )
            )

        if plano.frequencia_km and plano.frequencia_km > 0:
            ultimo = float(plano.ultimo_registro_km or 0.0)
            atual = float(equipamento.km_atual or 0.0)
            proxima_execucao = ultimo + float(plano.frequencia_km)
            restante = proxima_execucao - atual
            status = self._status_por_restante(
                restante=restante,
                proximidade=max(float(plano.frequencia_km) * self.PROXIMIDADE_MANUTENCAO, 1.0),
            )
            regras.append(
                FrotaPreventivaRegraStatus(
                    tipo="KM",
                    limite=float(plano.frequencia_km),
                    leitura_atual=atual,
                    ultimo_registro=ultimo,
                    proxima_execucao=round(proxima_execucao, 2),
                    restante=round(max(restante, 0), 2) if restante > 0 else None,
                    vencido_por=round(abs(restante), 2) if restante < 0 else None,
                    status=status,  # type: ignore[arg-type]
                )
            )

        return regras

    @staticmethod
    def _status_por_restante(restante: float, proximidade: float) -> str:
        if restante <= 0:
            return "VENCIDO"
        if restante <= proximidade:
            return "PROXIMO_VENCIMENTO"
        return "EM_DIA"

    def _proximidade_dias(self, frequencia_dias: int) -> int:
        return int(min(max(math.ceil(frequencia_dias * 0.1), self.DIAS_PROXIMIDADE_MIN), self.DIAS_PROXIMIDADE_MAX))

    @staticmethod
    def _agrupar_status_regras(regras: list[FrotaPreventivaRegraStatus]) -> str:
        if any(regra.status == "VENCIDO" for regra in regras):
            return "VENCIDO"
        if any(regra.status == "PROXIMO_VENCIMENTO" for regra in regras):
            return "PROXIMO_VENCIMENTO"
        return "EM_DIA"

    def _serializar_plano(self, contexto: _PlanoContexto) -> FrotaPreventivaPlanoItem:
        return FrotaPreventivaPlanoItem(
            plano_id=contexto.plano.id,
            equipamento_id=contexto.equipamento.id,
            equipamento_nome=contexto.equipamento.nome,
            equipamento_tipo=contexto.equipamento.tipo,
            equipamento_status=self._normalizar_status(contexto.equipamento.status),
            unidade_produtiva_id=contexto.equipamento.unidade_produtiva_id,
            plano_descricao=contexto.plano.descricao,
            tipo_regra=self._tipo_regra_resumo(contexto.regras),  # type: ignore[arg-type]
            limite_resumo=" • ".join(self._formatar_limite_regra(regra) for regra in contexto.regras) or "Sem limite",
            leitura_atual_resumo=" • ".join(self._formatar_leitura_atual(regra) for regra in contexto.regras) or "—",
            proxima_execucao_resumo=" • ".join(self._formatar_proxima_execucao(regra) for regra in contexto.regras) or "—",
            status=contexto.status,  # type: ignore[arg-type]
            regras=contexto.regras,
            os_preventiva_aberta_id=contexto.os_aberta.id if contexto.os_aberta else None,
            os_preventiva_aberta_numero=contexto.os_aberta.numero_os if contexto.os_aberta else None,
        )

    @staticmethod
    def _tipo_regra_resumo(regras: list[FrotaPreventivaRegraStatus]) -> str:
        tipos = [regra.tipo for regra in regras]
        return "_".join(tipos) if tipos else "DIAS"

    @staticmethod
    def _formatar_limite_regra(regra: FrotaPreventivaRegraStatus) -> str:
        if regra.tipo == "DIAS":
            return f"{int(regra.limite)} dias"
        if regra.tipo == "HORAS":
            return f"{regra.limite:.0f} h"
        return f"{regra.limite:.0f} km"

    @staticmethod
    def _formatar_leitura_atual(regra: FrotaPreventivaRegraStatus) -> str:
        if regra.tipo == "DIAS":
            return f"Base {regra.ultimo_registro.strftime('%d/%m/%Y') if isinstance(regra.ultimo_registro, datetime) else '—'}"
        if isinstance(regra.leitura_atual, (int, float)):
            suffix = "h" if regra.tipo == "HORAS" else "km"
            return f"Atual {regra.leitura_atual:.0f} {suffix}"
        return "—"

    @staticmethod
    def _formatar_proxima_execucao(regra: FrotaPreventivaRegraStatus) -> str:
        if regra.tipo == "DIAS":
            return (
                f"Vence {regra.proxima_execucao.strftime('%d/%m/%Y')}"
                if isinstance(regra.proxima_execucao, datetime)
                else "—"
            )
        if isinstance(regra.proxima_execucao, (int, float)):
            suffix = "h" if regra.tipo == "HORAS" else "km"
            return f"Em {regra.proxima_execucao:.0f} {suffix}"
        return "—"

    @staticmethod
    def _sort_key_item(item: FrotaPreventivaPlanoItem) -> tuple[int, str, str]:
        severity = {"VENCIDO": 0, "PROXIMO_VENCIMENTO": 1, "EM_DIA": 2}
        return (severity.get(item.status, 3), item.equipamento_nome, item.plano_descricao)

    @staticmethod
    def _montar_resumo(contextos: list[_PlanoContexto]) -> FrotaPreventivaStatusResumo:
        return FrotaPreventivaStatusResumo(
            planos_em_dia=sum(1 for contexto in contextos if contexto.status == "EM_DIA"),
            planos_proximos_vencimento=sum(1 for contexto in contextos if contexto.status == "PROXIMO_VENCIMENTO"),
            planos_vencidos=sum(1 for contexto in contextos if contexto.status == "VENCIDO"),
            os_preventivas_abertas=sum(1 for contexto in contextos if contexto.os_aberta is not None),
        )

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

    async def _obter_plano_com_equipamento(
        self,
        plano_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None,
    ) -> tuple[PlanoManutencao, Equipamento]:
        stmt = select(PlanoManutencao).where(PlanoManutencao.id == plano_id)
        plano = (await self.session.execute(stmt)).scalar_one_or_none()
        if not plano:
            raise EntityNotFoundError("Plano de manutenção não encontrado.")

        equipamento = await self._obter_equipamento(plano.equipamento_id, unidade_produtiva_id)
        return plano, equipamento

    async def _buscar_os_preventiva_aberta(
        self,
        plano_id: uuid.UUID,
        equipamento_id: uuid.UUID,
    ) -> OrdemServico | None:
        stmt = (
            select(OrdemServico)
            .where(
                OrdemServico.tenant_id == self.tenant_id,
                OrdemServico.equipamento_id == equipamento_id,
                OrdemServico.plano_manutencao_id == plano_id,
                OrdemServico.tipo == "PREVENTIVA",
                OrdemServico.status.in_(["ABERTA", "EM_EXECUCAO"]),
            )
            .order_by(OrdemServico.data_abertura.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    @staticmethod
    def _serializar_resposta_os(
        ordem: OrdemServico,
        criada: bool,
        plano_id: uuid.UUID,
    ) -> GerarOsPreventivaResponse:
        return GerarOsPreventivaResponse(
            criada=criada,
            ordem_servico_id=ordem.id,
            numero_os=ordem.numero_os,
            status=ordem.status,
            tipo=ordem.tipo,
            equipamento_id=ordem.equipamento_id,
            plano_id=plano_id,
            data_abertura=ordem.data_abertura,
            descricao_problema=ordem.descricao_problema,
        )
