import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from financeiro.models.cenario import FinanceiroSafraCenario
from financeiro.schemas.cenario_schema import CenarioSafraCreate
from agricola.safras.models import Safra
from fastapi import HTTPException


class CenarioFinanceiroService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def salvar(self, data: CenarioSafraCreate) -> FinanceiroSafraCenario:
        """Salva um novo cenário de simulação para a safra."""
        # Valida safra
        safra = await self.session.get(Safra, data.safra_id)
        if not safra or safra.tenant_id != self.tenant_id:
            raise HTTPException(status_code=404, detail="Safra não encontrada")

        cenario = FinanceiroSafraCenario(
            tenant_id=self.tenant_id,
            safra_id=data.safra_id,
            nome=data.nome,
            receita_percentual=data.receita_percentual,
            custos_percentual=data.custos_percentual,
            resultado_simulado=data.resultado_simulado,
            margem_simulada=data.margem_simulada
        )
        self.session.add(cenario)
        await self.session.commit()
        await self.session.refresh(cenario)
        return cenario

    async def listar(self, safra_id: uuid.UUID):
        """Lista todos os cenários salvos para uma safra específica."""
        stmt = select(FinanceiroSafraCenario).where(
            and_(
                FinanceiroSafraCenario.tenant_id == self.tenant_id,
                FinanceiroSafraCenario.safra_id == safra_id
            )
        ).order_by(FinanceiroSafraCenario.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def escolher(self, cenario_id: uuid.UUID) -> FinanceiroSafraCenario:
        """Marca um cenário como o escolhido para a safra, desmarcando outros."""
        from sqlalchemy import update
        from datetime import datetime, timezone

        # Busca o cenário para saber a safra_id
        cenario = (
            await self.session.execute(
                select(FinanceiroSafraCenario).where(
                    and_(
                        FinanceiroSafraCenario.id == cenario_id,
                        FinanceiroSafraCenario.tenant_id == self.tenant_id
                    )
                )
            )
        ).scalars().first()

        if not cenario:
            raise HTTPException(status_code=404, detail="Cenário não encontrado")

        # Desmarca todos os outros da mesma safra
        await self.session.execute(
            update(FinanceiroSafraCenario)
            .where(
                and_(
                    FinanceiroSafraCenario.safra_id == cenario.safra_id,
                    FinanceiroSafraCenario.tenant_id == self.tenant_id
                )
            )
            .values(escolhido=False, escolhido_at=None)
        )

        # Marca o atual
        cenario.escolhido = True
        cenario.escolhido_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(cenario)
        return cenario

    async def analisar_desvio(self, safra_id: uuid.UUID):
        """Compara o cenário escolhido com o resultado real (DRE) da safra."""
        from financeiro.services.lancamento_service import LancamentoService

        # Busca cenário escolhido
        stmt = select(FinanceiroSafraCenario).where(
            and_(
                FinanceiroSafraCenario.safra_id == safra_id,
                FinanceiroSafraCenario.tenant_id == self.tenant_id,
                FinanceiroSafraCenario.escolhido == True
            )
        ).limit(1)
        
        cenario = (await self.session.execute(stmt)).scalar_one_or_none()
        
        # Busca DRE Real
        dre_real = await LancamentoService(self.session, self.tenant_id).gerar_dre(safra_id)
        
        if not cenario:
            return {
                "cenario_escolhido": None,
                "resultado_real": dre_real.resultado_operacional,
                "resultado_planejado": 0,
                "desvio": 0,
                "desvio_percentual": 0
            }

        resultado_planejado = float(cenario.resultado_simulado)
        resultado_real = dre_real.resultado_operacional
        desvio = resultado_real - resultado_planejado
        desvio_pct = (desvio / abs(resultado_planejado) * 100) if resultado_planejado != 0 else 0

        return {
            "cenario_escolhido": cenario.nome,
            "resultado_real": resultado_real,
            "resultado_planejado": resultado_planejado,
            "desvio": desvio,
            "desvio_percentual": desvio_pct
        }

    async def deletar(self, cenario_id: uuid.UUID):
        """Remove um cenário salvo."""
        from sqlalchemy import delete
        stmt = delete(FinanceiroSafraCenario).where(
            and_(
                FinanceiroSafraCenario.id == cenario_id,
                FinanceiroSafraCenario.tenant_id == self.tenant_id
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
