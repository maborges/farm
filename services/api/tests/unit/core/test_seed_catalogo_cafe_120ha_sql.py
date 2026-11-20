from __future__ import annotations

import re
from pathlib import Path


SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "initial_load"
    / "sql"
    / "seed_catalogo_cafe_120ha.sql"
)


def _seed_source() -> str:
    return SEED_PATH.read_text(encoding="utf-8")


def test_seed_catalogo_cafe_tem_codigos_unicos_e_cobertura_operacional():
    source = _seed_source()
    codes = re.findall(r"'((?:CAF|EPI|MAT|COMB)-[A-Z0-9-]+)'", source)

    assert len(codes) >= 40
    assert len(codes) == len(set(codes))
    assert {
        "CAF-FERT-CALCARIO",
        "CAF-FERT-UREIA",
        "CAF-FUN-FERRUGEM",
        "CAF-INS-BICHO-MINEIRO",
        "CAF-HERB-POS-EMERGENCIA",
        "CAF-BIO-TRICHODERMA",
        "EPI-RESP-PFF2",
        "MAT-COLHEITA-PANO",
        "MAT-COLHEITA-BIGBAG",
        "COMB-DIESEL-S10",
    }.issubset(codes)


def test_seed_catalogo_cafe_nao_fixa_marcas_registros_ou_recomendacoes_de_uso():
    source = _seed_source().lower()

    assert "registro_mapa" not in source
    assert "principio_ativo" not in source
    assert "bayer" not in source
    assert "responsável técnico" in source
