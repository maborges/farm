"""
Step IA-Growth-11 — Geração de Copy via LLM personalizado.
Este serviço gera comunicações persuasivas adaptadas ao contexto do produtor rural.
"""
from __future__ import annotations
import json
import os
import uuid
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, Tuple

from ia.models import IAGrowthCopyCache
from ia import usage_service as _usage_svc
from ia.insights_service import tenant_tem_ia, _ia_globalmente_habilitada

@dataclass
class ContextoUsuarioGrowth:
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    tier_atual: str
    nivel_uso: str # BAIXO, MEDIO, ALTO
    roi_acumulado: float
    perfil_persona: str # CONSERVADOR, EXPLORADOR, etc. (Growth-12)

@dataclass
class DadosGrowth:
    taxa_conversao_atual: float
    abordagem_vencedora: str # Melhor tipo_abordagem para o perfil/contexto (Growth-12)

@dataclass
class CTAResponseLLM:
    titulo: str
    descricao: str
    botao: str
    tipo_abordagem: str
    origem: str = "LLM"

class IAGrowthLLMService:
    @staticmethod
    def _gerar_perfil_hash(usuario_ctx: ContextoUsuarioGrowth) -> str:
        """Gera um hash único para o perfil do usuário para granularidade de cache (Growth-12)."""
        payload = f"{usuario_ctx.perfil_persona}|{usuario_ctx.nivel_uso}|{usuario_ctx.tier_atual}"
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    async def _obter_cache(session: AsyncSession, tenant_id: uuid.UUID, contexto: str, perfil_hash: str) -> Optional[Dict[str, Any]]:
        """Busca copy no cache se não estiver expirado (TTL 12h)."""
        stmt = select(IAGrowthCopyCache).where(
            IAGrowthCopyCache.tenant_id == tenant_id,
            IAGrowthCopyCache.contexto == contexto,
            IAGrowthCopyCache.perfil_hash == perfil_hash
        )
        result = await session.execute(stmt)
        cache = result.scalar_one_or_none()
        
        if cache:
            # TTL de 12 horas
            if datetime.now(timezone.utc) - cache.created_at.replace(tzinfo=timezone.utc) < timedelta(hours=12):
                return cache.cta
            else:
                # Remove cache expirado
                await session.delete(cache)
                await session.flush()
        
        return None

    @staticmethod
    async def _salvar_cache(session: AsyncSession, tenant_id: uuid.UUID, contexto: str, perfil_hash: str, cta: Dict[str, Any]):
        """Salva ou atualiza o cache de copy."""
        # Limpa anterior
        await session.execute(
            delete(IAGrowthCopyCache).where(
                IAGrowthCopyCache.tenant_id == tenant_id,
                IAGrowthCopyCache.contexto == contexto,
                IAGrowthCopyCache.perfil_hash == perfil_hash
            )
        )
        
        new_cache = IAGrowthCopyCache(
            tenant_id=tenant_id,
            contexto=contexto,
            perfil_hash=perfil_hash,
            cta=cta
        )
        session.add(new_cache)
        await session.flush()

    @staticmethod
    def _montar_prompt(contexto: str, usuario_ctx: ContextoUsuarioGrowth, growth_ctx: DadosGrowth) -> str:
        dados_input = {
            "contexto_app": contexto,
            "usuario": asdict(usuario_ctx),
            "performance_historica": asdict(growth_ctx)
        }

        return f"""Você é um especialista em Growth e Copywriting para o setor de agronegócio (Produtores Rurais).
Sua missão é gerar um CTA (Call to Action) curto, persuasivo e altamente personalizado para convencer o produtor a fazer um upgrade ou contratar um novo módulo de Inteligência Artificial.

CONTEXTO DO USUÁRIO E PERSONA:
{json.dumps(dados_input, ensure_ascii=False, indent=2)}

DIRETRIZES DE COMUNICAÇÃO:
1. Use linguagem simples, direta e rural-friendly. Evite "startupês" ou termos técnicos complexos de marketing.
2. Foco total em VALOR PRÁTICO: Produtividade, Lucro, Controle, Segurança e Economia.
3. Adapte o tom à PERSONA do Growth:
   - CONSERVADOR: Seja sutil, foque em segurança e prova social.
   - EXPLORADOR: Foque em inovação e novas possibilidades.
   - ORIENTADO_A_RESULTADO: Use dados numéricos e ROI.
   - INICIANTE: Foco em simplicidade e primeiros passos.
   - AVANCADO: Foco em escala e refinamento tecnológico.
4. Utilize a Abordagem Vencedora informada para guiar o argumento principal.
5. Tipos de Abordagem permitidos: URGENCIA, PROVA_SOCIAL, GANHO, PERDA, EDUCATIVO.

Responda EXCLUSIVAMENTE em formato JSON:
{{
  "titulo": "Título curto e impactante (max 40 caracteres)",
  "descricao": "Frase de valor que conecte com a dor/desejo do produtor (max 120 caracteres)",
  "botao": "Texto do botão de ação (max 20 caracteres)",
  "tipo_abordagem": "Uma das 5 abordagens acima"
}}"""

    @classmethod
    async def gerar_copy_cta_llm(
        cls,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        contexto: str,
        usuario_ctx: ContextoUsuarioGrowth,
        growth_ctx: DadosGrowth,
        usuario_id: Optional[uuid.UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Gera copy personalizado via LLM com cache e fallback.
        """
        # 1. Verifica Cache
        perfil_hash = cls._gerar_perfil_hash(usuario_ctx)
        cached_cta = await cls._obter_cache(session, tenant_id, contexto, perfil_hash)
        if cached_cta:
            logger.info(f"Usando copy cacheado para tenant={tenant_id}, contexto={contexto}")
            return cached_cta

        # 2. Verifica Disponibilidade de IA (Tier + Feature Flag Global)
        # Nota: Feature flag por tenant 'llm_growth_enabled' deve ser checada no caller ou aqui via config.
        # Por enquanto usamos o tenant_tem_ia geral.
        if not await tenant_tem_ia(tenant_id, session) or not _ia_globalmente_habilitada():
            return None

        # 3. Verifica Limites de Uso
        from core.models.billing import AssinaturaTenant, PlanoAssinatura
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            ).limit(1)
        )
        tier_value = (await session.execute(stmt)).scalar_one_or_none()
        
        pode_usar, fonte_consumo = await _usage_svc.verificar_limite_ia(tenant_id, tier_value, session)
        if not pode_usar:
            return None

        # 4. Chamada LLM
        import httpx
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        prompt = cls._montar_prompt(contexto, usuario_ctx, growth_ctx)
        model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 400,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                
            content = resp.json()["content"][0]["text"].strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            parsed = json.loads(content[start:end])
            
            # Sanitização básica
            cta = {
                "titulo": parsed.get("titulo", "Evolua sua Gestão")[:40],
                "descricao": parsed.get("descricao", "Descubra como a IA pode aumentar sua produtividade.")[:120],
                "botao": parsed.get("botao", "Ver Detalhes")[:20],
                "tipo_abordagem": parsed.get("tipo_abordagem", "GANHO"),
                "origem": "LLM"
            }

            # 5. Salva no Cache
            await cls._salvar_cache(session, tenant_id, contexto, perfil_hash, cta)
            
            # 6. Registra Uso
            if fonte_consumo == "PACOTE":
                await _usage_svc.consumir_credito_pacote(tenant_id, session)
            
            await _usage_svc.registrar_uso_ia(
                session, tenant_id, "growth_copy_llm", "SUCESSO",
                modelo=model, usuario_id=usuario_id, fonte_consumo=fonte_consumo
            )
            
            return cta

        except Exception as exc:
            logger.error(f"IA falhou na geração de copy de growth: {exc}")
            await _usage_svc.registrar_uso_ia(session, tenant_id, "growth_copy_llm", "ERRO", modelo=model, usuario_id=usuario_id)
            return None
