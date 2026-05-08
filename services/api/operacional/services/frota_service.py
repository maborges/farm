import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from core.cadastros.equipamentos.models import Equipamento as Maquinario
from operacional.models.frota import PlanoManutencao, OrdemServico, RegistroManutencao, ItemOrdemServico, JornadaEquipamento
from operacional.schemas.frota import (
    PlanoManutencaoCreate, OrdemServicoCreate, OrdemServicoUpdate,
    ItemOrdemServicoCreate
)
from operacional.services.estoque_service import EstoqueService

class FrotaService(BaseService[Maquinario]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(Maquinario, session, tenant_id)

    def _normalizar_payload_maquinario(self, payload: dict) -> dict:
        normalized = dict(payload)

        ano = normalized.pop("ano", None)
        if ano is not None and "ano_fabricacao" not in normalized:
            normalized["ano_fabricacao"] = ano

        placa_chassi = normalized.pop("placa_chassi", None)
        if placa_chassi:
            normalized.setdefault("placa", placa_chassi)

        tipo_map = {
            "COLHEITADEIRA": "COLHEDORA",
            "VEICULO_LEVE": "VEICULO",
            "VEICULO_PESADO": "VEICULO",
            "OUTROS": "OUTRO",
            "CAMINHAO": "VEICULO",
            "PICKUP": "VEICULO",
        }
        status_map = {
            "MANUTENCAO": "EM_MANUTENCAO",
            "PARADO": "INATIVO",
        }

        if normalized.get("tipo") in tipo_map:
            normalized["tipo"] = tipo_map[normalized["tipo"]]
        if normalized.get("status") in status_map:
            normalized["status"] = status_map[normalized["status"]]

        return normalized

    async def create(self, obj_in):
        payload = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        return await super().create(self._normalizar_payload_maquinario(payload))

    async def update(self, id, obj_in):
        payload = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        return await super().update(id, self._normalizar_payload_maquinario(payload))

    async def criar_plano_manutencao(self, dados: PlanoManutencaoCreate) -> PlanoManutencao:
        payload = dados.model_dump()
        plano = PlanoManutencao(
            equipamento_id=payload["maquinario_id"],
            descricao=payload["descricao"],
            frequencia_dias=payload.get("frequencia_dias"),
            frequencia_horas=payload.get("frequencia_horas"),
            frequencia_km=payload.get("frequencia_km"),
        )
        self.session.add(plano)
        await self.session.flush()
        return plano

    async def listar_planos(self, maquinario_id: uuid.UUID) -> List[PlanoManutencao]:
        stmt = select(PlanoManutencao).where(PlanoManutencao.equipamento_id == maquinario_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def abrir_os(self, dados: OrdemServicoCreate) -> OrdemServico:
        # Gera numero de OS sequencial ou baseado em timestamp
        timestamp = int(datetime.now().timestamp())
        numero_os = f"OS-{timestamp}"
        
        # 1.5 Herança de Contexto (Jornada Ativa)
        stmt_jornada = (
            select(JornadaEquipamento.safra_id, JornadaEquipamento.talhao_id)
            .where(
                JornadaEquipamento.tenant_id == self.tenant_id,
                JornadaEquipamento.equipamento_id == dados.maquinario_id,
                JornadaEquipamento.status == "ABERTA"
            )
            .order_by(JornadaEquipamento.data_inicio.desc())
            .limit(1)
        )
        jornada_ctx = (await self.session.execute(stmt_jornada)).first()

        os = OrdemServico(
            tenant_id=self.tenant_id,
            numero_os=numero_os,
            equipamento_id=dados.maquinario_id,
            tipo=dados.tipo,
            descricao_problema=dados.descricao_problema,
            horimetro_na_abertura=dados.horimetro_na_abertura,
            km_na_abertura=dados.km_na_abertura,
            tecnico_responsavel=dados.tecnico_responsavel,
            safra_id=jornada_ctx.safra_id if jornada_ctx else None,
            talhao_id=jornada_ctx.talhao_id if jornada_ctx else None,
        )
        
        # Opcional: Marcar maquinário em manutenção
        maquina = await self.session.get(Maquinario, dados.maquinario_id)
        if maquina:
            maquina.status = "EM_MANUTENCAO"
            
        self.session.add(os)
        await self.session.commit()
        return os

    async def adicionar_item_os(self, os_id: uuid.UUID, dados: ItemOrdemServicoCreate) -> ItemOrdemServico:
        os = await self.session.get(OrdemServico, os_id)
        if not os or os.tenant_id != self.tenant_id:
            raise BusinessRuleError("Ordem de serviço não encontrada.")
        
        # Busca preço médio do produto para registrar o custo histórico na OS
        from core.cadastros.models import ProdutoCatalogo as Produto
        produto = await self.session.get(Produto, dados.produto_id)
        if not produto:
            raise BusinessRuleError("Produto não encontrado.")

        item = ItemOrdemServico(
            os_id=os_id,
            produto_id=dados.produto_id,
            quantidade=dados.quantidade,
            preco_unitario_na_data=produto.preco_medio
        )
        
        # Atualiza custo total de peças na OS
        os.custo_total_pecas += (dados.quantidade * produto.preco_medio)
        
        self.session.add(item)
        await self.session.commit()
        return item

    async def fechar_os(self, os_id: uuid.UUID, dados: OrdemServicoUpdate) -> OrdemServico:
        os = await self.session.get(OrdemServico, os_id)
        if not os or os.tenant_id != self.tenant_id:
            raise BusinessRuleError("Ordem de serviço não encontrada.")
            
        if os.status == "CONCLUIDA":
            raise BusinessRuleError("Esta OS já foi concluída.")

        # 1. Atualiza dados básicos
        for key, value in dados.model_dump(exclude_unset=True).items():
            setattr(os, key, value)
            
        os.status = "CONCLUIDA"
        os.data_conclusao = datetime.now(timezone.utc)
        
        # 2. Marcar maquinário como ATIVO e atualizar horímetro se houve evolução
        maquina = await self.session.get(Maquinario, os.equipamento_id)
        if maquina:
            maquina.status = "ATIVO"
            # Aqui poderíamos atualizar o horímetro da máquina se a OS registrou o uso final
        
        # 3. Baixa Automática no Estoque para cada item da OS
        estoque_svc = EstoqueService(self.session, self.tenant_id)
        
        stmt_itens = select(ItemOrdemServico).where(ItemOrdemServico.os_id == os_id)
        itens = (await self.session.execute(stmt_itens)).scalars().all()
        
        for item in itens:
            await estoque_svc.registrar_saida_insumo(
                produto_id=item.produto_id,
                quantidade=item.quantidade,
                unidade_produtiva_id=maquina.unidade_produtiva_id, # Usamos a fazenda do maquinário
                origem_id=os.id,
                origem_tipo="ORDEM_SERVICO",
                motivo=f"Uso na OS {os.numero_os} - {maquina.nome}"
            )
            
        # 4. Gera registro histórico consolidado
        custo_os = os.custo_total_pecas + (os.custo_mao_obra or 0)
        registro = RegistroManutencao(
            equipamento_id=os.equipamento_id,
            os_id=os.id,
            tipo=os.tipo,
            descricao=f"OS {os.numero_os} concluída: {os.descricao_problema}",
            custo_total=custo_os,
            horimetro_na_data=os.horimetro_na_abertura,
            km_na_data=os.km_na_abertura,
            tecnico_responsavel=os.tecnico_responsavel,
            safra_id=os.safra_id,
            talhao_id=os.talhao_id,
        )
        self.session.add(registro)

        if os.tipo == "PREVENTIVA" and os.plano_manutencao_id:
            plano = await self.session.get(PlanoManutencao, os.plano_manutencao_id)
            if plano:
                plano.ultimo_registro_data = os.data_conclusao
                plano.ultimo_registro_horas = os.horimetro_na_abertura
                plano.ultimo_registro_km = os.km_na_abertura

        # 5. Integração Financeira: Despesa de Manutenção
        if maquina and maquina.unidade_produtiva_id and custo_os > 0:
            from datetime import date as _date
            from financeiro.models.despesa import Despesa
            from financeiro.models.plano_conta import PlanoConta
            stmt_pc = (
                select(PlanoConta.id)
                .where(
                    PlanoConta.tenant_id == self.tenant_id,
                    PlanoConta.categoria_rfb == "CUSTEIO",
                    PlanoConta.natureza == "ANALITICA",
                    PlanoConta.ativo == True,
                )
                .limit(1)
            )
            plano_id = (await self.session.execute(stmt_pc)).scalar()
            if plano_id:
                hoje = _date.today()
                self.session.add(Despesa(
                    id=uuid.uuid4(),
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=maquina.unidade_produtiva_id,
                    plano_conta_id=plano_id,
                    descricao=f"Manutenção — {os.numero_os}: {maquina.nome}",
                    valor_total=round(custo_os, 2),
                    data_emissao=hoje,
                    data_vencimento=hoje,
                    data_pagamento=hoje,
                    status="PAGO",
                ))

        await self.session.commit()
        await self.session.refresh(os)
        return os
