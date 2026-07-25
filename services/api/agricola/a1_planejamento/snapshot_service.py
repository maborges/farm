import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import EntityNotFoundError
from core.cadastros.produtos.service import ProdutoService
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.pessoas.models import Pessoa
from operacional.services.frota_custo_service import FrotaCustoService
from operacional.services.frota_dashboard_service import FrotaDashboardService
from rh.models import ColaboradorRH
from core.cadastros.tipos_servico.models import TipoServico


class SnapshotCustoService:
    """Congela o custo unitário lido de um cadastro mestre no momento do planejamento.

    O valor retornado nunca é escrito de volta no cadastro de origem — só é
    persistido no item de orçamento (custo_unitario_snapshot/snapshot_data).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def capturar(
        self, origem_tipo: str, origem_id: uuid.UUID, unidade: str
    ) -> tuple[Decimal | None, dict[str, Any] | None]:
        if origem_tipo == "PRODUTO":
            return await self._capturar_produto(origem_id)
        if origem_tipo == "MAQUINA":
            return await self._capturar_maquina(origem_id)
        if origem_tipo == "PESSOA":
            return await self._capturar_pessoa(origem_id, unidade)
        if origem_tipo == "SERVICO":
            return await self._capturar_servico(origem_id)
        # MANUAL: sem cadastro mestre — usa o custo_unitario informado no payload.
        return None, None

    async def _capturar_produto(self, produto_id: uuid.UUID) -> tuple[Decimal, dict[str, Any]]:
        produto = await ProdutoService(self.session, self.tenant_id)._get_produto(produto_id)
        preco = Decimal(str(produto.preco_medio or 0))
        snapshot = {
            "produto_id": str(produto_id),
            "nome": produto.nome,
            "preco_medio": str(preco),
            "unidade_medida": getattr(produto, "unidade_medida", None),
        }
        return preco, snapshot

    async def _capturar_maquina(self, equipamento_id: uuid.UUID) -> tuple[Decimal, dict[str, Any]]:
        stmt = select(Equipamento).where(
            Equipamento.id == equipamento_id,
            Equipamento.tenant_id == self.tenant_id,
        )
        equipamento = (await self.session.execute(stmt)).scalar_one_or_none()
        if not equipamento:
            raise EntityNotFoundError(f"Equipamento {equipamento_id} não encontrado.")

        custo_svc = FrotaCustoService(self.session, self.tenant_id)
        resultado = await custo_svc.obter_custo_equipamento(equipamento_id)
        custo_total_acumulado = float(getattr(resultado.equipamento, "custo_total", 0) or 0)
        custo_hora = FrotaDashboardService._calcular_custo_por_hora(
            custo_total_acumulado, equipamento.horimetro_atual
        )
        preco = Decimal(str(custo_hora or 0))
        snapshot = {
            "equipamento_id": str(equipamento_id),
            "nome": equipamento.nome,
            "horimetro_atual": equipamento.horimetro_atual,
            "custo_total_acumulado": custo_total_acumulado,
            "custo_hora": str(preco),
        }
        return preco, snapshot

    async def _capturar_servico(self, tipo_servico_id: uuid.UUID) -> tuple[Decimal, dict[str, Any]]:
        stmt = select(TipoServico).where(
            TipoServico.id == tipo_servico_id,
            or_(TipoServico.tenant_id == self.tenant_id, TipoServico.tenant_id.is_(None)),
        )
        tipo_servico = (await self.session.execute(stmt)).scalar_one_or_none()
        if not tipo_servico:
            raise EntityNotFoundError(f"Tipo de serviço {tipo_servico_id} não encontrado.")

        preco = Decimal(str(tipo_servico.custo_referencia or 0))
        snapshot = {
            "tipo_servico_id": str(tipo_servico_id),
            "nome": tipo_servico.nome,
            "unidade_medida": tipo_servico.unidade_medida,
            "custo_referencia": str(preco),
        }
        return preco, snapshot

    async def _capturar_pessoa(self, colaborador_id: uuid.UUID, unidade: str) -> tuple[Decimal, dict[str, Any]]:
        stmt = select(ColaboradorRH).where(
            ColaboradorRH.id == colaborador_id,
            ColaboradorRH.tenant_id == self.tenant_id,
        )
        colaborador = (await self.session.execute(stmt)).scalar_one_or_none()
        if not colaborador:
            raise EntityNotFoundError(f"Colaborador {colaborador_id} não encontrado.")

        usa_diaria = unidade.strip().lower() in ("d", "dia", "diaria", "diária", "d/h")
        valor = colaborador.valor_diaria if usa_diaria else colaborador.valor_hora
        if valor is None:
            valor = colaborador.valor_diaria if colaborador.valor_diaria is not None else colaborador.valor_hora
        preco = Decimal(str(valor or 0))

        pessoa = (await self.session.execute(
            select(Pessoa).where(Pessoa.id == colaborador.pessoa_id)
        )).scalar_one_or_none()

        snapshot = {
            "colaborador_id": str(colaborador_id),
            "nome": pessoa.nome_exibicao if pessoa else None,
            "tipo_contrato": colaborador.tipo_contrato,
            "valor_diaria": str(colaborador.valor_diaria) if colaborador.valor_diaria is not None else None,
            "valor_hora": str(colaborador.valor_hora) if colaborador.valor_hora is not None else None,
            "base_usada": "valor_diaria" if usa_diaria else "valor_hora",
        }
        return preco, snapshot
