"""Services para integração de NFe e financeiro com Sankhya."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import IntegrationJobTrigger
from integracoes.sankhya.models import (
    SankhyaLancamentoFinanceiro,
    SankhyaNFe,
)
from integracoes.sankhya.services.canonical_adapter import SankhyaCanonicalAdapter
from integracoes.sankhya.services.external_association_helper import (
    SankhyaExternalAssociationHelper,
)
from integracoes.sankhya.services.sync_service import SankhyaWSClient, get_sankhya_connection_data


class SankhyaNFeService:
    """Serviço para integração de notas fiscais com Sankhya."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.adapter = SankhyaCanonicalAdapter(db)
        self.association_helper = SankhyaExternalAssociationHelper(db)

    async def exportar_nfe(self, tenant_id: str, nfe_data: dict[str, Any]) -> dict[str, Any]:
        try:
            connection_data = await get_sankhya_connection_data(self.db, tenant_id)
        except ValueError:
            raise Exception("Sankhya não configurado")

        job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code="nfe",
            trigger_type=IntegrationJobTrigger.MANUAL,
            request_payload={"operacao": "exportar_nfe"},
        )
        async with SankhyaWSClient(connection_data) as client:
            try:
                sankhya_data = self._prepare_nfe_data(nfe_data)
                resultado = await client.executar_ws("NFe", "save", sankhya_data)
            except Exception as exc:
                await self.adapter.finish_sync_job(
                    tenant_id=tenant_id,
                    feature_code="nfe",
                    success=False,
                    processados=0,
                    erros=1,
                    error_message=str(exc),
                    trigger_type=IntegrationJobTrigger.MANUAL,
                    request_payload={"operacao": "exportar_nfe", "job_id": str(job.id)},
                )
                raise

        if resultado.get("success"):
            await self._atualizar_nfe_exportada(
                tenant_id,
                nfe_data.get("chave_acesso"),
                resultado.get("sankhya_id"),
            )
            await self.adapter.finish_sync_job(
                tenant_id=tenant_id,
                feature_code="nfe",
                success=True,
                processados=1,
                erros=0,
                trigger_type=IntegrationJobTrigger.MANUAL,
                request_payload={"operacao": "exportar_nfe", "job_id": str(job.id)},
            )
        else:
            await self.adapter.finish_sync_job(
                tenant_id=tenant_id,
                feature_code="nfe",
                success=False,
                processados=1,
                erros=1,
                error_message=resultado.get("error"),
                trigger_type=IntegrationJobTrigger.MANUAL,
                request_payload={"operacao": "exportar_nfe", "job_id": str(job.id)},
            )

        return resultado

    async def importar_nfe_entrada(
        self, tenant_id: str, periodo_inicio: date, periodo_fim: date
    ) -> int:
        try:
            connection_data = await get_sankhya_connection_data(self.db, tenant_id)
        except ValueError:
            return 0

        importadas = 0
        job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code="nfe",
            trigger_type=IntegrationJobTrigger.PULL,
            request_payload={"operacao": "importar_nfe_entrada"},
        )
        async with SankhyaWSClient(connection_data) as client:
            try:
                resultado = await client.executar_ws(
                    "NFe",
                    "findEntradaByPeriodo",
                    {
                        "dataInicio": periodo_inicio.strftime("%Y-%m-%d"),
                        "dataFim": periodo_fim.strftime("%Y-%m-%d"),
                    },
                )

                for nfe_data in resultado.get("nfe", []):
                    await self._salvar_nfe_entrada(tenant_id, nfe_data)
                    importadas += 1
                await self.adapter.finish_sync_job(
                    tenant_id=tenant_id,
                    feature_code="nfe",
                    success=True,
                    processados=importadas,
                    erros=0,
                    trigger_type=IntegrationJobTrigger.PULL,
                    request_payload={"operacao": "importar_nfe_entrada", "job_id": str(job.id)},
                )
            except Exception as exc:  # pragma: no cover - integração externa
                await self.adapter.finish_sync_job(
                    tenant_id=tenant_id,
                    feature_code="nfe",
                    success=False,
                    processados=importadas,
                    erros=1,
                    error_message=str(exc),
                    trigger_type=IntegrationJobTrigger.PULL,
                    request_payload={"operacao": "importar_nfe_entrada", "job_id": str(job.id)},
                )
                print(f"Erro ao importar NFe entrada: {exc}")

        return importadas

    async def listar_nfe(
        self,
        tenant_id: str,
        *,
        tipo_operacao: str | None = None,
        exportado: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SankhyaNFe]:
        stmt = select(SankhyaNFe).where(SankhyaNFe.tenant_id == tenant_id)
        if tipo_operacao:
            stmt = stmt.where(SankhyaNFe.tipo_operacao == tipo_operacao)
        if exportado is not None:
            stmt = stmt.where(SankhyaNFe.exportado_sankhya == exportado)
        stmt = stmt.offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    def _prepare_nfe_data(self, nfe_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "CHAVEACESSO": nfe_data.get("chave_acesso"),
            "NUMNOTA": nfe_data.get("numero"),
            "SERIE": nfe_data.get("serie"),
            "CFOP": nfe_data.get("cfop"),
            "CODPARC": nfe_data.get("cod_parc"),
            "VLTOTAL": nfe_data.get("valor_total"),
            "VLPROD": nfe_data.get("valor_produtos"),
            "VLFRETE": nfe_data.get("valor_frete"),
            "VLSEGURO": nfe_data.get("valor_seguro"),
            "VLDESC": nfe_data.get("valor_desconto"),
            "VLIPI": nfe_data.get("valor_ipi"),
            "VLICMS": nfe_data.get("valor_icms"),
            "VLPIS": nfe_data.get("valor_pis"),
            "VLCOFINS": nfe_data.get("valor_cofins"),
            "DATAEMISSAO": nfe_data.get("data_emissao"),
            "ITENS": nfe_data.get("itens", []),
        }

    async def _atualizar_nfe_exportada(
        self, tenant_id: str, chave_acesso: str, sankhya_id: str
    ) -> None:
        stmt = select(SankhyaNFe).where(
            SankhyaNFe.tenant_id == tenant_id,
            SankhyaNFe.chave_acesso == chave_acesso,
        )
        nfe = (await self.db.execute(stmt)).scalar_one_or_none()
        if not nfe:
            return

        nfe.exportado_sankhya = True
        nfe.sankhya_id = sankhya_id
        nfe.sincronizado_em = datetime.utcnow()
        self.db.add(nfe)
        await self.db.commit()

    async def _salvar_nfe_entrada(self, tenant_id: str, data: dict[str, Any]) -> SankhyaNFe:
        nfe = SankhyaNFe(
            tenant_id=tenant_id,
            sankhya_id=str(data.get("CODNEG", "")),
            tipo_operacao="ENTRADA",
            numero=str(data.get("NUMNOTA", "")),
            serie=data.get("SERIE", ""),
            modelo=data.get("MODNOTA", "55"),
            chave_acesso=data.get("CHAVEACESSO", ""),
            cnpj_emitente=data.get("CGCEMIT", ""),
            valor_total=float(data.get("VLTOTAL", 0) or 0),
            valor_produtos=float(data.get("VLPROD", 0) or 0),
            valor_frete=float(data.get("VLFRETE", 0) or 0),
            valor_icms=float(data.get("VLICMS", 0) or 0),
            data_emissao=self._parse_date(data.get("DATAEMISSAO")),
            status_sankhya=data.get("STATUS", ""),
            importado_sankhya=True,
            sincronizado_em=datetime.utcnow(),
        )

        stmt = select(SankhyaNFe).where(
            SankhyaNFe.tenant_id == tenant_id,
            SankhyaNFe.chave_acesso == nfe.chave_acesso,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            for key, value in nfe.__dict__.items():
                if not key.startswith("_") and value is not None:
                    setattr(existing, key, value)
            nfe = existing
        else:
            self.db.add(nfe)

        await self.db.commit()
        await self.db.refresh(nfe)
        await self.association_helper.sync_nfe(tenant_id, data)
        return nfe

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None


class SankhyaFinanceiroService:
    """Serviço para integração financeira com Sankhya."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.adapter = SankhyaCanonicalAdapter(db)
        self.association_helper = SankhyaExternalAssociationHelper(db)

    async def exportar_contas_pagar(
        self, tenant_id: str, lancamentos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            connection_data = await get_sankhya_connection_data(self.db, tenant_id)
        except ValueError:
            raise Exception("Sankhya não configurado")

        exportados = 0
        erros: list[dict[str, Any]] = []
        job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code="financeiro",
            trigger_type=IntegrationJobTrigger.MANUAL,
            request_payload={"operacao": "exportar_contas_pagar"},
        )
        async with SankhyaWSClient(connection_data) as client:
            for lancamento in lancamentos:
                try:
                    sankhya_data = self._prepare_lancamento_data(lancamento, "CONTAS_PAGAR")
                    resultado = await client.executar_ws("Lancamento", "save", sankhya_data)
                    if resultado.get("success"):
                        await self._atualizar_lancamento_exportado(
                            tenant_id,
                            lancamento.get("id"),
                            resultado.get("sankhya_id"),
                        )
                        exportados += 1
                    else:
                        erros.append({"id": lancamento.get("id"), "erro": resultado.get("error")})
                except Exception as exc:  # pragma: no cover - integração externa
                    erros.append({"id": lancamento.get("id"), "erro": str(exc)})
        await self.adapter.finish_sync_job(
            tenant_id=tenant_id,
            feature_code="financeiro",
            success=not erros,
            processados=len(lancamentos),
            erros=len(erros),
            error_message=erros[0]["erro"] if erros else None,
            trigger_type=IntegrationJobTrigger.MANUAL,
            request_payload={"operacao": "exportar_contas_pagar", "job_id": str(job.id)},
        )
        return {"exportados": exportados, "erros": erros}

    async def exportar_contas_receber(
        self, tenant_id: str, lancamentos: list[dict[str, Any]]
    ) -> dict[str, Any]:
        try:
            connection_data = await get_sankhya_connection_data(self.db, tenant_id)
        except ValueError:
            raise Exception("Sankhya não configurado")

        exportados = 0
        erros: list[dict[str, Any]] = []
        job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code="financeiro",
            trigger_type=IntegrationJobTrigger.MANUAL,
            request_payload={"operacao": "exportar_contas_receber"},
        )
        async with SankhyaWSClient(connection_data) as client:
            for lancamento in lancamentos:
                try:
                    sankhya_data = self._prepare_lancamento_data(lancamento, "CONTAS_RECEBER")
                    resultado = await client.executar_ws("Lancamento", "save", sankhya_data)
                    if resultado.get("success"):
                        await self._atualizar_lancamento_exportado(
                            tenant_id,
                            lancamento.get("id"),
                            resultado.get("sankhya_id"),
                        )
                        exportados += 1
                    else:
                        erros.append({"id": lancamento.get("id"), "erro": resultado.get("error")})
                except Exception as exc:  # pragma: no cover - integração externa
                    erros.append({"id": lancamento.get("id"), "erro": str(exc)})
        await self.adapter.finish_sync_job(
            tenant_id=tenant_id,
            feature_code="financeiro",
            success=not erros,
            processados=len(lancamentos),
            erros=len(erros),
            error_message=erros[0]["erro"] if erros else None,
            trigger_type=IntegrationJobTrigger.MANUAL,
            request_payload={"operacao": "exportar_contas_receber", "job_id": str(job.id)},
        )
        return {"exportados": exportados, "erros": erros}

    async def importar_lancamentos(
        self,
        tenant_id: str,
        periodo_inicio: date,
        periodo_fim: date,
        tipo: str = "AMBOS",
    ) -> int:
        try:
            connection_data = await get_sankhya_connection_data(self.db, tenant_id)
        except ValueError:
            return 0

        importados = 0
        job = await self.adapter.start_sync_job(
            tenant_id=tenant_id,
            feature_code="financeiro",
            trigger_type=IntegrationJobTrigger.PULL,
            request_payload={"operacao": "importar_lancamentos", "tipo": tipo},
        )
        async with SankhyaWSClient(connection_data) as client:
            try:
                resultado = await client.executar_ws(
                    "Lancamento",
                    "findByPeriodo",
                    {
                        "dataInicio": periodo_inicio.strftime("%Y-%m-%d"),
                        "dataFim": periodo_fim.strftime("%Y-%m-%d"),
                        "tipo": tipo,
                    },
                )

                for lanc_data in resultado.get("lancamentos", []):
                    await self._salvar_lancamento(tenant_id, lanc_data)
                    importados += 1
                await self.adapter.finish_sync_job(
                    tenant_id=tenant_id,
                    feature_code="financeiro",
                    success=True,
                    processados=importados,
                    erros=0,
                    trigger_type=IntegrationJobTrigger.PULL,
                    request_payload={
                        "operacao": "importar_lancamentos",
                        "tipo": tipo,
                        "job_id": str(job.id),
                    },
                )
            except Exception as exc:  # pragma: no cover - integração externa
                await self.adapter.finish_sync_job(
                    tenant_id=tenant_id,
                    feature_code="financeiro",
                    success=False,
                    processados=importados,
                    erros=1,
                    error_message=str(exc),
                    trigger_type=IntegrationJobTrigger.PULL,
                    request_payload={
                        "operacao": "importar_lancamentos",
                        "tipo": tipo,
                        "job_id": str(job.id),
                    },
                )
                print(f"Erro ao importar lançamentos: {exc}")

        return importados

    async def listar_lancamentos(
        self,
        tenant_id: str,
        *,
        tipo: str | None = None,
        exportado: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SankhyaLancamentoFinanceiro]:
        stmt = select(SankhyaLancamentoFinanceiro).where(
            SankhyaLancamentoFinanceiro.tenant_id == tenant_id
        )
        if tipo:
            stmt = stmt.where(SankhyaLancamentoFinanceiro.tipo == tipo)
        if exportado is not None:
            stmt = stmt.where(SankhyaLancamentoFinanceiro.exportado_sankhya == exportado)
        stmt = stmt.offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

    def _prepare_lancamento_data(self, lancamento: dict[str, Any], tipo: str) -> dict[str, Any]:
        return {
            "TIPO": tipo,
            "CODPARC": lancamento.get("cod_parc"),
            "CODNEG": lancamento.get("cod_negocio"),
            "DESDOB": lancamento.get("desdobramento"),
            "VLRDESDOB": lancamento.get("valor"),
            "DTNEG": lancamento.get("data_negocio"),
            "DTVENC": lancamento.get("data_vencimento"),
            "HISTORICO": lancamento.get("historico"),
            "RATEIO": lancamento.get("rateio", {}),
        }

    async def _atualizar_lancamento_exportado(
        self, tenant_id: str, local_id: int, sankhya_id: str
    ) -> None:
        stmt = select(SankhyaLancamentoFinanceiro).where(
            SankhyaLancamentoFinanceiro.tenant_id == tenant_id,
            SankhyaLancamentoFinanceiro.id == local_id,
        )
        lancamento = (await self.db.execute(stmt)).scalar_one_or_none()
        if not lancamento:
            return

        lancamento.exportado_sankhya = True
        lancamento.sankhya_id = sankhya_id
        lancamento.sincronizado_em = datetime.utcnow()
        self.db.add(lancamento)
        await self.db.commit()

    async def _salvar_lancamento(
        self, tenant_id: str, data: dict[str, Any]
    ) -> SankhyaLancamentoFinanceiro:
        lancamento = SankhyaLancamentoFinanceiro(
            tenant_id=tenant_id,
            sankhya_id=str(data.get("DESDOB", "")),
            tipo=data.get("TIPO", "CONTAS_PAGAR"),
            numero_documento=data.get("NUMDOC", ""),
            valor=float(data.get("VLRDESDOB", 0) or 0),
            valor_saldo=float(data.get("VLRSALDO", 0) or 0),
            data_lancamento=self._parse_date(data.get("DTLANC")),
            data_vencimento=self._parse_date(data.get("DTVENC")),
            historico=data.get("HISTORICO", ""),
            rateio=data.get("RATEIO", {}),
            status=data.get("STATUS", "ABERTO"),
            importado_sankhya=True,
            sincronizado_em=datetime.utcnow(),
        )

        stmt = select(SankhyaLancamentoFinanceiro).where(
            SankhyaLancamentoFinanceiro.tenant_id == tenant_id,
            SankhyaLancamentoFinanceiro.sankhya_id == lancamento.sankhya_id
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            for key, value in lancamento.__dict__.items():
                if not key.startswith("_") and value is not None:
                    setattr(existing, key, value)
            lancamento = existing
        else:
            self.db.add(lancamento)

        await self.db.commit()
        await self.db.refresh(lancamento)
        await self.association_helper.sync_financeiro(tenant_id, data)
        return lancamento

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None
