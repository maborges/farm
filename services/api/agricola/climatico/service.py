import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import cast, func, or_, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from agricola.climatico.models import ModeloFitossanitario, PrevisaoClima, RegistroClima
from agricola.climatico.schemas import (
    ClimaAlertaResponse,
    ClimaResumoResponse,
    ModeloFitossanitarioCreate,
    ModeloFitossanitarioUpdate,
    validar_regras_fitossanitarias,
)
from alert_engine.models import AlertStatus, OperationalAlert
from core.base_service import BaseService


@dataclass(frozen=True)
class ResultadoRiscoFitossanitario:
    status: str
    resultados: list[dict]


class ClimaService(BaseService[RegistroClima]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(RegistroClima, session, tenant_id)

    async def _ensure_tenant_context(self) -> None:
        """Reaplica o tenant antes das leituras protegidas por RLS."""
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )

    async def get_resumo_climatico(self, unidade_produtiva_id: UUID) -> ClimaResumoResponse:
        await self._ensure_tenant_context()
        # Busca o último registro de clima
        stmt_registro = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).order_by(RegistroClima.data_registro.desc()).limit(1)

        result_registro = await self.session.execute(stmt_registro)
        ultimo_registro = result_registro.scalars().first()

        # Busca alertas ativos relacionados ao clima para esta unidade
        alertas = await self._fetch_alertas_clima(unidade_produtiva_id)

        status_operacional = "SEM_DADOS"
        if ultimo_registro:
            status_operacional = "NORMAL"
            if any(a.severity.name == 'CRITICAL' for a in alertas):
                status_operacional = "CRITICO"
            elif any(a.severity.name == 'WARNING' for a in alertas):
                status_operacional = "ATENCAO"

        return ClimaResumoResponse(
            unidade_produtiva_id=unidade_produtiva_id,
            data_registro=ultimo_registro.data_registro if ultimo_registro else None,
            temperatura_atual=ultimo_registro.temp_media_c if ultimo_registro else None,
            temperatura_min=ultimo_registro.temp_min_c if ultimo_registro else None,
            temperatura_max=ultimo_registro.temp_max_c if ultimo_registro else None,
            umidade=ultimo_registro.umidade_rel_pct if ultimo_registro else None,
            precipitacao_mm=ultimo_registro.precipitacao_mm if ultimo_registro else None,
            vento_kmh=ultimo_registro.vento_kmh if ultimo_registro else None,
            condicao=None,
            fonte=ultimo_registro.fonte if ultimo_registro else None,
            status_operacional=status_operacional,
            alertas_ativos=len(alertas)
        )

    async def _fetch_alertas_clima(self, unidade_produtiva_id: UUID) -> list:
        """Busca alertas climáticos ativos para a unidade, usando cast explícito para evitar
        conflitos de tipo UUID vs VARCHAR no asyncpg."""
        source_types_clima = ['CLIMA_CHUVA_RECENTE', 'CLIMA_VENTO_ALTO', 'CLIMA_TEMPERATURA_EXTREMA']
        stmt = select(OperationalAlert).where(
            cast(OperationalAlert.tenant_id, PG_UUID) == cast(str(self.tenant_id), PG_UUID),
            OperationalAlert.source_id == str(unidade_produtiva_id),
            OperationalAlert.source_type.in_(source_types_clima),
            OperationalAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED])
        ).order_by(OperationalAlert.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_alertas_ativos(self, unidade_produtiva_id: UUID) -> list[ClimaAlertaResponse]:
        await self._ensure_tenant_context()
        alertas = await self._fetch_alertas_clima(unidade_produtiva_id)
        return [
            ClimaAlertaResponse(
                id=a.id,
                severity=a.severity.name,
                priority=a.priority.name,
                title=a.title,
                description=a.message,
                source_type=a.source_type,
                created_at=a.created_at
            ) for a in alertas
        ]

    async def get_previsoes_unidade(self, unidade_produtiva_id: UUID, dias: int = 5) -> list[PrevisaoClima]:
        """Retorna previsões de clima para os próximos `dias` dias para a unidade produtiva."""
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje + timedelta(days=dias)
        stmt = select(PrevisaoClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
        ).where(
            PrevisaoClima.data_previsao >= hoje,
            PrevisaoClima.data_previsao <= limite,
        ).order_by(PrevisaoClima.data_previsao.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_clima_periodo(self, unidade_produtiva_id: UUID, data_inicio: date, data_fim: date):
        await self._ensure_tenant_context()
        stmt = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(
            RegistroClima.data_registro >= data_inicio,
            RegistroClima.data_registro <= data_fim
        ).order_by(RegistroClima.data_registro.asc())

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_chuva_acumulada(self, unidade_produtiva_id: UUID, dias: int = 30) -> float:
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje - timedelta(days=dias)

        stmt = select(func.sum(RegistroClima.precipitacao_mm)).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(RegistroClima.data_registro >= limite)

        resultado = await self.session.execute(stmt)
        val = resultado.scalar()
        return float(val) if val else 0.0

    async def get_analise_avancada(self, unidade_produtiva_id: UUID, dias_historico: int = 30) -> dict:
        """Analisa dados climáticos históricos e retorna inteligência agronômica.

        Args:
            unidade_produtiva_id: ID da unidade produtiva.
            dias_historico: Número de dias retroativos a considerar.

        Returns:
            dict com gdu_acumulado, riscos climáticos, historico e risco_doencas por cultura ativa.
        """
        await self._ensure_tenant_context()
        hoje = date.today()
        limite = hoje - timedelta(days=dias_historico)

        stmt = select(RegistroClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(RegistroClima.data_registro >= limite).order_by(RegistroClima.data_registro.asc())

        result = await self.session.execute(stmt)
        registros = result.scalars().all()

        historico = []
        gdu_acumulado = 0.0
        chuva_acumulada = 0.0
        temp_base = 10.0

        for r in registros:
            if r.temp_max_c is not None and r.temp_min_c is not None:
                gdu_dia = max(0.0, float((r.temp_max_c + r.temp_min_c) / 2) - temp_base)
                gdu_acumulado += gdu_dia

            if r.precipitacao_mm is not None:
                chuva_acumulada += float(r.precipitacao_mm)

            historico.append({
                "data": r.data_registro,
                "temp_min": float(r.temp_min_c) if r.temp_min_c is not None else None,
                "temp_max": float(r.temp_max_c) if r.temp_max_c is not None else None,
                "temp_media": float(r.temp_media_c) if r.temp_media_c is not None else None,
                "precipitacao": float(r.precipitacao_mm) if r.precipitacao_mm is not None else None
            })

        stmt_prev = select(PrevisaoClima).filter_by(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_produtiva_id
        ).where(PrevisaoClima.data_previsao >= hoje).order_by(PrevisaoClima.data_previsao.asc()).limit(5)

        result_prev = await self.session.execute(stmt_prev)
        previsoes = result_prev.scalars().all()

        riscos = []
        if not registros and not previsoes:
            riscos.append({
                "tipo": "Sem dados",
                "nivel": "INDETERMINADO",
                "mensagem": "Não há observações ou previsões suficientes para calcular riscos climáticos.",
                "data_alerta": None,
            })
        else:
            min_temp_prevista = min([float(p.temp_min_c) for p in previsoes if p.temp_min_c is not None], default=99.0)
            if min_temp_prevista <= 4.0:
                riscos.append({
                    "tipo": "Geada",
                    "nivel": "CRITICO" if min_temp_prevista <= 0 else "ALTO",
                    "mensagem": f"Alerta de geada nos próximos dias. Temperatura mínima prevista: {min_temp_prevista}°C",
                    "data_alerta": None
                })

            chuva_prevista = sum([float(p.precipitacao_mm) for p in previsoes if p.precipitacao_mm is not None])
            if registros and chuva_acumulada < 30.0 and chuva_prevista < 10.0:
                riscos.append({
                    "tipo": "Estresse Hídrico",
                    "nivel": "ALTO",
                    "mensagem": f"Baixo volume de chuva nos últimos {dias_historico} dias e pouca previsão de precipitação.",
                    "data_alerta": None
                })

        if not riscos:
            riscos.append({
                "tipo": "Normal",
                "nivel": "BAIXO",
                "mensagem": "Condições climáticas dentro da normalidade.",
                "data_alerta": hoje
            })

        # ---- Motor de Inteligência Fitossanitária ----
        resultado_fitossanitario = await self._calcular_risco_doencas(
            unidade_produtiva_id=unidade_produtiva_id,
            registros=registros,
        )

        return {
            "gdu_acumulado": round(gdu_acumulado, 2),
            "gdu_progresso_pct": None,
            "riscos": riscos,
            "historico": historico,
            "risco_fitossanitario_status": resultado_fitossanitario.status,
            "agricultura": {
                "janela_pulverizacao": [],
                "balanco_hidrico": self._calcular_balanco_hidrico(registros),
                "risco_doencas": resultado_fitossanitario.resultados,
            } if registros else None,
        }

    @staticmethod
    def _calcular_balanco_hidrico(registros: list[RegistroClima]) -> list[dict]:
        """Calcula o saldo diário com dados observados, sem inventar leituras ausentes."""
        resultado = []
        for registro in registros[-7:]:
            chuva = float(registro.precipitacao_mm or 0)
            et_mm = float(registro.evapotranspiracao_mm) if registro.evapotranspiracao_mm is not None else None
            if et_mm is None:
                continue
            resultado.append({
                "data": registro.data_registro,
                "etc_mm": et_mm,
                "chuva_efetiva_mm": chuva,
                "saldo_mm": round(chuva - et_mm, 2) if et_mm is not None else None,
                "status": "deficit" if chuva < et_mm else "conforto",
            })
        return resultado

    async def _calcular_risco_doencas(
        self,
        unidade_produtiva_id: UUID,
        registros: list[RegistroClima],
    ) -> ResultadoRiscoFitossanitario:
        """Cruza dados climáticos com culturas ativas e modelos de risco fitossanitário.

        Args:
            unidade_produtiva_id: ID da unidade produtiva.
            registros: Registros climáticos dos últimos N dias.

        Returns:
            Estado do cálculo e resultados de favorabilidade climática.
        """
        from agricola.cultivos.models import Cultivo, CultivoArea
        from agricola.safras.models import Safra
        from core.cadastros.propriedades.models import AreaRural

        # Buscar culturas ativas (safras em plantio ou desenvolvimento)
        fases_ativas = ["PLANTIO", "DESENVOLVIMENTO", "PREPARO_SOLO"]
        stmt_safras = (
            select(Cultivo.cultura)
            .join(Safra, Safra.id == Cultivo.safra_id)
            .join(CultivoArea, CultivoArea.cultivo_id == Cultivo.id)
            .join(AreaRural, AreaRural.id == CultivoArea.area_id)
            .where(
                Safra.tenant_id == self.tenant_id,
                Cultivo.tenant_id == self.tenant_id,
                CultivoArea.tenant_id == self.tenant_id,
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                Safra.status.in_(fases_ativas),
            )
            .distinct()
        )
        result_culturas = await self.session.execute(stmt_safras)
        culturas_ativas = [row[0] for row in result_culturas.fetchall()]

        if not culturas_ativas:
            return ResultadoRiscoFitossanitario("SEM_CULTURA_ATIVA", [])

        modelos_personalizados = []
        if self.tenant_id is not None:
            stmt_personalizados = select(ModeloFitossanitario).where(
                ModeloFitossanitario.tenant_id == self.tenant_id,
                ModeloFitossanitario.cultura.in_(culturas_ativas),
            )
            res_pers = await self.session.execute(stmt_personalizados)
            modelos_personalizados = list(res_pers.scalars().all())

        stmt_globais = select(ModeloFitossanitario).where(
            ModeloFitossanitario.tenant_id.is_(None),
            ModeloFitossanitario.cultura.in_(culturas_ativas),
        )
        res_glob = await self.session.execute(stmt_globais)
        modelos_globais = res_glob.scalars().all()

        # Resolve somente a chave exata; uma regra local para outra doença não
        # remove os modelos globais restantes da cultura.
        modelos_por_chave = {
            (modelo.cultura, modelo.doenca): modelo for modelo in modelos_globais
        }
        for modelo in modelos_personalizados:
            modelos_por_chave[(modelo.cultura, modelo.doenca)] = modelo
        modelos_finais = list(modelos_por_chave.values())

        if not modelos_finais:
            return ResultadoRiscoFitossanitario("SEM_MODELO_APLICAVEL", [])

        # Requer a janela de sete datas distintas usada pelo agregador. Isso é
        # suficiência técnica da janela atual, não validação epidemiológica.
        datas_disponiveis = sorted({registro.data_registro for registro in registros})
        if len(datas_disponiveis) < 7:
            return ResultadoRiscoFitossanitario(
                "DADOS_CLIMATICOS_INSUFICIENTES", []
            )
        datas_janela = set(datas_disponiveis[-7:])
        registros_janela = [
            registro for registro in registros if registro.data_registro in datas_janela
        ]
        stats, variaveis_invalidas = self._calcular_stats_climaticas(registros_janela)

        resultado = []
        estados = []
        for modelo in modelos_finais:
            try:
                regras = validar_regras_fitossanitarias(modelo.regras_risco)
            except (TypeError, ValueError):
                estados.append("CONFIGURACAO_INVALIDA")
                continue

            variaveis_regra = {condicao["variavel"] for condicao in regras["condicoes"]}
            if variaveis_regra.intersection(variaveis_invalidas):
                estados.append("DADOS_CLIMATICOS_INVALIDOS")
                continue

            favorabilidade = self._avaliar_modelo(regras, stats)
            if favorabilidade is None:
                estados.append("DADOS_CLIMATICOS_INSUFICIENTES")
                continue

            nivel_legado = self._classificar_nivel(favorabilidade, regras)
            nivel_favorabilidade = {
                "baixo": "baixa",
                "medio": "moderada",
                "alto": "alta",
                "critico": "muito_alta",
            }[nivel_legado]
            resultado.append({
                "doenca": modelo.doenca,
                "cultura": modelo.cultura,
                "nivel_favorabilidade": nivel_favorabilidade,
                "favorabilidade_pct": favorabilidade,
                # Campos mantidos como aliases deprecated para clientes antigos.
                "nivel": nivel_legado,
                "probabilidade_pct": favorabilidade,
                "auto_copied": False,
            })
            estados.append("CALCULADO")

        if all(estado == "CALCULADO" for estado in estados):
            status_resultado = "CALCULADO"
        elif len(set(estados)) == 1:
            status_resultado = estados[0]
        else:
            status_resultado = "PARCIAL"

        return ResultadoRiscoFitossanitario(
            status_resultado,
            sorted(resultado, key=lambda item: item["favorabilidade_pct"], reverse=True),
        )

    @staticmethod
    def _calcular_stats_climaticas(
        registros: list[RegistroClima],
    ) -> tuple[dict[str, float | None], set[str]]:
        """Calcula médias e acumulados das variáveis climáticas.

        Args:
            registros: Lista de RegistroClima a analisar.

        Returns:
            (médias, variáveis inválidas). Ausências permanecem como None.
        """
        if not registros:
            return {}, set()

        campos = ["temp_media_c", "temp_max_c", "temp_min_c", "umidade_rel_pct", "precipitacao_mm"]
        stats: dict[str, float | None] = {}
        invalidas: set[str] = set()
        for campo in campos:
            valores = []
            for registro in registros:
                bruto = getattr(registro, campo)
                if bruto is None:
                    continue
                if isinstance(bruto, bool) or not isinstance(bruto, int | float | Decimal):
                    invalidas.add(campo)
                    continue
                try:
                    valor = float(bruto)
                except (OverflowError, ValueError):
                    invalidas.add(campo)
                    continue
                if not math.isfinite(valor):
                    invalidas.add(campo)
                    continue
                if campo == "umidade_rel_pct" and not 0 <= valor <= 100:
                    invalidas.add(campo)
                    continue
                if campo == "precipitacao_mm" and valor < 0:
                    invalidas.add(campo)
                    continue
                # Faixa ampla de plausibilidade física para temperatura do ar;
                # não é limiar fitossanitário.
                if campo.startswith("temp_") and not -90 <= valor <= 60:
                    invalidas.add(campo)
                    continue
                valores.append(valor)
            media = sum(valores) / len(valores) if valores else None
            if media is not None and not math.isfinite(media):
                invalidas.add(campo)
                media = None
            stats[campo] = media
        return stats, invalidas

    @staticmethod
    def _avaliar_modelo(regras: dict, stats: dict[str, float | None]) -> int | None:
        """Calcula score heurístico de favorabilidade, nunca probabilidade.

        Args:
            regras: dict de regras lido do campo JSONB do ModeloFitossanitario.
            stats: Estatísticas climáticas calculadas.

        Returns:
            Favorabilidade heurística de 0 a 100 ou None se faltar uma variável.
        """
        regras = validar_regras_fitossanitarias(regras)
        condicoes = regras["condicoes"]

        score_total = 0.0
        peso_total = 0.0

        for cond in condicoes:
            variavel = cond.get("variavel")
            operador = cond.get("operador")
            peso = float(cond.get("peso", 1.0))
            if variavel not in stats or stats[variavel] is None:
                return None
            if peso <= 0:
                continue
            valor_real = stats[variavel]

            satisfeita = False
            if operador == ">=":
                satisfeita = valor_real >= float(cond["valor"])
            elif operador == "<=":
                satisfeita = valor_real <= float(cond["valor"])
            elif operador == ">":
                satisfeita = valor_real > float(cond["valor"])
            elif operador == "<":
                satisfeita = valor_real < float(cond["valor"])
            elif operador == "between":
                satisfeita = float(cond["min"]) <= valor_real <= float(cond["max"])

            score_total += peso if satisfeita else 0.0
            peso_total += peso

        if peso_total == 0:
            return 0

        return max(0, min(100, round((score_total / peso_total) * 100)))

    @staticmethod
    def _classificar_nivel(favorabilidade_pct: int, regras: dict) -> str:
        """Classifica a faixa do score de favorabilidade configurada no modelo.

        Args:
            favorabilidade_pct: Score heurístico de 0 a 100.
            regras: JSON validado com os limiares de faixa existentes.

        Returns:
            Faixa legada: 'critico', 'alto', 'medio' ou 'baixo'.
        """
        if favorabilidade_pct >= regras.get("nivel_critico_pct", 80):
            return "critico"
        if favorabilidade_pct >= regras.get("nivel_alto_pct", 60):
            return "alto"
        if favorabilidade_pct >= regras.get("nivel_medio_pct", 35):
            return "medio"
        return "baixo"


class ModeloFitossanitarioService:
    def __init__(self, session: AsyncSession, tenant_id: UUID | None = None):
        self.session = session
        self.tenant_id = tenant_id

    async def _set_tenant_context(self) -> None:
        """Aplica o contexto RLS da operação atual."""
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id) if self.tenant_id else ""},
        )

    async def get_all(self, include_globals: bool = True) -> list[ModeloFitossanitario]:
        await self._set_tenant_context()
        # Se include_globals for False, retorna apenas os daquele tenant.
        # Se include_globals for True, retorna do tenant atual + globais que não tenham sido customizados
        stmt = select(ModeloFitossanitario)
        
        if self.tenant_id:
            if include_globals:
                stmt = stmt.where(
                    or_(
                        ModeloFitossanitario.tenant_id == self.tenant_id,
                        ModeloFitossanitario.tenant_id.is_(None)
                    )
                )
            else:
                stmt = stmt.where(ModeloFitossanitario.tenant_id == self.tenant_id)
        else:
            # Backoffice: only globals
            stmt = stmt.where(ModeloFitossanitario.tenant_id.is_(None))

        stmt = stmt.order_by(ModeloFitossanitario.cultura, ModeloFitossanitario.doenca, ModeloFitossanitario.tenant_id.nulls_last())
        result = await self.session.execute(stmt)
        modelos = list(result.scalars().all())

        # Resolver sobreposição (se o tenant tem uma regra para Soja - Ferrugem, ignorar a global)
        if self.tenant_id and include_globals:
            resolved = {}
            for m in modelos:
                key = (m.cultura, m.doenca)
                # Como a query retorna os do tenant primeiro (por causa do order_by nulls_last, ops na vdd precisamos tratar)
                # Vamos priorizar tenant > global
                if key not in resolved or (m.tenant_id is not None):
                    resolved[key] = m
            # Marcar is_global para retornar na API
            for m in resolved.values():
                m.is_global = (m.tenant_id is None)
            return list(resolved.values())
        else:
            for m in modelos:
                m.is_global = (m.tenant_id is None)
            return modelos

    async def get_by_id(self, modelo_id: UUID) -> ModeloFitossanitario:
        await self._set_tenant_context()
        stmt = select(ModeloFitossanitario).where(ModeloFitossanitario.id == modelo_id)
        if self.tenant_id:
            stmt = stmt.where(
                or_(
                    ModeloFitossanitario.tenant_id == self.tenant_id,
                    ModeloFitossanitario.tenant_id.is_(None)
                )
            )
        else:
            stmt = stmt.where(ModeloFitossanitario.tenant_id.is_(None))

        result = await self.session.execute(stmt)
        modelo = result.scalar_one_or_none()
        if not modelo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo fitossanitário não encontrado ou sem permissão")
        modelo.is_global = (modelo.tenant_id is None)
        return modelo

    async def create(self, data: ModeloFitossanitarioCreate) -> ModeloFitossanitario:
        await self._set_tenant_context()
        # Verifica conflitos
        stmt = select(ModeloFitossanitario).where(
            ModeloFitossanitario.cultura == data.cultura,
            ModeloFitossanitario.doenca == data.doenca,
            ModeloFitossanitario.tenant_id == self.tenant_id
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modelo para esta cultura e doença já existe neste contexto")

        modelo = ModeloFitossanitario(
            **data.model_dump(),
            tenant_id=self.tenant_id,
            is_global=self.tenant_id is None,
        )
        self.session.add(modelo)
        await self.session.commit()
        await self.session.refresh(modelo)
        modelo.is_global = (modelo.tenant_id is None)
        return modelo

    async def update(self, modelo_id: UUID, data: ModeloFitossanitarioUpdate) -> ModeloFitossanitario:
        await self._set_tenant_context()
        modelo = await self.get_by_id(modelo_id)
        
        # Não permite editar modelo global através do endpoint de tenant
        if self.tenant_id and modelo.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modelos globais não podem ser editados. Crie uma cópia.")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(modelo, key, value)
            
        await self.session.commit()
        await self.session.refresh(modelo)
        modelo.is_global = (modelo.tenant_id is None)
        return modelo

    async def delete(self, modelo_id: UUID) -> None:
        await self._set_tenant_context()
        modelo = await self.get_by_id(modelo_id)
        
        # Não permite deletar modelo global através do endpoint de tenant
        if self.tenant_id and modelo.tenant_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modelos globais não podem ser excluídos. Eles pertencem à plataforma.")

        await self.session.delete(modelo)
        await self.session.commit()

    async def copiar_modelo_global(self, global_id: UUID) -> ModeloFitossanitario:
        await self._set_tenant_context()
        if not self.tenant_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operação requer um tenant ativo.")
            
        stmt = select(ModeloFitossanitario).where(
            ModeloFitossanitario.id == global_id,
            ModeloFitossanitario.tenant_id.is_(None)
        )
        result = await self.session.execute(stmt)
        global_modelo = result.scalar_one_or_none()
        
        if not global_modelo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo global não encontrado.")

        try:
            validar_regras_fitossanitarias(global_modelo.regras_risco)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O modelo global possui regras inválidas e não pode ser copiado.",
            ) from exc
            
        # Verifica se o tenant já possui um para a mesma cultura/doenca
        existing_stmt = select(ModeloFitossanitario).where(
            ModeloFitossanitario.cultura == global_modelo.cultura,
            ModeloFitossanitario.doenca == global_modelo.doenca,
            ModeloFitossanitario.tenant_id == self.tenant_id
        )
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            # Já existe, vamos apenas atualizar as regras
            existing.regras_risco = global_modelo.regras_risco
            modelo = existing
        else:
            # Cria novo
            modelo = ModeloFitossanitario(
                tenant_id=self.tenant_id,
                cultura=global_modelo.cultura,
                doenca=global_modelo.doenca,
                regras_risco=global_modelo.regras_risco
            )
            self.session.add(modelo)
            
        await self.session.commit()
        await self.session.refresh(modelo)
        modelo.is_global = False
        return modelo
