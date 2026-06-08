from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
import sqlalchemy as sa
from core.base_service import BaseService
from core.exceptions import EntityNotFoundError, BusinessRuleError
from agricola.rastreabilidade.models import LoteRastreabilidade, CertificacaoPropriedade, CadernoLoteComercial
from agricola.rastreabilidade.schemas import LoteRastreabilidadeCreate, CertificacaoCreate, LoteComercialCreate


class RastreabilidadeService(BaseService[LoteRastreabilidade]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(LoteRastreabilidade, session, tenant_id)

    @staticmethod
    async def buscar_por_codigo(session: AsyncSession, codigo_lote: str):
        """Busca pública por código de lote — sem filtro de tenant."""
        stmt = select(LoteRastreabilidade).where(LoteRastreabilidade.codigo_lote == codigo_lote)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def criar_lote(self, dados: LoteRastreabilidadeCreate) -> LoteRastreabilidade:
        dados_dict = dados.model_dump()
        dados_dict["qr_code_url"] = f"https://api.agrosaas.com/v1/public/track/{dados.codigo_lote}"
        return await super().create(dados_dict)

    async def cadeia_rastreabilidade(self, lote_id: UUID) -> dict:
        from agricola.safras.models import Safra
        from core.cadastros.propriedades.models import AreaRural
        from agricola.operacoes.models import OperacaoAgricola, InsumoOperacao
        from agricola.romaneios.models import RomaneioColheita
        from core.cadastros.models import ProdutoCatalogo as Produto
        from agricola.colheita.models import ProdutoColhido
        from financeiro.comercializacao.models import ComercializacaoCommodity
        from core.cadastros.commodities.models import Commodity

        lote = await self.get_or_fail(lote_id)

        # Safra
        safra = await self.session.get(Safra, lote.safra_id)
        if not safra:
            raise EntityNotFoundError(f"Safra {lote.safra_id} não encontrada.")

        # Talhão
        talhao = await self.session.get(AreaRural, lote.talhao_id)

        # Operações agrícolas no talhão/safra (com insumos via selectin)
        stmt_ops = (
            select(OperacaoAgricola)
            .where(
                OperacaoAgricola.safra_id == lote.safra_id,
                OperacaoAgricola.talhao_id == lote.talhao_id,
                OperacaoAgricola.tenant_id == self.tenant_id,
            )
            .order_by(OperacaoAgricola.data_realizada)
        )
        operacoes = list((await self.session.execute(stmt_ops)).scalars().all())

        # Busca nomes dos produtos dos insumos
        produto_ids = {i.produto_id for op in operacoes for i in op.insumos}
        produtos: dict[UUID, Produto] = {}
        if produto_ids:
            stmt_prods = select(Produto).where(Produto.id.in_(produto_ids))
            produtos = {p.id: p for p in (await self.session.execute(stmt_prods)).scalars().all()}

        # Romaneios
        stmt_rom = (
            select(RomaneioColheita)
            .where(
                RomaneioColheita.safra_id == lote.safra_id,
                RomaneioColheita.talhao_id == lote.talhao_id,
                RomaneioColheita.tenant_id == self.tenant_id,
            )
            .order_by(RomaneioColheita.data_colheita)
        )
        romaneios = list((await self.session.execute(stmt_rom)).scalars().all())

        # ── ProdutoColhido (estoque colhido classificado) ───────────
        stmt_pc = (
            select(ProdutoColhido)
            .where(
                ProdutoColhido.safra_id == lote.safra_id,
                ProdutoColhido.talhao_id == lote.talhao_id,
                ProdutoColhido.tenant_id == self.tenant_id,
            )
            .order_by(ProdutoColhido.data_entrada)
        )
        produtos_colhidos = list((await self.session.execute(stmt_pc)).scalars().all())

        # Buscar dados das commodities
        pc_commodity_ids = {pc.commodity_id for pc in produtos_colhidos}
        commodities: dict[UUID, Commodity] = {}
        if pc_commodity_ids:
            stmt_comm = select(Commodity).where(Commodity.id.in_(pc_commodity_ids))
            commodities = {c.id: c for c in (await self.session.execute(stmt_comm)).scalars().all()}

        # ── Comercializações (vendas vinculadas aos produtos colhidos) ─
        pc_ids = [pc.id for pc in produtos_colhidos]
        comercializacoes = []
        if pc_ids:
            stmt_comm = (
                select(ComercializacaoCommodity)
                .where(ComercializacaoCommodity.produto_colhido_id.in_(pc_ids))
                .order_by(ComercializacaoCommodity.created_at)
            )
            comercializacoes = list((await self.session.execute(stmt_comm)).scalars().all())

        # Monta resposta
        return {
            "lote": {
                "id": str(lote.id),
                "codigo_lote": lote.codigo_lote,
                "produto": lote.produto,
                "variedade": lote.variedade,
                "quantidade_total": lote.quantidade_total,
                "unidade": lote.unidade,
                "status": lote.status,
                "certificacoes": lote.certificacoes,
                "qr_code_url": lote.qr_code_url,
                "data_geracao": lote.data_geracao.isoformat() if lote.data_geracao else None,
            },
            "safra": {
                "id": str(safra.id),
                "cultura": safra.cultura,
                "ano_safra": safra.ano_safra,
                "area_plantada_ha": float(safra.area_plantada_ha or 0),
                "status": safra.status,
            },
            "talhao": {
                "id": str(talhao.id) if talhao else None,
                "nome": talhao.nome if talhao else "—",
                "area_ha": float(talhao.area_hectares or talhao.area_hectares_manual or 0) if talhao else 0,
            } if talhao else None,
            "operacoes": [
                {
                    "id": str(op.id),
                    "tipo": op.tipo,
                    "subtipo": op.subtipo,
                    "descricao": op.descricao,
                    "data_realizada": op.data_realizada.isoformat(),
                    "area_aplicada_ha": float(op.area_aplicada_ha or 0),
                    "custo_total": float(op.custo_total or 0),
                    "status": op.status,
                    "insumos": [
                        {
                            "produto_nome": produtos[i.produto_id].nome if i.produto_id in produtos else str(i.produto_id),
                            "unidade": i.unidade,
                            "dose_por_ha": float(i.dose_por_ha or 0),
                            "quantidade_total": float(i.quantidade_total or 0),
                            "custo_total": float(i.custo_total or 0),
                        }
                        for i in op.insumos
                    ],
                }
                for op in operacoes
            ],
            "romaneios": [
                {
                    "id": str(r.id),
                    "numero_romaneio": r.numero_romaneio,
                    "data_colheita": r.data_colheita.isoformat(),
                    "peso_bruto_kg": float(r.peso_bruto_kg or 0),
                    "peso_liquido_kg": float(r.peso_liquido_kg or 0),
                    "sacas_60kg": float(r.sacas_60kg or 0),
                    "umidade_pct": float(r.umidade_pct or 0),
                    "impureza_pct": float(r.impureza_pct or 0),
                    "destino": r.destino,
                    "receita_total": float(r.receita_total or 0),
                }
                for r in romaneios
            ],
            "produtos_colhidos": [
                {
                    "id": str(pc.id),
                    "commodity_nome": commodities[pc.commodity_id].nome if pc.commodity_id in commodities else None,
                    "commodity_codigo": commodities[pc.commodity_id].codigo if pc.commodity_id in commodities else None,
                    "quantidade": float(pc.quantidade),
                    "unidade": pc.unidade,
                    "peso_liquido_kg": float(pc.peso_liquido_kg),
                    "umidade_pct": float(pc.umidade_pct) if pc.umidade_pct else None,
                    "impureza_pct": float(pc.impureza_pct) if pc.impureza_pct else None,
                    "status": pc.status,
                    "destino": pc.destino,
                    "data_entrada": pc.data_entrada.isoformat(),
                }
                for pc in produtos_colhidos
            ],
            "comercializacoes": [
                {
                    "id": str(c.id),
                    "numero_contrato": c.numero_contrato,
                    "comprador_id": str(c.comprador_id),
                    "quantidade": float(c.quantidade),
                    "unidade": c.unidade,
                    "preco_unitario": float(c.preco_unitario),
                    "valor_total": float(c.valor_total),
                    "moeda": c.moeda,
                    "status": c.status,
                    "forma_pagamento": c.forma_pagamento,
                    "data_entrega_prevista": c.data_entrega_prevista.isoformat() if c.data_entrega_prevista else None,
                    "data_entrega_real": c.data_entrega_real.isoformat() if c.data_entrega_real else None,
                    "nf_numero": c.nf_numero,
                }
                for c in comercializacoes
            ],
            "resumo": {
                "total_operacoes": len(operacoes),
                "custo_total_operacoes": round(sum(float(op.custo_total or 0) for op in operacoes), 2),
                "total_insumos_aplicados": sum(len(op.insumos) for op in operacoes),
                "total_colhido_sacas": round(sum(float(r.sacas_60kg or 0) for r in romaneios), 2),
                "total_estoque_kg": round(sum(float(pc.peso_liquido_kg or 0) for pc in produtos_colhidos), 2),
                "total_vendido_kg": round(
                    sum(float(c.valor_total or 0) for c in comercializacoes if c.status == "FINALIZADO"), 2
                ),
                "receita_total_romaneios": round(sum(float(r.receita_total or 0) for r in romaneios), 2),
                "receita_total_comercializacoes": round(sum(float(c.valor_total or 0) for c in comercializacoes), 2),
            },
        }


class CertificacaoService(BaseService[CertificacaoPropriedade]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(CertificacaoPropriedade, session, tenant_id)


class LoteComercialService(BaseService[CadernoLoteComercial]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(CadernoLoteComercial, session, tenant_id)

    @staticmethod
    async def buscar_por_token(session: AsyncSession, qr_code_token: str):
        """Busca pública de lote comercial pelo token de QR code — sem filtro de tenant."""
        stmt = select(CadernoLoteComercial).where(CadernoLoteComercial.qr_code_token == qr_code_token)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def criar_lote_comercial(self, dados: LoteComercialCreate) -> CadernoLoteComercial:
        # 1. Deve existir produto_colhido_id ou lote_beneficiamento_id
        if not dados.produto_colhido_id and not dados.lote_beneficiamento_id:
            raise BusinessRuleError("Deve ser informado pelo menos um produto colhido ou um lote de beneficiamento como origem física.")

        if dados.produto_colhido_id and dados.lote_beneficiamento_id:
            raise BusinessRuleError("Informe apenas o produto colhido ou o lote de beneficiamento, não ambos.")

        # Validar existência da comercialização e que pertence ao mesmo tenant
        from financeiro.comercializacao.models import ComercializacaoCommodity
        comercializacao = await self.session.get(ComercializacaoCommodity, dados.comercializacao_id)
        if not comercializacao or comercializacao.tenant_id != self.tenant_id:
            raise EntityNotFoundError("Comercialização não encontrada.")

        # Validar saldo físico de estoque (não exceder peso físico do lote)
        if dados.produto_colhido_id:
            from agricola.colheita.models import ProdutoColhido
            prod_colhido = await self.session.get(ProdutoColhido, dados.produto_colhido_id)
            if not prod_colhido or prod_colhido.tenant_id != self.tenant_id:
                raise EntityNotFoundError("Produto colhido não encontrado.")
            peso_origem = float(prod_colhido.peso_liquido_kg)
            stmt_sum = select(sa.func.sum(CadernoLoteComercial.peso_liquido_kg)).where(
                CadernoLoteComercial.produto_colhido_id == dados.produto_colhido_id,
                CadernoLoteComercial.tenant_id == self.tenant_id,
                CadernoLoteComercial.status != "REVOGADO"
            )
            peso_consumido = (await self.session.execute(stmt_sum)).scalar() or 0.0
            if peso_consumido + dados.peso_liquido_kg > peso_origem:
                raise BusinessRuleError(f"O peso total comercializado ({peso_consumido + dados.peso_liquido_kg} kg) excede o peso físico do produto colhido ({peso_origem} kg).")

        elif dados.lote_beneficiamento_id:
            from agricola.beneficiamento.models import LoteBeneficiamento
            lote_benef = await self.session.get(LoteBeneficiamento, dados.lote_beneficiamento_id)
            if not lote_benef or lote_benef.tenant_id != self.tenant_id:
                raise EntityNotFoundError("Lote de beneficiamento não encontrado.")
            peso_origem = float(lote_benef.peso_saida_kg or lote_benef.peso_entrada_kg or 0.0)
            stmt_sum = select(sa.func.sum(CadernoLoteComercial.peso_liquido_kg)).where(
                CadernoLoteComercial.lote_beneficiamento_id == dados.lote_beneficiamento_id,
                CadernoLoteComercial.tenant_id == self.tenant_id,
                CadernoLoteComercial.status != "REVOGADO"
            )
            peso_consumido = (await self.session.execute(stmt_sum)).scalar() or 0.0
            if peso_consumido + dados.peso_liquido_kg > peso_origem:
                raise BusinessRuleError(f"O peso total comercializado ({peso_consumido + dados.peso_liquido_kg} kg) excede o peso físico do lote de beneficiamento ({peso_origem} kg).")

        # Gerar token seguro de alta entropia
        import secrets
        qr_code_token = secrets.token_hex(32)

        dados_dict = dados.model_dump()
        dados_dict["tenant_id"] = self.tenant_id
        dados_dict["qr_code_token"] = qr_code_token
        dados_dict["status"] = "RASCUNHO"

        lote_comercial = CadernoLoteComercial(**dados_dict)
        self.session.add(lote_comercial)
        await self.session.commit()
        await self.session.refresh(lote_comercial)
        return lote_comercial

    async def gerar_snapshot_passaporte(self, lote_id: UUID, user_id: UUID) -> CadernoLoteComercial:
        import json
        import hashlib
        from datetime import datetime, date
        from agricola.colheita.models import ProdutoColhido
        from agricola.beneficiamento.models import LoteBeneficiamento
        from core.cadastros.commodities.models import Commodity, CommodityClassificacao
        from agricola.safras.models import Safra
        from core.cadastros.propriedades.models import AreaRural
        from core.models.unidade_produtiva import UnidadeProdutiva
        from agricola.caderno.models import CadernoCampoEntrada, CadernoCampoFoto
        from core.services.audit_service import write_audit_log

        lote = await self.get_or_fail(lote_id)

        safra_id = None
        talhao_id = None
        data_origem = None

        commodity_nome = "Café"
        variedade_nome = None

        if lote.produto_colhido_id:
            prod_colhido = await self.session.get(ProdutoColhido, lote.produto_colhido_id)
            if not prod_colhido or prod_colhido.tenant_id != self.tenant_id:
                raise EntityNotFoundError("Produto colhido não encontrado.")
            safra_id = prod_colhido.safra_id
            talhao_id = prod_colhido.talhao_id
            data_origem = prod_colhido.data_entrada

            commodity = await self.session.get(Commodity, prod_colhido.commodity_id)
            if commodity:
                commodity_nome = commodity.nome
            if prod_colhido.classificacao_id:
                classificacao = await self.session.get(CommodityClassificacao, prod_colhido.classificacao_id)
                if classificacao:
                    variedade_nome = classificacao.classe

        elif lote.lote_beneficiamento_id:
            lote_benef = await self.session.get(LoteBeneficiamento, lote.lote_beneficiamento_id)
            if not lote_benef or lote_benef.tenant_id != self.tenant_id:
                raise EntityNotFoundError("Lote de beneficiamento não encontrado.")
            safra_id = lote_benef.safra_id
            talhao_id = lote_benef.talhao_id
            data_origem = lote_benef.data_saida or lote_benef.data_entrada

            commodity_nome = f"Café {lote_benef.metodo.upper()}"
            if lote_benef.cultivo_id:
                from agricola.cultivos.models import Cultivo
                cultivo = await self.session.get(Cultivo, lote_benef.cultivo_id)
                if cultivo:
                    variedade_nome = cultivo.nome
        else:
            raise BusinessRuleError("Origem física não configurada para este lote comercial.")

        safra = await self.session.get(Safra, safra_id)
        if not safra:
            raise EntityNotFoundError("Safra não encontrada.")

        talhao = await self.session.get(AreaRural, talhao_id)
        if not talhao:
            raise EntityNotFoundError("Talhão não encontrado.")

        up = await self.session.get(UnidadeProdutiva, talhao.unidade_produtiva_id)
        if not up:
            raise EntityNotFoundError("Unidade produtiva não encontrada.")

        stmt_cert = select(CertificacaoPropriedade).where(
            CertificacaoPropriedade.unidade_produtiva_id == talhao.unidade_produtiva_id,
            CertificacaoPropriedade.tenant_id == self.tenant_id,
            CertificacaoPropriedade.status == "VALIDA",
            CertificacaoPropriedade.data_validade >= datetime.utcnow().date()
        )
        certificacoes = (await self.session.execute(stmt_cert)).scalars().all()

        certificacoes_ativas = [
            {
                "nome": c.nome,
                "extensao": c.extensao,
                "numero_registro": c.numero_registro,
                "data_validade": c.data_validade.isoformat() if isinstance(c.data_validade, (date, datetime)) else str(c.data_validade),
                "orgao_certificador": c.orgao_certificador
            }
            for c in certificacoes
        ]

        stmt_events = (
            select(CadernoCampoEntrada)
            .where(
                CadernoCampoEntrada.safra_id == safra_id,
                CadernoCampoEntrada.talhao_id == talhao_id,
                CadernoCampoEntrada.tenant_id == self.tenant_id,
                CadernoCampoEntrada.status_evento.in_(["CONSOLIDADO", "APROVADO"]),
                CadernoCampoEntrada.excluida == False,
                CadernoCampoEntrada.origem_invalidada == False,
                CadernoCampoEntrada.retificado_por_evento_id == None
            )
            .order_by(CadernoCampoEntrada.data_registro)
        )
        events = (await self.session.execute(stmt_events)).scalars().all()

        timeline_events = []
        fotos_publicas = []

        for ev in events:
            stmt_photos = select(CadernoCampoFoto).where(
                CadernoCampoFoto.entrada_id == ev.id,
                CadernoCampoFoto.publica == True
            )
            photos = (await self.session.execute(stmt_photos)).scalars().all()

            ev_photos = []
            for p in photos:
                photo_data = {
                    "url": p.url,
                    "latitude": float(p.latitude) if p.latitude is not None else None,
                    "longitude": float(p.longitude) if p.longitude is not None else None,
                    "data_captura": p.data_captura.isoformat() if p.data_captura else None
                }
                ev_photos.append(photo_data)
                fotos_publicas.append(photo_data)

            timeline_events.append({
                "id": str(ev.id),
                "tipo": ev.tipo,
                "tipo_evento": ev.tipo_evento,
                "descricao": ev.descricao,
                "data_registro": ev.data_registro.isoformat() if isinstance(ev.data_registro, (date, datetime)) else str(ev.data_registro),
                "fotos": ev_photos
            })

        protocolo = f"PRC-{datetime.utcnow().year}-{lote.id.hex[:8].upper()}"

        # Escopo 6 — Passaporte: Auditoria de Equipamento & Calibração
        equipamento_calibrado = None
        data_ultima_calibracao = None
        conformidade_sanitaria = None

        operacoes_com_maquina = []
        for ev in events:
            if ev.operacao_id:
                from agricola.operacoes.models import OperacaoAgricola
                op = await self.session.get(OperacaoAgricola, ev.operacao_id)
                if op and op.maquina_id:
                    operacoes_com_maquina.append(op)

        if operacoes_com_maquina:
            from core.cadastros.equipamentos.models import Equipamento, EquipamentoCalibracao
            from operacional.models.checklist import ChecklistRealizado, ChecklistModelo
            from sqlalchemy import Date, func

            equipamento_calibrado = False
            conformidade_sanitaria = False

            maquinas_ids = {op.maquina_id for op in operacoes_com_maquina}
            for mq_id in maquinas_ids:
                mq = await self.session.get(Equipamento, mq_id)
                if mq and mq.tipo == "PULVERIZADOR":
                    # Busca última calibração da máquina
                    calib_stmt = (
                        select(EquipamentoCalibracao)
                        .where(
                            EquipamentoCalibracao.equipamento_id == mq_id,
                            EquipamentoCalibracao.tenant_id == self.tenant_id
                        )
                        .order_by(EquipamentoCalibracao.data_calibracao.desc())
                        .limit(1)
                    )
                    last_calib = (await self.session.execute(calib_stmt)).scalars().first()
                    if last_calib:
                        equipamento_calibrado = True
                        data_ultima_calibracao = last_calib.data_calibracao.isoformat()

                    # Verifica se houve checklist sanitário aprovado nos dias das operações
                    checklists_aprovados = True
                    for op in operacoes_com_maquina:
                        if op.maquina_id == mq_id:
                            chk_stmt = (
                                select(ChecklistRealizado)
                                .join(ChecklistModelo)
                                .where(
                                    ChecklistRealizado.tenant_id == self.tenant_id,
                                    ChecklistRealizado.equipamento_id == mq_id,
                                    ChecklistRealizado.liberado_para_uso == True,
                                    func.cast(ChecklistRealizado.data_hora, Date) == op.data_realizada,
                                    (ChecklistModelo.nome.ilike("%sanit%") | ChecklistModelo.nome.ilike("%limpez%") | ChecklistModelo.nome.ilike("%higien%"))
                                )
                            )
                            chk = (await self.session.execute(chk_stmt)).scalars().first()
                            if not chk:
                                checklists_aprovados = False
                                break
                    if checklists_aprovados:
                        conformidade_sanitaria = True

        snapshot_data = {
            "lote_codigo": lote.codigo_lote,
            "produto": commodity_nome,
            "variedade": variedade_nome,
            "peso_liquido_kg": float(lote.peso_liquido_kg),
            "quantidade_volumes": int(lote.quantidade_volumes),
            "safra": safra.ano_safra,
            "fazenda": up.nome,
            "municipio": up.municipio,
            "uf": up.uf,
            "talhoes": [talhao.nome],
            "geometria": talhao.geometria,
            "centroide_lat": float(talhao.centroide_lat) if talhao.centroide_lat is not None else None,
            "centroide_lng": float(talhao.centroide_lng) if talhao.centroide_lng is not None else None,
            "talhao_area_ha": float(talhao.area_hectares or talhao.area_hectares_manual or 0) if talhao else 0,
            "datas_principais": {
                "criado_em": lote.created_at.isoformat() if lote.created_at else datetime.utcnow().isoformat(),
                "data_entrada_origem": data_origem.isoformat() if isinstance(data_origem, (date, datetime)) else str(data_origem),
            },
            "timeline": timeline_events,
            "certificacoes": certificacoes_ativas,
            "fotos": fotos_publicas,
            "protocolo": protocolo,
            "equipamento_calibrado": equipamento_calibrado,
            "data_ultima_calibracao": data_ultima_calibracao,
            "conformidade_sanitaria": conformidade_sanitaria
        }

        canonical_json = json.dumps(snapshot_data, sort_keys=True, default=str)
        snapshot_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

        lote.snapshot_json = snapshot_data
        lote.snapshot_hash = snapshot_hash
        lote.snapshot_gerado_em = datetime.utcnow()
        lote.assinado_por_usuario_id = user_id
        lote.assinado_em = datetime.utcnow()
        lote.status = "ATIVO"

        self.session.add(lote)
        await self.session.commit()
        await self.session.refresh(lote)

        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=user_id,
            action="sign_passport",
            resource="caderno_lotes_comerciais",
            resource_id=lote.id,
            payload_before={"status": "RASCUNHO"},
            payload_after={"status": "ATIVO", "hash": snapshot_hash}
        )

        return lote

    async def gerar_qrcode_svg(self, lote_id: UUID) -> str:
        lote = await self.get_or_fail(lote_id)
        url = f"https://agrosaas.com.br/p/rastreabilidade/{lote.qr_code_token}"
        from reportlab.graphics.barcode.qr import QrCodeWidget
        widget = QrCodeWidget(url)
        widget.getBounds()
        if not widget.qr or not widget.qr.modules:
            raise BusinessRuleError("Falha ao gerar matriz do QR Code.")

        modules = widget.qr.modules
        size = len(modules)

        path_parts = []
        for y, row in enumerate(modules):
            for x, active in enumerate(row):
                if active:
                    path_parts.append(f"M{x},{y}h1v1h-1z")

        path_data = "".join(path_parts)

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100%" height="100%">'
            f'<path d="{path_data}" fill="#000000" shape-rendering="crispEdges"/>'
            f'</svg>'
        )
        return svg
