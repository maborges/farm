from decimal import Decimal
import uuid
from typing import Optional

from sqlalchemy import func, or_, select
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

    async def _check_limite_hectares(
        self,
        nova_area_ha: Decimal | float | None,
        excluir_unidade_id: uuid.UUID | None = None,
    ) -> None:
        """Verifica se a soma de hectares das propriedades ativas respeita o limite do pacote.

        Args:
            nova_area_ha: Área em hectares da propriedade sendo criada ou atualizada.
            excluir_unidade_id: ID da propriedade atual para desconsiderar na soma em atualizações.

        Returns:
            None: Validação aprovada sem retorno.

        Raises:
            BusinessRuleError: Quando a área somada ultrapassa o limite_hectares do plano.
        """
        if nova_area_ha is None or Decimal(str(nova_area_ha)) <= 0:
            return

        stmt_plano = (
            select(PlanoAssinatura.limite_hectares)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == self.tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
            )
            .limit(1)
        )
        limite_ha = (await self.session.execute(stmt_plano)).scalar_one_or_none()
        if limite_ha is None or Decimal(str(limite_ha)) <= 0:
            return

        area_expr = func.coalesce(UnidadeProdutiva.area_total_calculada_ha, UnidadeProdutiva.area_total_ha, 0)
        stmt_soma = select(func.coalesce(func.sum(area_expr), 0)).where(
            UnidadeProdutiva.tenant_id == self.tenant_id,
            UnidadeProdutiva.ativo == True,
        )
        if excluir_unidade_id is not None:
            stmt_soma = stmt_soma.where(UnidadeProdutiva.id != excluir_unidade_id)

        area_atual = Decimal(str((await self.session.execute(stmt_soma)).scalar_one() or 0))
        area_nova = Decimal(str(nova_area_ha))
        limite_decimal = Decimal(str(limite_ha))

        if area_atual + area_nova > limite_decimal:
            raise BusinessRuleError(
                f"Seu pacote permite até {limite_decimal:.2f} hectares no total. "
                f"Área já cadastrada: {area_atual:.2f} ha; tentativa: +{area_nova:.2f} ha. "
                "Faça upgrade de pacote para cadastrar uma área maior."
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

        area_efetiva = obj_data.get("area_total_calculada_ha") or obj_data.get("area_total_ha")
        await self._check_limite_hectares(area_efetiva)

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

        if "area_total_calculada_ha" in obj_data or "area_total_ha" in obj_data:
            area_efetiva = obj_data.get("area_total_calculada_ha") or obj_data.get("area_total_ha")
            await self._check_limite_hectares(area_efetiva, excluir_unidade_id=id)

        unidade = await super().update(id, obj_data)
        return unidade

    async def hard_delete(self, id: uuid.UUID) -> None:
        """Deleta a Unidade Produtiva limpando dependências.
        A deleção fundiária e de módulos satélites é gerida pelo cascade oficial
        do banco/mapeamento. Não fazemos limpeza manual de tabelas opcionais aqui.
        """
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

    async def list_all(self, skip: int = 0, limit: int = 100, **filters) -> list[UnidadeProdutiva]:
        """Lista UPs com a visão territorial oficial acoplada para o frontend."""
        unidades = await super().list_all(skip=skip, limit=limit, **filters)
        if not unidades:
            return unidades

        from core.services.territory_read_service import TerritoryReadService

        svc = TerritoryReadService(self.session, self.tenant_id)
        visoes = await svc.obter_visoes_territoriais_em_lote([unidade.id for unidade in unidades])
        for unidade in unidades:
            visao = visoes.get(unidade.id)
            if visao is not None:
                setattr(unidade, "territorio", visao)
        return unidades

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
