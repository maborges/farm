import uuid
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError
from core.cadastros.produtos.models import Produto
from core.cadastros.tipos_servico.models import TipoServico
from agricola.receitas_aplicacao.models import (
    ReceitaAplicacao,
    ReceitaAplicacaoInsumo,
    ReceitaAplicacaoMaoObra,
)
from agricola.receitas_aplicacao.schemas import ReceitaAplicacaoCreate, ReceitaAplicacaoUpdate


class ReceitaAplicacaoService(BaseService[ReceitaAplicacao]):
    """CRUD do cadastro reutilizável de Receita de Aplicação (produto+dose/ha e
    mão de obra padrão). Não toca em nenhum plano operacional — a aplicação em
    lote a tarefas de um plano vive em `PlanoOperacionalService.aplicar_receita`,
    que só LÊ estes dados (sem FK de volta para o plano)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(ReceitaAplicacao, session, tenant_id, user_id=user_id)

    async def _validar_produto(self, produto_id: uuid.UUID) -> None:
        stmt = select(Produto).where(
            Produto.id == produto_id,
            or_(Produto.tenant_id.is_(None), Produto.tenant_id == self.tenant_id),
        )
        if not (await self.session.execute(stmt)).scalars().first():
            raise EntityNotFoundError(f"Produto {produto_id} não encontrado.")

    async def _validar_tipo_servico(self, tipo_servico_id: uuid.UUID) -> None:
        stmt = select(TipoServico).where(
            TipoServico.id == tipo_servico_id,
            or_(TipoServico.tenant_id.is_(None), TipoServico.tenant_id == self.tenant_id),
        )
        if not (await self.session.execute(stmt)).scalars().first():
            raise EntityNotFoundError(f"Tipo de serviço {tipo_servico_id} não encontrado.")

    async def criar(self, dados: ReceitaAplicacaoCreate) -> ReceitaAplicacao:
        for insumo in dados.insumos:
            await self._validar_produto(insumo.produto_id)
        for mao_obra in dados.mao_obra:
            await self._validar_tipo_servico(mao_obra.tipo_servico_id)

        receita = ReceitaAplicacao(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            nome=dados.nome,
            tipo_operacao=dados.tipo_operacao,
            created_by=self.user_id,
        )
        self.session.add(receita)
        await self.session.flush()

        for insumo in dados.insumos:
            self.session.add(ReceitaAplicacaoInsumo(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                receita_id=receita.id,
                produto_id=insumo.produto_id,
                deposito_id=insumo.deposito_id,
                dose_ha=insumo.dose_ha,
                unidade_dose=insumo.unidade_dose,
            ))
        for mao_obra in dados.mao_obra:
            self.session.add(ReceitaAplicacaoMaoObra(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                receita_id=receita.id,
                tipo_servico_id=mao_obra.tipo_servico_id,
                funcao=mao_obra.funcao,
                quantidade_pessoas=mao_obra.quantidade_pessoas,
                horas_fixas=mao_obra.horas_fixas,
                horas_por_hectare=mao_obra.horas_por_hectare,
            ))
        await self.session.flush()
        return receita

    async def atualizar(self, receita_id: uuid.UUID, dados: ReceitaAplicacaoUpdate) -> ReceitaAplicacao:
        receita = await self.get_or_fail(receita_id)
        dados_dict = dados.model_dump(exclude_unset=True, exclude={"insumos", "mao_obra"})
        for campo, valor in dados_dict.items():
            setattr(receita, campo, valor)
        self.session.add(receita)

        if dados.insumos is not None:
            for insumo in dados.insumos:
                await self._validar_produto(insumo.produto_id)
            await self._substituir_insumos(receita.id, dados.insumos)

        if dados.mao_obra is not None:
            for mao_obra in dados.mao_obra:
                await self._validar_tipo_servico(mao_obra.tipo_servico_id)
            await self._substituir_mao_obra(receita.id, dados.mao_obra)

        await self.session.flush()
        return receita

    async def _substituir_insumos(self, receita_id: uuid.UUID, insumos: list) -> None:
        stmt = select(ReceitaAplicacaoInsumo).where(
            ReceitaAplicacaoInsumo.tenant_id == self.tenant_id,
            ReceitaAplicacaoInsumo.receita_id == receita_id,
        )
        for atual in (await self.session.execute(stmt)).scalars().all():
            await self.session.delete(atual)
        await self.session.flush()
        for insumo in insumos:
            self.session.add(ReceitaAplicacaoInsumo(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                receita_id=receita_id,
                produto_id=insumo.produto_id,
                deposito_id=insumo.deposito_id,
                dose_ha=insumo.dose_ha,
                unidade_dose=insumo.unidade_dose,
            ))

    async def _substituir_mao_obra(self, receita_id: uuid.UUID, mao_obra_lista: list) -> None:
        stmt = select(ReceitaAplicacaoMaoObra).where(
            ReceitaAplicacaoMaoObra.tenant_id == self.tenant_id,
            ReceitaAplicacaoMaoObra.receita_id == receita_id,
        )
        for atual in (await self.session.execute(stmt)).scalars().all():
            await self.session.delete(atual)
        await self.session.flush()
        for mao_obra in mao_obra_lista:
            self.session.add(ReceitaAplicacaoMaoObra(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                receita_id=receita_id,
                tipo_servico_id=mao_obra.tipo_servico_id,
                funcao=mao_obra.funcao,
                quantidade_pessoas=mao_obra.quantidade_pessoas,
                horas_fixas=mao_obra.horas_fixas,
                horas_por_hectare=mao_obra.horas_por_hectare,
            ))

    async def excluir(self, receita_id: uuid.UUID) -> None:
        await self.hard_delete(receita_id)

    async def listar_insumos(self, receita_id: uuid.UUID) -> list[ReceitaAplicacaoInsumo]:
        stmt = select(ReceitaAplicacaoInsumo).where(
            ReceitaAplicacaoInsumo.tenant_id == self.tenant_id,
            ReceitaAplicacaoInsumo.receita_id == receita_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def listar_mao_obra(self, receita_id: uuid.UUID) -> list[ReceitaAplicacaoMaoObra]:
        stmt = select(ReceitaAplicacaoMaoObra).where(
            ReceitaAplicacaoMaoObra.tenant_id == self.tenant_id,
            ReceitaAplicacaoMaoObra.receita_id == receita_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def obter_com_itens(self, receita_id: uuid.UUID) -> ReceitaAplicacao:
        receita = await self.get_or_fail(receita_id)
        receita.insumos = await self.listar_insumos(receita_id)
        receita.mao_obra = await self.listar_mao_obra(receita_id)
        return receita

    async def listar_com_itens(self, apenas_ativas: bool = True) -> list[ReceitaAplicacao]:
        filtros = {"ativo": True} if apenas_ativas else {}
        receitas = await self.list_all(skip=0, limit=1000, **filtros)
        for receita in receitas:
            receita.insumos = await self.listar_insumos(receita.id)
            receita.mao_obra = await self.listar_mao_obra(receita.id)
        return receitas
