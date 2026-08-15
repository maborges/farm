import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.cadastros.pessoas.models import Pessoa, PessoaProfissionalAgronomo
from core.cadastros.produtos.models import Produto, ProdutoAgricola
from core.operational_context import validate_safra_in_tenant
from core.services.storage_service import save_and_track
from agricola.receituario_agronomico.models import (
    ReceituarioAgronomico,
    ReceituarioItem,
    StatusReceituario,
)
from agricola.receituario_agronomico.schemas import (
    ReceituarioAgronomicoCreate,
    ReceituarioAgronomicoUpdate,
)


class ReceituarioAgronomicoService(BaseService[ReceituarioAgronomico]):
    """OPERATIONS-GAP-01 §21.16/§21.19: documento legal de Receituário
    Agronômico (Lei 7.802/1989). Emissão exige agrônomo com CREA ativo/válido;
    saída de estoque de produtos `requer_receituario=True` passa a exigir um
    receituário EMITIDO e não vencido vinculado (ver
    `operacional/services/estoque_service.py::_validar_receituario_vigente`)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(ReceituarioAgronomico, session, tenant_id, user_id=user_id)

    async def _validar_agronomo(self, agronomo_pessoa_id: uuid.UUID) -> PessoaProfissionalAgronomo:
        stmt = select(Pessoa).where(Pessoa.id == agronomo_pessoa_id, Pessoa.tenant_id == self.tenant_id)
        if not (await self.session.execute(stmt)).scalars().first():
            raise EntityNotFoundError(f"Pessoa {agronomo_pessoa_id} não encontrada.")

        stmt_perfil = select(PessoaProfissionalAgronomo).where(
            PessoaProfissionalAgronomo.pessoa_id == agronomo_pessoa_id,
            PessoaProfissionalAgronomo.tenant_id == self.tenant_id,
        )
        perfil = (await self.session.execute(stmt_perfil)).scalars().first()
        if perfil is None or not perfil.ativo:
            raise BusinessRuleError(
                "Pessoa informada não possui perfil profissional de agrônomo (CREA) ativo."
            )
        if perfil.crea_validade is not None and perfil.crea_validade < date.today():
            raise BusinessRuleError(f"CREA {perfil.crea_numero}/{perfil.crea_uf} vencido em {perfil.crea_validade}.")
        return perfil

    async def _validar_produto(self, produto_id: uuid.UUID) -> ProdutoAgricola | None:
        stmt = select(Produto).where(
            Produto.id == produto_id,
            (Produto.tenant_id.is_(None)) | (Produto.tenant_id == self.tenant_id),
        )
        produto = (await self.session.execute(stmt)).scalars().first()
        if not produto:
            raise EntityNotFoundError(f"Produto {produto_id} não encontrado.")

        stmt_detalhe = select(ProdutoAgricola).where(ProdutoAgricola.produto_id == produto_id)
        return (await self.session.execute(stmt_detalhe)).scalars().first()

    async def emitir(self, dados: ReceituarioAgronomicoCreate) -> ReceituarioAgronomico:
        perfil = await self._validar_agronomo(dados.agronomo_pessoa_id)
        if dados.safra_id is not None:
            await validate_safra_in_tenant(self.session, tenant_id=self.tenant_id, safra_id=dados.safra_id)

        receituario = ReceituarioAgronomico(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            numero=dados.numero,
            agronomo_pessoa_id=dados.agronomo_pessoa_id,
            crea_numero=perfil.crea_numero,
            crea_uf=perfil.crea_uf,
            unidade_produtiva_id=dados.unidade_produtiva_id,
            safra_id=dados.safra_id,
            talhao_id=dados.talhao_id,
            operacao_agricola_id=dados.operacao_agricola_id,
            cultura=dados.cultura,
            praga_alvo=dados.praga_alvo,
            data_emissao=dados.data_emissao,
            data_validade=dados.data_emissao + timedelta(days=dados.validade_dias),
            status=StatusReceituario.RASCUNHO.value,
            observacoes=dados.observacoes,
        )
        self.session.add(receituario)
        await self.session.flush()

        for item in dados.itens:
            detalhe = await self._validar_produto(item.produto_id)
            self.session.add(ReceituarioItem(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                receituario_id=receituario.id,
                produto_id=item.produto_id,
                dose=item.dose,
                unidade_dose=item.unidade_dose,
                cultura=item.cultura or dados.cultura,
                praga_alvo=item.praga_alvo or dados.praga_alvo,
                carencia_dias=detalhe.periodo_carencia_dias if detalhe else None,
            ))
        await self.session.flush()
        return receituario

    async def atualizar(self, receituario_id: uuid.UUID, dados: ReceituarioAgronomicoUpdate) -> ReceituarioAgronomico:
        receituario = await self.get_or_fail(receituario_id)
        if receituario.status != StatusReceituario.RASCUNHO.value:
            raise BusinessRuleError("Somente receituários em RASCUNHO podem ser editados.")

        for campo in ("cultura", "praga_alvo", "observacoes"):
            valor = getattr(dados, campo)
            if valor is not None:
                setattr(receituario, campo, valor)

        if dados.itens is not None:
            for item_antigo in list(receituario.itens):
                await self.session.delete(item_antigo)
            await self.session.flush()
            for item in dados.itens:
                detalhe = await self._validar_produto(item.produto_id)
                self.session.add(ReceituarioItem(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    receituario_id=receituario.id,
                    produto_id=item.produto_id,
                    dose=item.dose,
                    unidade_dose=item.unidade_dose,
                    cultura=item.cultura or receituario.cultura,
                    praga_alvo=item.praga_alvo or receituario.praga_alvo,
                    carencia_dias=detalhe.periodo_carencia_dias if detalhe else None,
                ))
        await self.session.flush()
        return receituario

    async def obter_com_itens(self, receituario_id: uuid.UUID) -> ReceituarioAgronomico:
        stmt = select(ReceituarioAgronomico).where(
            ReceituarioAgronomico.id == receituario_id,
            ReceituarioAgronomico.tenant_id == self.tenant_id,
        )
        receituario = (await self.session.execute(stmt)).scalars().first()
        if not receituario:
            raise EntityNotFoundError("Receituário agronômico não encontrado.")
        stmt_itens = select(ReceituarioItem).where(ReceituarioItem.receituario_id == receituario_id)
        receituario.itens = list((await self.session.execute(stmt_itens)).scalars().all())
        return receituario

    async def anexar_pdf(self, receituario_id: uuid.UUID, content: bytes, filename: str) -> ReceituarioAgronomico:
        receituario = await self.get_or_fail(receituario_id)
        storage_path = await save_and_track(
            self.session, self.tenant_id, content,
            area_rural_id=str(receituario.unidade_produtiva_id), filename=filename,
        )
        receituario.arquivo_pdf_url = storage_path
        receituario.arquivo_pdf_tamanho_bytes = len(content)
        if receituario.status == StatusReceituario.RASCUNHO.value:
            receituario.status = StatusReceituario.EMITIDO.value
        await self.session.flush()
        return receituario

    async def cancelar(self, receituario_id: uuid.UUID, motivo: str) -> ReceituarioAgronomico:
        receituario = await self.get_or_fail(receituario_id)
        if receituario.status == StatusReceituario.CANCELADO.value:
            raise BusinessRuleError("Receituário já está cancelado.")
        receituario.status = StatusReceituario.CANCELADO.value
        receituario.motivo_cancelamento = motivo
        await self.session.flush()
        return receituario

    async def listar_vigentes_por_produto(
        self, produto_id: uuid.UUID, safra_id: uuid.UUID | None = None,
    ) -> list[ReceituarioAgronomico]:
        stmt = (
            select(ReceituarioAgronomico)
            .join(ReceituarioItem, ReceituarioItem.receituario_id == ReceituarioAgronomico.id)
            .where(
                ReceituarioAgronomico.tenant_id == self.tenant_id,
                ReceituarioItem.produto_id == produto_id,
                ReceituarioAgronomico.status == StatusReceituario.EMITIDO.value,
                ReceituarioAgronomico.data_validade >= date.today(),
            )
        )
        if safra_id is not None:
            stmt = stmt.where(ReceituarioAgronomico.safra_id == safra_id)
        return list((await self.session.execute(stmt)).scalars().all())
