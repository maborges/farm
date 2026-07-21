"""Contrato oficial das operações Sankhya expostas pelo adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

LOAD_RECORDS_SERVICE = "CRUDServiceProvider.loadRecords"


class SankhyaGatewayAuthorizationError(PermissionError):
    """Indicar que o Gateway autenticou, mas bloqueou o serviço ou entidade."""


@dataclass(frozen=True)
class SankhyaGatewayOperation:
    """Descrever uma operação do adapter sobre o Gateway Sankhya."""

    entity: str
    fields: tuple[str, ...]
    result_key: str
    aliases: dict[str, str] = field(default_factory=dict)
    criteria: str | None = None
    parameters: tuple[dict[str, str], ...] = ()
    module: str = "mge"
    service_name: str = LOAD_RECORDS_SERVICE
    id_field: str | None = None


GATEWAY_OPERATIONS = {
    ("PessoaFisica", "findAll"): SankhyaGatewayOperation(
        entity="Parceiro",
        fields=(
            "CODPARC",
            "NOMEPARC",
            "TIPPESSOA",
            "CGC_CPF",
            "EMAIL",
            "TELEFONE",
            "CEP",
            "IDENTINSCESTAD",
            "ATIVO",
        ),
        criteria="TIPPESSOA = ?",
        parameters=({"$": "F", "type": "S"},),
        result_key="pessoas",
        aliases={"NOMEPARC": "NOME", "IDENTINSCESTAD": "INSCRICAO"},
        id_field="CODPARC",
    ),
    ("PessoaJuridica", "findAll"): SankhyaGatewayOperation(
        entity="Parceiro",
        fields=(
            "CODPARC",
            "NOMEPARC",
            "RAZAOSOCIAL",
            "TIPPESSOA",
            "CGC_CPF",
            "EMAIL",
            "TELEFONE",
            "CEP",
            "IDENTINSCESTAD",
            "ATIVO",
        ),
        criteria="TIPPESSOA = ?",
        parameters=({"$": "J", "type": "S"},),
        result_key="pessoas",
        aliases={
            "NOMEPARC": "NOME",
            "RAZAOSOCIAL": "NOMEFANTASIA",
            "IDENTINSCESTAD": "INSCRICAO",
        },
        id_field="CODPARC",
    ),
    ("Produto", "findAll"): SankhyaGatewayOperation(
        entity="Produto",
        fields=("CODPROD", "DESCRPROD", "REFERENCIA", "NCM", "CODVOL", "ATIVO"),
        result_key="produtos",
        aliases={"CODVOL": "UNIDADE", "REFERENCIA": "COMPLEMENTO"},
        id_field="CODPROD",
    ),
}


def resolve_gateway_operation(service: str, method: str) -> SankhyaGatewayOperation:
    """Obter uma operação homologada ou falhar antes de consumir URL externa."""
    operation = GATEWAY_OPERATIONS.get((service, method))
    if operation is None:
        raise ValueError(f"Operação {service}.{method} não mapeada para o Gateway Sankhya.")
    return operation


def build_gateway_service_url(base_url: str, operation: SankhyaGatewayOperation) -> str:
    """Resolver a URL oficial do módulo sem reutilizar paths arbitrários da base."""
    parsed = urlsplit(base_url)
    prefix = parsed.path.split("/gateway/v1", maxsplit=1)[0].rstrip("/")
    path = f"{prefix}/gateway/v1/{operation.module}/service.sbr"
    query = urlencode({"serviceName": operation.service_name, "outputType": "json"})
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


def operation_public_metadata(operation: SankhyaGatewayOperation) -> dict[str, Any]:
    """Publicar apenas metadados não sensíveis usados pela tela de configuração."""
    return {
        "module": operation.module,
        "service_name": operation.service_name,
        "entity": operation.entity,
        "path": f"/gateway/v1/{operation.module}/service.sbr",
        "query": {"serviceName": operation.service_name, "outputType": "json"},
    }
