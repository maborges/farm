"""Carga opcional de modelos fitossanitários globais de referência.

Registra modelos-base inspirados em faixas climáticas publicadas pela Embrapa
e UFV com `tenant_id = NULL` e `is_global = True`. Esses registros servem
exclusivamente como biblioteca de referência para visualização e cópia pelo
produtor/agrônomo, nunca sendo avaliados automaticamente em produção.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import os
import sys
from pathlib import Path

from sqlalchemy import select, text

API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from agricola.climatico.models import ModeloFitossanitario  # noqa: E402
from agricola.climatico.schemas import validar_regras_fitossanitarias  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import async_session_maker, catalog_admin_async_session_maker  # noqa: E402

_OBSERVACAO_PADRAO = (
    "Modelo-base de referência ambiental (triagem); revise e ajuste os "
    "limiares com seu agrônomo para cultivar, estádio fenológico, histórico de "
    "inóculo e microclima da fazenda antes de usar."
)


def _referencia(
    cultura: str,
    doenca: str,
    *,
    agente_causal: str,
    fonte_parametros: str,
    fonte_url: str,
    condicoes: list[dict[str, object]],
) -> dict[str, object]:
    """Constrói um item padronizado do catálogo de referência fitossanitária.

    Args:
        cultura: Nome canônico da cultura (compatível com seed_culturas).
        doenca: Nome popular da doença monitorada.
        agente_causal: Nome científico do patógeno associado.
        fonte_parametros: Referência institucional/bibliográfica da faixa.
        fonte_url: Endereço HTTP/HTTPS público da fonte consultada.
        condicoes: Lista de condições climáticas no formato do motor.

    Returns:
        Dicionário estruturado pronto para validação e persistência.
    """
    return {
        "cultura": cultura,
        "doenca": doenca,
        "regras_risco": {
            "condicoes": condicoes,
            "nivel_medio_pct": 35,
            "nivel_alto_pct": 60,
            "nivel_critico_pct": 80,
            "metadados": {
                "tipo_resultado": "referencia_favorabilidade_climatica",
                "somente_referencia": True,
                "agente_causal": agente_causal,
                "fonte_parametros": fonte_parametros,
                "fonte_url": fonte_url,
                "versao_regra": "1.0-ref",
                "observacao": _OBSERVACAO_PADRAO,
            },
        },
    }


MODELOS_FITOSSANITARIOS_BASE: tuple[dict[str, object], ...] = (
    # -----------------------------------------------------------------------
    # GRÃOS (25 modelos — 9 culturas)
    # -----------------------------------------------------------------------
    _referencia(
        "Soja",
        "Ferrugem Asiática",
        agente_causal="Phakopsora pachyrhizi",
        fonte_parametros="Embrapa Soja — Doc. 256 / Tecnologias de Produção de Soja",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1158639/1/Doc-256-2023OL-1.pdf#page=16",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 26.5, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Soja",
        "Mofo-branco",
        agente_causal="Sclerotinia sclerotiorum",
        fonte_parametros="Embrapa Soja — Doc. 256 / Manejo de Mofo-branco",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1158639/1/Doc-256-2023OL-1.pdf",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 22.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Soja",
        "Mancha-alvo",
        agente_causal="Corynespora cassiicola",
        fonte_parametros="Embrapa Soja — Doc. 256 / Manual de Identificação de Doenças de Soja",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1158639/1/Doc-256-2023OL-1.pdf",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Soja",
        "Oídio",
        agente_causal="Erysiphe diffusa",
        fonte_parametros="Embrapa Soja — Doc. 256 / Manual de Identificação de Doenças de Soja",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1158639/1/Doc-256-2023OL-1.pdf",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": "<=", "valor": 65.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": "<=", "valor": 1.0, "peso": 0.15},
        ],
    ),
    _referencia(
        "Milho",
        "Mancha-de-turcicum",
        agente_causal="Exserohilum turcicum",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças Foliares do Milho",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 27.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Milho",
        "Cercosporiose",
        agente_causal="Cercospora zeae-maydis",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças Foliares do Milho",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Milho",
        "Ferrugem Polissora",
        agente_causal="Puccinia polysora",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças Foliares do Milho",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 32.0, "peso": 0.50},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.30},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Trigo",
        "Ferrugem-da-folha",
        agente_causal="Puccinia triticina",
        fonte_parametros="Embrapa Trigo — Doenças do Trigo",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Trigo",
        "Giberela",
        agente_causal="Fusarium graminearum",
        fonte_parametros="Embrapa Trigo — Manejo de Giberela na Espiga",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 30.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Trigo",
        "Brusone-do-trigo",
        agente_causal="Pyricularia oryzae (patótipo Triticum)",
        fonte_parametros="Embrapa Trigo — Brusone na Cultura do Trigo",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 24.0, "max": 27.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Arroz",
        "Brusone",
        agente_causal="Pyricularia oryzae / Magnaporthe oryzae",
        fonte_parametros="Embrapa Arroz e Feijão — Manejo de Brusone no Arroz",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 28.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Arroz",
        "Mancha-parda",
        agente_causal="Bipolaris oryzae",
        fonte_parametros="Embrapa Arroz e Feijão — Doenças do Arroz",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Feijão",
        "Antracnose",
        agente_causal="Colletotrichum lindemuthianum",
        fonte_parametros="Embrapa Arroz e Feijão — Doenças do Feijoeiro",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Feijão",
        "Mancha-angular",
        agente_causal="Pseudocercospora griseola",
        fonte_parametros="Embrapa Arroz e Feijão — Doenças do Feijoeiro",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Feijão",
        "Ferrugem-do-feijoeiro",
        agente_causal="Uromyces appendiculatus",
        fonte_parametros="Embrapa Arroz e Feijão — Doenças do Feijoeiro",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 17.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Feijão",
        "Mofo-branco",
        agente_causal="Sclerotinia sclerotiorum",
        fonte_parametros="Embrapa Arroz e Feijão — Manejo de Mofo-branco no Feijoeiro",
        fonte_url="https://www.embrapa.br/arroz-e-feijao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Aveia",
        "Ferrugem-da-folha",
        agente_causal="Puccinia coronata f. sp. avenae",
        fonte_parametros="Embrapa Trigo — Doenças de Cereais de Inverno",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Aveia",
        "Helmintosporiose",
        agente_causal="Drechslera avenae / Pyrenophora avenae",
        fonte_parametros="Embrapa Trigo — Doenças de Cereais de Inverno",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cevada",
        "Mancha-reticular",
        agente_causal="Pyrenophora teres",
        fonte_parametros="Embrapa Trigo — Doenças da Cevada",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cevada",
        "Giberela",
        agente_causal="Fusarium graminearum",
        fonte_parametros="Embrapa Trigo — Doenças da Cevada",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 25.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Cevada",
        "Ferrugem-da-folha",
        agente_causal="Puccinia hordei",
        fonte_parametros="Embrapa Trigo — Doenças da Cevada",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Sorgo",
        "Antracnose",
        agente_causal="Colletotrichum sublineolum",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças do Sorgo",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Sorgo",
        "Helmintosporiose",
        agente_causal="Exserohilum turcicum",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças do Sorgo",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 27.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Milheto",
        "Ferrugem-do-milheto",
        agente_causal="Puccinia substriata var. indica",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças do Milheto",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 17.0, "max": 22.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Milheto",
        "Brusone-do-milheto",
        agente_causal="Pyricularia grisea",
        fonte_parametros="Embrapa Milho e Sorgo — Doenças do Milheto",
        fonte_url="https://www.embrapa.br/milho-e-sorgo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 24.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    # -----------------------------------------------------------------------
    # FIBRAS (3 modelos — 1 cultura; Sisal fora do catálogo climático diário:
    # Podridão-vermelha por Aspergillus niger é oportunista de ferimentos e
    # déficit hídrico prolongado, sem gatilho por umidade/chuva diária)
    # -----------------------------------------------------------------------
    _referencia(
        "Algodão",
        "Mancha-de-ramulária",
        agente_causal="Ramulariopsis pseudoglycines / Ramularia areola",
        fonte_parametros="Embrapa Algodão — Manejo de Doenças do Algodoeiro",
        fonte_url="https://www.embrapa.br/algodao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Algodão",
        "Ramulose",
        agente_causal="Colletotrichum gossypii var. cephalosporioides",
        fonte_parametros="Embrapa Algodão — Manejo de Doenças do Algodoeiro",
        fonte_url="https://www.embrapa.br/algodao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Algodão",
        "Mancha-de-alternária",
        agente_causal="Alternaria macrospora / Alternaria alternata",
        fonte_parametros="Embrapa Algodão — Manejo de Doenças do Algodoeiro",
        fonte_url="https://www.embrapa.br/algodao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    # -----------------------------------------------------------------------
    # FRUTAS (13 modelos — 6 culturas)
    # -----------------------------------------------------------------------
    _referencia(
        "Laranja",
        "Pinta-preta-dos-citros",
        agente_causal="Phyllosticta citricarpa",
        fonte_parametros="Embrapa Mandioca e Fruticultura / Fundecitrus — Doenças dos Citros",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.5, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Laranja",
        "Podridão-floral-dos-citros",
        agente_causal="Colletotrichum abscissum / Colletotrichum acutatum",
        fonte_parametros="Embrapa Mandioca e Fruticultura / Fundecitrus — Podridão Floral",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 28.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Limão",
        "Verrugose-dos-citros",
        agente_causal="Elsinoë fawcettii",
        fonte_parametros="Embrapa Mandioca e Fruticultura — Doenças dos Citros",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Limão",
        "Podridão-floral-dos-citros",
        agente_causal="Colletotrichum abscissum / Colletotrichum acutatum",
        fonte_parametros="Embrapa Mandioca e Fruticultura / Fundecitrus — Podridão Floral",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 28.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Banana",
        "Sigatoka-negra",
        agente_causal="Pseudocercospora fijiensis / Mycosphaerella fijiensis",
        fonte_parametros="Embrapa Mandioca e Fruticultura — Manejo das Sigatokas",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 21.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Banana",
        "Sigatoka-amarela",
        agente_causal="Pseudocercospora musae / Mycosphaerella musicola",
        fonte_parametros="Embrapa Mandioca e Fruticultura — Manejo das Sigatokas",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 21.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Maçã",
        "Sarna-da-macieira",
        agente_causal="Venturia inaequalis",
        fonte_parametros="Embrapa Uva e Vinho — Doenças da Macieira",
        fonte_url="https://www.embrapa.br/uva-e-vinho",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 14.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Maçã",
        "Mancha-foliar-de-glomerella",
        agente_causal="Colletotrichum spp. / Glomerella cingulata",
        fonte_parametros="Embrapa Uva e Vinho / Epagri — Mancha Foliar de Glomerella",
        fonte_url="https://www.embrapa.br/uva-e-vinho",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 28.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 10.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Uva",
        "Míldio-da-videira",
        agente_causal="Plasmopara viticola",
        fonte_parametros="Embrapa Uva e Vinho — Doenças Fúngicas da Videira",
        fonte_url="https://www.embrapa.br/uva-e-vinho",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 26.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Uva",
        "Oídio-da-videira",
        agente_causal="Erysiphe necator",
        fonte_parametros="Embrapa Uva e Vinho — Doenças Fúngicas da Videira",
        fonte_url="https://www.embrapa.br/uva-e-vinho",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": "<=", "valor": 70.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": "<=", "valor": 1.0, "peso": 0.15},
        ],
    ),
    _referencia(
        "Uva",
        "Podridão-cinzenta",
        agente_causal="Botrytis cinerea",
        fonte_parametros="Embrapa Uva e Vinho — Doenças Fúngicas da Videira",
        fonte_url="https://www.embrapa.br/uva-e-vinho",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 24.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Manga",
        "Antracnose",
        agente_causal="Colletotrichum gloeosporioides",
        fonte_parametros="Embrapa Semiárido — Doenças da Mangueira",
        fonte_url="https://www.embrapa.br/semiarido",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Manga",
        "Oídio-da-mangueira",
        agente_causal="Oidium mangiferae",
        fonte_parametros="Embrapa Semiárido — Doenças da Mangueira",
        fonte_url="https://www.embrapa.br/semiarido",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 26.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": "<=", "valor": 70.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": "<=", "valor": 1.0, "peso": 0.15},
        ],
    ),
    # -----------------------------------------------------------------------
    # HORTALIÇAS (16 modelos — 8 culturas)
    # -----------------------------------------------------------------------
    _referencia(
        "Tomate",
        "Requeima",
        agente_causal="Phytophthora infestans",
        fonte_parametros="Embrapa Hortaliças — Doenças do Tomateiro",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 24.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Tomate",
        "Pinta-preta",
        agente_causal="Alternaria solani / Alternaria linariae",
        fonte_parametros="Embrapa Hortaliças — Doenças do Tomateiro",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 24.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Batata",
        "Requeima",
        agente_causal="Phytophthora infestans",
        fonte_parametros="Embrapa Hortaliças — Doenças da Batateira",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 12.0, "max": 20.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Batata",
        "Pinta-preta",
        agente_causal="Alternaria grandis / Alternaria solani",
        fonte_parametros="Embrapa Hortaliças — Doenças da Batateira",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 24.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cebola",
        "Míldio-da-cebola",
        agente_causal="Peronospora destructor",
        fonte_parametros="Embrapa Hortaliças — Doenças da Cebola",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 12.0, "max": 21.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cebola",
        "Mancha-púrpura",
        agente_causal="Alternaria porri",
        fonte_parametros="Embrapa Hortaliças — Doenças da Cebola",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 21.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cenoura",
        "Queima-das-folhas",
        agente_causal="Alternaria dauci / Cercospora carotae",
        fonte_parametros="Embrapa Hortaliças — Queima-das-folhas da Cenoura",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 16.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Alface",
        "Míldio-da-alface",
        agente_causal="Bremia lactucae",
        fonte_parametros="Embrapa Hortaliças — Doenças da Alface",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 12.0, "max": 20.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Alface",
        "Mofo-branco",
        agente_causal="Sclerotinia sclerotiorum",
        fonte_parametros="Embrapa Hortaliças — Doenças da Alface",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Pimenta",
        "Antracnose",
        agente_causal="Colletotrichum spp.",
        fonte_parametros="Embrapa Hortaliças — Doenças de Capsicum",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 23.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Pimenta",
        "Oídio",
        agente_causal="Leveillula taurica",
        fonte_parametros="Embrapa Hortaliças — Doenças de Capsicum",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 26.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": "<=", "valor": 70.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": "<=", "valor": 1.0, "peso": 0.15},
        ],
    ),
    _referencia(
        "Pepino",
        "Míldio-das-cucurbitáceas",
        agente_causal="Pseudoperonospora cubensis",
        fonte_parametros="Embrapa Hortaliças — Doenças de Cucurbitáceas",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 16.0, "max": 22.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Pepino",
        "Oídio-das-cucurbitáceas",
        agente_causal="Podosphaera xanthii",
        fonte_parametros="Embrapa Hortaliças — Doenças de Cucurbitáceas",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 26.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": "<=", "valor": 70.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": "<=", "valor": 1.0, "peso": 0.15},
        ],
    ),
    _referencia(
        "Brócolis",
        "Podridão-negra",
        agente_causal="Xanthomonas campestris pv. campestris",
        fonte_parametros="Embrapa Hortaliças — Doenças de Brássicas",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 32.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Brócolis",
        "Mancha-de-alternária",
        agente_causal="Alternaria brassicicola / Alternaria brassicae",
        fonte_parametros="Embrapa Hortaliças — Doenças de Brássicas",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Brócolis",
        "Míldio-das-brássicas",
        agente_causal="Hyaloperonospora parasitica",
        fonte_parametros="Embrapa Hortaliças — Doenças de Brássicas",
        fonte_url="https://www.embrapa.br/hortalicas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 10.0, "max": 20.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    # -----------------------------------------------------------------------
    # PASTAGEM (7 modelos — 6 culturas)
    # -----------------------------------------------------------------------
    _referencia(
        "Braquiária",
        "Mela / Queima-das-folhas",
        agente_causal="Rhizoctonia solani (AG-1 IA)",
        fonte_parametros="Embrapa Gado de Corte — Doenças de Forrageiras Tropicais",
        fonte_url="https://www.embrapa.br/gado-de-corte",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 30.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Brizantha",
        "Mela / Queima-das-folhas",
        agente_causal="Rhizoctonia solani (AG-1 IA)",
        fonte_parametros="Embrapa Gado de Corte — Doenças de Forrageiras Tropicais",
        fonte_url="https://www.embrapa.br/gado-de-corte",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 25.0, "max": 30.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Mombaça",
        "Mancha-foliar",
        agente_causal="Bipolaris maydis",
        fonte_parametros="Embrapa Gado de Corte — Doenças em Megathyrsus maximus",
        fonte_url="https://www.embrapa.br/gado-de-corte",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Tanzânia",
        "Mancha-foliar",
        agente_causal="Bipolaris maydis",
        fonte_parametros="Embrapa Gado de Corte — Doenças em Megathyrsus maximus",
        fonte_url="https://www.embrapa.br/gado-de-corte",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Aries",
        "Ferrugem-da-folha",
        agente_causal="Puccinia coronata f. sp. avenae",
        fonte_parametros="Embrapa Trigo — Doenças de Aveias Forrageiras",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Azevém",
        "Brusone-do-azevém",
        agente_causal="Pyricularia oryzae / Pyricularia grisea",
        fonte_parametros="Embrapa Trigo — Doenças de Forrageiras de Inverno",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Azevém",
        "Ferrugem-da-folha",
        agente_causal="Puccinia coronata",
        fonte_parametros="Embrapa Trigo — Doenças de Forrageiras de Inverno",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    # -----------------------------------------------------------------------
    # OUTROS (14 modelos — 7 culturas)
    # -----------------------------------------------------------------------
    _referencia(
        "Cana-de-Açúcar",
        "Ferrugem-alaranjada",
        agente_causal="Puccinia kuehnii",
        fonte_parametros="Embrapa Meio Ambiente — Favorabilidade Climática de Ferrugens da Cana",
        fonte_url="https://www.embrapa.br/meio-ambiente",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 19.0, "max": 26.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Cana-de-Açúcar",
        "Ferrugem-marrom",
        agente_causal="Puccinia melanocephala",
        fonte_parametros="Embrapa Meio Ambiente — Favorabilidade Climática de Ferrugens da Cana",
        fonte_url="https://www.embrapa.br/meio-ambiente",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 28.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Café",
        "Ferrugem do Cafeeiro",
        agente_causal="Hemileia vastatrix",
        fonte_parametros="Embrapa Café — Sistemas de Produção 1 (MG)",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1148365/1/Sistemas-de-Producao-1-Cafe.pdf#page=59",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Café",
        "Cercosporiose",
        agente_causal="Cercospora coffeicola",
        fonte_parametros="Embrapa Café — Sistemas de Produção 1 / UFV Infectário",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1148365/1/Sistemas-de-Producao-1-Cafe.pdf#page=61",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 25.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 1.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Café",
        "Mancha-de-phoma",
        agente_causal="Phoma tarda / Phoma spp.",
        fonte_parametros="Embrapa Café — Sistemas de Produção 1 (MG)",
        fonte_url="https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1148365/1/Sistemas-de-Producao-1-Cafe.pdf",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 12.0, "max": 21.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Eucalipto",
        "Ferrugem-do-eucalipto",
        agente_causal="Austropuccinia psidii",
        fonte_parametros="Embrapa Florestas — Zoneamento da Ferrugem do Eucalipto",
        fonte_url="https://www.embrapa.br/florestas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 25.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Eucalipto",
        "Mancha-de-cylindrocladium",
        agente_causal="Calonectria spp. / Cylindrocladium candelabrum",
        fonte_parametros="Embrapa Florestas — Doenças Foliares do Eucalipto",
        fonte_url="https://www.embrapa.br/florestas",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 22.0, "max": 30.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 80.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Mandioca",
        "Antracnose",
        agente_causal="Colletotrichum gloeosporioides f. sp. manihotis",
        fonte_parametros="Embrapa Mandioca e Fruticultura — Doenças da Mandioca",
        fonte_url="https://www.embrapa.br/mandioca-e-fruticultura",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Girassol",
        "Mancha-de-alternária",
        agente_causal="Alternariaster helianthi / Alternaria helianthi",
        fonte_parametros="Embrapa Soja — Doenças do Girassol",
        fonte_url="https://www.embrapa.br/soja",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 24.0, "max": 30.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Girassol",
        "Mofo-branco",
        agente_causal="Sclerotinia sclerotiorum",
        fonte_parametros="Embrapa Soja — Doenças do Girassol",
        fonte_url="https://www.embrapa.br/soja",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 18.0, "max": 23.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
    _referencia(
        "Amendoim",
        "Mancha-preta",
        agente_causal="Nothopassalora personata / Cercosporidium personatum",
        fonte_parametros="Embrapa Algodão — Doenças Foliares do Amendoim",
        fonte_url="https://www.embrapa.br/algodao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 20.0, "max": 26.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Amendoim",
        "Mancha-castanha",
        agente_causal="Passalora arachidicola / Cercospora arachidicola",
        fonte_parametros="Embrapa Algodão — Doenças Foliares do Amendoim",
        fonte_url="https://www.embrapa.br/algodao",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 16.0, "max": 25.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 90.0, "peso": 0.40},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Canola",
        "Canela-preta",
        agente_causal="Leptosphaeria maculans",
        fonte_parametros="Embrapa Trigo — Manejo de Doenças da Canola",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 14.0, "max": 24.0, "peso": 0.45},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 2.0, "peso": 0.20},
        ],
    ),
    _referencia(
        "Canola",
        "Podridão-de-esclerotínia",
        agente_causal="Sclerotinia sclerotiorum",
        fonte_parametros="Embrapa Trigo — Manejo de Doenças da Canola",
        fonte_url="https://www.embrapa.br/trigo",
        condicoes=[
            {"variavel": "temp_media_c", "operador": "between", "min": 15.0, "max": 22.0, "peso": 0.40},
            {"variavel": "umidade_rel_pct", "operador": ">=", "valor": 85.0, "peso": 0.35},
            {"variavel": "precipitacao_mm", "operador": ">=", "valor": 3.0, "peso": 0.25},
        ],
    ),
)


def _validar_catalogo_base() -> None:
    """Valida todas as entradas do catálogo antes de iniciar qualquer escrita.

    Args:
        Nenhum.

    Returns:
        Nenhum.

    Raises:
        ValueError: Se alguma regra do catálogo possuir formato inválido.
    """
    for item in MODELOS_FITOSSANITARIOS_BASE:
        regras = item.get("regras_risco")
        if not isinstance(regras, dict):
            raise ValueError("regras_risco deve ser um objeto JSON")
        validar_regras_fitossanitarias(regras)


def _eh_modelo_global_legado(modelo: ModeloFitossanitario) -> bool:
    """Identifica registros globais legados sem `metadados.fonte_parametros`.

    Args:
        modelo: Entidade ORM global inspecionada.

    Returns:
        True quando o modelo não possui metadados válidos de proveniência.
    """
    regras = modelo.regras_risco
    if not isinstance(regras, dict):
        return True
    metadados = regras.get("metadados")
    if not isinstance(metadados, dict):
        return True
    return not str(metadados.get("fonte_parametros") or "").strip()


def _validar_ambiente_para_limpeza() -> None:
    """Impede substituição de modelos globais em produção.

    Raises:
        RuntimeError: Se APP_ENV ou settings.environment indicar produção.
    """
    ambientes = (
        os.environ.get("APP_ENV", "").strip().lower(),
        str(settings.environment or "").strip().lower(),
    )
    if any(env in {"production", "prod"} for env in ambientes):
        raise RuntimeError("--replace-legacy-globals não é permitido em produção.")


async def _fetch_chaves_globais_existentes(session) -> set[tuple[str, str]]:
    """Consulta chaves (cultura, doenca) globais existentes respeitando RLS.

    Args:
        session: Sessão SQLAlchemy assíncrona ativa.

    Returns:
        Conjunto de tuplas (cultura, doenca) já cadastradas com tenant_id nulo.
    """
    await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
    result = await session.execute(
        select(
            ModeloFitossanitario.cultura,
            ModeloFitossanitario.doenca,
        ).where(ModeloFitossanitario.tenant_id.is_(None))
    )
    return {tuple(row) for row in result.all()}


async def _carregar_estado_global(
    session,
    replace_legacy_globals: bool,
) -> tuple[set[tuple[str, str]], list[ModeloFitossanitario]]:
    """Retorna chaves globais mantidas e eventuais modelos legados a substituir.

    Args:
        session: Sessão SQLAlchemy assíncrona ativa.
        replace_legacy_globals: Se True, separa modelos legados sem metadados.

    Returns:
        Tupla (chaves_mantidas, modelos_legados_para_remocao).
    """
    if not replace_legacy_globals:
        return await _fetch_chaves_globais_existentes(session), []

    await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
    result = await session.execute(
        select(ModeloFitossanitario).where(ModeloFitossanitario.tenant_id.is_(None))
    )
    globais = list(result.scalars().all())
    legados = [modelo for modelo in globais if _eh_modelo_global_legado(modelo)]
    mantidas = {
        (modelo.cultura, modelo.doenca)
        for modelo in globais
        if not _eh_modelo_global_legado(modelo)
    }
    return mantidas, legados


def _construir_modelo_global(item: dict[str, object]) -> ModeloFitossanitario:
    """Instancia um modelo fitossanitário global a partir do catálogo-base.

    Args:
        item: Dicionário validado de `MODELOS_FITOSSANITARIOS_BASE`.

    Returns:
        Instância ORM pronta para persistência.
    """
    return ModeloFitossanitario(
        tenant_id=None,
        is_global=True,
        cultura=str(item["cultura"]),
        doenca=str(item["doenca"]),
        regras_risco=copy.deepcopy(item["regras_risco"]),
    )


async def _persistir_alteracoes_modelos(
    session,
    legados: list[ModeloFitossanitario],
    pendentes: list[dict[str, object]],
) -> None:
    """Remove legados com flush prévio e persiste modelos pendentes na transação.

    Args:
        session: Sessão SQLAlchemy assíncrona ativa.
        legados: Lista de modelos globais sem metadados a remover.
        pendentes: Lista de modelos-base a inserir.

    Raises:
        RuntimeError: Se o RLS bloquear a escrita global na tabela.
        Exception: Propaga erro de persistência após executar rollback.
    """
    try:
        for legado in legados:
            await session.delete(legado)
        if legados:
            await session.flush()
        for item in pendentes:
            session.add(_construir_modelo_global(item))
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if "row-level security policy" in str(exc).lower():
            raise RuntimeError(
                "Escrita global bloqueada pelo RLS em modelos_fitossanitarios. "
                "Execute `alembic upgrade head` (migration 20261119_rls_global_catalog_admin_write) "
                "ou configure CATALOG_ADMIN_DATABASE_URL com uma role administrativa autorizada."
            ) from exc
        raise


async def _executar_carga_modelos(
    session,
    *,
    dry_run: bool = False,
    replace_legacy_globals: bool = False,
) -> tuple[int, int, int]:
    """Executa a carga (ou prévia) retornando inseridos, existentes e removidos.

    Args:
        session: Sessão SQLAlchemy assíncrona ativa.
        dry_run: Quando verdadeiro, apenas contabiliza sem gravar no banco.
        replace_legacy_globals: Remove globais legados sem metadados antes de inserir.

    Returns:
        Tupla (quantidade_inserida, quantidade_ja_existente, quantidade_removida).

    Raises:
        ValueError: Se alguma entrada falhar na validação estrutural.
        RuntimeError: Se `replace_legacy_globals` for acionado em produção ou bloqueado por RLS.
    """
    if replace_legacy_globals:
        _validar_ambiente_para_limpeza()
    _validar_catalogo_base()
    existentes, legados = await _carregar_estado_global(session, replace_legacy_globals)
    pendentes = [
        item
        for item in MODELOS_FITOSSANITARIOS_BASE
        if (str(item["cultura"]), str(item["doenca"])) not in existentes
    ]
    total_base = len(MODELOS_FITOSSANITARIOS_BASE)
    if not dry_run and (pendentes or legados):
        await _persistir_alteracoes_modelos(session, legados, pendentes)
    return len(pendentes), total_base - len(pendentes), len(legados)


async def _seed_modelos_fitossanitarios(
    session,
    *,
    dry_run: bool = False,
    replace_legacy_globals: bool = False,
) -> tuple[int, int]:
    """Insere modelos fitossanitários globais ausentes sem sobrescrever existentes.

    Args:
        session: Sessão SQLAlchemy assíncrona ativa.
        dry_run: Quando verdadeiro, apenas contabiliza sem persistir alterações.
        replace_legacy_globals: Remove globais legados sem metadados antes de inserir.

    Returns:
        Tupla (quantidade_inserida, quantidade_ja_existente).

    Raises:
        ValueError: Se alguma entrada falhar na validação estrutural.
        RuntimeError: Se bloqueado em produção ou por RLS.
        Exception: Propaga erro de persistência após executar rollback.
    """
    inseridos, existentes, _ = await _executar_carga_modelos(
        session,
        dry_run=dry_run,
        replace_legacy_globals=replace_legacy_globals,
    )
    return inseridos, existentes


def _imprimir_resumo_carga(
    contagens: tuple[int, int, int],
    *,
    dry_run: bool = False,
) -> None:
    """Exibe resumo da carga ou prévia para o operador.

    Args:
        contagens: Tupla (inseridos, existentes, removidos).
        dry_run: Indica se a execução foi apenas simulação sem escrita.
    """
    inseridos, existentes, removidos = contagens
    if dry_run:
        detalhe_legados = f"{removidos} legados a remover, " if removidos > 0 else ""
        print(
            f"[DRY-RUN] Prévia concluída (nada foi gravado no banco): "
            f"{detalhe_legados}{inseridos} modelos pendentes para inserção "
            f"({existentes} já existiam). Execute novamente sem --dry-run para gravar."
        )
        return
    detalhe_legados = f"{removidos} legados removidos, " if removidos > 0 else ""
    print(
        f"Carga de modelos-base fitossanitários concluída: "
        f"{detalhe_legados}{inseridos} inseridos ({existentes} já existiam)."
    )


async def seed(
    *,
    dry_run: bool = False,
    replace_legacy_globals: bool = False,
) -> tuple[int, int]:
    """Executa a carga inicial opcional dos modelos fitossanitários globais.

    Args:
        dry_run: Quando verdadeiro, apenas calcula a prévia sem gravar no banco.
        replace_legacy_globals: Remove globais legados sem metadados fora de produção.

    Returns:
        Tupla (quantidade_inserida, quantidade_ja_existente).
    """
    if replace_legacy_globals:
        _validar_ambiente_para_limpeza()

    from sqlalchemy.orm import configure_mappers

    from core.model_registry import register_models

    register_models()
    configure_mappers()

    session_factory = catalog_admin_async_session_maker or async_session_maker
    async with session_factory() as session:
        contagens = await _executar_carga_modelos(
            session,
            dry_run=dry_run,
            replace_legacy_globals=replace_legacy_globals,
        )

    _imprimir_resumo_carga(contagens, dry_run=dry_run)
    return contagens[0], contagens[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="simula a verificação de modelos pendentes sem gravar no banco",
    )
    parser.add_argument(
        "--replace-legacy-globals",
        action="store_true",
        help=(
            "remove modelos globais legados sem metadados.fonte_parametros "
            "antes de inserir os modelos atualizados (bloqueado em produção)"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        seed(
            dry_run=args.dry_run,
            replace_legacy_globals=args.replace_legacy_globals,
        )
    )
