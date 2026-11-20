import copy
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.climatico.models import PrevisaoClima, RegistroClima
from pecuaria.climatico.models import ModeloZoosanitario
from pecuaria.climatico.schemas import (
    InteligenciaPecuariaResponse,
    ModeloZoosanitarioCreate,
    ModeloZoosanitarioUpdate,
    validar_regras_zoosanitarias,
)


def _deduplicar_modelos_por_chave(
    modelos: list[ModeloZoosanitario],
) -> list[ModeloZoosanitario]:
    """Prioriza modelos do tenant sobre modelos globais para cada (especie, tipo_risco)."""
    resolvidos: dict[tuple[str, str], ModeloZoosanitario] = {}
    for modelo in modelos:
        chave = (modelo.especie, modelo.tipo_risco)
        if chave not in resolvidos or modelo.tenant_id is not None:
            resolvidos[chave] = modelo
    for modelo in resolvidos.values():
        modelo.is_global = modelo.tenant_id is None
    return list(resolvidos.values())


class ModeloZoosanitarioService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _set_tenant_context(self, tenant_id: UUID | None) -> None:
        """Aplica o contexto RLS para operações de modelos climáticos."""
        value = str(tenant_id) if tenant_id else ""
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": value},
        )

    @staticmethod
    def _filtro_tenant(tenant_id: UUID | None):
        """Constrói predicado SQLAlchemy seguro para tenant_id opcional."""
        if tenant_id is None:
            return ModeloZoosanitario.tenant_id.is_(None)
        return ModeloZoosanitario.tenant_id == tenant_id

    async def get_tenant_model(
        self, tenant_id: UUID, especie: str, tipo_risco: str
    ) -> ModeloZoosanitario | None:
        """Busca exclusivamente o modelo ativo do tenant, sem copiar globais.

        Args:
            tenant_id: Identificador do tenant autenticado.
            especie: Espécie animal configurada.
            tipo_risco: Tipo de risco zoossanitário (ex: Estresse Térmico).

        Returns:
            Instância de ModeloZoosanitario do tenant ou None se não habilitado.
        """
        await self._set_tenant_context(tenant_id)
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id == tenant_id,
            ModeloZoosanitario.especie == especie,
            ModeloZoosanitario.tipo_risco == tipo_risco,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_models(self, tenant_id: UUID | None) -> list[ModeloZoosanitario]:
        """Lista modelos do tenant deduplicados contra o catálogo global de referência.

        Args:
            tenant_id: Identificador do tenant ou None para catálogo global do backoffice.

        Returns:
            Lista de modelos com flag is_global coerente e prioridade para personalizações do tenant.
        """
        await self._set_tenant_context(tenant_id)
        if tenant_id:
            stmt = select(ModeloZoosanitario).where(
                or_(
                    ModeloZoosanitario.tenant_id == tenant_id,
                    ModeloZoosanitario.tenant_id.is_(None),
                )
            ).order_by(
                ModeloZoosanitario.especie,
                ModeloZoosanitario.tipo_risco,
                ModeloZoosanitario.tenant_id.nulls_last(),
            )
            modelos = list((await self.session.execute(stmt)).scalars().all())
            return _deduplicar_modelos_por_chave(modelos)

        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id.is_(None)
        ).order_by(ModeloZoosanitario.especie, ModeloZoosanitario.tipo_risco)
        modelos = list((await self.session.execute(stmt)).scalars().all())
        for modelo in modelos:
            modelo.is_global = True
        return modelos

    async def create_model(
        self,
        tenant_id: UUID | None,
        payload: ModeloZoosanitarioCreate,
        is_global: bool = False,
        commit: bool = True,
    ) -> ModeloZoosanitario:
        """Cria um novo modelo zoossanitário para tenant ou catálogo global."""
        await self._set_tenant_context(tenant_id)
        stmt = select(ModeloZoosanitario).where(
            self._filtro_tenant(tenant_id),
            ModeloZoosanitario.especie == payload.especie,
            ModeloZoosanitario.tipo_risco == payload.tipo_risco,
        )
        if (await self.session.execute(stmt)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Modelo já existe para esta espécie e risco",
            )

        modelo = ModeloZoosanitario(
            tenant_id=tenant_id,
            especie=payload.especie,
            tipo_risco=payload.tipo_risco,
            regras_risco=copy.deepcopy(payload.regras_risco),
            is_global=is_global if tenant_id is None else False,
        )
        self.session.add(modelo)
        if commit:
            await self.session.commit()
            await self.session.refresh(modelo)
        else:
            await self.session.flush()
        return modelo

    async def update_model(
        self, tenant_id: UUID | None, model_id: UUID, payload: ModeloZoosanitarioUpdate
    ) -> ModeloZoosanitario:
        """Atualiza as regras de risco de um modelo existente no contexto informado."""
        await self._set_tenant_context(tenant_id)
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.id == model_id,
            self._filtro_tenant(tenant_id),
        )
        modelo = (await self.session.execute(stmt)).scalars().first()
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")

        modelo.regras_risco = copy.deepcopy(payload.regras_risco)
        await self.session.commit()
        await self.session.refresh(modelo)
        return modelo

    async def delete_model(self, tenant_id: UUID | None, model_id: UUID) -> None:
        """Remove um modelo zoossanitário pertencente ao contexto informado."""
        await self._set_tenant_context(tenant_id)
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.id == model_id,
            self._filtro_tenant(tenant_id),
        )
        modelo = (await self.session.execute(stmt)).scalars().first()
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")

        await self.session.delete(modelo)
        await self.session.commit()

    async def _buscar_modelo_global(self, global_id: UUID) -> ModeloZoosanitario:
        """Busca modelo global válido para cópia, levantando 404 se ausente."""
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.id == global_id,
            ModeloZoosanitario.tenant_id.is_(None),
        )
        modelo_global = (await self.session.execute(stmt)).scalars().first()
        if not modelo_global:
            raise HTTPException(status_code=404, detail="Modelo global não encontrado")
        return modelo_global

    async def _upsert_copia_tenant(
        self, tenant_id: UUID, modelo_global: ModeloZoosanitario
    ) -> ModeloZoosanitario:
        """Cria ou atualiza o modelo do tenant a partir do modelo global validado."""
        regras_copia = copy.deepcopy(modelo_global.regras_risco)
        stmt = select(ModeloZoosanitario).where(
            ModeloZoosanitario.tenant_id == tenant_id,
            ModeloZoosanitario.especie == modelo_global.especie,
            ModeloZoosanitario.tipo_risco == modelo_global.tipo_risco,
        )
        existente = (await self.session.execute(stmt)).scalars().first()
        if existente:
            existente.regras_risco = regras_copia
            existente.is_global = False
            return existente

        modelo = ModeloZoosanitario(
            tenant_id=tenant_id,
            especie=modelo_global.especie,
            tipo_risco=modelo_global.tipo_risco,
            regras_risco=regras_copia,
            is_global=False,
        )
        self.session.add(modelo)
        return modelo

    async def copy_global_to_tenant(self, tenant_id: UUID, global_id: UUID) -> ModeloZoosanitario:
        """Valida e persiste uma cópia do modelo global para uso explícito pelo tenant.

        Args:
            tenant_id: Identificador do tenant que adota o modelo.
            global_id: Identificador do modelo global de referência.

        Returns:
            ModeloZoosanitario persistido com tenant_id do solicitante e is_global=False.

        Raises:
            HTTPException: 404 se o modelo global não existir ou 422 se suas regras forem inválidas.
        """
        await self._set_tenant_context(tenant_id)
        modelo_global = await self._buscar_modelo_global(global_id)
        try:
            validar_regras_zoosanitarias(modelo_global.regras_risco)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="O modelo global possui regras inválidas e não pode ser copiado.",
            ) from exc

        modelo = await self._upsert_copia_tenant(tenant_id, modelo_global)
        await self.session.commit()
        await self.session.refresh(modelo)
        modelo.is_global = False
        return modelo


class InteligenciaPecuariaService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.model_svc = ModeloZoosanitarioService(session)

    async def _set_tenant_context(self, tenant_id: UUID) -> None:
        """Aplica o contexto RLS antes de consultar dados climáticos da unidade."""
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

    async def analisar_estresse_termico(self, tenant_id: UUID, unidade_produtiva_id: UUID, especie: str) -> InteligenciaPecuariaResponse | None:
        """Calcula o risco de estresse térmico baseado nos registros de clima recentes."""
        # 1. Buscar exclusivamente o modelo zoossanitário habilitado pelo tenant
        modelo = await self.model_svc.get_tenant_model(tenant_id, especie, "Estresse Térmico")
        if not modelo:
            return None  # Não há regra cadastrada

        # 2. Buscar último clima da fazenda (ex: de hoje)
        hoje = date.today()
        # Força o RLS de novo para ter certeza que não foi perdido!
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        
        stmt_clima = select(RegistroClima).where(
            RegistroClima.tenant_id == tenant_id,
            RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
            RegistroClima.data_registro >= hoje - timedelta(days=7)
        ).order_by(RegistroClima.data_registro.asc())
        
        registros = list((await self.session.execute(stmt_clima)).scalars().all())
        previsoes = await self._buscar_previsoes(tenant_id, unidade_produtiva_id, hoje)
        clima = registros[-1] if registros else None
        if not clima or clima.temp_media_c is None or clima.umidade_rel_pct is None:
            return self._resposta_sem_dados(especie, registros, previsoes)

        # 3. Calcular ITH (Índice de Temperatura e Umidade)
        # Fórmula clássica: ITH = (0.8 * T) + ((UR/100) * (T - 14.4)) + 46.4
        temperatura = float(clima.temp_media_c)
        umidade = float(clima.umidade_rel_pct)
        ith = self._calcular_ith(temperatura, umidade)

        # 4. Avaliar contra as regras do modelo
        regras = modelo.regras_risco
        critico = float(regras.get("nivel_critico") or 82)
        alto = float(regras.get("nivel_alto") or 78)
        medio = float(regras.get("nivel_medio") or 72)
        
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

        idade_dados = max((hoje - clima.data_registro).days, 0)
        alertas = self._gerar_alertas(idade_dados, ith)
        return InteligenciaPecuariaResponse(
            especie=especie,
            tipo_risco="Estresse Térmico",
            risco_atual=risco,
            data_analise=datetime.utcnow(),
            valor_referencia=round(ith, 1),
            detalhes=detalhes,
            historico=self._historico_ith(registros),
            alertas=alertas,
            idade_dados_dias=idade_dados,
            dados_atualizados=idade_dados <= 2,
            **self._resumo_previsao(previsoes, regras),
        )

    async def _buscar_previsoes(self, tenant_id: UUID, unidade_id: UUID, hoje: date) -> list[PrevisaoClima]:
        """Busca três dias de previsão climática da unidade com RLS aplicado."""
        await self._set_tenant_context(tenant_id)
        limite = hoje + timedelta(days=2)
        stmt = select(PrevisaoClima).where(
            PrevisaoClima.tenant_id == tenant_id,
            PrevisaoClima.unidade_produtiva_id == unidade_id,
            PrevisaoClima.data_previsao >= hoje,
            PrevisaoClima.data_previsao <= limite,
        ).order_by(PrevisaoClima.data_previsao.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    def _resumo_previsao(self, previsoes: list[PrevisaoClima], regras: dict) -> dict[str, dict | list]:
        """Converte previsão meteorológica em indicadores preventivos pecuários."""
        limites = self._limites_risco(regras)
        dias = [self._resumo_dia(previsao, limites) for previsao in previsoes]
        periodos = [periodo for previsao in previsoes for periodo in (previsao.periodos or [])]
        estresse = self._resumo_estresse(periodos, limites)
        chuva = self._resumo_chuva(previsoes)
        return {
            "previsao_ith": dias,
            "estresse_previsto": estresse,
            "chuva_prevista": chuva,
            "janela_manejo": self._janela_manejo(periodos, limites),
        }

    @staticmethod
    def _limites_risco(regras: dict) -> tuple[float, float, float]:
        """Obtém limites configuráveis de ITH, aplicando os padrões técnicos."""
        return (
            float(regras.get("nivel_critico") or 82),
            float(regras.get("nivel_alto") or 78),
            float(regras.get("nivel_medio") or 72),
        )

    @staticmethod
    def _resumo_dia(previsao: PrevisaoClima, limites: tuple[float, float, float]) -> dict:
        """Calcula o pico diário de ITH e o risco térmico correspondente."""
        iths = []
        for periodo in previsao.periodos or []:
            temperatura = periodo.get("temperatura_c")
            umidade = periodo.get("umidade_pct")
            if temperatura is not None and umidade is not None:
                iths.append(InteligenciaPecuariaService._calcular_ith(float(temperatura), float(umidade)))
        ith_max = round(max(iths), 1) if iths else None
        return {
            "data": previsao.data_previsao.isoformat(),
            "horizonte_horas": min((previsao.data_previsao - date.today()).days + 1, 3) * 24,
            "ith_max": ith_max,
            "risco": InteligenciaPecuariaService._classificar_risco(ith_max, limites),
            "temperatura_max_c": float(previsao.temp_max_c) if previsao.temp_max_c is not None else None,
            "umidade_disponivel": bool(iths),
        }

    @staticmethod
    def _classificar_risco(ith: float | None, limites: tuple[float, float, float]) -> str:
        """Classifica ITH sem inferir risco quando faltam variáveis."""
        if ith is None:
            return "INDETERMINADO"
        critico, alto, medio = limites
        if ith >= critico:
            return "CRITICO"
        if ith >= alto:
            return "ALTO"
        if ith >= medio:
            return "MEDIO"
        return "BAIXO"

    @staticmethod
    def _resumo_estresse(periodos: list[dict], limites: tuple[float, float, float]) -> dict:
        """Resume duração observável e maior intensidade de estresse em 72 horas."""
        iths = [
            InteligenciaPecuariaService._calcular_ith(float(p["temperatura_c"]), float(p["umidade_pct"]))
            for p in periodos
            if p.get("temperatura_c") is not None and p.get("umidade_pct") is not None
        ]
        risco = InteligenciaPecuariaService._classificar_risco(max(iths) if iths else None, limites)
        return {
            "duracao_horas": len([ith for ith in iths if ith >= limites[2]]) * 3,
            "intensidade": risco,
            "horizonte_horas": 72,
            "dados_suficientes": bool(iths),
        }

    @staticmethod
    def _resumo_chuva(previsoes: list[PrevisaoClima]) -> dict:
        """Soma o volume e identifica a maior probabilidade de chuva prevista."""
        volumes = [float(p.precipitacao_mm) for p in previsoes if p.precipitacao_mm is not None]
        probabilidades = [float(p.probabilidade_chuva_pct) for p in previsoes if p.probabilidade_chuva_pct is not None]
        return {
            "volume_mm_72h": round(sum(volumes), 1) if volumes else None,
            "probabilidade_max_pct": round(max(probabilidades), 1) if probabilidades else None,
            "dados_suficientes": bool(volumes or probabilidades),
        }

    @staticmethod
    def _janela_manejo(periodos: list[dict], limites: tuple[float, float, float]) -> dict:
        """Encontra o primeiro período sem estresse térmico, chuva relevante ou vento forte."""
        for periodo in periodos:
            temperatura = periodo.get("temperatura_c")
            umidade = periodo.get("umidade_pct")
            if temperatura is None or umidade is None:
                continue
            ith = InteligenciaPecuariaService._calcular_ith(float(temperatura), float(umidade))
            chuva = float(periodo.get("probabilidade_chuva_pct") or 0)
            vento = float(periodo.get("vento_kmh") or 0)
            if ith < limites[2] and chuva < 50 and vento < 30:
                return {"horario": periodo.get("horario"), "status": "RECOMENDADA", "ith": round(ith, 1)}
        return {"horario": None, "status": "NAO_IDENTIFICADA", "ith": None}

    @staticmethod
    def _historico_ith(registros: list[RegistroClima]) -> list[dict[str, float | str | None]]:
        """Converte observações recentes em série histórica de ITH."""
        historico = []
        for registro in registros:
            ith = None
            if registro.temp_media_c is not None and registro.umidade_rel_pct is not None:
                ith = round(InteligenciaPecuariaService._calcular_ith(float(registro.temp_media_c), float(registro.umidade_rel_pct)), 1)
            historico.append({
                "data": registro.data_registro.isoformat(),
                "ith": ith,
                "temperatura_c": float(registro.temp_media_c) if registro.temp_media_c is not None else None,
                "umidade_pct": float(registro.umidade_rel_pct) if registro.umidade_rel_pct is not None else None,
            })
        return historico

    @staticmethod
    def _gerar_alertas(idade_dados: int, ith: float) -> list[str]:
        """Gera alertas explicáveis para atualização e risco térmico."""
        alertas = []
        if idade_dados > 2:
            alertas.append("Dados climáticos desatualizados há mais de 2 dias.")
        if ith >= 78:
            alertas.append("Tendência de estresse térmico alto ou crítico.")
        elif ith >= 72:
            alertas.append("Tendência de estresse térmico moderado.")
        return alertas

    @staticmethod
    def _resposta_sem_dados(especie: str, registros: list[RegistroClima], previsoes: list[PrevisaoClima]) -> InteligenciaPecuariaResponse:
        """Retorna estado indeterminado sem transformar ausência em risco baixo."""
        idade = max((date.today() - registros[-1].data_registro).days, 0) if registros else None
        return InteligenciaPecuariaResponse(
            especie=especie,
            tipo_risco="Estresse Térmico",
            risco_atual="MEDIO",
            data_analise=datetime.utcnow(),
            valor_referencia=None,
            detalhes=["Temperatura média e umidade relativa são necessárias para calcular o ITH."],
            historico=InteligenciaPecuariaService._historico_ith(registros),
            alertas=["Dados climáticos insuficientes para determinar o risco."],
            idade_dados_dias=idade,
            dados_atualizados=idade is not None and idade <= 2,
            **InteligenciaPecuariaService._resumo_previsao_sem_modelo(previsoes),
        )

    @staticmethod
    def _resumo_previsao_sem_modelo(previsoes: list[PrevisaoClima]) -> dict[str, dict | list]:
        """Retorna previsão neutra quando ainda não há modelo zoossanitário configurado."""
        dias = [{"data": p.data_previsao.isoformat(), "horizonte_horas": min((p.data_previsao - date.today()).days + 1, 3) * 24, "ith_max": None, "risco": "INDETERMINADO", "temperatura_max_c": float(p.temp_max_c) if p.temp_max_c is not None else None, "umidade_disponivel": False} for p in previsoes]
        return {"previsao_ith": dias, "estresse_previsto": {"duracao_horas": None, "intensidade": "INDETERMINADO", "horizonte_horas": 72, "dados_suficientes": False}, "chuva_prevista": InteligenciaPecuariaService._resumo_chuva(previsoes), "janela_manejo": {"horario": None, "status": "NAO_IDENTIFICADA", "ith": None}}

    @staticmethod
    def _calcular_ith(temperatura_c: float, umidade_pct: float) -> float:
        """Calcula o índice de temperatura e umidade com entradas normalizadas."""
        return (0.8 * temperatura_c) + ((umidade_pct / 100.0) * (temperatura_c - 14.4)) + 46.4
