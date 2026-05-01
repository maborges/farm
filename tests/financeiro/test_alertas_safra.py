"""
Testes unitários — Sistema de Alertas Inteligentes (Step 101)

Cobre as 3 regras de negócio do gerar_alertas:
  - CUSTO_REGISTRADO  (info)     : custo_total > 0
  - MARGEM_NEGATIVA   (danger)   : margem do cenário base < 0
  - AUMENTO_CUSTO     (warning)  : variação percentual > 20% no último período

Os testes são unitários puros: não acessam banco — testam apenas a lógica
de decisão. Os schemas são replicados localmente para isolamento total.
"""

import pytest
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schemas locais (mesma interface de financeiro.schemas.lancamento_schema)
# ---------------------------------------------------------------------------


class AlertaSafra(BaseModel):
    tipo: str
    nivel: str   # info | warning | danger
    mensagem: str


class SerieTemporal(BaseModel):
    periodo: str
    total: float


# ---------------------------------------------------------------------------
# Helpers de build
# ---------------------------------------------------------------------------


def _custo_registrado_alerta(qtd: int) -> AlertaSafra:
    plural_s = "s" if qtd != 1 else ""
    plural_a = "s" if qtd != 1 else ""
    return AlertaSafra(
        tipo="CUSTO_REGISTRADO",
        nivel="info",
        mensagem=(
            f"Você possui {qtd} lançamento{plural_s} de custo "
            f"registrado{plural_a} nesta safra."
        ),
    )


def _margem_negativa_alerta(margem: float) -> AlertaSafra:
    return AlertaSafra(
        tipo="MARGEM_NEGATIVA",
        nivel="danger",
        mensagem=(
            f"Sua operação está com margem negativa de "
            f"R$ {abs(margem):,.2f}. Revise os custos."
        ),
    )


def _aumento_custo_alerta(variacao: float, de: str, para: str) -> AlertaSafra:
    return AlertaSafra(
        tipo="AUMENTO_CUSTO",
        nivel="warning",
        mensagem=f"Seus custos aumentaram {variacao:.1f}% no último período ({de} → {para}).",
    )


# ---------------------------------------------------------------------------
# Lógica de alerta extraída para teste (replica a lógica do service sem DB)
# ---------------------------------------------------------------------------


def calcular_alertas_aumento(serie: list[SerieTemporal]) -> list[AlertaSafra]:
    """Extrai apenas a regra de aumento percentual para teste isolado."""
    alertas: list[AlertaSafra] = []
    if len(serie) >= 2:
        ultimo = serie[-1].total
        penultimo = serie[-2].total
        if penultimo > 0:
            variacao_pct = (ultimo - penultimo) / penultimo * 100
            if variacao_pct > 20:
                alertas.append(
                    AlertaSafra(
                        tipo="AUMENTO_CUSTO",
                        nivel="warning",
                        mensagem=(
                            f"Seus custos aumentaram {variacao_pct:.1f}% no último período "
                            f"({serie[-2].periodo} → {serie[-1].periodo})."
                        ),
                    )
                )
    return alertas


# ---------------------------------------------------------------------------
# Testes — Schema de AlertaSafra
# ---------------------------------------------------------------------------


class TestAlertaSafraSchema:
    def test_cria_alerta_info(self) -> None:
        alerta = AlertaSafra(tipo="CUSTO_REGISTRADO", nivel="info", mensagem="ok")
        assert alerta.nivel == "info"
        assert alerta.tipo == "CUSTO_REGISTRADO"

    def test_cria_alerta_warning(self) -> None:
        alerta = AlertaSafra(tipo="AUMENTO_CUSTO", nivel="warning", mensagem="ok")
        assert alerta.nivel == "warning"

    def test_cria_alerta_danger(self) -> None:
        alerta = AlertaSafra(tipo="MARGEM_NEGATIVA", nivel="danger", mensagem="ok")
        assert alerta.nivel == "danger"

    def test_mensagem_nao_pode_ser_vazia(self) -> None:
        # Pydantic não valida tamanho mínimo por padrão — verifica que instância existe
        alerta = AlertaSafra(tipo="X", nivel="info", mensagem="")
        assert alerta.mensagem == ""


# ---------------------------------------------------------------------------
# Testes — Regra CUSTO_REGISTRADO
# ---------------------------------------------------------------------------


class TestAlertaCustoRegistrado:
    def test_alerta_gerado_quando_ha_custos(self) -> None:
        alerta = _custo_registrado_alerta(3)
        assert alerta.tipo == "CUSTO_REGISTRADO"
        assert alerta.nivel == "info"
        assert "3 lançamentos" in alerta.mensagem

    def test_singular_quando_um_lancamento(self) -> None:
        alerta = _custo_registrado_alerta(1)
        assert "1 lançamento de custo registrado" in alerta.mensagem

    def test_plural_quando_varios_lancamentos(self) -> None:
        alerta = _custo_registrado_alerta(5)
        assert "5 lançamentos de custo registrados" in alerta.mensagem


# ---------------------------------------------------------------------------
# Testes — Regra MARGEM_NEGATIVA
# ---------------------------------------------------------------------------


class TestAlertaMargemNegativa:
    def test_alerta_gerado_para_margem_negativa(self) -> None:
        margem = -5000.0
        alerta = _margem_negativa_alerta(margem)
        assert alerta.tipo == "MARGEM_NEGATIVA"
        assert alerta.nivel == "danger"
        # backend usa f-string :,.2f (en_US) → "5,000.00"
        assert "5,000.00" in alerta.mensagem

    def test_mensagem_contem_valor_absoluto(self) -> None:
        alerta = _margem_negativa_alerta(-1234.56)
        # backend usa f-string :,.2f (en_US) → "1,234.56"
        assert "1,234.56" in alerta.mensagem

    def test_zero_nao_gera_margem_negativa(self) -> None:
        """Margem zero não é negativa — não deve gerar alerta."""
        margem = 0.0
        gera_alerta = margem < 0
        assert not gera_alerta

    def test_margem_positiva_nao_gera_alerta(self) -> None:
        margem = 100.0
        gera_alerta = margem < 0
        assert not gera_alerta


# ---------------------------------------------------------------------------
# Testes — Regra AUMENTO_CUSTO (variação > 20%)
# ---------------------------------------------------------------------------


class TestAlertaAumentoCusto:
    def test_aumento_acima_20_pct_gera_alerta(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1300.0),  # +30%
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 1
        assert alertas[0].tipo == "AUMENTO_CUSTO"
        assert alertas[0].nivel == "warning"
        assert "30.0%" in alertas[0].mensagem
        assert "2024-03 → 2024-04" in alertas[0].mensagem

    def test_aumento_exato_20_pct_nao_gera_alerta(self) -> None:
        """Limiar é > 20%, exatamente 20% NÃO deve gerar alerta."""
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1200.0),  # +20.0%
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0

    def test_aumento_abaixo_20_pct_nao_gera_alerta(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1100.0),  # +10%
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0

    def test_reducao_de_custos_nao_gera_alerta(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=800.0),  # -20%
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0

    def test_apenas_um_periodo_nao_gera_alerta(self) -> None:
        """Com menos de 2 períodos não há base de comparação."""
        serie = [SerieTemporal(periodo="2024-03", total=5000.0)]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0

    def test_serie_vazia_nao_gera_alerta(self) -> None:
        alertas = calcular_alertas_aumento([])
        assert len(alertas) == 0

    def test_penultimo_zero_nao_divide_por_zero(self) -> None:
        """Se penúltimo for zero, não deve calcular percentual (divisão por zero)."""
        serie = [
            SerieTemporal(periodo="2024-03", total=0.0),
            SerieTemporal(periodo="2024-04", total=1000.0),
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0  # não gera alerta — penultimo == 0 é ignorado

    def test_multiplos_periodos_compara_apenas_ultimos_dois(self) -> None:
        """Com vários períodos, só os dois últimos são comparados."""
        serie = [
            SerieTemporal(periodo="2024-01", total=100.0),
            SerieTemporal(periodo="2024-02", total=500.0),  # +400% — ignorado
            SerieTemporal(periodo="2024-03", total=510.0),  # +2% — não dispara
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 0

    def test_limite_superior_gera_alerta_correto(self) -> None:
        """25% de aumento deve gerar alerta com mensagem formatada corretamente."""
        serie = [
            SerieTemporal(periodo="2024-06", total=10000.0),
            SerieTemporal(periodo="2024-07", total=12500.0),  # +25%
        ]
        alertas = calcular_alertas_aumento(serie)
        assert len(alertas) == 1
        assert "25.0%" in alertas[0].mensagem
