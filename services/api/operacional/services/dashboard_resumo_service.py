from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from campo.models import TarefaCampo
from operacional.schemas.dashboard_resumo_schema import (
    DashboardResumoOperacionalDominioResponse,
    DashboardResumoOperacionalResponse,
)


class DashboardResumoOperacionalService:
    _STATUS_CONTAGEM = ("PENDENTE", "EM_EXECUCAO", "CONCLUIDA")

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.unidade_produtiva_id = unidade_produtiva_id

    async def resumir(self) -> DashboardResumoOperacionalResponse:
        rows = await self._agregar_por_dominio()
        agricultura = self._montar_dominio(rows.get("agricola"))
        pecuaria = self._montar_dominio(rows.get("pecuaria"))
        return DashboardResumoOperacionalResponse(
            pendentes=agricultura.pendentes + pecuaria.pendentes,
            em_execucao=agricultura.em_execucao + pecuaria.em_execucao,
            atrasadas=agricultura.atrasadas + pecuaria.atrasadas,
            concluidas=agricultura.concluidas + pecuaria.concluidas,
            agricultura=agricultura,
            pecuaria=pecuaria,
        )

    async def _agregar_por_dominio(self) -> dict[str, dict[str, int]]:
        hoje = date.today()
        stmt = (
            select(
                TarefaCampo.module.label("module"),
                func.sum(case((TarefaCampo.status_execucao == "PENDENTE", 1), else_=0)).label("pendentes"),
                func.sum(case((TarefaCampo.status_execucao == "EM_EXECUCAO", 1), else_=0)).label("em_execucao"),
                func.sum(case((TarefaCampo.status_execucao == "CONCLUIDA", 1), else_=0)).label("concluidas"),
                func.sum(
                    case(
                        (
                            and_(
                                TarefaCampo.status_execucao.in_(("PENDENTE", "EM_EXECUCAO")),
                                TarefaCampo.data_programada.is_not(None),
                                TarefaCampo.data_programada < hoje,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("atrasadas"),
            )
            .where(
                TarefaCampo.tenant_id == self.tenant_id,
                TarefaCampo.status_execucao.in_(self._STATUS_CONTAGEM),
            )
            .group_by(TarefaCampo.module)
        )
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)

        rows = (await self.session.execute(stmt)).all()
        resultado: dict[str, dict[str, int]] = {}
        for row in rows:
            resultado[str(row.module)] = {
                "pendentes": int(row.pendentes or 0),
                "em_execucao": int(row.em_execucao or 0),
                "atrasadas": int(row.atrasadas or 0),
                "concluidas": int(row.concluidas or 0),
            }
        return resultado

    @staticmethod
    def _montar_dominio(row: dict[str, int] | None) -> DashboardResumoOperacionalDominioResponse:
        if not row:
            return DashboardResumoOperacionalDominioResponse(
                pendentes=0,
                em_execucao=0,
                atrasadas=0,
                concluidas=0,
            )
        return DashboardResumoOperacionalDominioResponse(
            pendentes=row["pendentes"],
            em_execucao=row["em_execucao"],
            atrasadas=row["atrasadas"],
            concluidas=row["concluidas"],
        )

