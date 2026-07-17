from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.propriedades.propriedade_models import NaturezaVinculo, Propriedade
from core.cadastros.propriedades.propriedade_schemas import ExploracaoCreate, ExploracaoUpdate
from core.cadastros.propriedades.propriedade_service import ExploracaoRuralService, PropriedadeService
from core.cadastros.propriedade_imovel.models import PropriedadeImovel, TipoVinculoPropriedadeImovel
from core.cadastros.propriedade_imovel.schemas import PropriedadeImovelUpdate
from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.schemas.cadastro_completo_input import CadastroCompletoCreate, CadastroCompletoUpdate
from core.schemas.unidade_produtiva_input import UnidadeProdutivaCreate, UnidadeProdutivaUpdate
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from imoveis.models.imovel import ImovelRural, TipoImovel
from imoveis.services.imovel_service import ImovelService


class CadastroCompletoService:
    """Orquestra o cadastro completo sem repassar campos fundiários para a UP."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.up_svc = UnidadeProdutivaService(session, tenant_id, user_id)
        self.prop_svc = PropriedadeService(Propriedade, session, tenant_id, user_id)
        self.expl_svc = ExploracaoRuralService(session, tenant_id)
        self.imovel_svc = ImovelService(session)
        self.vinculo_svc = PropriedadeImovelService(session, tenant_id)

    def _tem_dados_fundiarios(self, dados: CadastroCompletoCreate | CadastroCompletoUpdate) -> bool:
        """Indica se o bloco de imóvel trouxe dados concretos de alteração."""
        imovel = getattr(dados, "imovel_rural", None)
        if imovel is None:
            return False
        payload = imovel.model_dump(exclude={"id"}, exclude_none=True)
        return any(valor not in ("", [], {}) for valor in payload.values())

    async def criar_cadastro_completo(self, dados: CadastroCompletoCreate):
        """Cria UP, propriedade, exploração e imóvel em uma única operação coordenada."""
        setattr(dados, "_bypass_sincronismo", True)
        try:
            unidade = await self._criar_unidade_produtiva(dados.unidade_produtiva)
            propriedade = await self._resolver_propriedade(unidade.id, unidade, dados.propriedade, criar_se_ausente=True)
            await self._resolver_exploracao(unidade.id, propriedade.id, dados.exploracao_rural, criar_se_ausente=True)
            imovel = await self._resolver_imovel(unidade, propriedade, dados.imovel_rural, dados.propriedade_imovel)
            if imovel is not None:
                await self._resolver_vinculo(propriedade.id, imovel, dados.propriedade_imovel)
            return await self.up_svc.get(unidade.id)
        except EntityNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except BusinessRuleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except IntegrityError as exc:
            logger.warning("Conflito ao criar cadastro completo", error=str(exc))
            raise HTTPException(
                status_code=409,
                detail="Conflito de integridade nos dados fundiários.",
            ) from exc

    async def atualizar_cadastro_completo(self, id: uuid.UUID, dados: CadastroCompletoUpdate):
        """Atualiza o cadastro completo preservando ids e evitando recreação implícita."""
        setattr(dados, "_bypass_sincronismo", True)
        try:
            unidade = await self._atualizar_unidade_produtiva(id, dados.unidade_produtiva)
            propriedade = await self._resolver_propriedade(
                unidade.id,
                unidade,
                dados.propriedade,
                criar_se_ausente=bool(dados.propriedade or dados.exploracao_rural or dados.imovel_rural),
            )
            if propriedade is None:
                propriedade = await self._resolver_propriedade(unidade.id, unidade, None, criar_se_ausente=True)
            await self._resolver_exploracao(
                unidade.id,
                propriedade.id,
                dados.exploracao_rural,
                criar_se_ausente=True,
            )
            imovel = await self._resolver_imovel(unidade, propriedade, dados.imovel_rural, dados.propriedade_imovel)
            if imovel is not None and dados.imovel_rural is None:
                imovel = await self._sincronizar_imovel_principal_com_unidade(unidade, imovel)
            if imovel is not None:
                await self._resolver_vinculo(propriedade.id, imovel, dados.propriedade_imovel)
            elif dados.propriedade_imovel and dados.propriedade_imovel.id:
                await self._resolver_vinculo_por_id(propriedade.id, dados.propriedade_imovel)
            return await self.up_svc.get(unidade.id)
        except EntityNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except BusinessRuleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except IntegrityError as exc:
            logger.warning("Conflito ao atualizar cadastro completo", error=str(exc))
            raise HTTPException(
                status_code=409,
                detail="Conflito de integridade nos dados fundiários.",
            ) from exc

    async def _criar_unidade_produtiva(self, dados: UnidadeProdutivaCreate):
        """Persiste a UP recebendo apenas campos operacionais válidos."""
        up_payload = dados.model_dump()
        up_payload.pop("propriedade_id", None)
        up_payload.pop("imovel_rural_id", None)
        up_payload.pop("propriedade_imovel_id", None)
        return await self.up_svc.create_unidade_produtiva(UnidadeProdutivaCreate(**up_payload))

    async def _atualizar_unidade_produtiva(
        self,
        id: uuid.UUID,
        dados: UnidadeProdutivaUpdate | None,
    ):
        """Atualiza a UP somente quando o bloco operacional foi enviado."""
        if dados is None:
            return await self.up_svc.get_or_fail(id)
        up_payload = dados.model_dump(exclude_unset=True)
        up_payload.pop("propriedade_id", None)
        up_payload.pop("imovel_rural_id", None)
        up_payload.pop("propriedade_imovel_id", None)
        if not up_payload:
            return await self.up_svc.get_or_fail(id)
        return await self.up_svc.update(id, UnidadeProdutivaUpdate(**up_payload))

    async def _resolver_propriedade(
        self,
        unidade_id: uuid.UUID,
        unidade,
        bloco,
        *,
        criar_se_ausente: bool,
    ):
        """Obtém, atualiza ou cria a Propriedade associada à UP."""
        propriedade = await self._buscar_propriedade_da_unidade(unidade_id)
        if bloco and bloco.id:
            propriedade = await self.prop_svc.get_or_fail(bloco.id)
            update_data = bloco.model_dump(exclude={"id"}, exclude_none=True)
            if update_data:
                propriedade = await self.prop_svc.update(propriedade.id, update_data)
            return propriedade
        if propriedade is not None and bloco is not None:
            update_data = bloco.model_dump(exclude={"id"}, exclude_none=True)
            if update_data:
                propriedade = await self.prop_svc.update(propriedade.id, update_data)
            return propriedade
        if propriedade is not None:
            return propriedade
        if not criar_se_ausente:
            return None
        payload = self._propriedade_padrao(unidade, bloco)
        return await self.prop_svc.create(payload)

    async def _resolver_exploracao(
        self,
        unidade_id: uuid.UUID,
        propriedade_id: uuid.UUID,
        bloco,
        *,
        criar_se_ausente: bool,
    ):
        """Obtém, atualiza ou cria a Exploração Rural da UP."""
        exploracoes = await self.expl_svc.listar_por_fazenda(unidade_id)
        exploracao = exploracoes[0] if exploracoes else None
        if bloco and bloco.id:
            exploracao = await self.expl_svc.obter(bloco.id)
            if exploracao is None:
                raise EntityNotFoundError("Exploração rural não encontrada no tenant atual.")
            update_data = bloco.model_dump(exclude={"id"}, exclude_none=True)
            if update_data:
                exploracao = await self.expl_svc.atualizar(bloco.id, ExploracaoUpdate(**update_data))
            return exploracao
        if exploracao is not None and bloco is not None:
            update_data = bloco.model_dump(exclude={"id"}, exclude_none=True)
            if update_data:
                exploracao = await self.expl_svc.atualizar(exploracao.id, ExploracaoUpdate(**update_data))
            return exploracao
        if exploracao is not None:
            return exploracao
        if not criar_se_ausente:
            return None
        return await self.expl_svc.criar(
            propriedade_id=propriedade_id,
            data=ExploracaoCreate(
                unidade_produtiva_id=unidade_id,
                natureza=self._natureza_padrao(bloco),
                data_inicio=date.today(),
                area_explorada_ha=None,
            ),
        )

    async def _resolver_imovel(
        self,
        unidade,
        propriedade,
        bloco,
        vinculo_bloco,
    ) -> ImovelRural | None:
        """Cria ou atualiza o Imóvel Rural somente quando há bloco de imóvel."""
        if bloco is None:
            return None
        payload = bloco.model_dump(exclude={"id"}, exclude_none=True)
        if not payload and bloco.id is None:
            return None

        vinculo_explicit = await self._resolver_vinculo_explicit(propriedade.id, vinculo_bloco)
        vinculo_principal_pedido = self._vinculo_principal(vinculo_bloco)

        if bloco.id:
            imovel = await self.imovel_svc.get_imovel_by_id(bloco.id, self.tenant_id)
            if imovel is None:
                raise EntityNotFoundError("Imóvel rural não encontrado no tenant atual.")
            vinculo_existente = await self._buscar_vinculo(propriedade.id, imovel.id)
            if vinculo_existente is None:
                raise BusinessRuleError("O imóvel informado não está vinculado à propriedade atual.")
        elif vinculo_principal_pedido is False and payload:
            return await self._criar_imovel(unidade, propriedade, bloco, vinculo_bloco)
        elif vinculo_explicit is not None:
            imovel = await self.imovel_svc.get_imovel_by_id(vinculo_explicit.imovel_rural_id, self.tenant_id)
            if imovel is None:
                raise EntityNotFoundError("Imóvel rural não encontrado no tenant atual.")
        else:
            imovel = await self._resolver_imovel_existente_da_propriedade(propriedade.id)
            if imovel is None:
                return await self._criar_imovel(unidade, propriedade, bloco, vinculo_bloco)

        if not payload:
            return imovel

        dados_imovel = self._payload_imovel(unidade, bloco)
        if not dados_imovel:
            return imovel
        dados_imovel["propriedade_id"] = propriedade.id
        dados_imovel["tipo_vinculo"] = self._tipo_vinculo(vinculo_bloco)
        imovel, _ = await self.imovel_svc.atualizar_imovel(imovel, dados_imovel, self.user_id)
        return imovel

    async def _resolver_imovel_existente_da_propriedade(self, propriedade_id: uuid.UUID) -> ImovelRural | None:
        """Resolve o imóvel principal vigente da propriedade quando a referência não veio no payload."""
        vinculos = await self.vinculo_svc.listar(propriedade_id=propriedade_id, ativo=True)
        if not vinculos:
            return None

        principais = [v for v in vinculos if v.vinculo_principal and v.data_fim is None]
        if len(principais) == 1:
            imovel = await self.imovel_svc.get_imovel_by_id(principais[0].imovel_rural_id, self.tenant_id)
            if imovel is None:
                raise EntityNotFoundError("Imóvel rural principal não encontrado no tenant atual.")
            return imovel

        raise BusinessRuleError(
            "A propriedade possui múltiplos vínculos ativos. Informe imovel_rural.id ou propriedade_imovel.id."
        )

    async def _resolver_vinculo_explicit(self, propriedade_id: uuid.UUID, bloco) -> PropriedadeImovel | None:
        """Resolve o vínculo explícito informado no payload, quando houver."""
        if bloco is None or getattr(bloco, "id", None) is None:
            return None
        vinculo = await self.vinculo_svc.obter(bloco.id)
        if vinculo.propriedade_id != propriedade_id:
            raise BusinessRuleError("O vínculo informado não pertence à propriedade atual.")
        return vinculo

    async def _criar_imovel(
        self,
        unidade,
        propriedade,
        bloco,
        vinculo_bloco,
    ) -> ImovelRural:
        """Cria um Imóvel Rural novo com os campos canônicos do bloco."""
        dados_imovel = self._payload_imovel(unidade, bloco)
        dados_imovel["propriedade_id"] = propriedade.id
        dados_imovel["tipo_vinculo"] = self._tipo_vinculo(vinculo_bloco)
        dados_imovel["tipo"] = self._tipo_imovel(bloco)
        dados_imovel["created_by"] = self.user_id
        imovel, _ = await self.imovel_svc.criar_imovel(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade.id,
            **dados_imovel,
        )
        return imovel

    async def _resolver_vinculo(
        self,
        propriedade_id: uuid.UUID,
        imovel: ImovelRural,
        bloco,
    ) -> PropriedadeImovel | None:
        """Garante o vínculo canônico entre Propriedade e Imóvel."""
        existente = await self._buscar_vinculo(propriedade_id, imovel.id)
        if bloco and bloco.id:
            existente = await self.vinculo_svc.obter(bloco.id)
        if existente is None:
            existente = await self.vinculo_svc.garantir_vinculo_ativo(
                propriedade_id=propriedade_id,
                imovel_rural_id=imovel.id,
                tipo_vinculo=self._tipo_vinculo(bloco),
                origem_documental=self._origem_documental(bloco),
                data_inicio=self._data_inicio(bloco),
                usuario_id=self.user_id,
                vinculo_principal=self._vinculo_principal(bloco),
            )
        if bloco is None:
            return existente

        update_data = self._payload_vinculo(bloco, propriedade_id, imovel.id)
        if update_data:
            existente = await self.vinculo_svc.atualizar(existente.id, update_data, self.user_id)
        if self._vinculo_principal(bloco):
            existente = await self.vinculo_svc.definir_vinculo_principal(propriedade_id, existente.id, self.user_id)
        return existente

    async def _sincronizar_imovel_principal_com_unidade(self, unidade, imovel: ImovelRural) -> ImovelRural:
        """Reflete no imóvel principal os atributos compartilhados alterados na UP."""
        dados_compartilhados: dict[str, Any] = {}
        for campo in ("nome", "municipio", "uf", "area_total_ha", "area_app_ha", "area_rl_ha"):
            valor = getattr(unidade, campo, None)
            if valor is not None and not self._valores_equivalentes(getattr(imovel, campo, None), valor):
                dados_compartilhados[campo] = valor

        coordenadas = getattr(unidade, "coordenadas_sede", None)
        if coordenadas:
            partes = [parte.strip() for parte in str(coordenadas).split(",")]
            if len(partes) == 2:
                try:
                    latitude = Decimal(partes[0].replace(",", "."))
                    longitude = Decimal(partes[1].replace(",", "."))
                except Exception:
                    latitude = longitude = None
                if latitude is not None and longitude is not None:
                    if getattr(imovel, "latitude", None) != latitude:
                        dados_compartilhados["latitude"] = latitude
                    if getattr(imovel, "longitude", None) != longitude:
                        dados_compartilhados["longitude"] = longitude

        if not dados_compartilhados:
            return imovel

        if "area_total_ha" in dados_compartilhados and "motivo_alteracao_area" not in dados_compartilhados:
            dados_compartilhados["motivo_alteracao_area"] = "Sincronizado a partir da atualização da Unidade Produtiva."

        imovel, _ = await self.imovel_svc.atualizar_imovel(imovel, dados_compartilhados, self.user_id)
        return imovel

    @staticmethod
    def _valores_equivalentes(atual: Any, novo: Any) -> bool:
        """Compara valores compartilhados sem disparar diffs numéricos espúrios."""
        if atual == novo:
            return True
        if atual is None or novo is None:
            return False

        tipos_numericos = (int, float, Decimal)
        if isinstance(atual, tipos_numericos) and isinstance(novo, tipos_numericos):
            try:
                return Decimal(str(atual)) == Decimal(str(novo))
            except Exception:
                return False

        return False

    async def _resolver_vinculo_por_id(
        self,
        propriedade_id: uuid.UUID,
        bloco,
    ) -> PropriedadeImovel | None:
        """Atualiza um vínculo explicitamente apontado, mesmo sem bloco de imóvel."""
        if bloco is None or bloco.id is None:
            return None
        vinculo = await self.vinculo_svc.obter(bloco.id)
        update_data = self._payload_vinculo(bloco, propriedade_id, vinculo.imovel_rural_id)
        if update_data:
            vinculo = await self.vinculo_svc.atualizar(vinculo.id, update_data, self.user_id)
        if self._vinculo_principal(bloco):
            vinculo = await self.vinculo_svc.definir_vinculo_principal(propriedade_id, vinculo.id, self.user_id)
        return vinculo

    async def _buscar_propriedade_da_unidade(self, unidade_id: uuid.UUID):
        """Resolve a propriedade pela exploração vigente da UP."""
        exploracoes = await self.expl_svc.listar_por_fazenda(unidade_id)
        if not exploracoes:
            return None
        propriedade_id = exploracoes[0].propriedade_id
        return await self.prop_svc.get(propriedade_id)

    async def _buscar_vinculo(self, propriedade_id: uuid.UUID, imovel_id: uuid.UUID):
        """Busca o vínculo canônico atual entre propriedade e imóvel."""
        vinculos = await self.vinculo_svc.listar(
            propriedade_id=propriedade_id,
            imovel_rural_id=imovel_id,
        )
        return vinculos[0] if vinculos else None

    def _propriedade_padrao(self, unidade, bloco) -> dict[str, Any]:
        """Monta a propriedade mínima quando o bloco não foi enviado."""
        nome = getattr(bloco, "nome", None) or unidade.nome
        payload = {"nome": nome}
        for campo in ("cpf_cnpj", "inscricao_estadual", "ie_isento", "email", "telefone", "nome_fantasia", "regime_tributario", "cor", "icone", "ordem", "ativo", "observacoes"):
            valor = getattr(bloco, campo, None) if bloco is not None else None
            if valor is not None:
                payload[campo] = valor
        return payload

    def _payload_imovel(self, unidade, bloco) -> dict[str, Any]:
        """Normaliza o bloco de imóvel para o payload canônico do service."""
        payload = bloco.model_dump(exclude={"id"}, exclude_none=True)
        payload["nome"] = payload.get("nome") or unidade.nome
        payload["municipio"] = payload.get("municipio") or unidade.municipio or "Não informado"
        payload["uf"] = payload.get("uf") or unidade.uf or "NI"
        payload["area_total_ha"] = payload.get("area_total_ha") or unidade.area_total_ha or Decimal("0")
        return payload

    def _payload_vinculo(self, bloco, propriedade_id: uuid.UUID, imovel_id: uuid.UUID) -> PropriedadeImovelUpdate:
        """Cria o payload de vínculo com IDs explícitos e sem campos legados."""
        payload = bloco.model_dump(exclude={"id"}, exclude_none=True) if bloco is not None else {}
        payload.pop("id", None)
        payload.pop("propriedade_id", None)
        payload.pop("imovel_rural_id", None)
        payload.pop("vinculo_principal", None)
        payload["propriedade_id"] = propriedade_id
        payload["imovel_rural_id"] = imovel_id
        return PropriedadeImovelUpdate(**payload) if payload else PropriedadeImovelUpdate(
            propriedade_id=propriedade_id,
            imovel_rural_id=imovel_id,
        )

    @staticmethod
    def _natureza_padrao(bloco) -> str:
        """Define a natureza da exploração quando o bloco não traz valor explícito."""
        if bloco is not None and getattr(bloco, "natureza", None):
            return str(bloco.natureza)
        return NaturezaVinculo.PROPRIA.value

    @staticmethod
    def _tipo_vinculo(bloco) -> TipoVinculoPropriedadeImovel | None:
        """Obtém o tipo de vínculo quando o bloco o informar."""
        if bloco is None:
            return None
        return getattr(bloco, "tipo_vinculo", None)

    @staticmethod
    def _vinculo_principal(bloco) -> bool | None:
        """Lê o pedido explícito de principalidade do bloco de vínculo."""
        if bloco is None:
            return None
        return getattr(bloco, "vinculo_principal", None)

    @staticmethod
    def _origem_documental(bloco) -> str:
        """Define a origem documental segura do vínculo."""
        if bloco is not None and getattr(bloco, "origem_documental", None):
            return str(bloco.origem_documental)
        return "Cadastro completo da propriedade"

    @staticmethod
    def _data_inicio(bloco) -> date:
        """Define a vigência inicial do vínculo."""
        if bloco is not None and getattr(bloco, "data_inicio", None):
            return bloco.data_inicio
        return date.today()

    @staticmethod
    def _tipo_imovel(bloco) -> TipoImovel:
        """Define o tipo do imóvel com fallback para rural."""
        if bloco is None:
            return TipoImovel.RURAL
        valor = getattr(bloco, "tipo", None)
        if not valor:
            return TipoImovel.RURAL
        try:
            return TipoImovel(valor)
        except ValueError:
            return TipoImovel.RURAL
