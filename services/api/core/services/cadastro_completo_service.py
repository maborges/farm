import uuid
from decimal import Decimal
from typing import Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.schemas.cadastro_completo_input import CadastroCompletoCreate, CadastroCompletoUpdate
from core.services.unidade_produtiva_service import UnidadeProdutivaService
from core.cadastros.propriedades.propriedade_service import PropriedadeService, ExploracaoRuralService
from core.cadastros.propriedades.propriedade_models import Propriedade, ExploracaoRural
from core.cadastros.propriedades.propriedade_schemas import ExploracaoCreate, ExploracaoUpdate
from imoveis.services.imovel_service import ImovelService
from core.cadastros.propriedade_imovel.service import PropriedadeImovelService
from core.cadastros.propriedade_imovel.models import TipoVinculoPropriedadeImovel

class CadastroCompletoService:
    """
    Orquestrador para criação unificada (Tela de Propriedade).
    Garante a integridade entre UnidadeProdutiva, Propriedade, ImovelRural e PropriedadeImovel.
    """
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
        return False

    async def criar_cadastro_completo(self, dados: CadastroCompletoCreate):
        setattr(dados, '_bypass_sincronismo', True)

        try:
            async with self.session.begin_nested():
                # 1. Unidade Produtiva (remove fundiários p/ evitar inserção direta)
                up_data = dados.model_dump(exclude={"propriedade_id", "imovel_rural_id", "propriedade_imovel_id"})
                
                unidade = await self.up_svc.create_unidade_produtiva(dados.__class__(**up_data))
                setattr(dados, '_bypass_sincronismo', True) # re-set in case inner call wiped it
                
                # 2. Propriedade (Cria a estrutura base de área rural caso não exista)
                from core.cadastros.propriedades.service import AreaRuralService
                from core.cadastros.propriedades.models import AreaRural
                area_svc = AreaRuralService(AreaRural, self.session, self.tenant_id)
                await area_svc.criar_estrutura_base(unidade.id)
                
                prop = None
                if dados.propriedade_id:
                    prop = await self.prop_svc.get(dados.propriedade_id)
                
                if not prop:
                    # Tenta ver se foi criado implicitamente por trigger ou hook (embora o normal seja criar aqui)
                    # Não, o padrão da aplicação anterior era UP não ter Propriedade até criar um arrendamento.
                    # Mas agora queremos garantir que sempre tenha Propriedade (A UP *é* uma Propriedade)
                    prop_data = {
                        "nome": unidade.nome,
                        "area_total_ha": unidade.area_total_ha or Decimal('0'),
                        "tipo": "PROPRIA" if unidade.tipo_propriedade == "fazenda" else "ARRENDADA",
                    }
                    prop = await self.prop_svc.create(prop_data)

                # 3. Exploracao Rural (Ponte UP <-> Propriedade)
                expl = await self.expl_svc.criar(
                    propriedade_id=prop.id,
                    data=ExploracaoCreate(
                        unidade_produtiva_id=unidade.id,
                        natureza="PROPRIA" if unidade.tipo_propriedade == "fazenda" else "ARRENDAMENTO",
                        data_inicio=date.today(),
                        area_explorada_ha=unidade.area_total_ha
                    )
                )


                
                return await self.up_svc.get(unidade.id)
        except IntegrityError as exc:
            logger.warning(f"Erro de integridade no cadastro completo: {exc}")
            raise HTTPException(status_code=400, detail="Erro de integridade nos dados fundiários (NIRF/Matrícula duplicada ou conflito de vínculo principal).")

    async def atualizar_cadastro_completo(self, id: uuid.UUID, dados: CadastroCompletoUpdate):
        setattr(dados, '_bypass_sincronismo', True)

        try:
            async with self.session.begin_nested():
                # 1. Unidade Produtiva (Atualizar sem campos fundiários legados)
                up_data = dados.model_dump(exclude={"propriedade_id", "imovel_rural_id", "propriedade_imovel_id"}, exclude_unset=True)
                
                # Explicitly pass bypass flag
                from core.schemas.unidade_produtiva_input import UnidadeProdutivaUpdate
                update_schema = UnidadeProdutivaUpdate(**up_data)
                setattr(update_schema, '_bypass_sincronismo', True)

                unidade = await self.up_svc.update(id, update_schema)
                
                # Recuperar a propriedade associada
                exploracoes = await self.expl_svc.listar_por_fazenda(unidade.id)
                prop = None
                
                # Resolve pendência dos 86 legados
                if not exploracoes:
                    prop_data = {
                        "nome": unidade.nome,
                        "area_total_ha": unidade.area_total_ha or Decimal('0'),
                        "tipo": "PROPRIA" if unidade.tipo_propriedade == "fazenda" else "ARRENDADA",
                    }
                    prop = await self.prop_svc.create(prop_data)
                    await self.expl_svc.criar(
                        propriedade_id=prop.id,
                        data=ExploracaoCreate(
                            unidade_produtiva_id=unidade.id,
                            natureza="PROPRIA" if unidade.tipo_propriedade == "fazenda" else "ARRENDAMENTO",
                            data_inicio=date.today(),
                            area_explorada_ha=unidade.area_total_ha
                        )
                    )
                else:
                    prop = await self.prop_svc.get(exploracoes[0].propriedade_id)

                # 2. Imovel Rural
                imovel = None
                if dados.imovel_rural_id:
                    imovel = await self.imovel_svc.get_imovel_by_id(dados.imovel_rural_id, self.tenant_id)

                # Se não tem imovel rural, mas vieram dados fundiários, pode ser um orfão ou o usuário preenchendo agora
                if not imovel and self._tem_dados_fundiarios(dados):
                    try:
                        imovel, alertas = await self.imovel_svc.criar_imovel(
                            tenant_id=self.tenant_id,
                            unidade_produtiva_id=unidade.id,
                            nome=unidade.nome,
                            municipio=unidade.municipio or "Não informado",
                            uf=unidade.uf or "NI",
                            area_total_ha=unidade.area_total_ha or Decimal('0'),
                            nirf=getattr(dados, 'nirf', None),
                            car_numero=getattr(dados, 'codigo_car', None),
                            ccir_numero=getattr(dados, 'ccir', None),
                            numero_matricula=getattr(dados, 'numero_matricula', None),
                            propriedade_id=prop.id,
                            tipo_vinculo=None,
                            created_by=self.user_id
                        )
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=str(e))
                elif imovel and self._tem_dados_fundiarios(dados):
                    try:
                        imovel_data = {}
                        if getattr(dados, 'nirf', None) is not None: imovel_data["nirf"] = getattr(dados, 'nirf')
                        if getattr(dados, 'codigo_car', None) is not None: imovel_data["car_numero"] = getattr(dados, 'codigo_car')
                        if getattr(dados, 'ccir', None) is not None: imovel_data["ccir_numero"] = getattr(dados, 'ccir')
                        if getattr(dados, 'numero_matricula', None) is not None: imovel_data["numero_matricula"] = getattr(dados, 'numero_matricula')
                        if getattr(dados, 'sigef_codigo', None) is not None: imovel_data["sigef_codigo"] = getattr(dados, 'sigef_codigo')

                        if getattr(dados, 'area_total_ha', None) is not None:
                            imovel_data["area_total_ha"] = dados.area_total_ha
                            imovel_data["motivo_alteracao_area"] = "Atualização via Cadastro Completo (UI Unificada)"

                        await self.imovel_svc.atualizar_imovel(
                            imovel=imovel,
                            dados=imovel_data,
                            usuario_id=self.user_id
                        )
                        
                        # Garante vínculo
                        await self.imovel_svc._garantir_vinculo_propriedade_imovel(
                            propriedade_id=prop.id,
                            imovel=imovel,
                            tipo_vinculo=None,
                            usuario_id=self.user_id
                        )

                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=str(e))
                
                return await self.up_svc.get(unidade.id)
        except IntegrityError as exc:
            logger.warning(f"Erro de integridade na atualização do cadastro completo: {exc}")
            raise HTTPException(status_code=400, detail="Conflito de integridade nos dados fundiários (Vínculo principal existente ou duplicidade).")
