from datetime import date
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.caderno.models import VisitaTecnica
from agricola.safras.models import Safra
from core.services.auth_service import AuthService
from notificacoes.models import Notificacao

SAFRAS_ENCERRADAS = ("ENCERRADA", "CANCELADA", "CONCLUIDA")


class CarteiraService:
    """Serviço de consolidação da carteira multi-tenant para consultores e produtores."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obter_resumo_carteira(self, user_id: UUID) -> dict:
        """Consolida indicadores operacionais dos tenants ativos vinculados ao usuário.

        Args:
            user_id: UUID do usuário autenticado.

        Returns:
            dict: Totais consolidados e lista de resumos por tenant acessível.
        """
        me = await AuthService(self.session).get_user_me(user_id)
        tenant_ids = [t.tenant_id for t in me.tenants]
        if not tenant_ids:
            return self._resposta_vazia()

        safras_map = await self._contar_safras_ativas(tenant_ids)
        alertas_map = await self._contar_alertas_abertos(tenant_ids, user_id)
        visitas_map = await self._obter_ultima_visita(tenant_ids)

        itens = [
            self._montar_item_tenant(t, safras_map, alertas_map, visitas_map)
            for t in me.tenants
        ]
        itens.sort(key=lambda item: (-item["alertas_abertos"], item["nome_tenant"].lower()))
        return self._montar_resposta(itens)

    async def _contar_safras_ativas(self, tenant_ids: list[UUID]) -> dict[UUID, int]:
        """Conta safras ativas (não encerradas/canceladas) por tenant.

        Args:
            tenant_ids: Lista de UUIDs de tenants acessíveis.

        Returns:
            dict[UUID, int]: Mapeamento tenant_id -> quantidade de safras ativas.
        """
        stmt = (
            select(Safra.tenant_id, func.count(Safra.id))
            .where(Safra.tenant_id.in_(tenant_ids), Safra.status.notin_(SAFRAS_ENCERRADAS))
            .group_by(Safra.tenant_id)
        )
        rows = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in rows.all()}

    async def _contar_alertas_abertos(
        self, tenant_ids: list[UUID], user_id: UUID
    ) -> dict[UUID, int]:
        """Conta notificações/alertas não lidos por tenant para o usuário.

        Args:
            tenant_ids: Lista de UUIDs de tenants acessíveis.
            user_id: UUID do usuário autenticado.

        Returns:
            dict[UUID, int]: Mapeamento tenant_id -> quantidade de alertas abertos.
        """
        stmt = (
            select(Notificacao.tenant_id, func.count(Notificacao.id))
            .where(
                Notificacao.tenant_id.in_(tenant_ids),
                Notificacao.lida.is_(False),
                or_(Notificacao.usuario_id.is_(None), Notificacao.usuario_id == user_id),
            )
            .group_by(Notificacao.tenant_id)
        )
        rows = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in rows.all()}

    async def _obter_ultima_visita(self, tenant_ids: list[UUID]) -> dict[UUID, date]:
        """Obtém a data da última visita técnica registrada por tenant.

        Args:
            tenant_ids: Lista de UUIDs de tenants acessíveis.

        Returns:
            dict[UUID, date]: Mapeamento tenant_id -> data da última visita.
        """
        stmt = (
            select(VisitaTecnica.tenant_id, func.max(VisitaTecnica.data_visita))
            .where(VisitaTecnica.tenant_id.in_(tenant_ids))
            .group_by(VisitaTecnica.tenant_id)
        )
        rows = await self.session.execute(stmt)
        return {row[0]: row[1] for row in rows.all() if row[1] is not None}

    def _montar_item_tenant(
        self,
        tenant_info: object,
        safras_map: dict[UUID, int],
        alertas_map: dict[UUID, int],
        visitas_map: dict[UUID, date],
    ) -> dict:
        """Formata o resumo de um tenant acessível."""
        tid = getattr(tenant_info, "tenant_id")
        perfil = getattr(tenant_info, "perfil", None)
        fazendas = getattr(tenant_info, "fazendas", []) or []
        ultima_visita = visitas_map.get(tid)
        return {
            "tenant_id": str(tid),
            "nome_tenant": getattr(tenant_info, "nome_tenant"),
            "is_owner": bool(getattr(tenant_info, "is_owner", False)),
            "perfil_nome": perfil.nome if perfil else None,
            "total_propriedades": len(fazendas),
            "safras_ativas": safras_map.get(tid, 0),
            "alertas_abertos": alertas_map.get(tid, 0),
            "ultima_visita_tecnica": ultima_visita.isoformat() if ultima_visita else None,
            "fazendas": [
                {"unidade_produtiva_id": str(f.unidade_produtiva_id), "nome": f.nome}
                for f in fazendas
            ],
        }

    def _montar_resposta(self, itens: list[dict]) -> dict:
        """Agrega totais consolidados da carteira."""
        return {
            "total_tenants": len(itens),
            "total_propriedades": sum(i["total_propriedades"] for i in itens),
            "total_safras_ativas": sum(i["safras_ativas"] for i in itens),
            "total_alertas_abertos": sum(i["alertas_abertos"] for i in itens),
            "tenants": itens,
        }

    def _resposta_vazia(self) -> dict:
        """Retorna estrutura vazia quando o usuário não possui tenants ativos."""
        return {
            "total_tenants": 0,
            "total_propriedades": 0,
            "total_safras_ativas": 0,
            "total_alertas_abertos": 0,
            "tenants": [],
        }
