from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import Equipamento
from core.exceptions import EntityNotFoundError
from operacional.models.checklist import ChecklistModelo, ChecklistRealizado
from operacional.models.documento_equipamento import DocumentoEquipamento
from operacional.models.frota import JornadaEquipamento, OrdemServico, PlanoManutencao
from operacional.schemas.frota_disponibilidade import (
    FrotaDisponibilidadeBloqueioResponse,
    FrotaDisponibilidadeChecklistPendente,
    FrotaDisponibilidadeDocumentoVencido,
    FrotaDisponibilidadeEquipamentoItem,
    FrotaDisponibilidadeEquipamentoResponse,
    FrotaDisponibilidadeNaoConformidade,
    FrotaDisponibilidadeOsAberta,
    FrotaDisponibilidadeResponse,
    FrotaDisponibilidadeResumo,
)
from operacional.services.frota_dashboard_service import FrotaDashboardService


@dataclass
class _ChecklistContexto:
    exige_checklist: bool
    modelo: ChecklistModelo | None
    ultimo: ChecklistRealizado | None
    checklist_recente: bool
    motivo_pendencia: str | None
    nao_conformidades: list[FrotaDisponibilidadeNaoConformidade]


@dataclass
class _EquipamentoDisponibilidade:
    equipamento: Equipamento
    status_operacional: str
    motivo_status: str | None
    checklist: _ChecklistContexto
    os_aberta: OrdemServico | None
    jornada_aberta: JornadaEquipamento | None
    documentos_vencidos: list[DocumentoEquipamento]
    manutencao_preventiva_vencida: bool


class FrotaDisponibilidadeService(FrotaDashboardService):
    CHECKLIST_RECENTE_HORAS = 24

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(session, tenant_id)

    async def obter_disponibilidade(
        self,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDisponibilidadeResponse:
        agora = datetime.now(timezone.utc)
        itens = await self._montar_disponibilidade(unidade_produtiva_id, agora)
        return FrotaDisponibilidadeResponse(
            resumo=self._montar_resumo(itens),
            equipamentos=[self._serializar_item(item) for item in self._ordenar_itens(itens)],
            gerado_em=agora,
        )

    async def obter_disponibilidade_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDisponibilidadeEquipamentoResponse:
        agora = datetime.now(timezone.utc)
        itens = await self._montar_disponibilidade(unidade_produtiva_id, agora)
        item = next((registro for registro in itens if registro.equipamento.id == equipamento_id), None)
        if not item:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant/contexto informado.")
        return FrotaDisponibilidadeEquipamentoResponse(
            equipamento=self._serializar_item(item),
            checklist=FrotaDisponibilidadeChecklistPendente(
                exige_checklist=item.checklist.exige_checklist,
                modelo_id=item.checklist.modelo.id if item.checklist.modelo else None,
                modelo_nome=item.checklist.modelo.nome if item.checklist.modelo else None,
                ultimo_checklist_id=item.checklist.ultimo.id if item.checklist.ultimo else None,
                ultimo_checklist_em=item.checklist.ultimo.data_hora if item.checklist.ultimo else None,
                checklist_recente=item.checklist.checklist_recente,
                motivo=item.checklist.motivo_pendencia,
            ),
            nao_conformidades=item.checklist.nao_conformidades,
            gerado_em=agora,
        )

    async def bloquear_equipamento(
        self,
        equipamento_id: uuid.UUID,
        motivo: str | None,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDisponibilidadeBloqueioResponse:
        equipamento = await self._obter_equipamento(equipamento_id, unidade_produtiva_id)
        agora = datetime.now(timezone.utc)
        equipamento.bloqueado_operacional = True
        equipamento.motivo_bloqueio_operacional = motivo or "Bloqueio operacional manual."
        equipamento.bloqueado_operacional_em = agora
        equipamento.liberado_operacional_em = None
        await self.session.commit()
        await self.session.refresh(equipamento)
        return FrotaDisponibilidadeBloqueioResponse(
            equipamento_id=equipamento.id,
            equipamento_nome=equipamento.nome,
            bloqueado_operacional=True,
            motivo_bloqueio_operacional=equipamento.motivo_bloqueio_operacional,
            bloqueado_operacional_em=equipamento.bloqueado_operacional_em,
            liberado_operacional_em=equipamento.liberado_operacional_em,
            mensagem="Equipamento bloqueado com sucesso.",
        )

    async def liberar_equipamento(
        self,
        equipamento_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> FrotaDisponibilidadeBloqueioResponse:
        equipamento = await self._obter_equipamento(equipamento_id, unidade_produtiva_id)
        agora = datetime.now(timezone.utc)
        equipamento.bloqueado_operacional = False
        equipamento.motivo_bloqueio_operacional = None
        equipamento.liberado_operacional_em = agora
        await self.session.commit()
        await self.session.refresh(equipamento)
        return FrotaDisponibilidadeBloqueioResponse(
            equipamento_id=equipamento.id,
            equipamento_nome=equipamento.nome,
            bloqueado_operacional=False,
            motivo_bloqueio_operacional=None,
            bloqueado_operacional_em=equipamento.bloqueado_operacional_em,
            liberado_operacional_em=equipamento.liberado_operacional_em,
            mensagem="Equipamento liberado com sucesso.",
        )

    async def _montar_disponibilidade(
        self,
        unidade_produtiva_id: uuid.UUID | None,
        agora: datetime,
    ) -> list[_EquipamentoDisponibilidade]:
        equipamentos = await self._listar_equipamentos(unidade_produtiva_id)
        if not equipamentos:
            return []
        equipamento_ids = [equipamento.id for equipamento in equipamentos]

        ordens = await self._listar_ordens_servico(equipamento_ids)
        documentos = await self._listar_documentos(equipamento_ids)
        planos = await self._listar_planos(equipamento_ids)
        modelos = await self._listar_modelos_checklist()
        checklists = await self._listar_checklists(equipamento_ids)
        jornadas = await self._listar_jornadas(equipamento_ids, status="ABERTA")

        hoje = agora.date()
        os_aberta_map: dict[uuid.UUID, OrdemServico] = {}
        for ordem in ordens:
            if ordem.status in {"ABERTA", "EM_EXECUCAO"} and ordem.equipamento_id not in os_aberta_map:
                os_aberta_map[ordem.equipamento_id] = ordem

        documentos_map: dict[uuid.UUID, list[DocumentoEquipamento]] = defaultdict(list)
        for documento in documentos:
            if documento.data_vencimento is not None and documento.data_vencimento < hoje:
                documentos_map[documento.equipamento_id].append(documento)

        jornadas_map: dict[uuid.UUID, JornadaEquipamento] = {}
        for jornada in jornadas:
            if jornada.equipamento_id not in jornadas_map:
                jornadas_map[jornada.equipamento_id] = jornada

        planos_map: dict[uuid.UUID, list[PlanoManutencao]] = defaultdict(list)
        for plano in planos:
            planos_map[plano.equipamento_id].append(plano)

        checklists_map: dict[uuid.UUID, list[ChecklistRealizado]] = defaultdict(list)
        for checklist in checklists:
            checklists_map[checklist.equipamento_id].append(checklist)

        itens: list[_EquipamentoDisponibilidade] = []
        for equipamento in equipamentos:
            checklist_ctx = self._resolver_checklist(equipamento, modelos, checklists_map[equipamento.id], agora)
            manutencao_status = self._calcular_status_manutencao(equipamento, planos_map[equipamento.id])
            manutencao_preventiva_vencida = manutencao_status.status == "VENCIDA"
            os_aberta = os_aberta_map.get(equipamento.id)
            jornada_aberta = jornadas_map.get(equipamento.id)
            documentos_vencidos = documentos_map[equipamento.id]

            status_operacional, motivo_status = self._resolver_status_operacional(
                equipamento=equipamento,
                checklist_ctx=checklist_ctx,
                os_aberta=os_aberta,
                jornada_aberta=jornada_aberta,
                documentos_vencidos=documentos_vencidos,
                manutencao_preventiva_vencida=manutencao_preventiva_vencida,
            )

            itens.append(
                _EquipamentoDisponibilidade(
                    equipamento=equipamento,
                    status_operacional=status_operacional,
                    motivo_status=motivo_status,
                    checklist=checklist_ctx,
                    os_aberta=os_aberta,
                    jornada_aberta=jornada_aberta,
                    documentos_vencidos=documentos_vencidos,
                    manutencao_preventiva_vencida=manutencao_preventiva_vencida,
                )
            )
        return itens

    async def _listar_modelos_checklist(self) -> list[ChecklistModelo]:
        stmt = select(ChecklistModelo).where(
            ChecklistModelo.tenant_id == self.tenant_id,
            ChecklistModelo.ativo == True,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _listar_checklists(self, equipamento_ids: list[uuid.UUID]) -> list[ChecklistRealizado]:
        stmt = (
            select(ChecklistRealizado)
            .where(
                ChecklistRealizado.tenant_id == self.tenant_id,
                ChecklistRealizado.equipamento_id.in_(equipamento_ids),
            )
            .order_by(ChecklistRealizado.data_hora.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    def _resolver_checklist(
        self,
        equipamento: Equipamento,
        modelos: list[ChecklistModelo],
        checklists: list[ChecklistRealizado],
        agora: datetime,
    ) -> _ChecklistContexto:
        modelo_especifico = next((modelo for modelo in modelos if modelo.tipo_equipamento == equipamento.tipo), None)
        modelo_generico = next((modelo for modelo in modelos if modelo.tipo_equipamento is None), None)
        modelo = modelo_especifico or modelo_generico
        exige_checklist = modelo is not None
        ultimo = checklists[0] if checklists else None
        checklist_recente = False
        motivo_pendencia = None
        nao_conformidades: list[FrotaDisponibilidadeNaoConformidade] = []

        if ultimo:
            checklist_recente = ultimo.data_hora >= agora - timedelta(hours=self.CHECKLIST_RECENTE_HORAS)
            nao_conformidades = [
                FrotaDisponibilidadeNaoConformidade(
                    ordem=int(item.get("ordem", 0)),
                    descricao=str(item.get("descricao", "Item não identificado")),
                    observacao=item.get("observacao"),
                    status="NOK",
                )
                for item in (ultimo.respostas or [])
                if item.get("status") == "NOK"
            ]

        if exige_checklist:
            if ultimo is None:
                motivo_pendencia = "Checklist exigido, mas ainda não realizado."
            elif not checklist_recente:
                motivo_pendencia = "Último checklist fora da janela operacional recente."

        return _ChecklistContexto(
            exige_checklist=exige_checklist,
            modelo=modelo,
            ultimo=ultimo,
            checklist_recente=checklist_recente,
            motivo_pendencia=motivo_pendencia,
            nao_conformidades=nao_conformidades,
        )

    def _resolver_status_operacional(
        self,
        equipamento: Equipamento,
        checklist_ctx: _ChecklistContexto,
        os_aberta: OrdemServico | None,
        jornada_aberta: JornadaEquipamento | None,
        documentos_vencidos: list[DocumentoEquipamento],
        manutencao_preventiva_vencida: bool,
    ) -> tuple[str, str | None]:
        if equipamento.bloqueado_operacional:
            return "BLOQUEADO", equipamento.motivo_bloqueio_operacional or "Bloqueio operacional manual."
        if self._normalizar_status(equipamento.status) == "EM_MANUTENCAO" or os_aberta is not None:
            if os_aberta is not None:
                return "EM_MANUTENCAO", f"OS {os_aberta.numero_os} em aberto."
            return "EM_MANUTENCAO", "Equipamento marcado em manutenção."
        if jornada_aberta is not None:
            return "EM_USO", f"Jornada {jornada_aberta.tipo_operacao} em andamento."
        if checklist_ctx.ultimo and not checklist_ctx.ultimo.liberado_para_uso:
            return "NAO_CONFORME", "Último checklist liberou não conformidades obrigatórias."
        if documents_len := len(documentos_vencidos):
            return "DOCUMENTO_VENCIDO", f"{documents_len} documento(s) vencido(s)."
        if manutencao_preventiva_vencida:
            return "BLOQUEADO", "Plano de manutenção preventiva vencido."
        if checklist_ctx.exige_checklist and (checklist_ctx.ultimo is None or not checklist_ctx.checklist_recente):
            return "CHECKLIST_PENDENTE", checklist_ctx.motivo_pendencia
        return "DISPONIVEL", None

    def _serializar_item(self, item: _EquipamentoDisponibilidade) -> FrotaDisponibilidadeEquipamentoItem:
        return FrotaDisponibilidadeEquipamentoItem(
            equipamento_id=item.equipamento.id,
            equipamento_nome=item.equipamento.nome,
            equipamento_tipo=item.equipamento.tipo,
            equipamento_status=self._normalizar_status(item.equipamento.status),
            unidade_produtiva_id=item.equipamento.unidade_produtiva_id,
            status_operacional=item.status_operacional,  # type: ignore[arg-type]
            ultimo_checklist_em=item.checklist.ultimo.data_hora if item.checklist.ultimo else None,
            checklist_pendente=item.checklist.exige_checklist and (item.checklist.ultimo is None or not item.checklist.checklist_recente),
            nao_conforme=bool(item.checklist.ultimo and not item.checklist.ultimo.liberado_para_uso),
            bloqueado_manual=bool(item.equipamento.bloqueado_operacional),
            motivo_status=item.motivo_status,
            motivo_bloqueio_manual=item.equipamento.motivo_bloqueio_operacional,
            os_aberta=(
                FrotaDisponibilidadeOsAberta(
                    os_id=item.os_aberta.id,
                    numero_os=item.os_aberta.numero_os,
                    tipo=item.os_aberta.tipo,
                    status=item.os_aberta.status,
                    data_abertura=item.os_aberta.data_abertura,
                )
                if item.os_aberta
                else None
            ),
            documentos_vencidos=[
                FrotaDisponibilidadeDocumentoVencido(
                    id=documento.id,
                    tipo=documento.tipo,
                    descricao=documento.descricao,
                    numero=documento.numero,
                    data_vencimento=documento.data_vencimento,
                )
                for documento in item.documentos_vencidos
            ],
            manutencao_preventiva_vencida=item.manutencao_preventiva_vencida,
        )

    @staticmethod
    def _montar_resumo(itens: list[_EquipamentoDisponibilidade]) -> FrotaDisponibilidadeResumo:
        return FrotaDisponibilidadeResumo(
            disponiveis=sum(1 for item in itens if item.status_operacional == "DISPONIVEL"),
            em_uso=sum(1 for item in itens if item.status_operacional == "EM_USO"),
            em_manutencao=sum(1 for item in itens if item.status_operacional == "EM_MANUTENCAO"),
            bloqueados=sum(1 for item in itens if item.status_operacional == "BLOQUEADO"),
            checklist_pendente=sum(
                1
                for item in itens
                if item.checklist.exige_checklist and (item.checklist.ultimo is None or not item.checklist.checklist_recente)
            ),
            nao_conformes=sum(1 for item in itens if item.checklist.ultimo is not None and not item.checklist.ultimo.liberado_para_uso),
            documentos_vencidos=sum(1 for item in itens if item.documentos_vencidos),
        )

    @staticmethod
    def _ordenar_itens(itens: list[_EquipamentoDisponibilidade]) -> list[_EquipamentoDisponibilidade]:
        order = {
            "BLOQUEADO": 0,
            "EM_MANUTENCAO": 1,
            "EM_USO": 2,
            "NAO_CONFORME": 3,
            "DOCUMENTO_VENCIDO": 4,
            "CHECKLIST_PENDENTE": 5,
            "DISPONIVEL": 6,
        }
        return sorted(itens, key=lambda item: (order.get(item.status_operacional, 99), item.equipamento.nome))

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
