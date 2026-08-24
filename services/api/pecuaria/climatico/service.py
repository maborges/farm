from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.climatico.models import RegistroClima
from pecuaria.climatico.models import ModeloZoosanitario
from pecuaria.climatico.schemas import (
    InteligenciaPecuariaResponse,
    ModeloZoosanitarioCreate,
    ModeloZoosanitarioUpdate,
)


class ModeloZoosanitarioService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _copy_global_model_if_not_exists(self, tenant_id: UUID, especie: str, tipo_risco: str) -> ModeloZoosanitario | None:
        """Busca o modelo global correspondente e copia para o tenant se ainda não existir."""
        stmt_global = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id.is_(None),
            ModeloZoosanitario.is_global.is_(True),
            ModeloZoosanitario.especie == especie,
            ModeloZoosanitario.tipo_risco == tipo_risco
        )
        global_result = await self.session.execute(stmt_global)
        modelo_global = global_result.scalars().first()

        if not modelo_global:
            return None

        novo_modelo = ModeloZoosanitario(
            tenant_id=tenant_id,
            especie=especie,
            tipo_risco=tipo_risco,
            regras_risco=modelo_global.regras_risco,
            is_global=False
        )
        self.session.add(novo_modelo)
        await self.session.flush()
        # Não fazer commit aqui para não quebrar a transação e o RLS (SET LOCAL)!
        return novo_modelo

    async def get_or_copy_model(self, tenant_id: UUID, especie: str, tipo_risco: str) -> ModeloZoosanitario | None:
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id == tenant_id,
            ModeloZoosanitario.especie == especie,
            ModeloZoosanitario.tipo_risco == tipo_risco
        )
        result = await self.session.execute(stmt)
        modelo = result.scalars().first()

        if modelo:
            return modelo

        # Se não existe, tenta copiar do global
        return await self._copy_global_model_if_not_exists(tenant_id, especie, tipo_risco)

    async def get_all_models(self, tenant_id: UUID | None) -> list[ModeloZoosanitario]:
        """
        Retorna os modelos do tenant, ou todos os globais se tenant_id for None.
        Para tenants, inclui os globais também (apenas para listagem visual ou cópia).
        """
        if tenant_id:
            stmt = select(ModeloZoosanitario).where(
                or_(
                    ModeloZoosanitario.tenant_id == tenant_id,
                    ModeloZoosanitario.is_global.is_(True)
                )
            ).order_by(ModeloZoosanitario.especie)
        else:
            stmt = select(ModeloZoosanitario).where(ModeloZoosanitario.tenant_id.is_(None)).order_by(ModeloZoosanitario.especie)
            
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_model(self, tenant_id: UUID | None, payload: ModeloZoosanitarioCreate, is_global: bool = False, commit: bool = True) -> ModeloZoosanitario:
        # Verifica duplicidade
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id == tenant_id,
            ModeloZoosanitario.especie == payload.especie,
            ModeloZoosanitario.tipo_risco == payload.tipo_risco
        )
        if (await self.session.execute(stmt)).scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modelo já existe para esta espécie e risco")

        modelo = ModeloZoosanitario(
            tenant_id=tenant_id,
            especie=payload.especie,
            tipo_risco=payload.tipo_risco,
            regras_risco=payload.regras_risco,
            is_global=is_global
        )
        self.session.add(modelo)
        if commit:
            await self.session.commit()
            await self.session.refresh(modelo)
        else:
            await self.session.flush()
        return modelo

    async def update_model(self, tenant_id: UUID | None, model_id: UUID, payload: ModeloZoosanitarioUpdate) -> ModeloZoosanitario:
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.id == model_id,
            ModeloZoosanitario.tenant_id == tenant_id
        )
        modelo = (await self.session.execute(stmt)).scalars().first()
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")

        modelo.regras_risco = payload.regras_risco
        await self.session.commit()
        await self.session.refresh(modelo)
        return modelo

    async def delete_model(self, tenant_id: UUID | None, model_id: UUID) -> None:
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.id == model_id,
            ModeloZoosanitario.tenant_id == tenant_id
        )
        modelo = (await self.session.execute(stmt)).scalars().first()
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")

        await self.session.delete(modelo)
        await self.session.commit()

    async def copy_global_to_tenant(self, tenant_id: UUID, global_id: UUID) -> ModeloZoosanitario:
        stmt_global = select(ModeloZoosanitario).where(ModeloZoosanitario.id == global_id, ModeloZoosanitario.is_global.is_(True))
        modelo_global = (await self.session.execute(stmt_global)).scalars().first()
        if not modelo_global:
            raise HTTPException(status_code=404, detail="Modelo global não encontrado")
            
        return await self.create_model(
            tenant_id=tenant_id,
            payload=ModeloZoosanitarioCreate(
                especie=modelo_global.especie,
                tipo_risco=modelo_global.tipo_risco,
                regras_risco=modelo_global.regras_risco
            ),
            is_global=False,
            commit=False
        )


class InteligenciaPecuariaService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.model_svc = ModeloZoosanitarioService(session)

    async def analisar_estresse_termico(self, tenant_id: UUID, unidade_produtiva_id: UUID, especie: str) -> InteligenciaPecuariaResponse | None:
        """Calcula o risco de estresse térmico baseado nos registros de clima recentes."""
        # 1. Buscar o modelo zoossanitário para estresse térmico e espécie
        modelo = await self.model_svc.get_or_copy_model(tenant_id, especie, "Estresse Térmico")
        if not modelo:
            return None  # Não há regra cadastrada

        # 2. Buscar último clima da fazenda (ex: de hoje)
        hoje = date.today()
        # Força o RLS de novo para ter certeza que não foi perdido!
        await self.session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
        
        stmt_clima = select(RegistroClima).where(
            RegistroClima.tenant_id == tenant_id,
            RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
            RegistroClima.data_registro >= hoje - timedelta(days=2)
        ).order_by(RegistroClima.data_registro.desc()).limit(1)
        
        clima = (await self.session.execute(stmt_clima)).scalars().first()
        if not clima or clima.temp_media_c is None or clima.umidade_rel_pct is None:
            return None # Sem dados climáticos suficientes

        # 3. Calcular ITH (Índice de Temperatura e Umidade)
        # Fórmula clássica: ITH = (0.8 * T) + ((UR/100) * (T - 14.4)) + 46.4
        T = float(clima.temp_media_c)
        UR = float(clima.umidade_rel_pct)
        ith = (0.8 * T) + ((UR / 100.0) * (T - 14.4)) + 46.4

        # 4. Avaliar contra as regras do modelo
        regras = modelo.regras_risco
        critico = regras.get("nivel_critico", 82)
        alto = regras.get("nivel_alto", 78)
        medio = regras.get("nivel_medio", 72)
        
        if ith >= critico:
            risco = "CRITICO"
            detalhes = ["Risco de mortalidade! Fornecer sombreamento imediato e aspersão.", "Redução severa na produção esperada."]
        elif ith >= alto:
            risco = "ALTO"
            detalhes = ["Atenção: Queda no consumo de matéria seca e produção.", "Disponibilizar água fresca e evitar manejo em horários quentes."]
        elif ith >= medio:
            risco = "MEDIO"
            detalhes = ["Animais começam a reduzir consumo.", "Iniciar monitoramento respiratório."]
        else:
            risco = "BAIXO"
            detalhes = ["Zona de conforto térmico."]

        return InteligenciaPecuariaResponse(
            especie=especie,
            tipo_risco="Estresse Térmico",
            risco_atual=risco,
            data_analise=datetime.utcnow(),
            valor_referencia=round(ith, 1),
            detalhes=detalhes
        )
