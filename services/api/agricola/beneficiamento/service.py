import uuid
from uuid import UUID
from datetime import date
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.services.audit_service import write_audit_log

from agricola.beneficiamento.models import LoteBeneficiamento, LoteBeneficiamentoCafeDetalhe
from agricola.beneficiamento.schemas import (
    BeneficiamentoKPIs,
    BeneficiamentoRelatorioRendimento,
    CafeQualidadeMargemItem,
    CafeQualidadeMargemPorBebida,
    CafeQualidadeMargemResponse,
    LoteBeneficiamentoCafeDetalheCreate,
    LoteBeneficiamentoCafeDetalheUpdate,
    LoteBeneficiamentoCreate,
    LoteBeneficiamentoUpdate,
    LoteFromRomaneiosRequest,
    RendimentoPorMetodo,
)
from agricola.beneficiamento.models import LoteBeneficiamentoRomaneio
from agricola.colheita.models import ProdutoColhido
from agricola.romaneios.models import RomaneioColheita
from agricola.qualidade_resolver import resolver_qualidade_efetiva

# Fatores de redução esperados por método de café (referência para cálculo de
# perda). Culturas sem `detalhe_cafe` usam `LoteBeneficiamento.fator_esperado_manual`.
FATOR_ESPERADO = {
    "NATURAL":    4.8,  # cereja seca com casca
    "LAVADO":     5.5,  # cereja despolpada+lavada
    "HONEY":      4.5,  # cereja despolpada s/ lavagem
    "DESCASCADO": 4.2,  # coco (já sem casca externa)
}


class BeneficiamentoService(BaseService[LoteBeneficiamento]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(LoteBeneficiamento, session, tenant_id)

    @staticmethod
    def _status_qualidade_produto(produto_colhido: ProdutoColhido | None, romaneio: RomaneioColheita) -> str | None:
        return resolver_qualidade_efetiva(produto_colhido, romaneio).qualidade_status

    @staticmethod
    def _peso_entrada_produto(produto_colhido: ProdutoColhido | None, romaneio: RomaneioColheita) -> float:
        qualidade = resolver_qualidade_efetiva(produto_colhido, romaneio)
        if qualidade.peso_liquido_comercial_kg is not None:
            return float(qualidade.peso_liquido_comercial_kg)

        if produto_colhido:
            if produto_colhido.peso_liquido_kg is not None:
                return float(produto_colhido.peso_liquido_kg)

        if romaneio.peso_liquido_padrao_kg is not None:
            return float(romaneio.peso_liquido_padrao_kg)
        return float(romaneio.peso_liquido_kg or 0)

    async def _get_produto_colhido_por_romaneio(self, romaneio_id: UUID) -> ProdutoColhido | None:
        stmt = select(ProdutoColhido).where(
            ProdutoColhido.tenant_id == self.tenant_id,
            ProdutoColhido.romaneio_id == romaneio_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _get_detalhe_cafe(self, lote_id: UUID) -> LoteBeneficiamentoCafeDetalhe | None:
        stmt = select(LoteBeneficiamentoCafeDetalhe).where(
            LoteBeneficiamentoCafeDetalhe.tenant_id == self.tenant_id,
            LoteBeneficiamentoCafeDetalhe.lote_id == lote_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _anexar_detalhe(self, lote: LoteBeneficiamento) -> LoteBeneficiamento:
        """`detalhe_cafe` é lazy='noload' (padrão do projeto, evita N+1) — para
        expor no response é preciso carregar e anexar explicitamente."""
        lote.detalhe_cafe = await self._get_detalhe_cafe(lote.id)
        return lote

    async def obter_com_detalhe(self, lote_id: UUID) -> LoteBeneficiamento:
        lote = await self.get_or_fail(lote_id)
        return await self._anexar_detalhe(lote)

    async def listar_com_detalhe(self, **filters) -> list[LoteBeneficiamento]:
        lotes = await self.list_all(**filters)
        for lote in lotes:
            await self._anexar_detalhe(lote)
        return lotes

    @staticmethod
    def _resolver_commodity_id(
        romaneio: RomaneioColheita | None,
        produto_colhido: ProdutoColhido | None,
    ) -> UUID | None:
        if romaneio and romaneio.commodity_id:
            return romaneio.commodity_id
        if produto_colhido and produto_colhido.commodity_id:
            return produto_colhido.commodity_id
        return None

    @staticmethod
    def _qualidade_estoque_metadata(
        *,
        lote_id: UUID,
        romaneio_id: UUID,
        qualidade_laudo_id: UUID | None,
        qualidade_status: str | None,
        peso_desconto_qualidade_kg: float,
    ) -> dict:
        return {
            "lote_beneficiamento_id": str(lote_id),
            "romaneio_id": str(romaneio_id),
            "qualidade_laudo_id": str(qualidade_laudo_id) if qualidade_laudo_id else None,
            "qualidade_status": qualidade_status,
            "peso_desconto_qualidade_kg": float(peso_desconto_qualidade_kg),
        }

    @staticmethod
    def _qualidade_estoque_observacao(metadata: dict) -> str:
        return (
            "Qualidade efetiva aplicada ao lote de estoque: "
            f"{json.dumps(metadata, ensure_ascii=False, sort_keys=True)}"
        )

    async def _bloquear_se_reprovado(
        self,
        romaneio: RomaneioColheita,
        produto_colhido: ProdutoColhido | None,
        contexto: str,
    ) -> None:
        status = self._status_qualidade_produto(produto_colhido, romaneio)
        if status != "REPROVADO":
            return

        payload = {
            "romaneio_id": str(romaneio.id),
            "produto_colhido_id": str(produto_colhido.id) if produto_colhido else None,
            "qualidade_status": status,
            "contexto": contexto,
        }
        await write_audit_log(
            session=self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action="block_quality_rejected",
            resource="agricola_lotes_beneficiamento",
            resource_id=None,
            payload_before=None,
            payload_after=payload,
            ip_address=self.ip_address,
        )
        raise BusinessRuleError("Beneficiamento bloqueado: item com qualidade REPROVADO.")

    async def _criar_detalhe_cafe(self, lote_id: UUID, dados: LoteBeneficiamentoCafeDetalheCreate) -> None:
        detalhe = LoteBeneficiamentoCafeDetalhe(
            tenant_id=self.tenant_id,
            lote_id=lote_id,
            **dados.model_dump(),
        )
        self.session.add(detalhe)
        await self.session.flush()

    async def criar(self, dados: LoteBeneficiamentoCreate) -> LoteBeneficiamento:
        d = dados.model_dump(exclude={"detalhe_cafe"})
        lote = await super().create(d)
        if dados.detalhe_cafe is not None:
            await self._criar_detalhe_cafe(lote.id, dados.detalhe_cafe)
            await self.session.commit()
            await self.session.refresh(lote)
        return await self._anexar_detalhe(lote)

    async def atualizar(self, lote_id: UUID, dados: LoteBeneficiamentoUpdate) -> LoteBeneficiamento:
        patch = dados.model_dump(exclude_unset=True, exclude={"detalhe_cafe"})

        # Recalcula campos derivados quando peso de saída é informado
        if "peso_saida_kg" in patch and patch["peso_saida_kg"]:
            lote = await self.get_or_fail(lote_id)
            peso_entrada = float(lote.peso_entrada_kg)
            peso_saida = float(patch["peso_saida_kg"])

            if peso_saida <= 0:
                raise BusinessRuleError("Peso de saída deve ser maior que zero.")
            if peso_saida > peso_entrada:
                raise BusinessRuleError("Peso de saída não pode ser maior que o peso de entrada.")

            # Fator de redução real
            fator_real = round(peso_entrada / peso_saida, 3)
            patch["fator_reducao"] = fator_real

            # Sacas de 60 kg beneficiadas
            patch["sacas_beneficiadas"] = round(peso_saida / 60.0, 3)

            # % de perda vs. fator esperado — café usa FATOR_ESPERADO[metodo] via
            # extensão; culturas sem extensão usam fator_esperado_manual informado
            # pelo usuário; sem nenhum dos dois, perda_pct não é calculada.
            detalhe_cafe = await self._get_detalhe_cafe(lote_id)
            fator_esp = (
                FATOR_ESPERADO.get(detalhe_cafe.metodo, 4.8) if detalhe_cafe
                else (patch.get("fator_esperado_manual") or lote.fator_esperado_manual)
            )
            if fator_esp:
                fator_esp = float(fator_esp)
                peso_esperado = peso_entrada / fator_esp
                patch["perda_pct"] = round((peso_esperado - peso_saida) / peso_esperado * 100, 2)

        # Calcula dias de secagem
        if "data_fim_secagem" in patch and patch["data_fim_secagem"]:
            lote = await self.get_or_fail(lote_id)
            inicio = patch.get("data_inicio_secagem") or lote.data_inicio_secagem
            if inicio:
                delta = (patch["data_fim_secagem"] - inicio).days
                patch["dias_secagem"] = max(0, delta)

        updated = await self.update(lote_id, patch)

        if dados.detalhe_cafe is not None:
            detalhe = await self._get_detalhe_cafe(lote_id)
            detalhe_patch = dados.detalhe_cafe.model_dump(exclude_unset=True)
            if detalhe is None:
                if "metodo" not in detalhe_patch:
                    raise BusinessRuleError("Método é obrigatório ao criar a extensão de café.")
                await self._criar_detalhe_cafe(
                    lote_id, LoteBeneficiamentoCafeDetalheCreate(**detalhe_patch)
                )
            else:
                for field, value in detalhe_patch.items():
                    setattr(detalhe, field, value)
                self.session.add(detalhe)
            await self.session.commit()
            await self.session.refresh(updated)

        return await self._anexar_detalhe(updated)

    async def kpis_safra(self, safra_id: UUID) -> BeneficiamentoKPIs:
        stmt = select(
            func.count(LoteBeneficiamento.id),
            func.coalesce(func.sum(LoteBeneficiamento.peso_entrada_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.peso_saida_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.sacas_beneficiadas), 0),
            func.avg(LoteBeneficiamento.fator_reducao),
        ).where(
            LoteBeneficiamento.tenant_id == self.tenant_id,
            LoteBeneficiamento.safra_id == safra_id,
        )
        row = (await self.session.execute(stmt)).first()

        stmt_scaa = select(func.avg(LoteBeneficiamentoCafeDetalhe.pontuacao_scaa)).select_from(
            LoteBeneficiamento
        ).join(
            LoteBeneficiamentoCafeDetalhe, LoteBeneficiamentoCafeDetalhe.lote_id == LoteBeneficiamento.id
        ).where(
            LoteBeneficiamento.tenant_id == self.tenant_id,
            LoteBeneficiamento.safra_id == safra_id,
        )
        pontuacao_media = (await self.session.execute(stmt_scaa)).scalar()

        stmt_proc = select(func.count(LoteBeneficiamento.id)).where(
            LoteBeneficiamento.tenant_id == self.tenant_id,
            LoteBeneficiamento.safra_id == safra_id,
            LoteBeneficiamento.status.in_(["RECEBIMENTO", "SECAGEM", "CLASSIFICACAO"]),
        )
        em_processo = (await self.session.execute(stmt_proc)).scalar() or 0

        stmt_conc = select(func.count(LoteBeneficiamento.id)).where(
            LoteBeneficiamento.tenant_id == self.tenant_id,
            LoteBeneficiamento.safra_id == safra_id,
            LoteBeneficiamento.status.in_(["ARMAZENADO", "VENDIDO"]),
        )
        concluidos = (await self.session.execute(stmt_conc)).scalar() or 0

        return BeneficiamentoKPIs(
            total_lotes=row[0],
            peso_entrada_total_kg=float(row[1]),
            peso_saida_total_kg=float(row[2]),
            sacas_beneficiadas_total=float(row[3]),
            fator_reducao_medio=float(row[4]) if row[4] else None,
            lotes_em_processo=em_processo,
            lotes_concluidos=concluidos,
            pontuacao_media_scaa=float(pontuacao_media) if pontuacao_media else None,
        )

    async def criar_from_romaneio(self, romaneio_id: UUID) -> LoteBeneficiamento:
        """Cria um LoteBeneficiamento pré-populado a partir de um Romaneio."""
        stmt = select(RomaneioColheita).where(
            RomaneioColheita.id == romaneio_id,
            RomaneioColheita.tenant_id == self.tenant_id,
        )
        romaneio = (await self.session.execute(stmt)).scalars().first()
        if not romaneio:
            raise EntityNotFoundError(f"Romaneio {romaneio_id} não encontrado.")
        produto_colhido = await self._get_produto_colhido_por_romaneio(romaneio.id)
        await self._bloquear_se_reprovado(romaneio, produto_colhido, "romaneio")

        numero_lote = f"BEN-{romaneio.numero_romaneio}" if romaneio.numero_romaneio else f"BEN-{uuid.uuid4().hex[:8]}"

        dados = LoteBeneficiamentoCreate(
            safra_id=romaneio.safra_id,
            talhao_id=romaneio.talhao_id,
            production_unit_id=romaneio.production_unit_id,
            romaneio_id=romaneio_id,
            numero_lote=numero_lote,
            data_entrada=romaneio.data_colheita,
            peso_entrada_kg=self._peso_entrada_produto(produto_colhido, romaneio),
            umidade_entrada_pct=float(romaneio.umidade_pct) if romaneio.umidade_pct else None,
        )

        lote = await self.criar(dados)
        return lote

    async def criar_from_romaneios(self, req: LoteFromRomaneiosRequest) -> LoteBeneficiamento:
        """Cria um LoteBeneficiamento agrupando múltiplos romaneios (blend)."""
        stmt = select(RomaneioColheita).where(
            RomaneioColheita.id.in_(req.romaneio_ids),
            RomaneioColheita.tenant_id == self.tenant_id,
        )
        romaneios = (await self.session.execute(stmt)).scalars().all()

        if not romaneios or len(romaneios) != len(req.romaneio_ids):
            raise EntityNotFoundError("Um ou mais romaneios não encontrados.")

        safra_ids = set(r.safra_id for r in romaneios)
        if len(safra_ids) > 1:
            raise BusinessRuleError("Todos os romaneios devem ser da mesma safra.")

        safra_id = safra_ids.pop()
        pesos_por_romaneio: dict[UUID, float] = {}

        peso_total = 0.0
        for romaneio in romaneios:
            produto_colhido = await self._get_produto_colhido_por_romaneio(romaneio.id)
            await self._bloquear_se_reprovado(romaneio, produto_colhido, "blend_romaneios")
            peso_item = self._peso_entrada_produto(produto_colhido, romaneio)
            pesos_por_romaneio[romaneio.id] = peso_item
            peso_total += peso_item

        numero_lote = req.numero_lote or f"BEN-MULTI-{uuid.uuid4().hex[:6]}"

        primeiro = romaneios[0]

        dados = LoteBeneficiamentoCreate(
            safra_id=safra_id,
            talhao_id=primeiro.talhao_id,
            production_unit_id=primeiro.production_unit_id,
            romaneio_id=primeiro.id,
            numero_lote=numero_lote,
            data_entrada=primeiro.data_colheita,
            peso_entrada_kg=peso_total,
            umidade_entrada_pct=float(primeiro.umidade_pct) if primeiro.umidade_pct else None,
            detalhe_cafe=req.detalhe_cafe,
        )

        lote = await self.criar(dados)

        for romaneio in romaneios:
            nm = LoteBeneficiamentoRomaneio(
                tenant_id=self.tenant_id,
                lote_id=lote.id,
                romaneio_id=romaneio.id,
                peso_entrada_kg=pesos_por_romaneio[romaneio.id],
            )
            self.session.add(nm)

        await self.session.commit()
        await self.session.refresh(lote)
        return await self._anexar_detalhe(lote)

    async def gerar_venda(self, lote_id: UUID) -> dict:
        """
        Gera uma Comercializacao (venda) a partir de um lote ARMAZENADO.
        Retorna dict com id e info da comercialização criada.
        """
        lote = await self.get_or_fail(lote_id)

        if lote.status != "ARMAZENADO":
            raise BusinessRuleError(
                f"Apenas lotes com status ARMAZENADO podem gerar venda. Status atual: {lote.status}"
            )

        from financeiro.comercializacao.service import ComercializacaoService
        from financeiro.comercializacao.schemas import ComercializacaoCommodityCreate

        stmt_romaneio = select(RomaneioColheita).where(
            RomaneioColheita.id == lote.romaneio_id,
            RomaneioColheita.tenant_id == self.tenant_id,
        )
        romaneio = (await self.session.execute(stmt_romaneio)).scalars().first() if lote.romaneio_id else None
        produto_colhido = await self._get_produto_colhido_por_romaneio(lote.romaneio_id) if lote.romaneio_id else None
        commodity_id = self._resolver_commodity_id(romaneio, produto_colhido)
        if not commodity_id:
            raise BusinessRuleError(
                "Romaneio deve ter commodity associada para gerar venda."
            )

        dados_venda = ComercializacaoCommodityCreate(
            commodity_id=commodity_id,
            comprador_id=None,
            quantidade=float(lote.sacas_beneficiadas or 0),
            unidade="SC60",
            status="RASCUNHO",
            dados_extras={
                "lote_beneficiamento_id": str(lote.id),
                "origem": "beneficiamento_auto",
            }
        )

        com_svc = ComercializacaoService(self.session, self.tenant_id)
        comercializacao = await com_svc.criar(dados_venda)
        await self.session.commit()
        await self.session.refresh(comercializacao)

        return {
            "id": str(comercializacao.id),
            "numero_contrato": comercializacao.numero_contrato,
            "quantidade": float(comercializacao.quantidade),
            "status": comercializacao.status,
        }

    async def relatorio_rendimento(self, safra_id: UUID) -> BeneficiamentoRelatorioRendimento:
        """Gera relatório de rendimento por método de beneficiamento (café) ou
        'GENERICO' para lotes sem extensão de café."""
        metodo_col = func.coalesce(LoteBeneficiamentoCafeDetalhe.metodo, "GENERICO")
        stmt = select(
            metodo_col,
            func.count(LoteBeneficiamento.id).label("total_lotes"),
            func.coalesce(func.sum(LoteBeneficiamento.peso_entrada_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.peso_saida_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.sacas_beneficiadas), 0),
            func.avg(LoteBeneficiamento.fator_reducao),
            func.coalesce(func.sum(LoteBeneficiamento.perda_secagem_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.perda_quebra_kg), 0),
            func.coalesce(func.sum(LoteBeneficiamento.perda_defeito_kg), 0),
            func.avg(LoteBeneficiamento.fator_esperado_manual),
        ).select_from(LoteBeneficiamento).outerjoin(
            LoteBeneficiamentoCafeDetalhe, LoteBeneficiamentoCafeDetalhe.lote_id == LoteBeneficiamento.id
        ).where(
            LoteBeneficiamento.tenant_id == self.tenant_id,
            LoteBeneficiamento.safra_id == safra_id,
            LoteBeneficiamento.peso_saida_kg > 0,
        ).group_by(metodo_col)

        rows = (await self.session.execute(stmt)).all()

        por_metodo = []
        total_peso_entrada = 0.0
        total_peso_saida = 0.0
        total_sacas = 0.0

        for row in rows:
            metodo = row[0]
            total_lotes = row[1]
            peso_entrada = float(row[2] or 0)
            peso_saida = float(row[3] or 0)
            sacas = float(row[4] or 0)
            fator_real = float(row[5]) if row[5] else None
            perda_secagem = float(row[6] or 0)
            perda_quebra = float(row[7] or 0)
            perda_defeito = float(row[8] or 0)
            fator_esperado_manual_medio = float(row[9]) if row[9] else None

            fator_esperado = FATOR_ESPERADO.get(metodo, fator_esperado_manual_medio or 4.8)

            eficiencia_pct = 0.0
            if fator_real and fator_real > 0:
                eficiencia_pct = round((fator_esperado / fator_real) * 100, 2)

            perda_total = perda_secagem + perda_quebra + perda_defeito

            por_metodo.append(RendimentoPorMetodo(
                metodo=metodo,
                total_lotes=total_lotes,
                peso_entrada_kg=round(peso_entrada, 3),
                peso_saida_kg=round(peso_saida, 3),
                sacas_beneficiadas=round(sacas, 3),
                fator_reducao_real=round(fator_real, 3) if fator_real else None,
                fator_reducao_esperado=fator_esperado,
                eficiencia_pct=eficiencia_pct,
                perda_secagem_kg=round(perda_secagem, 3),
                perda_quebra_kg=round(perda_quebra, 3),
                perda_defeito_kg=round(perda_defeito, 3),
                perda_total_kg=round(perda_total, 3),
            ))

            total_peso_entrada += peso_entrada
            total_peso_saida += peso_saida
            total_sacas += sacas

        rendimento_medio_pct = 0.0
        if total_peso_entrada > 0 and total_peso_saida > 0:
            rendimento_medio_pct = round((total_peso_saida / total_peso_entrada) * 100, 2)

        return BeneficiamentoRelatorioRendimento(
            safra_id=safra_id,
            total_lotes=sum(m.total_lotes for m in por_metodo),
            peso_entrada_total_kg=round(total_peso_entrada, 3),
            peso_saida_total_kg=round(total_peso_saida, 3),
            sacas_total=round(total_sacas, 3),
            rendimento_medio_pct=rendimento_medio_pct,
            por_metodo=por_metodo,
        )

    async def armazenar_no_estoque(self, lote_id: UUID) -> dict:
        """
        Cria um LoteEstoque a partir de um lote beneficiado ARMAZENADO.
        Integração com o módulo de estoque.
        """
        lote = await self.get_or_fail(lote_id)

        if lote.status != "ARMAZENADO":
            raise BusinessRuleError(
                f"Apenas lotes ARMAZENADO podem ser armazenados. Status atual: {lote.status}"
            )
        if not lote.sacas_beneficiadas or lote.sacas_beneficiadas <= 0:
            raise BusinessRuleError("Lote deve ter sacas_beneficiadas > 0")
        if not lote.armazem_id:
            raise BusinessRuleError("Lote deve ter armazem_id preenchido")

        stmt_romaneio = select(RomaneioColheita).where(
            RomaneioColheita.id == lote.romaneio_id,
            RomaneioColheita.tenant_id == self.tenant_id,
        )
        romaneio = (await self.session.execute(stmt_romaneio)).scalars().first() if lote.romaneio_id else None
        produto_colhido = await self._get_produto_colhido_por_romaneio(lote.romaneio_id) if lote.romaneio_id else None
        qualidade = resolver_qualidade_efetiva(produto_colhido, romaneio)
        if qualidade.qualidade_status == "REPROVADO":
            raise BusinessRuleError("Lote com qualidade REPROVADO não pode ser armazenado no estoque.")
        commodity_id = self._resolver_commodity_id(romaneio, produto_colhido)
        if not commodity_id:
            raise BusinessRuleError("Romaneio deve ter commodity associada.")

        from operacional.services.estoque_service import EstoqueService
        from operacional.schemas.estoque import LoteCreate

        metadata_qualidade = self._qualidade_estoque_metadata(
            lote_id=lote.id,
            romaneio_id=(lote.romaneio_id or lote.id),
            qualidade_laudo_id=qualidade.qualidade_laudo_id,
            qualidade_status=qualidade.qualidade_status,
            peso_desconto_qualidade_kg=qualidade.peso_desconto_qualidade_kg,
        )

        estoque_svc = EstoqueService(self.session, self.tenant_id)
        lote_estoque = await estoque_svc.criar_lote(
            LoteCreate(
                produto_id=commodity_id,
                numero_lote=lote.numero_lote,
                deposito_id=lote.armazem_id,
                quantidade_inicial=float(lote.sacas_beneficiadas),
                custo_unitario=0.0,
                qualidade_laudo_id=qualidade.qualidade_laudo_id,
                qualidade_status=qualidade.qualidade_status,
                peso_desconto_qualidade_kg=qualidade.peso_desconto_qualidade_kg,
                metadata_json=metadata_qualidade,
            )
        )

        await estoque_svc._registrar_movimento(
            deposito_id=lote.armazem_id,
            produto_id=commodity_id,
            tipo="ENTRADA",
            quantidade=float(lote.sacas_beneficiadas),
            origem_id=lote.id,
            origem_tipo="BENEFICIAMENTO",
            lote_id=lote_estoque.id,
            motivo=self._qualidade_estoque_observacao(metadata_qualidade),
        )

        lote.lote_estoque_id = lote_estoque.id
        await self.session.commit()
        await self.session.refresh(lote)

        return {
            "lote_estoque_id": str(lote_estoque.id),
            "quantidade": float(lote.sacas_beneficiadas),
            "deposito_id": str(lote.armazem_id),
        }

    async def _obter_custo_total_safra(self, safra_id: UUID) -> float:
        """Obtém custo total consolidado da safra via DREAgricolaV1Service."""
        try:
            from agricola.dre import DREAgricolaV1Service

            dre = await DREAgricolaV1Service(self.session, self.tenant_id).gerar(safra_id=safra_id)
            return float(dre.totais.custo_total or 0.0)
        except Exception:
            return 0.0

    async def _mapear_precos_por_lote(self) -> dict[str, float]:
        """Mapeia preço unitário médio de venda por lote_beneficiamento_id nas comercializações."""
        from financeiro.comercializacao.models import ComercializacaoCommodity

        stmt = select(ComercializacaoCommodity).where(
            ComercializacaoCommodity.tenant_id == self.tenant_id,
            ComercializacaoCommodity.status != "CANCELADO",
        )
        vendas = (await self.session.execute(stmt)).scalars().all()
        totais: dict[str, list[float]] = {}
        for v in vendas:
            extras = v.dados_extras if isinstance(v.dados_extras, dict) else {}
            lote_ref = extras.get("lote_beneficiamento_id")
            if lote_ref and float(v.preco_unitario or 0) > 0:
                totais.setdefault(str(lote_ref), []).append(float(v.preco_unitario))
        return {k: round(sum(vals) / len(vals), 2) for k, vals in totais.items() if vals}

    @staticmethod
    def _agrupar_por_bebida(itens: list[CafeQualidadeMargemItem]) -> list[CafeQualidadeMargemPorBebida]:
        """Agrupa métricas de preço e margem por classificação de bebida ABIC."""
        grupos: dict[str, list[CafeQualidadeMargemItem]] = {}
        for item in itens:
            chave = item.bebida or "NAO_CLASSIFICADA"
            grupos.setdefault(chave, []).append(item)

        resultado: list[CafeQualidadeMargemPorBebida] = []
        for bebida, lista in sorted(grupos.items()):
            scaa_vals = [i.pontuacao_scaa for i in lista if i.pontuacao_scaa is not None]
            precos = [i.preco_venda_por_saca for i in lista if i.preco_venda_por_saca is not None]
            margens = [i.margem_por_saca for i in lista if i.margem_por_saca is not None]
            resultado.append(
                CafeQualidadeMargemPorBebida(
                    bebida=bebida,
                    total_lotes=len(lista),
                    sacas_totais=round(sum(i.sacas_beneficiadas for i in lista), 2),
                    scaa_medio=round(sum(scaa_vals) / len(scaa_vals), 2) if scaa_vals else None,
                    preco_medio_saca=round(sum(precos) / len(precos), 2) if precos else None,
                    margem_media_saca=round(sum(margens) / len(margens), 2) if margens else None,
                )
            )
        return resultado

    async def analise_qualidade_margem(self, safra_id: UUID) -> CafeQualidadeMargemResponse:
        """Correlaciona qualidade (SCA/ABIC/peneira), custo/saca e preço de venda por lote.

        Args:
            safra_id: Identificador da safra analisada.

        Returns:
            CafeQualidadeMargemResponse: Consolidado de lotes, prêmio por qualidade e agrupamento por bebida.
        """
        lotes = await self.listar_com_detalhe(safra_id=safra_id)
        custo_total_safra = await self._obter_custo_total_safra(safra_id)
        precos_por_lote = await self._mapear_precos_por_lote()

        total_sacas = sum(float(l.sacas_beneficiadas or 0) for l in lotes)
        custo_medio_saca = round(custo_total_safra / total_sacas, 2) if total_sacas > 0 and custo_total_safra > 0 else None

        itens: list[CafeQualidadeMargemItem] = []
        for lote in lotes:
            det = getattr(lote, "detalhe_cafe", None)
            scaa = float(det.pontuacao_scaa) if det and det.pontuacao_scaa is not None else None
            sacas = float(lote.sacas_beneficiadas or 0)
            preco = precos_por_lote.get(str(lote.id))
            margem = round(preco - custo_medio_saca, 2) if preco is not None and custo_medio_saca is not None else None
            margem_pct = round((margem / preco) * 100, 2) if margem is not None and preco and preco > 0 else None
            itens.append(
                CafeQualidadeMargemItem(
                    lote_id=lote.id,
                    numero_lote=lote.numero_lote,
                    status=lote.status,
                    metodo=det.metodo if det else None,
                    bebida=det.bebida if det else None,
                    peneira_principal=det.peneira_principal if det else None,
                    pontuacao_scaa=scaa,
                    especial=bool(scaa is not None and scaa >= 80),
                    sacas_beneficiadas=round(sacas, 2),
                    custo_por_saca=custo_medio_saca,
                    preco_venda_por_saca=preco,
                    margem_por_saca=margem,
                    margem_pct=margem_pct,
                    receita_estimada=round(sacas * preco, 2) if preco is not None else 0.0,
                    origem_preco="LOTE" if preco is not None else "SEM_VENDA",
                )
            )

        precos_esp = [i.preco_venda_por_saca for i in itens if i.especial and i.preco_venda_por_saca is not None]
        precos_conv = [i.preco_venda_por_saca for i in itens if not i.especial and i.preco_venda_por_saca is not None]
        media_esp = round(sum(precos_esp) / len(precos_esp), 2) if precos_esp else None
        media_conv = round(sum(precos_conv) / len(precos_conv), 2) if precos_conv else None
        premio_pct = (
            round(((media_esp - media_conv) / media_conv) * 100, 2)
            if media_esp is not None and media_conv is not None and media_conv > 0
            else None
        )

        return CafeQualidadeMargemResponse(
            safra_id=safra_id,
            custo_total_safra=round(custo_total_safra, 2),
            total_sacas_safra=round(total_sacas, 2),
            custo_medio_saca_safra=custo_medio_saca,
            preco_medio_saca_especial=media_esp,
            preco_medio_saca_convencional=media_conv,
            premio_qualidade_pct=premio_pct,
            lotes=itens,
            por_bebida=self._agrupar_por_bebida(itens),
        )
