from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.safras.models import Safra
from core.constants import PlanTier
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from ia import usage_service as _usage_svc
from ia.essential_service import IAEssentialService
from ia.growth_service import IAGrowthService
from ia.insights_service import _ia_globalmente_habilitada, tenant_tem_ia
from ia.models import IAGrowthAssistenteInteracao, IAGrowthEvento, IAUso


class IACommercialAssistantService:
    _PERGUNTAS_BASE = [
        "Por que esse plano é recomendado?",
        "O que ganho com o Profissional?",
        "Vale a pena ir para Enterprise?",
        "Como aproveitar melhor meu plano atual?",
    ]

    @staticmethod
    def _is_privilegiado(claims: dict) -> bool:
        return claims.get("is_owner") is True or claims.get("role") in {"owner", "admin"}

    @staticmethod
    async def _tier_atual(db: AsyncSession, tenant_id: uuid.UUID) -> str:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL"]),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or PlanTier.BASICO.value

    @staticmethod
    def _normalizar_lista(valores: List[str], limite: int = 3) -> List[str]:
        saida: List[str] = []
        for valor in valores:
            texto = (valor or "").strip()
            if texto and texto not in saida:
                saida.append(texto)
            if len(saida) >= limite:
                break
        return saida

    @staticmethod
    def _mapear_modulo(origem: str) -> Optional[str]:
        origem = (origem or "").lower()
        if any(k in origem for k in ("dre", "lancamento", "receita", "despesa", "financeiro")):
            return "Financeiro"
        if any(k in origem for k in ("analise", "solo", "safra", "caderno", "prescricao", "rastreabilidade", "agric")):
            return "Agrícola"
        if any(k in origem for k in ("compras", "estoque", "pedido", "lote", "suprimento")):
            return "Suprimentos"
        if any(k in origem for k in ("billing", "plano", "upgrade", "growth")):
            return "Comercial / IA"
        if any(k in origem for k in ("support", "ticket")):
            return "Suporte"
        return None

    @staticmethod
    async def _modulos_usados(db: AsyncSession, tenant_id: uuid.UUID, usuario_id: Optional[uuid.UUID], dias: int = 30) -> List[str]:
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        stmt = select(IAUso.origem).where(
            IAUso.tenant_id == tenant_id,
            IAUso.created_at >= desde,
        )
        if usuario_id:
            stmt = stmt.where(IAUso.usuario_id == usuario_id)
        rows = (await db.execute(stmt)).scalars().all()
        modulos = [IACommercialAssistantService._mapear_modulo(origem) for origem in rows]
        return IACommercialAssistantService._normalizar_lista([m for m in modulos if m])

    @staticmethod
    async def _cta_recente(db: AsyncSession, tenant_id: uuid.UUID, usuario_id: Optional[uuid.UUID]) -> Dict[str, int]:
        desde = datetime.now(timezone.utc) - timedelta(days=14)
        filtros = [
            IAGrowthEvento.tenant_id == tenant_id,
            IAGrowthEvento.created_at >= desde,
        ]
        if usuario_id:
            filtros.append(IAGrowthEvento.usuario_id == usuario_id)

        q = await db.execute(
            select(
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_viewed").label("views"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_clicked").label("clicks"),
                func.count(IAGrowthEvento.id).filter(IAGrowthEvento.evento == "upgrade_cta_dismissed").label("dismisses"),
            ).where(and_(*filtros))
        )
        row = q.one()
        return {
            "views": int(row.views or 0),
            "clicks": int(row.clicks or 0),
            "dismisses": int(row.dismisses or 0),
        }

    @staticmethod
    async def _safra_atual(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        safra_id = await IAEssentialService.resolve_safra_id(db, tenant_id, None)
        if not safra_id:
            return None
        stmt = select(Safra.ano_safra, Safra.cultura, Safra.status).where(
            Safra.id == safra_id,
            Safra.tenant_id == tenant_id,
        ).limit(1)
        row = (await db.execute(stmt)).mappings().first()
        return dict(row) if row else None

    @staticmethod
    async def gerar_contexto_usuario(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        visao_completa: bool = False,
    ) -> Dict[str, Any]:
        fit = await IAGrowthService.calcular_fit_plano(db, tenant_id, usuario_id)
        plano_atual = fit["plano_atual"]
        plano_sugerido = fit["plano_recomendado"]
        plano_atual_label = IAGrowthService.PLANO_LABEL.get(plano_atual, plano_atual)
        plano_sugerido_label = IAGrowthService.PLANO_LABEL.get(plano_sugerido, plano_sugerido)
        churn_level = fit["churn_risk_level"]
        persona = fit.get("persona") or "NEUTRO"
        score_fit = float(fit["score_fit"])
        score_oportunidade = await IAGrowthService.calcular_score_oportunidade(db, tenant_id, usuario_id)
        oferta = await IAGrowthService.calcular_tipo_oferta(
            db,
            tenant_id,
            usuario_id,
            fit=fit,
            score_oportunidade=score_oportunidade,
            categoria=score_oportunidade.get("categoria"),
        )
        incentivo = await IAGrowthService.gerar_incentivo_controlado(
            db,
            tenant_id,
            usuario_id,
            origem="ASSISTENTE",
            fit=fit,
            score_oportunidade=score_oportunidade,
            oferta_info=oferta,
        )

        modulos_usados = await IACommercialAssistantService._modulos_usados(db, tenant_id, usuario_id)
        cta_recente = await IACommercialAssistantService._cta_recente(db, tenant_id, usuario_id)
        safra = await IACommercialAssistantService._safra_atual(db, tenant_id)

        motivos = fit["motivos"] or []
        motivo_principal = motivos[0] if motivos else f"Seu momento atual aponta para {plano_sugerido_label}."

        if churn_level == "ALTO":
            oportunidade = "Há risco de abandono. O melhor próximo passo é apoio prático e valor imediato."
            proximos_passos = [
                "Abrir um guia rápido de uso",
                "Revisar recursos que estão bloqueados no plano atual",
                "Falar com o suporte antes de pensar em upgrade",
            ]
        elif plano_sugerido != plano_atual:
            oportunidade = f"Existe uma oportunidade clara de evoluir para {plano_sugerido_label} com base no uso real."
            proximos_passos = [
                f"Comparar o plano atual com {plano_sugerido_label}",
                "Ver quais recursos já estão sendo usados hoje",
                "Avaliar se o salto traz valor prático agora",
            ]
        else:
            oportunidade = "Seu plano atual parece coerente com o uso de hoje. O foco é extrair mais valor do que já está disponível."
            proximos_passos = [
                "Explorar melhor os módulos já liberados",
                "Ativar recursos pouco usados",
                "Perguntar como ganhar mais tempo no dia a dia",
            ]

        if cta_recente["dismisses"] >= 3 and cta_recente["dismisses"] > cta_recente["clicks"]:
            oportunidade = (
                "Você vem ignorando CTAs recentes. O melhor caminho agora é reduzir pressão e mostrar valor prático."
            )
            proximos_passos = [
                "Receber uma orientação mais leve e objetiva",
                "Revisar os recursos já disponíveis no plano atual",
                "Falar com suporte antes de qualquer movimento comercial",
            ]
        elif cta_recente["clicks"] > 0 and cta_recente["clicks"] >= cta_recente["dismisses"]:
            oportunidade = (
                oportunidade + " Há sinais de abertura para recomendações guiadas e próximos passos consultivos."
            )

        features_bloqueadas = IACommercialAssistantService._normalizar_lista(
            list(fit.get("funcionalidades_mais_relevantes", []))[3:6]
        )
        if not visao_completa:
            features_bloqueadas = features_bloqueadas[:2]

        if visao_completa:
            resumo_perfil = (
                f"{plano_atual_label} | Persona {persona} | churn {churn_level} | "
                f"fit {score_fit * 100:.0f}%"
            )
        else:
            resumo_perfil = (
                f"{plano_atual_label} | fit {score_fit * 100:.0f}% | orientação consultiva disponível"
            )

        return {
            "visao_completa": visao_completa,
            "resumo_perfil": resumo_perfil,
            "oportunidade_identificada": oportunidade,
            "plano_atual": plano_atual,
            "plano_atual_label": plano_atual_label,
            "plano_sugerido": plano_sugerido,
            "plano_sugerido_label": plano_sugerido_label,
            "motivo_principal": motivo_principal,
            "proximos_passos_sugeridos": proximos_passos,
            "perguntas_sugeridas": IACommercialAssistantService._PERGUNTAS_BASE,
            "score_fit": score_fit,
            "persona": persona if visao_completa else None,
            "churn_risk_level": churn_level,
            "safra_status": safra["status"] if safra else None,
            "safra_ano": safra["ano_safra"] if safra else None,
            "estagio_safra": safra["status"] if safra else None,
            "modulos_usados": modulos_usados if visao_completa else modulos_usados[:2],
            "features_bloqueadas": features_bloqueadas,
            "cta_recente": cta_recente,
            "sinais": fit.get("sinais", {}),
            "tipo_oferta": oferta["tipo_oferta"],
            "mensagem_oferta": oferta["mensagem_oferta"],
            "beneficio_destacado": oferta["beneficio_destacado"],
            "incentivo": incentivo,
        }

    @staticmethod
    def _mapear_acao(cta_sugerido: str, plano_recomendado: str, churn_level: str) -> Dict[str, Optional[str]]:
        cta_sugerido_lower = (cta_sugerido or "").lower()
        if churn_level == "ALTO":
            return {"acao_sugerida": "FALAR_COM_SUPORTE", "cta_url": "/dashboard/settings/support"}
        if "enterprise" in cta_sugerido_lower:
            return {"acao_sugerida": "VER_PLANO_ENTERPRISE", "cta_url": "/dashboard/settings/billing"}
        if "profissional" in cta_sugerido_lower or plano_recomendado == PlanTier.PROFISSIONAL.value:
            return {"acao_sugerida": "VER_PLANO_PROFISSIONAL", "cta_url": "/dashboard/settings/billing"}
        if "recurso" in cta_sugerido_lower:
            return {"acao_sugerida": "EXPLORAR_RECURSOS", "cta_url": "/dashboard/ia/performance"}
        return {"acao_sugerida": "VER_PLANOS", "cta_url": "/dashboard/settings/billing"}

    @staticmethod
    def _resposta_heuristica(contexto: Dict[str, Any], mensagem_usuario: str) -> Dict[str, Any]:
        texto = (mensagem_usuario or "").lower()
        plano_sugerido = contexto["plano_sugerido"]
        plano_sugerido_label = contexto["plano_sugerido_label"]
        plano_atual_label = contexto["plano_atual_label"]
        motivo = contexto["motivo_principal"]
        churn = contexto["churn_risk_level"]
        tipo_oferta = contexto.get("tipo_oferta", "CONSULTIVO")
        beneficio_destacado = contexto.get("beneficio_destacado") or plano_sugerido_label

        if churn == "ALTO":
            resposta = (
                "Percebi sinais de risco de abandono. Antes de falar em upgrade, "
                "o mais útil é te mostrar onde você pode ganhar valor rápido e sem complexidade."
            )
            cta_sugerido = "Ver ajuda rápida"
            acao_sugerida = "FALAR_COM_SUPORTE"
            cta_url = "/dashboard/settings/support"
        elif any(p in texto for p in ("por que", "porque", "motivo")):
            resposta = (
                f"O {plano_sugerido_label} foi sugerido porque o uso atual indica melhor encaixe com esse nível. "
                f"O principal motivo é: {motivo}"
            )
            cta_sugerido = f"Ver {plano_sugerido_label}"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANO_PROFISSIONAL" if plano_sugerido == PlanTier.PROFISSIONAL.value else "VER_PLANOS"
        elif any(p in texto for p in ("profissional", "vale a pena", "compensa")):
            resposta = (
                f"O {plano_sugerido_label} faz sentido quando você quer mais recursos e suporte para escalar. "
                f"Hoje o seu plano atual é {plano_atual_label}, então o ganho precisa ser prático e claro."
            )
            cta_sugerido = "Comparar planos"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANOS"
        elif "enterprise" in texto:
            resposta = (
                "Enterprise vale quando a operação pede escala, múltiplas unidades, rastreabilidade e governança avançada. "
                "Se isso ainda não pesa no dia a dia, talvez seja melhor explorar melhor o plano atual primeiro."
            )
            cta_sugerido = "Ver Enterprise"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANO_ENTERPRISE"
        elif any(p in texto for p in ("aproveitar", "melhor", "usar")):
            resposta = (
                f"Hoje eu começaria pelo que já está liberado no {plano_atual_label}: "
                "mapear os recursos mais usados, revisar o que ainda não virou rotina e te mostrar atalhos práticos."
            )
            cta_sugerido = "Explorar recursos"
            cta_url = "/dashboard/ia/performance"
            acao_sugerida = "EXPLORAR_RECURSOS"
        elif tipo_oferta == "SEM_INCENTIVO":
            resposta = (
                f"O cenário já aponta para {plano_sugerido_label}. O próximo passo é objetivo e sem pressão."
            )
            cta_sugerido = f"Ver {plano_sugerido_label}"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANOS"
        elif tipo_oferta == "INCENTIVO_FORTE":
            resposta = (
                f"Existe uma oportunidade clara de evoluir agora. O principal ganho está em {beneficio_destacado}."
            )
            cta_sugerido = "Ver oportunidade"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANOS"
        elif tipo_oferta == "INCENTIVO_LEVE":
            resposta = (
                f"Há uma oportunidade simples de avançar com foco em valor prático, especialmente em {beneficio_destacado}."
            )
            cta_sugerido = "Sugestão de evolução"
            cta_url = "/dashboard/settings/billing"
            acao_sugerida = "VER_PLANOS"
        elif tipo_oferta == "EDUCATIVO":
            resposta = (
                "Antes de avançar, vale explorar melhor o que você já tem disponível e destravar valor com menos fricção."
            )
            cta_sugerido = "Ver ajuda prática"
            cta_url = "/dashboard/ia/performance"
            acao_sugerida = "EXPLORAR_RECURSOS"
        else:
            resposta = (
                f"Meu conselho inicial é focar no valor prático do {plano_sugerido_label}. "
                "Posso te mostrar o que está liberado, o que está travado e qual próximo passo faz mais sentido para sua operação."
            )
            cta_sugerido = "Ver próximos passos"
            cta_url = "/dashboard/ia/performance"
            acao_sugerida = "VER_PROXIMOS_PASSOS"

        incentivo = contexto.get("incentivo")
        if incentivo and incentivo.get("status") in {"OFERECIDO", "APROVADO"}:
            prazo = incentivo.get("validade_fim")
            prazo_txt = f" até {prazo[:10]}" if isinstance(prazo, str) and len(prazo) >= 10 else " por tempo limitado"
            resposta = f"{resposta} Também existe um benefício temporário disponível{prazo_txt}."
            if tipo_oferta in {"INCENTIVO_LEVE", "INCENTIVO_FORTE"}:
                cta_sugerido = "Ver benefício temporário"
                cta_url = "/dashboard/ia/performance"
                acao_sugerida = "VER_PLANOS"

        return {
            "resposta_ia": resposta,
            "cta_sugerido": cta_sugerido,
            "cta_url": cta_url,
            "acao_sugerida": acao_sugerida,
            "plano_recomendado": plano_sugerido,
            "fonte": "HEURISTICO",
            "tipo_oferta": tipo_oferta,
            "mensagem_oferta": contexto.get("mensagem_oferta", ""),
            "beneficio_destacado": beneficio_destacado,
            "incentivo": contexto.get("incentivo"),
        }

    @staticmethod
    def _montar_prompt(contexto: Dict[str, Any], mensagem_usuario: str) -> str:
        dados_input = {
            "contexto": contexto,
            "mensagem_usuario": mensagem_usuario,
        }
        return f"""Você é um assistente comercial e de customer success para um SaaS do agro.
Sua resposta precisa ser consultiva, simples, sem prometer resultado financeiro garantido e sem propor upgrade automático.

Regras:
- Linguagem simples, objetiva e respeitosa.
- Explique sempre o motivo da recomendação.
- Se houver risco de churn, priorize ajuda prática e suporte.
- Se o usuário perguntar sobre plano, explique vantagens, limitações e o próximo passo.
- Não invente preços, números ou benefícios não presentes no contexto.
- Não pressione venda agressiva.

Responda exclusivamente em JSON com as chaves:
{{
  "resposta_ia": "texto curto e consultivo",
  "cta_sugerido": "texto do botão",
  "cta_url": "/rota/adequada",
  "plano_recomendado": "BASICO | PROFISSIONAL | ENTERPRISE",
  "acao_sugerida": "VER_PLANOS | VER_PLANO_PROFISSIONAL | VER_PLANO_ENTERPRISE | EXPLORAR_RECURSOS | FALAR_COM_SUPORTE",
  "tipo_oferta": "SEM_INCENTIVO | INCENTIVO_LEVE | INCENTIVO_FORTE | EDUCATIVO | CONSULTIVO",
  "mensagem_oferta": "explicacao consultiva do por que dessa abordagem",
  "beneficio_destacado": "beneficio principal destacado"
}}

CONTEXTO:
{json.dumps(dados_input, ensure_ascii=False, indent=2)}
"""

    @staticmethod
    async def registrar_interacao_assistente(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        plano_atual: str,
        plano_recomendado: str,
        persona: Optional[str],
        churn_risk_level: str,
        mensagem_usuario: str,
        resposta_ia: str,
        cta_sugerido: str,
        acao_sugerida: str,
    ) -> Optional[uuid.UUID]:
        try:
            row = IAGrowthAssistenteInteracao(
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                plano_atual=plano_atual,
                plano_recomendado=plano_recomendado,
                persona=persona,
                churn_risk_level=churn_risk_level,
                mensagem_usuario=mensagem_usuario,
                resposta_ia=resposta_ia,
                cta_sugerido=cta_sugerido,
                acao_sugerida=acao_sugerida,
            )
            db.add(row)
            await db.flush()
            return row.id
        except Exception as exc:
            logger.warning(f"[IA-Growth-17] Falha ao registrar interação do assistente: {exc}")
            return None

    @classmethod
    async def gerar_recomendacao_conversacional(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        usuario_id: Optional[uuid.UUID],
        mensagem_usuario: str,
        contexto_atual: Optional[Dict[str, Any]] = None,
        visao_completa: bool = False,
    ) -> Dict[str, Any]:
        contexto = contexto_atual or await cls.gerar_contexto_usuario(db, tenant_id, usuario_id, visao_completa=visao_completa)

        if not await tenant_tem_ia(tenant_id, db) or not _ia_globalmente_habilitada():
            heur = cls._resposta_heuristica(contexto, mensagem_usuario)
            log_id = await cls.registrar_interacao_assistente(
                db=db,
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                plano_atual=contexto["plano_atual"],
                plano_recomendado=heur["plano_recomendado"],
                persona=contexto.get("persona"),
                churn_risk_level=contexto["churn_risk_level"],
                mensagem_usuario=mensagem_usuario,
                resposta_ia=heur["resposta_ia"],
                cta_sugerido=heur["cta_sugerido"],
                acao_sugerida=heur["acao_sugerida"],
            )
            return {**heur, "log_id": log_id, "contexto": contexto}

        tier_value = await cls._tier_atual(db, tenant_id)
        pode_usar, fonte_consumo = await _usage_svc.verificar_limite_ia(tenant_id, tier_value, db)
        if not pode_usar:
            heur = cls._resposta_heuristica(contexto, mensagem_usuario)
            await _usage_svc.registrar_uso_ia(db, tenant_id, "growth_assistente_comercial", "FALLBACK", usuario_id=usuario_id)
            log_id = await cls.registrar_interacao_assistente(
                db=db,
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                plano_atual=contexto["plano_atual"],
                plano_recomendado=heur["plano_recomendado"],
                persona=contexto.get("persona"),
                churn_risk_level=contexto["churn_risk_level"],
                mensagem_usuario=mensagem_usuario,
                resposta_ia=heur["resposta_ia"],
                cta_sugerido=heur["cta_sugerido"],
                acao_sugerida=heur["acao_sugerida"],
            )
            return {**heur, "log_id": log_id, "contexto": contexto}

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            heur = cls._resposta_heuristica(contexto, mensagem_usuario)
            await _usage_svc.registrar_uso_ia(db, tenant_id, "growth_assistente_comercial", "FALLBACK", usuario_id=usuario_id)
            log_id = await cls.registrar_interacao_assistente(
                db=db,
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                plano_atual=contexto["plano_atual"],
                plano_recomendado=heur["plano_recomendado"],
                persona=contexto.get("persona"),
                churn_risk_level=contexto["churn_risk_level"],
                mensagem_usuario=mensagem_usuario,
                resposta_ia=heur["resposta_ia"],
                cta_sugerido=heur["cta_sugerido"],
                acao_sugerida=heur["acao_sugerida"],
            )
            return {**heur, "log_id": log_id, "contexto": contexto}

        prompt = cls._montar_prompt(contexto, mensagem_usuario)
        model = os.getenv("IA_MODEL", "claude-haiku-4-5-20251001")

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()

            content = resp.json()["content"][0]["text"].strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            parsed = json.loads(content[start:end])
            mapped = cls._mapear_acao(
                parsed.get("cta_sugerido", "Ver planos"),
                parsed.get("plano_recomendado", contexto["plano_sugerido"]),
                contexto["churn_risk_level"],
            )
            tipo_oferta_llm = str(parsed.get("tipo_oferta", contexto.get("tipo_oferta", "CONSULTIVO"))).upper()
            if tipo_oferta_llm not in {"SEM_INCENTIVO", "INCENTIVO_LEVE", "INCENTIVO_FORTE", "EDUCATIVO", "CONSULTIVO"}:
                tipo_oferta_llm = contexto.get("tipo_oferta", "CONSULTIVO")
            resposta = {
                "resposta_ia": parsed.get("resposta_ia", "Posso te ajudar a entender o próximo passo ideal.")[:500],
                "cta_sugerido": parsed.get("cta_sugerido", mapped["cta_url"] or "Ver planos")[:80],
                "cta_url": parsed.get("cta_url") or mapped["cta_url"],
                "plano_recomendado": parsed.get("plano_recomendado", contexto["plano_sugerido"]),
                "acao_sugerida": parsed.get("acao_sugerida", mapped["acao_sugerida"]),
                "fonte": "LLM",
                "tipo_oferta": tipo_oferta_llm,
                "mensagem_oferta": parsed.get("mensagem_oferta", contexto.get("mensagem_oferta", "")),
                "beneficio_destacado": parsed.get("beneficio_destacado", contexto.get("beneficio_destacado", "")),
            }
            if fonte_consumo == "PACOTE":
                await _usage_svc.consumir_credito_pacote(tenant_id, db)
            await _usage_svc.registrar_uso_ia(
                db,
                tenant_id,
                "growth_assistente_comercial",
                "SUCESSO",
                modelo=model,
                usuario_id=usuario_id,
                fonte_consumo=fonte_consumo,
            )
        except Exception as exc:
            logger.error(f"[IA-Growth-17] Falha no assistente comercial via LLM: {exc}")
            resposta = cls._resposta_heuristica(contexto, mensagem_usuario)
            await _usage_svc.registrar_uso_ia(db, tenant_id, "growth_assistente_comercial", "ERRO", modelo=model, usuario_id=usuario_id)

        log_id = await cls.registrar_interacao_assistente(
            db=db,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            plano_atual=contexto["plano_atual"],
            plano_recomendado=resposta["plano_recomendado"],
            persona=contexto.get("persona"),
            churn_risk_level=contexto["churn_risk_level"],
            mensagem_usuario=mensagem_usuario,
            resposta_ia=resposta["resposta_ia"],
            cta_sugerido=resposta["cta_sugerido"],
            acao_sugerida=resposta["acao_sugerida"],
        )
        incentivo = contexto.get("incentivo")
        if incentivo and incentivo.get("status") in {"OFERECIDO", "APROVADO"}:
            prazo = incentivo.get("validade_fim")
            prazo_txt = f" até {prazo[:10]}" if isinstance(prazo, str) and len(prazo) >= 10 else " por tempo limitado"
            resposta["resposta_ia"] = f"{resposta['resposta_ia']} Também há um benefício temporário disponível{prazo_txt}."
            resposta["cta_sugerido"] = "Ver benefício temporário"
            resposta["cta_url"] = "/dashboard/ia/performance"
            resposta["acao_sugerida"] = "VER_PLANOS"
        return {**resposta, "log_id": log_id, "contexto": contexto, "incentivo": incentivo}
