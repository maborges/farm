from decimal import Decimal
import uuid
from typing import Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.models.unidade_produtiva import UnidadeProdutiva
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from core.exceptions import BusinessRuleError
from core.services.geoprocessamento_service import GeoprocessamentoService


class UnidadeProdutivaService(BaseService[UnidadeProdutiva]):
    """
    Serviço que gerencia o ciclo de vida das unidades produtivas do AgroSaaS.
    Herda do BaseService que assegura blindagem por tenant_id de forma automática.

    Responsabilidades extras (EXEC-37):
      - Auto-criação/localização de ImovelRural ao receber dados fundiários.
      - Auto-criação do vínculo canônico PropriedadeImovel.
      - Overlay de leitura: campos fundiários retornados sempre refletem a
        fonte oficial (ImovelRural) quando há vínculo ativo.
    """
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(UnidadeProdutiva, session, tenant_id, user_id=user_id)

    # ------------------------------------------------------------------
    # Billing / limites
    # ------------------------------------------------------------------

    async def _check_limite_unidades(self) -> None:
        """Verifica se o tenant atingiu o limite de unidades produtivas do plano contratado.

        Raises:
            BusinessRuleError: quando o limite do plano for atingido.
        """
        stmt_plano = (
            select(PlanoAssinatura.max_fazendas)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == self.tenant_id,
                AssinaturaTenant.status == "ATIVA",
            )
            .limit(1)
        )
        result = await self.session.execute(stmt_plano)
        max_unidades = result.scalar_one_or_none()

        if max_unidades is None or max_unidades == -1:
            return  # Sem plano ativo ou ilimitado

        stmt_count = select(func.count(UnidadeProdutiva.id)).where(
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.ativo == True,
        )
        result_count = await self.session.execute(stmt_count)
        total = result_count.scalar_one()

        if total >= max_unidades:
            raise BusinessRuleError(
                f"Seu plano atingiu o limite de propriedades. Você tem {total} de {max_unidades} propriedade(s) ativas. "
                "Faça upgrade do plano para continuar."
            )

    # ------------------------------------------------------------------
    # CRUD principal
    # ------------------------------------------------------------------

    async def create_unidade_produtiva(self, dados: UnidadeProdutivaCreate) -> UnidadeProdutiva:
        """Cria uma nova Unidade Produtiva disparando sincronização fundiária.

        Args:
            dados: Schema validado de criação.

        Returns:
            UnidadeProdutiva: objeto criado e registrado na sessão.
        """
        await self._check_limite_unidades()
        unidade = await self.create(dados)
        return unidade

    async def create(self, obj_in: UnidadeProdutivaCreate | dict) -> UnidadeProdutiva:
        """Persiste a unidade produtiva calculando a área georreferenciada quando houver geometria."""
        if isinstance(obj_in, dict):
            obj_data = dict(obj_in)
        else:
            obj_data = obj_in.model_dump()

        obj_data.pop("area_total_calculada_ha", None)
        geometria = obj_data.get("geometria")
        if geometria:
            obj_data["area_total_calculada_ha"] = await self._calcular_area_georreferenciada(geometria)
        else:
            obj_data["area_total_calculada_ha"] = None

        return await super().create(obj_data)

    async def update(self, id: uuid.UUID, dados: UnidadeProdutivaUpdate | dict) -> UnidadeProdutiva:
        """Atualiza Unidade Produtiva disparando sincronização fundiária.

        Args:
            id: UUID da unidade.
            dados: Schema validado de atualização.

        Returns:
            UnidadeProdutiva: objeto atualizado.
        """
        if isinstance(dados, dict):
            obj_data = dict(dados)
        else:
            obj_data = dados.model_dump(exclude_unset=True)

        obj_data.pop("area_total_calculada_ha", None)
        if "geometria" in obj_data:
            geometria = obj_data.get("geometria")
            if geometria:
                obj_data["area_total_calculada_ha"] = await self._calcular_area_georreferenciada(geometria)
            else:
                obj_data["area_total_calculada_ha"] = None

        unidade = await super().update(id, obj_data)
        return unidade

    async def hard_delete(self, id: uuid.UUID) -> None:
        """Deleta a Unidade Produtiva limpando dependências.
        A deleção fundiária agora é gerida separadamente ou via cascata.
        """
        from core.cadastros.propriedades.propriedade_models import ExploracaoRural
        
        # Remove as explorações rurais que apontam para esta UP (se não for cascata automática)
        stmt_expl = select(ExploracaoRural).where(ExploracaoRural.unidade_produtiva_id == id)
        exploracoes = (await self.session.execute(stmt_expl)).scalars().all()
        for e in exploracoes:
            await self.session.delete(e)

        # Agora pode prosseguir com o hard_delete da classe base
        await super().hard_delete(id)

    async def get(self, id: uuid.UUID) -> Optional[UnidadeProdutiva]:
        """Retorna Unidade Produtiva aplicando overlay da fonte oficial fundiária.

        Quando há um ImovelRural vinculado via PropriedadeImovel, os campos
        CAR, NIRF, CCIR, SIGEF e Matrícula são sobrescritos com os dados da
        fonte oficial sem alterar o banco — apenas no objeto em memória.

        Args:
            id: UUID da unidade.

        Returns:
            UnidadeProdutiva ou None.
        """
        unidade = await super().get(id)
        if unidade is not None:
            await self._aplicar_compatibilidade_saida_territorial(unidade)
        return unidade

    # ------------------------------------------------------------------
    # Visão Territorial — Overlay de leitura (EXEC-37 § 8)
    # ------------------------------------------------------------------

    async def _aplicar_compatibilidade_saida_territorial(self, unidade: UnidadeProdutiva) -> None:
        """Sobrepõe campos fundiários antigos na saída da UP para compatibilidade (adaptador).

        Realiza o overlay sem escrever no banco: apenas substitui os atributos
        em memória do objeto para que a resposta reflita a fonte canônica.

        Args:
            unidade: Objeto UnidadeProdutiva já carregado da sessão.
        """
        from core.services.territory_read_service import TerritoryReadService
        
        svc = TerritoryReadService(self.session, self.tenant_id)
        visao = await svc.obter_visao_territorial_da_unidade(unidade.id)
        
        if not visao:
            return
            
        # Injeta o view model no objeto SQLAlchemy para o Pydantic
        setattr(unidade, "territorio", visao)

    # ------------------------------------------------------------------
    # Sincronização Fundiária — Auto-criação (EXEC-37 § 3, 4, 5)

    # ------------------------------------------------------------------
    # Backward compat aliases
    # ------------------------------------------------------------------

    async def create_fazenda(self, dados: UnidadeProdutivaCreate) -> UnidadeProdutiva:
        """Alias de compatibilidade para create_unidade_produtiva."""
        return await self.create_unidade_produtiva(dados)

    async def _calcular_area_georreferenciada(self, geometria: dict) -> Decimal:
        """Calcula a área georreferenciada em hectares com precisão decimal."""
        geoprocessamento_service = GeoprocessamentoService(self.session, self.tenant_id)
        area_ha = await geoprocessamento_service._calcular_area_geojson(geometria)
        return Decimal(str(round(area_ha, 4)))


# Backward compatibility alias
FazendaService = UnidadeProdutivaService
