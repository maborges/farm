"""
Testes unitários — Sistema de Recomendações (Step 102)

Cobre as 3 regras de negócio de gerar_recomendacoes:
  - REVISAR_CUSTOS   : margem < 0 (cenário base)
  - ANALISAR_INSUMOS : INSUMOS é a categoria de maior custo
  - VER_EVOLUCAO     : aumento percentual > 20% na série temporal

Os testes são unitários puros: sem DB, sem I/O.
A lógica de decisão é replicada localmente para isolamento.
"""

import uuid
import pytest
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Schemas locais (mesma interface de financeiro.schemas.lancamento_schema)
# ---------------------------------------------------------------------------


class SerieTemporal(BaseModel):
    periodo: str
    total: float


class RecomendacaoSafra(BaseModel):
    tipo: str
    mensagem: str
    acao: str
    rota: str


# ---------------------------------------------------------------------------
# Lógica determinística extraída para teste isolado
# (replica a lógica de LancamentoService.gerar_recomendacoes)
# ---------------------------------------------------------------------------


def _calcular_recomendacoes(
    safra_id: str,
    margem: float | None,
    categoria_maior: str | None,
    serie: list[SerieTemporal],
) -> list[RecomendacaoSafra]:
    """Replica a lógica do service sem depender de banco."""
    recomendacoes: list[RecomendacaoSafra] = []

    # Regra 1: Margem negativa
    if margem is not None and margem < 0:
        recomendacoes.append(RecomendacaoSafra(
            tipo="REVISAR_CUSTOS",
            mensagem="Revise seus custos operacionais. A margem atual está negativa.",
            acao="Ver cenários",
            rota=f"/agricola/safras/{safra_id}/cenarios",
        ))

    # Regra 2: INSUMOS é o maior custo
    if categoria_maior is not None and categoria_maior.upper() == "INSUMOS":
        recomendacoes.append(RecomendacaoSafra(
            tipo="ANALISAR_INSUMOS",
            mensagem="Custos com insumos estão elevados e lideram sua estrutura de custos.",
            acao="Analisar por categoria",
            rota=f"/agricola/safras/{safra_id}/cenarios",
        ))

    # Regra 3: Aumento > 20% na série
    if len(serie) >= 2:
        ultimo = serie[-1].total
        penultimo = serie[-2].total
        if penultimo > 0:
            variacao_pct = (ultimo - penultimo) / penultimo * 100
            if variacao_pct > 20:
                recomendacoes.append(RecomendacaoSafra(
                    tipo="VER_EVOLUCAO",
                    mensagem=f"Seus custos aumentaram {variacao_pct:.1f}% recentemente. Acompanhe a evolução.",
                    acao="Ver evolução de custos",
                    rota=f"/agricola/safras/{safra_id}/operacoes",
                ))

    return recomendacoes


SAFRA_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Testes — Schema de RecomendacaoSafra
# ---------------------------------------------------------------------------


class TestRecomendacaoSafraSchema:
    def test_cria_recomendacao_valida(self) -> None:
        rec = RecomendacaoSafra(
            tipo="REVISAR_CUSTOS",
            mensagem="Revise os custos",
            acao="Ver cenários",
            rota="/agricola/safras/abc/cenarios",
        )
        assert rec.tipo == "REVISAR_CUSTOS"
        assert rec.acao == "Ver cenários"
        assert "/cenarios" in rec.rota

    def test_rota_deve_ser_string(self) -> None:
        rec = RecomendacaoSafra(
            tipo="X", mensagem="Y", acao="Z", rota="/path"
        )
        assert isinstance(rec.rota, str)


# ---------------------------------------------------------------------------
# Testes — Regra REVISAR_CUSTOS (margem negativa)
# ---------------------------------------------------------------------------


class TestRecomendacaoRevisarCustos:
    def test_gerada_quando_margem_negativa(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=-1000.0, categoria_maior=None, serie=[])
        tipos = [r.tipo for r in recs]
        assert "REVISAR_CUSTOS" in tipos

    def test_conteudo_da_recomendacao(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=-500.0, categoria_maior=None, serie=[])
        rec = next(r for r in recs if r.tipo == "REVISAR_CUSTOS")
        assert "Revise" in rec.mensagem
        assert rec.acao == "Ver cenários"
        assert f"/agricola/safras/{SAFRA_ID}/cenarios" == rec.rota

    def test_nao_gerada_para_margem_zero(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=0.0, categoria_maior=None, serie=[])
        assert not any(r.tipo == "REVISAR_CUSTOS" for r in recs)

    def test_nao_gerada_para_margem_positiva(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=5000.0, categoria_maior=None, serie=[])
        assert not any(r.tipo == "REVISAR_CUSTOS" for r in recs)

    def test_nao_gerada_sem_cenario(self) -> None:
        """margem=None significa que não há cenário base cadastrado."""
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=[])
        assert not any(r.tipo == "REVISAR_CUSTOS" for r in recs)


# ---------------------------------------------------------------------------
# Testes — Regra ANALISAR_INSUMOS (maior custo)
# ---------------------------------------------------------------------------


class TestRecomendacaoAnalisarInsumos:
    def test_gerada_quando_insumos_e_maior_categoria(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior="INSUMOS", serie=[])
        assert any(r.tipo == "ANALISAR_INSUMOS" for r in recs)

    def test_case_insensitive_para_categoria(self) -> None:
        """Backend pode retornar 'insumos' ou 'INSUMOS' — ambos devem disparar."""
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior="insumos", serie=[])
        assert any(r.tipo == "ANALISAR_INSUMOS" for r in recs)

    def test_conteudo_da_recomendacao_insumos(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior="INSUMOS", serie=[])
        rec = next(r for r in recs if r.tipo == "ANALISAR_INSUMOS")
        assert "insumos" in rec.mensagem.lower()
        assert rec.acao == "Analisar por categoria"
        assert f"/agricola/safras/{SAFRA_ID}/cenarios" == rec.rota

    def test_nao_gerada_quando_categoria_e_operacoes(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior="OPERACOES", serie=[])
        assert not any(r.tipo == "ANALISAR_INSUMOS" for r in recs)

    def test_nao_gerada_quando_categoria_e_mao_obra(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior="MAO_OBRA", serie=[])
        assert not any(r.tipo == "ANALISAR_INSUMOS" for r in recs)

    def test_nao_gerada_sem_lancamentos(self) -> None:
        """Sem lançamentos, categoria_maior=None — não deve gerar recomendação."""
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=[])
        assert not any(r.tipo == "ANALISAR_INSUMOS" for r in recs)


# ---------------------------------------------------------------------------
# Testes — Regra VER_EVOLUCAO (aumento > 20%)
# ---------------------------------------------------------------------------


class TestRecomendacaoVerEvolucao:
    def test_gerada_com_aumento_acima_20_pct(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1300.0),  # +30%
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_mensagem_contem_percentual_formatado(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1250.0),  # +25%
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        rec = next(r for r in recs if r.tipo == "VER_EVOLUCAO")
        assert "25.0%" in rec.mensagem
        assert rec.acao == "Ver evolução de custos"
        assert f"/agricola/safras/{SAFRA_ID}/operacoes" == rec.rota

    def test_nao_gerada_com_exatamente_20_pct(self) -> None:
        """Limiar é > 20%, não >= 20%."""
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1200.0),  # +20.0%
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_nao_gerada_com_aumento_abaixo_20_pct(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1150.0),  # +15%
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_nao_gerada_com_queda_de_custos(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=700.0),  # -30%
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_nao_gerada_com_serie_de_um_periodo(self) -> None:
        serie = [SerieTemporal(periodo="2024-03", total=5000.0)]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_nao_gerada_com_serie_vazia(self) -> None:
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=[])
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)

    def test_nao_divide_por_zero_quando_penultimo_e_zero(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=0.0),
            SerieTemporal(periodo="2024-04", total=1000.0),
        ]
        recs = _calcular_recomendacoes(SAFRA_ID, margem=None, categoria_maior=None, serie=serie)
        assert not any(r.tipo == "VER_EVOLUCAO" for r in recs)


# ---------------------------------------------------------------------------
# Testes — Combinações (múltiplas regras ativas)
# ---------------------------------------------------------------------------


class TestRecomendacoesCombinadas:
    def test_todas_as_tres_regras_ativas(self) -> None:
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1500.0),  # +50%
        ]
        recs = _calcular_recomendacoes(
            SAFRA_ID,
            margem=-3000.0,
            categoria_maior="INSUMOS",
            serie=serie,
        )
        tipos = {r.tipo for r in recs}
        assert tipos == {"REVISAR_CUSTOS", "ANALISAR_INSUMOS", "VER_EVOLUCAO"}

    def test_ordem_de_prioridade_margem_primeiro(self) -> None:
        """Margem negativa deve aparecer primeiro (maior prioridade)."""
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1400.0),  # +40%
        ]
        recs = _calcular_recomendacoes(
            SAFRA_ID,
            margem=-500.0,
            categoria_maior="INSUMOS",
            serie=serie,
        )
        assert recs[0].tipo == "REVISAR_CUSTOS"

    def test_sem_condicoes_ativas_retorna_lista_vazia(self) -> None:
        """Safra saudável não deve gerar nenhuma recomendação."""
        serie = [
            SerieTemporal(periodo="2024-03", total=1000.0),
            SerieTemporal(periodo="2024-04", total=1050.0),  # +5%
        ]
        recs = _calcular_recomendacoes(
            SAFRA_ID,
            margem=2000.0,
            categoria_maior="OPERACOES",
            serie=serie,
        )
        assert recs == []

    def test_apenas_insumos_ativo_retorna_uma_recomendacao(self) -> None:
        recs = _calcular_recomendacoes(
            SAFRA_ID,
            margem=500.0,          # positiva
            categoria_maior="INSUMOS",
            serie=[],              # sem série
        )
        assert len(recs) == 1
        assert recs[0].tipo == "ANALISAR_INSUMOS"

    def test_rotas_incluem_safra_id(self) -> None:
        """Todas as rotas geradas devem conter o safra_id para navegação correta."""
        serie = [
            SerieTemporal(periodo="2024-03", total=100.0),
            SerieTemporal(periodo="2024-04", total=200.0),  # +100%
        ]
        recs = _calcular_recomendacoes(
            SAFRA_ID,
            margem=-100.0,
            categoria_maior="INSUMOS",
            serie=serie,
        )
        for rec in recs:
            assert SAFRA_ID in rec.rota
