import uuid
import pytest
from pydantic import ValidationError

from agricola.operacoes.schemas import (
    InsumoOperacaoCreate,
    OperacaoAgricolaCreate,
    OperacaoAgricolaUpdate,
)


def test_operacao_create_rejeita_area_aplicada_vazia():
    with pytest.raises(ValidationError):
        OperacaoAgricolaCreate(
            safra_id=uuid.uuid4(),
            talhao_id=uuid.uuid4(),
            tipo="PULVERIZACAO",
            descricao="Aplicacao foliar",
            data_realizada="2026-05-24",
            area_aplicada_ha="",
        )


def test_operacao_update_aceita_area_aplicada_vazia_como_none():
    payload = OperacaoAgricolaUpdate(area_aplicada_ha="")

    assert payload.area_aplicada_ha is None


def test_operacao_create_aceita_cultivo_id():
    cultivo_id = uuid.uuid4()
    payload = OperacaoAgricolaCreate(
        safra_id=uuid.uuid4(),
        talhao_id=uuid.uuid4(),
        cultivo_id=cultivo_id,
        tipo="PULVERIZACAO",
        descricao="Aplicacao foliar",
        data_realizada="2026-05-24",
        area_aplicada_ha=5,
    )

    assert payload.cultivo_id == cultivo_id


def test_insumo_create_aceita_area_aplicada_vazia_como_none():
    payload = InsumoOperacaoCreate(
        produto_id=uuid.uuid4(),
        dose_por_ha=1.5,
        unidade="L",
        area_aplicada="",
    )

    assert payload.area_aplicada is None
