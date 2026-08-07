"""
Serviços de integração externa:
  - OFX parser + conciliação bancária
  - Exportação Carnê-Leão (RFB)
  - Resumo para escritório contábil
"""
import io
import uuid
import csv
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from financeiro.models.despesa import Despesa
from financeiro.models.receita import Receita
from financeiro.models.plano_conta import PlanoConta
from financeiro.models.conciliacao import ContaBancaria, LancamentoBancario
from financeiro.models.ordem_pagamento import ItemOrdemPagamento, OrdemPagamento
from core.exceptions import BusinessRuleError, EntityNotFoundError


BANCOS_COM_REMESSA_CNAB240 = {"001", "237", "748", "756"}


# ── OFX Parser ────────────────────────────────────────────────────────────────

def _parse_ofx(content: str) -> list[dict]:
    """
    Parser mínimo para OFX/QFX (SGML legado e OFX 2.x).
    Retorna lista de transações: {fitid, data, valor, descricao, tipo}.
    """
    import re

    # Normaliza quebras de linha
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    transacoes = []
    # Encontra blocos STMTTRN
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL | re.IGNORECASE):
        def _tag(name: str) -> str | None:
            m = re.search(rf"<{name}>(.*?)(?:<|$)", bloco, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else None

        fitid = _tag("FITID")
        dtposted = _tag("DTPOSTED") or ""
        trnamt = _tag("TRNAMT") or "0"
        memo = _tag("MEMO") or _tag("NAME") or ""
        trntype = _tag("TRNTYPE") or "OTHER"

        # Converte data YYYYMMDD[HHMM[SS[.mmm][+-ZH:ZM]]]
        data_str = dtposted[:8] if len(dtposted) >= 8 else ""
        try:
            dt = date(int(data_str[:4]), int(data_str[4:6]), int(data_str[6:8]))
        except Exception:
            continue

        try:
            valor = float(trnamt.replace(",", "."))
        except ValueError:
            continue

        transacoes.append({
            "fitid": fitid,
            "data": dt,
            "valor": valor,
            "descricao": memo[:500],
            "tipo": "CREDIT" if valor >= 0 else "DEBIT",
        })

    return transacoes


# ── Conciliação Service ───────────────────────────────────────────────────────

class ConciliacaoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar_conta(self, dados: dict) -> ContaBancaria:
        saldo_inicial = dados.pop("saldo_inicial", 0.0)
        dados["tenant_id"] = self.tenant_id
        conta = ContaBancaria(**dados)
        self.session.add(conta)
        await self.session.flush()
        
        if saldo_inicial != 0.0:
            from datetime import datetime, timezone
            lancamento = LancamentoBancario(
                tenant_id=self.tenant_id,
                conta_id=conta.id,
                data=datetime.now(timezone.utc).date(),
                valor=saldo_inicial,
                descricao="Saldo Inicial",
                tipo="CREDIT" if saldo_inicial > 0 else "DEBIT",
                status_conciliacao="CONCILIADO"
            )
            self.session.add(lancamento)
            await self.session.flush()

        await self.session.refresh(conta)
        setattr(conta, "saldo_atual", saldo_inicial)
        return conta

    async def listar_contas(self) -> list[ContaBancaria]:
        from sqlalchemy import func
        stmt = (
            select(
                ContaBancaria,
                func.coalesce(func.sum(LancamentoBancario.valor), 0.0).label("saldo_atual")
            )
            .outerjoin(LancamentoBancario, ContaBancaria.id == LancamentoBancario.conta_id)
            .where(ContaBancaria.tenant_id == self.tenant_id)
            .group_by(ContaBancaria.id)
        )
        result = await self.session.execute(stmt)
        contas = []
        for conta, saldo in result.all():
            setattr(conta, "saldo_atual", float(saldo))
            contas.append(conta)
        return contas

    async def configurar_remessa(self, conta_id: uuid.UUID, dados: dict) -> ContaBancaria:
        """Configura o convênio de remessa de uma conta do tenant.

        Args:
            conta_id: Conta bancária a configurar.
            dados: Convênio, layout e situação de homologação informados pelo usuário.

        Returns:
            Conta bancária atualizada.

        Raises:
            BusinessRuleError: Se a configuração não permitir uma remessa segura.
        """
        conta = await self._obter_conta_tenant(conta_id)
        self._validar_configuracao_remessa(conta, dados)
        for campo, valor in dados.items():
            setattr(conta, campo, valor)
        self.session.add(conta)
        await self.session.flush()
        await self.session.refresh(conta)
        return conta

    async def validar_remessa(self, conta_id: uuid.UUID) -> ContaBancaria:
        """Confirma que uma conta pode gerar remessa de pagamentos."""
        conta = await self._obter_conta_tenant(conta_id)
        if not conta.ativa:
            raise BusinessRuleError("A conta bancária está inativa para remessas.")
        if conta.banco not in BANCOS_COM_REMESSA_CNAB240:
            raise BusinessRuleError("O banco desta conta ainda não possui suporte de remessa CNAB 240.")
        if not conta.homologada_para_remessa:
            raise BusinessRuleError("A conta bancária não está homologada para remessas.")
        if not conta.convenio_pagamentos or not conta.layout_remessa:
            raise BusinessRuleError("Informe o convênio e o layout de remessa antes de gerar pagamentos.")
        return conta

    async def simular_retorno_ordem(self, ordem_id: uuid.UUID, aprovado: bool) -> OrdemPagamento:
        """Processa um retorno bancário fictício, exclusivo de homologação."""
        ordem = (await self.session.execute(select(OrdemPagamento).where(
            OrdemPagamento.id == ordem_id, OrdemPagamento.tenant_id == self.tenant_id
        ))).scalar_one_or_none()
        if ordem is None:
            raise EntityNotFoundError("Ordem de pagamento indisponível ou não encontrada.")
        if ordem.ambiente != "HOMOLOGACAO":
            raise BusinessRuleError("A simulação de retorno é permitida somente em homologação.")
        if ordem.status != "PRONTA_PARA_REMESSA":
            raise BusinessRuleError("O retorno desta ordem já foi processado.")
        itens = list((await self.session.execute(select(ItemOrdemPagamento).where(
            ItemOrdemPagamento.ordem_pagamento_id == ordem.id, ItemOrdemPagamento.tenant_id == self.tenant_id
        ))).scalars().all())
        for item in itens:
            await self._processar_item_retorno_simulado(ordem, item, aprovado)
        ordem.status = "LIQUIDADA_SIMULADA" if aprovado else "REJEITADA_SIMULADA"
        self.session.add(ordem)
        await self.session.flush()
        return ordem

    async def _processar_item_retorno_simulado(self, ordem: OrdemPagamento, item: ItemOrdemPagamento, aprovado: bool) -> None:
        despesa = (await self.session.execute(select(Despesa).where(Despesa.id == item.despesa_id, Despesa.tenant_id == self.tenant_id))).scalar_one()
        item.status = "LIQUIDADO_SIMULADO" if aprovado else "REJEITADO_SIMULADO"
        if not aprovado:
            item.motivo_rejeicao = "Rejeição simulada de homologação"
            despesa.status = "LIBERADO_PAGAMENTO"
            self.session.add(despesa)
            return
        despesa.status = "PAGO"
        despesa.valor_pago = item.valor
        despesa.data_pagamento = ordem.data_pagamento
        despesa.conta_bancaria_pagamento_id = ordem.conta_bancaria_id
        self.session.add(LancamentoBancario(tenant_id=self.tenant_id, conta_id=ordem.conta_bancaria_id, data=ordem.data_pagamento, valor=-item.valor, descricao=f"DRY RUN ordem {ordem.id}", tipo="DEBIT", status_conciliacao="CONCILIADO", despesa_id=despesa.id))
        self.session.add(despesa)

    async def _obter_conta_tenant(self, conta_id: uuid.UUID) -> ContaBancaria:
        conta = (
            await self.session.execute(
                select(ContaBancaria).where(
                    ContaBancaria.id == conta_id,
                    ContaBancaria.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if conta is None:
            raise EntityNotFoundError("Conta bancária indisponível ou não encontrada.")
        return conta

    @staticmethod
    def _validar_configuracao_remessa(conta: ContaBancaria, dados: dict) -> None:
        homologada = dados.get("homologada_para_remessa", conta.homologada_para_remessa)
        convenio = dados.get("convenio_pagamentos", conta.convenio_pagamentos)
        layout = dados.get("layout_remessa", conta.layout_remessa)
        if homologada and conta.banco not in BANCOS_COM_REMESSA_CNAB240:
            raise BusinessRuleError("Este banco ainda não possui suporte de remessa CNAB 240.")
        if homologada and (not convenio or not layout):
            raise BusinessRuleError("Informe convênio e layout antes de homologar a conta para remessa.")

    async def excluir_conta(self, conta_id: uuid.UUID) -> None:
        from sqlalchemy import func
        from fastapi import HTTPException
        
        stmt = select(func.count(LancamentoBancario.id)).where(
            LancamentoBancario.conta_id == conta_id,
            LancamentoBancario.descricao != "Saldo Inicial"
        )
        count = (await self.session.execute(stmt)).scalar()
        
        if count > 0:
            raise HTTPException(status_code=400, detail="Não é possível excluir a conta pois já existem movimentações reais.")
            
        stmt_conta = select(ContaBancaria).where(ContaBancaria.id == conta_id, ContaBancaria.tenant_id == self.tenant_id)
        conta = (await self.session.execute(stmt_conta)).scalar_one_or_none()
        if conta:
            await self.session.delete(conta)

    async def importar_ofx(self, conta_id: uuid.UUID, ofx_content: str) -> dict:
        """
        Importa extrato OFX para uma conta bancária.
        Deduplica por FITID. Retorna contagem de importados/duplicados.
        """
        # Valida conta pertence ao tenant
        stmt = select(ContaBancaria).where(
            ContaBancaria.id == conta_id,
            ContaBancaria.tenant_id == self.tenant_id,
        )
        conta = (await self.session.execute(stmt)).scalar_one_or_none()
        if not conta:
            from core.exceptions import EntityNotFoundError
            raise EntityNotFoundError(f"Conta bancária {conta_id} indisponível ou não encontrada.")

        transacoes = _parse_ofx(ofx_content)
        importados = 0
        duplicados = 0

        # LOTE: Extrair fitids válidos para uma query de deduplicação em batch
        fitids_validos = [t["fitid"] for t in transacoes if t["fitid"]]
        existentes_set = set()

        if fitids_validos:
            stmt_dup_lote = select(LancamentoBancario.id_ofx).where(
                LancamentoBancario.conta_id == conta_id,
                LancamentoBancario.id_ofx.in_(fitids_validos)
            )
            existentes_set = set((await self.session.execute(stmt_dup_lote)).scalars().all())

        for t in transacoes:
            # Deduplicação em memória por FITID
            if t["fitid"] and t["fitid"] in existentes_set:
                duplicados += 1
                continue

            lanc = LancamentoBancario(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                conta_id=conta_id,
                data=t["data"],
                valor=t["valor"],
                descricao=t["descricao"],
                id_ofx=t["fitid"],
                tipo=t["tipo"],
                status_conciliacao="NAO_CONCILIADO",
            )
            self.session.add(lanc)
            importados += 1

        await self.session.flush()
        return {"importados": importados, "duplicados": duplicados, "total_ofx": len(transacoes)}

    async def listar_lancamentos(
        self,
        conta_id: uuid.UUID,
        status: Optional[str] = None,
        data_de: Optional[date] = None,
        data_ate: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LancamentoBancario]:
        stmt = select(LancamentoBancario).where(
            LancamentoBancario.tenant_id == self.tenant_id,
            LancamentoBancario.conta_id == conta_id,
        ).order_by(LancamentoBancario.data.desc()).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(LancamentoBancario.status_conciliacao == status)
        if data_de:
            stmt = stmt.where(LancamentoBancario.data >= data_de)
        if data_ate:
            stmt = stmt.where(LancamentoBancario.data <= data_ate)
        return list((await self.session.execute(stmt)).scalars().all())

    async def conciliar(
        self,
        lancamento_id: uuid.UUID,
        despesa_id: Optional[uuid.UUID] = None,
        receita_id: Optional[uuid.UUID] = None,
    ) -> LancamentoBancario:
        """Vincula um lançamento bancário a uma despesa ou receita."""
        stmt = select(LancamentoBancario).where(
            LancamentoBancario.id == lancamento_id,
            LancamentoBancario.tenant_id == self.tenant_id,
        )
        lanc = (await self.session.execute(stmt)).scalar_one_or_none()
        if not lanc:
            from core.exceptions import EntityNotFoundError
            raise EntityNotFoundError(f"Lançamento {lancamento_id} indisponível ou não encontrado.")

        lanc.despesa_id = despesa_id
        lanc.receita_id = receita_id
        lanc.status_conciliacao = "CONCILIADO"
        self.session.add(lanc)
        await self.session.flush()
        await self.session.refresh(lanc)
        return lanc

    async def sugerir_conciliacao(self, conta_id: uuid.UUID) -> list[dict]:
        """
        Sugere conciliações automáticas: cruza lançamentos bancários com
        despesas/receitas por valor + data (tolerância de ±3 dias).
        """
        stmt = select(LancamentoBancario).where(
            LancamentoBancario.conta_id == conta_id,
            LancamentoBancario.tenant_id == self.tenant_id,
            LancamentoBancario.status_conciliacao == "NAO_CONCILIADO",
        )
        lancamentos = list((await self.session.execute(stmt)).scalars().all())
        sugestoes = []
        tolerancia = timedelta(days=3)

        def _indexar_por_valor(linhas):
            indice: dict = {}
            for linha in linhas:
                indice.setdefault(linha.valor_total, []).append(linha)
            return indice

        def _buscar_match(lancamento, candidatos):
            for candidato in candidatos:
                if abs((candidato.data_vencimento - lancamento.data).days) <= 3:
                    return candidato
            return None

        lancamentos_debito = [lanc for lanc in lancamentos if lanc.valor < 0]
        lancamentos_credito = [lanc for lanc in lancamentos if lanc.valor >= 0]

        despesas_por_valor = {}
        if lancamentos_debito:
            valores = {abs(lanc.valor) for lanc in lancamentos_debito}
            menor_data = min(lanc.data for lanc in lancamentos_debito) - tolerancia
            maior_data = max(lanc.data for lanc in lancamentos_debito) + tolerancia
            stmt_desp = select(
                Despesa.id,
                Despesa.descricao,
                Despesa.valor_total,
                Despesa.data_vencimento,
            ).where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.valor_total.in_(valores),
                Despesa.data_vencimento >= menor_data,
                Despesa.data_vencimento <= maior_data,
                Despesa.status.in_(["A_PAGAR", "PAGO"]),
            )
            despesas_por_valor = _indexar_por_valor((await self.session.execute(stmt_desp)).all())

        receitas_por_valor = {}
        if lancamentos_credito:
            valores = {lanc.valor for lanc in lancamentos_credito}
            menor_data = min(lanc.data for lanc in lancamentos_credito) - tolerancia
            maior_data = max(lanc.data for lanc in lancamentos_credito) + tolerancia
            stmt_rec = select(
                Receita.id,
                Receita.descricao,
                Receita.valor_total,
                Receita.data_vencimento,
            ).where(
                Receita.tenant_id == self.tenant_id,
                Receita.valor_total.in_(valores),
                Receita.data_vencimento >= menor_data,
                Receita.data_vencimento <= maior_data,
                Receita.status.in_(["A_RECEBER", "RECEBIDO"]),
            )
            receitas_por_valor = _indexar_por_valor((await self.session.execute(stmt_rec)).all())

        for lanc in lancamentos_debito:
            candidato = _buscar_match(lanc, despesas_por_valor.get(abs(lanc.valor), []))
            if candidato:
                sugestoes.append({
                    "lancamento_id": lanc.id,
                    "tipo": "DESPESA",
                    "sugestao_id": candidato.id,
                    "descricao_lanc": lanc.descricao,
                    "descricao_fin": candidato.descricao,
                    "valor": abs(lanc.valor),
                    "data_lanc": lanc.data,
                    "confianca": "ALTA" if lanc.data == candidato.data_vencimento else "MEDIA",
                })

        for lanc in lancamentos_credito:
            candidato = _buscar_match(lanc, receitas_por_valor.get(lanc.valor, []))
            if candidato:
                sugestoes.append({
                    "lancamento_id": lanc.id,
                    "tipo": "RECEITA",
                    "sugestao_id": candidato.id,
                    "descricao_lanc": lanc.descricao,
                    "descricao_fin": candidato.descricao,
                    "valor": lanc.valor,
                    "data_lanc": lanc.data,
                    "confianca": "ALTA" if lanc.data == candidato.data_vencimento else "MEDIA",
                })

        return sugestoes


# ── Carnê-Leão Export ─────────────────────────────────────────────────────────

class CarneLeaoService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def exportar_csv(
        self,
        ano: int,
        unidade_produtiva_id: Optional[uuid.UUID] = None,
    ) -> str:
        """
        Gera CSV compatível com o layout de Livro Caixa do Produtor Rural (RFB).
        Colunas: competencia, tipo, categoria_rfb, descricao, valor, cpf_cnpj, nota_fiscal
        """
        jan1 = date(ano, 1, 1)
        dez31 = date(ano, 12, 31)

        # Receitas realizadas
        stmt_rec = select(
            Receita.data_recebimento,
            Receita.descricao,
            Receita.valor_recebido,
            Receita.valor_total,
            Receita.numero_nf,
            Receita.plano_conta_id,
        ).where(
            Receita.tenant_id == self.tenant_id,
            Receita.ativo == True,
            Receita.status.in_(["RECEBIDO", "RECEBIDO_PARCIAL"]),
            Receita.data_recebimento >= jan1,
            Receita.data_recebimento <= dez31,
        )
        if unidade_produtiva_id:
            stmt_rec = stmt_rec.where(Receita.unidade_produtiva_id == unidade_produtiva_id)
        receitas = (await self.session.execute(stmt_rec)).all()

        # Despesas pagas
        stmt_desp = select(
            Despesa.data_pagamento,
            Despesa.descricao,
            Despesa.valor_pago,
            Despesa.valor_total,
            Despesa.numero_nf,
            Despesa.fornecedor,
            Despesa.plano_conta_id,
        ).where(
            Despesa.tenant_id == self.tenant_id,
            Despesa.ativo == True,
            Despesa.status.in_(["PAGO", "PAGO_PARCIAL"]),
            Despesa.data_pagamento >= jan1,
            Despesa.data_pagamento <= dez31,
        )
        if unidade_produtiva_id:
            stmt_desp = stmt_desp.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)
        despesas = (await self.session.execute(stmt_desp)).all()

        # Carrega planos de conta para categoria_rfb
        plano_ids = {r.plano_conta_id for r in receitas} | {d.plano_conta_id for d in despesas}
        planos: dict[uuid.UUID, PlanoConta] = {}
        if plano_ids:
            stmt_pc = select(PlanoConta).where(PlanoConta.id.in_(plano_ids))
            for pc in (await self.session.execute(stmt_pc)).scalars().all():
                planos[pc.id] = pc

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Competência", "Tipo", "Categoria RFB", "Descrição",
            "Valor (R$)", "NF / Documento", "Pagador/Recebedor",
        ])

        for r in receitas:
            pc = planos.get(r.plano_conta_id)
            competencia = r.data_recebimento.strftime("%m/%Y") if r.data_recebimento else ""
            valor = float(r.valor_recebido or r.valor_total or 0)
            writer.writerow([
                competencia, "RECEITA",
                pc.categoria_rfb if pc else "RECEITA_ATIVIDADE",
                r.descricao, f"{valor:.2f}".replace(".", ","),
                r.numero_nf or "", "",
            ])

        for d in despesas:
            pc = planos.get(d.plano_conta_id)
            competencia = d.data_pagamento.strftime("%m/%Y") if d.data_pagamento else ""
            valor = float(d.valor_pago or d.valor_total or 0)
            writer.writerow([
                competencia, "DESPESA",
                pc.categoria_rfb if pc else "CUSTEIO",
                d.descricao, f"{valor:.2f}".replace(".", ","),
                d.numero_nf or "", d.fornecedor or "",
            ])

        return output.getvalue()


# ── API Contábil ─────────────────────────────────────────────────────────────

class ContabilService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def resumo(
        self,
        data_inicio: date,
        data_fim: date,
        unidade_produtiva_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Resumo financeiro estruturado para escritório contábil.
        Retorna receitas e despesas agrupadas por categoria RFB + totais.
        """
        # Receitas por categoria
        stmt_rec = (
            select(
                PlanoConta.categoria_rfb,
                PlanoConta.nome.label("categoria_nome"),
                func.sum(Receita.valor_recebido).label("total_recebido"),
                func.count(Receita.id).label("qtd"),
            )
            .join(PlanoConta, Receita.plano_conta_id == PlanoConta.id)
            .where(
                Receita.tenant_id == self.tenant_id,
                Receita.ativo == True,
                Receita.status.in_(["RECEBIDO", "RECEBIDO_PARCIAL"]),
                Receita.data_recebimento >= data_inicio,
                Receita.data_recebimento <= data_fim,
            )
            .group_by(PlanoConta.categoria_rfb, PlanoConta.nome)
        )
        if unidade_produtiva_id:
            stmt_rec = stmt_rec.where(Receita.unidade_produtiva_id == unidade_produtiva_id)

        # Despesas por categoria
        stmt_desp = (
            select(
                PlanoConta.categoria_rfb,
                PlanoConta.nome.label("categoria_nome"),
                func.sum(Despesa.valor_pago).label("total_pago"),
                func.count(Despesa.id).label("qtd"),
            )
            .join(PlanoConta, Despesa.plano_conta_id == PlanoConta.id)
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.ativo == True,
                Despesa.status.in_(["PAGO", "PAGO_PARCIAL"]),
                Despesa.data_pagamento >= data_inicio,
                Despesa.data_pagamento <= data_fim,
            )
            .group_by(PlanoConta.categoria_rfb, PlanoConta.nome)
        )
        if unidade_produtiva_id:
            stmt_desp = stmt_desp.where(Despesa.unidade_produtiva_id == unidade_produtiva_id)

        receitas_rows = (await self.session.execute(stmt_rec)).all()
        despesas_rows = (await self.session.execute(stmt_desp)).all()

        receitas = [
            {
                "categoria_rfb": r.categoria_rfb,
                "categoria_nome": r.categoria_nome,
                "total_recebido": float(r.total_recebido or 0),
                "quantidade": int(r.qtd),
            }
            for r in receitas_rows
        ]
        despesas = [
            {
                "categoria_rfb": d.categoria_rfb,
                "categoria_nome": d.categoria_nome,
                "total_pago": float(d.total_pago or 0),
                "quantidade": int(d.qtd),
            }
            for d in despesas_rows
        ]

        total_receitas = sum(r["total_recebido"] for r in receitas)
        total_despesas = sum(d["total_pago"] for d in despesas)

        return {
            "periodo": {"inicio": data_inicio.isoformat(), "fim": data_fim.isoformat()},
            "receitas": receitas,
            "despesas": despesas,
            "totais": {
                "total_receitas": round(total_receitas, 2),
                "total_despesas": round(total_despesas, 2),
                "resultado_liquido": round(total_receitas - total_despesas, 2),
            },
            "gerado_em": date.today().isoformat(),
        }
