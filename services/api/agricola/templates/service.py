from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, delete
from sqlalchemy.orm import selectinload

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from agricola.models.templates import (
    PhaseTemplate, PhaseTemplateChecklistItem, PhaseTemplateTask,
    PhaseGateRule, OperationTemplate, OperationTemplateItem, OperationDependency
)
from uuid import uuid4

from agricola.checklist.models import SafraChecklistItem
from agricola.tarefas.models import SafraTarefa, SafraTarefaNecessidade
from agricola.safras.models import Safra
from agricola.cultivos.models import Cultivo, CultivoArea

# Itens de template com esses tipos geram necessidade técnica estruturada —
# cobre tanto insumo/material físico (produto a escolher depois) quanto
# maquinário e mão de obra/serviço (recurso a alocar depois), para que o
# Plano Operacional consiga consolidar QUALQUER recurso do template em lote,
# não só produto. Ver `tipo_recurso` em InsumoConsolidadoResponse (planejamento
# operacional) para como o consumidor distingue os três casos.
_TIPO_ITEM_PARA_CATEGORIA_NECESSIDADE = {
    "SEMENTE": "SEMENTE",
    "FERTILIZANTE": "FERTILIZANTE",
    "DEFENSIVO": "DEFENSIVO",
    "MATERIAL": "MATERIAL",
    "COMBUSTIVEL": "COMBUSTIVEL",
    "OUTROS": "OUTRO",
    "MAQUINARIO": "MAQUINARIO",
    "MAO_DE_OBRA": "MAO_DE_OBRA",
    "SERVICO": "SERVICO",
}

# Fase do template -> tipo de tarefa (vocabulário de SafraTarefa.tipo).
# Sem mapeamento conhecido, cai em "OUTRO".
_FASE_PARA_TIPO_TAREFA = {
    "PLANTIO": "PLANTIO",
    "COLHEITA": "COLHEITA",
}


class PhaseTemplateService(BaseService[PhaseTemplate]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(PhaseTemplate, session, tenant_id)

    async def get_with_details(self, template_id: UUID) -> PhaseTemplate:
        stmt = select(PhaseTemplate).where(
            and_(
                PhaseTemplate.id == template_id,
                or_(PhaseTemplate.tenant_id == self.tenant_id, PhaseTemplate.tenant_id == None)
            )
        ).options(
            selectinload(PhaseTemplate.checklist_items),
            selectinload(PhaseTemplate.tasks),
            selectinload(PhaseTemplate.gate_rules)
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise BusinessRuleError("Template não encontrado ou sem permissão.")
        return obj

    async def listar(self, cultura: str | None = None, fase: str | None = None) -> List[PhaseTemplate]:
        """Lista templates do tenant + templates globais do sistema."""
        stmt = select(PhaseTemplate).where(
            or_(PhaseTemplate.tenant_id == self.tenant_id, PhaseTemplate.tenant_id == None),
            PhaseTemplate.ativo == True
        )
        if cultura:
            stmt = stmt.where(or_(PhaseTemplate.cultura == cultura, PhaseTemplate.cultura == None))
        if fase:
            stmt = stmt.where(PhaseTemplate.fase == fase)
        
        stmt = stmt.order_by(PhaseTemplate.is_system_default.desc(), PhaseTemplate.titulo)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def atualizar(self, template_id: UUID, dados) -> PhaseTemplate:
        """Atualiza template do tenant. Bloqueia edição de template global (tenant_id NULL)."""
        obj = await self.get_with_details(template_id)
        if obj.tenant_id is None:
            raise BusinessRuleError("Não é possível editar um template global do sistema. Duplique-o antes de customizar.")
        return await self.update(template_id, dados)

    async def excluir(self, template_id: UUID) -> None:
        """Exclui template do tenant. Bloqueia exclusão de template global (tenant_id NULL)."""
        obj = await self.get_with_details(template_id)
        if obj.tenant_id is None:
            raise BusinessRuleError("Não é possível excluir um template global do sistema.")
        await self.hard_delete(template_id)

    async def duplicar_global(self, global_template_id: UUID) -> PhaseTemplate:
        """Cria uma cópia de um template global para o tenant atual."""
        global_tmpl = await self.get_with_details(global_template_id)
        if global_tmpl.tenant_id is not None:
            raise BusinessRuleError("Apenas templates globais podem ser duplicados desta forma.")
        
        # Cria novo container
        new_tmpl = PhaseTemplate(
            tenant_id=self.tenant_id,
            cultura=global_tmpl.cultura,
            fase=global_tmpl.fase,
            titulo=f"{global_tmpl.titulo} (Cópia)",
            descricao=global_tmpl.descricao,
            ativo=True,
            is_system_default=False
        )
        self.session.add(new_tmpl)
        await self.session.flush()

        # Copia itens
        for item in global_tmpl.checklist_items:
            self.session.add(PhaseTemplateChecklistItem(
                phase_template_id=new_tmpl.id,
                titulo=item.titulo,
                descricao=item.descricao,
                obrigatorio=item.obrigatorio,
                ordem=item.ordem,
                ativo=item.ativo
            ))
        
        for task in global_tmpl.tasks:
            self.session.add(PhaseTemplateTask(
                phase_template_id=new_tmpl.id,
                tipo=task.tipo,
                titulo=task.titulo,
                descricao=task.descricao,
                criticidade=task.criticidade,
                ordem=task.ordem
            ))

        for rule in global_tmpl.gate_rules:
            self.session.add(PhaseGateRule(
                phase_template_id=new_tmpl.id,
                rule_type=rule.rule_type,
                config=rule.config,
                ativo=rule.ativo
            ))
            
        await self.session.flush()
        return new_tmpl


class OperationTemplateService(BaseService[OperationTemplate]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(OperationTemplate, session, tenant_id)

    async def get_with_details(self, template_id: UUID) -> OperationTemplate:
        stmt = select(OperationTemplate).where(
            and_(
                OperationTemplate.id == template_id,
                or_(OperationTemplate.tenant_id == self.tenant_id, OperationTemplate.tenant_id == None)
            )
        ).options(selectinload(OperationTemplate.items))
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            raise BusinessRuleError("Template de operações não encontrado.")
        return obj

    async def listar(self, cultura: str | None = None, fase: str | None = None) -> List[OperationTemplate]:
        stmt = select(OperationTemplate).where(
            or_(OperationTemplate.tenant_id == self.tenant_id, OperationTemplate.tenant_id == None),
            OperationTemplate.ativo == True
        )
        if cultura:
            stmt = stmt.where(or_(OperationTemplate.cultura == cultura, OperationTemplate.cultura == None))
        if fase:
            stmt = stmt.where(or_(OperationTemplate.fase == fase, OperationTemplate.fase == None))
            
        stmt = stmt.order_by(OperationTemplate.is_system_default.desc(), OperationTemplate.titulo)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def atualizar(self, template_id: UUID, dados) -> OperationTemplate:
        """Atualiza template do tenant. Bloqueia edição de template global (tenant_id NULL)."""
        obj = await self.get_with_details(template_id)
        if obj.tenant_id is None:
            raise BusinessRuleError("Não é possível editar um template global do sistema. Duplique-o antes de customizar.")
        return await self.update(template_id, dados)

    async def excluir(self, template_id: UUID) -> None:
        """Exclui template do tenant. Bloqueia exclusão de template global (tenant_id NULL)."""
        obj = await self.get_with_details(template_id)
        if obj.tenant_id is None:
            raise BusinessRuleError("Não é possível excluir um template global do sistema.")
        await self.hard_delete(template_id)

    async def _get_own_template_or_fail(self, template_id: UUID) -> OperationTemplate:
        """Garante que o template pertence ao tenant atual (nunca um template global)."""
        obj = await self.get_with_details(template_id)
        if obj.tenant_id is None:
            raise BusinessRuleError("Não é possível alterar itens de um template global do sistema.")
        return obj

    async def criar_item(self, template_id: UUID, dados) -> OperationTemplateItem:
        template = await self._get_own_template_or_fail(template_id)
        data = dados.model_dump()
        deps = data.pop("dependency_ids", [])

        item = OperationTemplateItem(**data, operation_template_id=template.id)
        self.session.add(item)
        await self.session.flush()

        for dep_id in deps:
            self.session.add(OperationDependency(item_id=item.id, dependency_id=dep_id))

        await self.session.flush()
        return item

    async def atualizar_item(self, template_id: UUID, item_id: UUID, dados) -> OperationTemplateItem:
        template = await self._get_own_template_or_fail(template_id)
        stmt = select(OperationTemplateItem).where(
            OperationTemplateItem.id == item_id,
            OperationTemplateItem.operation_template_id == template.id,
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if not item:
            raise BusinessRuleError("Item não encontrado neste template.")

        data = dados.model_dump(exclude_unset=True)
        deps = data.pop("dependency_ids", None)

        for key, val in data.items():
            setattr(item, key, val)

        if deps is not None:
            await self.session.execute(
                delete(OperationDependency).where(OperationDependency.item_id == item.id)
            )
            for dep_id in deps:
                self.session.add(OperationDependency(item_id=item.id, dependency_id=dep_id))

        await self.session.flush()
        return item

    async def excluir_item(self, template_id: UUID, item_id: UUID) -> None:
        template = await self._get_own_template_or_fail(template_id)
        stmt = select(OperationTemplateItem).where(
            OperationTemplateItem.id == item_id,
            OperationTemplateItem.operation_template_id == template.id,
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if not item:
            raise BusinessRuleError("Item não encontrado neste template.")

        await self.session.delete(item)
        await self.session.flush()

    async def duplicar_global(self, global_template_id: UUID) -> OperationTemplate:
        """Cria uma cópia de um template global operacional para o tenant atual."""
        global_tmpl = await self.get_with_details(global_template_id)
        if global_tmpl.tenant_id is not None:
            raise BusinessRuleError("Apenas templates globais podem ser duplicados desta forma.")
        
        new_tmpl = OperationTemplate(
            tenant_id=self.tenant_id,
            cultura=global_tmpl.cultura,
            fase=global_tmpl.fase,
            titulo=f"{global_tmpl.titulo} (Cópia)",
            descricao=global_tmpl.descricao,
            ativo=True,
            is_system_default=False
        )
        self.session.add(new_tmpl)
        await self.session.flush()

        for item in global_tmpl.items:
            self.session.add(OperationTemplateItem(
                operation_template_id=new_tmpl.id,
                tipo=item.tipo,
                titulo=item.titulo,
                descricao=item.descricao,
                dose_sugerida=item.dose_sugerida,
                unidade=item.unidade,
                unidade_medida_id=item.unidade_medida_id,
                can_generate_task=item.can_generate_task,
                ordem=item.ordem
            ))
            
        await self.session.flush()
        return new_tmpl

class TemplateApplicationService:
    """Service especializado em instanciar templates em uma Safra."""
    
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def aplicar_fase(self, safra_id: UUID, phase_template_id: UUID) -> Dict:
        """Instancia checklist e tarefas de um template na safra."""
        # 1. Carrega Safra e Template
        safra = await self.session.get(Safra, safra_id)
        if not safra or safra.tenant_id != self.tenant_id:
            raise BusinessRuleError("Safra não encontrada.")
            
        stmt = select(PhaseTemplate).where(PhaseTemplate.id == phase_template_id).options(
            selectinload(PhaseTemplate.checklist_items),
            selectinload(PhaseTemplate.tasks)
        )
        template = (await self.session.execute(stmt)).scalar_one_or_none()
        if not template:
            raise BusinessRuleError("Template de fase não encontrado.")

        res = {"checklist_criados": 0, "tarefas_criadas": 0}

        # 2. Instancia Checklist
        for tmpl_item in template.checklist_items:
            if not tmpl_item.ativo: continue
            
            item = SafraChecklistItem(
                safra_id=safra.id,
                tenant_id=self.tenant_id,
                template_id=tmpl_item.id,
                fase=template.fase,
                titulo=tmpl_item.titulo,
                descricao=tmpl_item.descricao,
                obrigatorio=tmpl_item.obrigatorio,
                ordem=tmpl_item.ordem
            )
            self.session.add(item)
            res["checklist_criados"] += 1

        # 3. Instancia Tarefas (como origem=TEMPLATE)
        for tmpl_task in template.tasks:
            # Note: PhaseTemplateTask não gera tarefa por talhão aqui, gera tarefa de governança da safra/fase
            # Se for necessário por talhão, o usuário deve selecionar no editor de instância
            tarefa = SafraTarefa(
                tenant_id=self.tenant_id,
                safra_id=safra.id,
                origem="TEMPLATE",
                tipo=tmpl_task.tipo,
                fase=template.fase,
                criticidade=tmpl_task.criticidade,
                descricao=tmpl_task.titulo,
                obs=tmpl_task.descricao,
                status="PENDENTE_APROVACAO"
            )
            self.session.add(tarefa)
            res["tarefas_criadas"] += 1

        await self.session.flush()
        return res

    async def aplicar_operacoes(self, safra_id: UUID, operation_template_id: UUID, talhao_ids: List[UUID]) -> Dict:
        """
        Gera tarefas operacionais para os talhões selecionados a partir de um
        template — 1 tarefa CONSOLIDADA por talhão, com uma SafraTarefaNecessidade
        por item técnico do template (mesmo padrão usado pela análise de solo:
        reúne os itens numa única tarefa em vez de uma tarefa por item).
        """
        safra = await self.session.get(Safra, safra_id)
        if not safra: raise BusinessRuleError("Safra não encontrada.")

        stmt = select(OperationTemplate).where(OperationTemplate.id == operation_template_id).options(
            selectinload(OperationTemplate.items)
        )
        template = (await self.session.execute(stmt)).scalar_one_or_none()
        if not template: raise BusinessRuleError("Template operacional não encontrado.")

        itens_geradores = [item for item in template.items if item.can_generate_task]
        itens_tecnicos = [
            item for item in itens_geradores
            if item.tipo in _TIPO_ITEM_PARA_CATEGORIA_NECESSIDADE
        ]

        area_stmt = (
            select(CultivoArea.area_id, CultivoArea.area_ha)
            .join(Cultivo, Cultivo.id == CultivoArea.cultivo_id)
            .where(Cultivo.safra_id == safra_id, CultivoArea.area_id.in_(talhao_ids))
        )
        area_ha_por_talhao = {
            row.area_id: row.area_ha for row in (await self.session.execute(area_stmt)).all()
        }

        tipo_tarefa = _FASE_PARA_TIPO_TAREFA.get(template.fase, "OUTRO")
        grupo_geracao_id = uuid4()
        tarefas_geradas = 0

        for talhao_id in talhao_ids:
            area_ha = area_ha_por_talhao.get(talhao_id)

            tarefa = SafraTarefa(
                tenant_id=self.tenant_id,
                safra_id=safra.id,
                talhao_id=talhao_id,
                grupo_geracao_id=grupo_geracao_id,
                origem="TEMPLATE",
                tipo=tipo_tarefa,
                fase=template.fase or safra.fase_atual,
                descricao=template.titulo,
                obs=f"Gerada a partir do template '{template.titulo}'.",
                area_ha=area_ha,
                status="PENDENTE_APROVACAO",
            )
            self.session.add(tarefa)
            await self.session.flush()  # garante tarefa.id para as necessidades

            for item in itens_tecnicos:
                dose = item.dose_sugerida
                quantidade = (dose * area_ha) if (dose is not None and area_ha is not None) else None
                necessidade = SafraTarefaNecessidade(
                    tenant_id=self.tenant_id,
                    safra_tarefa_id=tarefa.id,
                    categoria=_TIPO_ITEM_PARA_CATEGORIA_NECESSIDADE[item.tipo],
                    unidade_referencia=item.unidade or "UN",
                    unidade_medida_id=item.unidade_medida_id,
                    dose_tecnica=dose,
                    quantidade_tecnica=quantidade,
                    area_referencia_ha=area_ha,
                    origem_calculo="TEMPLATE",
                    parametros_calculo={
                        "operation_template_item_id": str(item.id),
                        "titulo_item": item.titulo,
                    },
                )
                self.session.add(necessidade)

            tarefas_geradas += 1

        await self.session.flush()
        return {"tarefas_geradas": tarefas_geradas, "grupo_geracao_id": str(grupo_geracao_id)}
