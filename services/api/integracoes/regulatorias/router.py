"""
Router de integrações regulatórias — endpoints proxy para APIs externas.
Autenticado (requer JWT válido) mas sem restrição de tenant específico.
"""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.dependencies import get_current_user_claims
from core.utils.cpf_cnpj import validar_cnpj as _validar_cnpj
from core.utils.cpf_cnpj import validar_cpf
from integracoes.regulatorias.service import (
    consultar_car,
    consultar_cep,
    consultar_cnpj,
    validar_formato_car,
)

router = APIRouter(tags=["Integrações Regulatórias"])


# ---------------------------------------------------------------------------
# Schemas de resposta
# ---------------------------------------------------------------------------


class CepResponse(BaseModel):
    cep: str
    logradouro: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None
    ibge_municipio_codigo: str | None = None


class CnpjResponse(BaseModel):
    cnpj: str
    razao_social: str | None = None
    nome_fantasia: str | None = None
    situacao_cadastral: str | None = None
    tipo: str | None = None
    cep: str | None = None
    logradouro: str | None = None
    bairro: str | None = None
    municipio: str | None = None
    uf: str | None = None


class CarResponse(BaseModel):
    car_codigo: str
    status: str | None = None
    status_descricao: str | None = None
    area_ha: float | None = None
    municipio: str | None = None
    uf: str | None = None
    data_cadastro: str | None = None


class CpfValidacaoResponse(BaseModel):
    cpf: str
    valido: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/cep/{cep}", response_model=CepResponse, summary="Consulta endereço pelo CEP")
async def get_cep(
    cep: str,
    _: dict = Depends(get_current_user_claims),
):
    """Consulta endereço pelo CEP via BrasilAPI (fallback ViaCEP)."""
    dados = await consultar_cep(cep)
    if not dados:
        raise HTTPException(status_code=404, detail=f"CEP '{cep}' não encontrado.")
    return CepResponse(**dados)


@router.get(
    "/cnpj/{cnpj}", response_model=CnpjResponse, summary="Consulta dados da empresa pelo CNPJ"
)
async def get_cnpj(
    cnpj: str,
    _: dict = Depends(get_current_user_claims),
):
    """Consulta dados da empresa via BrasilAPI. Valida dígitos verificadores antes de consultar."""
    if not _validar_cnpj(cnpj):
        raise HTTPException(
            status_code=422, detail="CNPJ inválido (dígitos verificadores incorretos)."
        )

    dados = await consultar_cnpj(cnpj)
    if not dados:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado na Receita Federal.")
    return CnpjResponse(**dados)


@router.get("/cpf/{cpf}/validar", response_model=CpfValidacaoResponse, summary="Valida CPF")
async def validar_cpf_endpoint(
    cpf: str,
    _: dict = Depends(get_current_user_claims),
):
    """Valida CPF usando algoritmo oficial (sem consulta externa)."""
    valido = validar_cpf(cpf)
    import re

    cpf_limpo = re.sub(r"\D", "", cpf)
    return CpfValidacaoResponse(cpf=cpf_limpo, valido=valido)


@router.get(
    "/car/{car_codigo:path}", response_model=CarResponse, summary="Consulta imóvel no SICAR/IBAMA"
)
async def get_car(
    car_codigo: str,
    _: dict = Depends(get_current_user_claims),
):
    """
    Consulta dados do imóvel rural no SICAR pelo código CAR.
    Formato esperado: UF-XXXXXXX-XXXX.XXXX.XXXX/XXXX-XX
    """
    if not validar_formato_car(car_codigo):
        raise HTTPException(
            status_code=422,
            detail="Formato de CAR inválido. Esperado: UF-XXXXXXX-XXXX.XXXX.XXXX/XXXX-XX",
        )

    dados = await consultar_car(car_codigo)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="CAR não encontrado no SICAR ou serviço indisponível. Preencha os dados manualmente.",
        )
    return CarResponse(**dados)
