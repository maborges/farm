"""Catálogo de colunas, mapeamento automático e templates de importação da Pecuária."""

from __future__ import annotations

from typing import Literal

from pecuaria.schemas.importacao_schema import CampoMapeavelInfo, TipoImportacaoPecuaria
from pecuaria.services.planilha_parser import (
    gerar_csv_bytes,
    gerar_xlsx_bytes,
    normalizar_texto_chave,
)

CAMPOS_POR_TIPO: dict[str, tuple[CampoMapeavelInfo, ...]] = {
    "LOTES": (
        CampoMapeavelInfo(chave="identificacao", rotulo="Identificação do Lote", obrigatorio=True, descricao="Nome ou código único do lote na fazenda"),
        CampoMapeavelInfo(chave="modo_gestao", rotulo="Modo de Gestão", obrigatorio=False, descricao="POR_LOTE (padrão) ou INDIVIDUAL"),
        CampoMapeavelInfo(chave="categoria", rotulo="Categoria", obrigatorio=True, descricao="Ex: Novilhos, Bezerros, Vacas, Recria"),
        CampoMapeavelInfo(chave="raca", rotulo="Raça", obrigatorio=True, descricao="Ex: Nelore, Angus, Brangus, Mestiço"),
        CampoMapeavelInfo(chave="quantidade_cabecas", rotulo="Qtd. Cabeças", obrigatorio=False, descricao="Obrigatório (>= 1) no modo POR_LOTE"),
        CampoMapeavelInfo(chave="peso_medio_kg", rotulo="Peso Médio Atual (kg)", obrigatorio=False, descricao="Peso médio vivo em kg"),
        CampoMapeavelInfo(chave="peso_inicial_medio_kg", rotulo="Peso Inicial Médio (kg)", obrigatorio=False, descricao="Referência inicial para arrobas produzidas"),
        CampoMapeavelInfo(chave="rendimento_carcaca_pct", rotulo="Rendimento Carcaça (%)", obrigatorio=False, descricao="Entre 30% e 70% (padrão 50%)"),
        CampoMapeavelInfo(chave="valor_aquisicao_total", rotulo="Valor Aquisição Total (R$)", obrigatorio=False, descricao="Investimento total na aquisição do lote"),
        CampoMapeavelInfo(chave="cotacao_arroba_override", rotulo="Cotação Manual (R$/@)", obrigatorio=False, descricao="Opcional; em branco usa referência pública"),
        CampoMapeavelInfo(chave="piquete", rotulo="Piquete / Pasto", obrigatorio=False, descricao="Nome exato do piquete cadastrado na fazenda"),
        CampoMapeavelInfo(chave="data_formacao", rotulo="Data Formação", obrigatorio=False, descricao="DD/MM/AAAA ou AAAA-MM-DD"),
        CampoMapeavelInfo(chave="observacoes", rotulo="Observações", obrigatorio=False, descricao="Notas adicionais"),
    ),
    "ANIMAIS": (
        CampoMapeavelInfo(chave="numero_brinco", rotulo="Nº Brinco", obrigatorio=True, descricao="Ao menos Brinco, SISBOV ou Microchip"),
        CampoMapeavelInfo(chave="numero_sisbov", rotulo="SISBOV", obrigatorio=False, descricao="Código SISBOV opcional"),
        CampoMapeavelInfo(chave="microchip", rotulo="Microchip", obrigatorio=False, descricao="Identificador eletrônico opcional"),
        CampoMapeavelInfo(chave="nome", rotulo="Nome", obrigatorio=False, descricao="Nome ou apelido do animal"),
        CampoMapeavelInfo(chave="lote", rotulo="Lote", obrigatorio=False, descricao="Identificação do lote na fazenda"),
        CampoMapeavelInfo(chave="especie", rotulo="Espécie", obrigatorio=False, descricao="BOVINO (padrão), OVINO, CAPRINO, etc."),
        CampoMapeavelInfo(chave="categoria", rotulo="Categoria", obrigatorio=True, descricao="BEZERRO, BEZERRA, GARROTE, NOVILHA, BOI, VACA_CORTE, etc."),
        CampoMapeavelInfo(chave="sexo", rotulo="Sexo", obrigatorio=False, descricao="MACHO, FEMEA ou CASTRADO (inferido se omitido)"),
        CampoMapeavelInfo(chave="raca", rotulo="Raça", obrigatorio=False, descricao="Ex: Nelore, Angus"),
        CampoMapeavelInfo(chave="pelagem", rotulo="Pelagem", obrigatorio=False, descricao="Pelagem opcional"),
        CampoMapeavelInfo(chave="peso_atual_kg", rotulo="Peso Atual (kg)", obrigatorio=False, descricao="Peso vivo inicial/atual em kg"),
        CampoMapeavelInfo(chave="valor_aquisicao", rotulo="Valor Aquisição (R$)", obrigatorio=False, descricao="Valor de compra do animal"),
        CampoMapeavelInfo(chave="data_nascimento", rotulo="Data Nascimento", obrigatorio=False, descricao="DD/MM/AAAA ou AAAA-MM-DD"),
        CampoMapeavelInfo(chave="data_entrada", rotulo="Data Entrada", obrigatorio=False, descricao="Data de entrada na fazenda"),
        CampoMapeavelInfo(chave="status", rotulo="Status", obrigatorio=False, descricao="ATIVO (padrão), VENDIDO, ABATIDO, MORTO, TRANSFERIDO"),
        CampoMapeavelInfo(chave="observacoes", rotulo="Observações", obrigatorio=False, descricao="Anotações individuais"),
    ),
    "PESAGENS": (
        CampoMapeavelInfo(chave="numero_brinco", rotulo="Nº Brinco", obrigatorio=False, descricao="Para pesagem individual"),
        CampoMapeavelInfo(chave="numero_sisbov", rotulo="SISBOV", obrigatorio=False, descricao="Alternativa individual"),
        CampoMapeavelInfo(chave="microchip", rotulo="Microchip", obrigatorio=False, descricao="Alternativa individual"),
        CampoMapeavelInfo(chave="lote", rotulo="Lote", obrigatorio=False, descricao="Obrigatório em pesagem coletiva (POR_LOTE)"),
        CampoMapeavelInfo(chave="data_evento", rotulo="Data da Pesagem", obrigatorio=True, descricao="DD/MM/AAAA ou AAAA-MM-DD"),
        CampoMapeavelInfo(chave="peso_kg", rotulo="Peso Individual / Médio (kg)", obrigatorio=False, descricao="Peso em kg do animal ou média do lote"),
        CampoMapeavelInfo(chave="peso_total_kg", rotulo="Peso Total do Lote (kg)", obrigatorio=False, descricao="Soma da balança para pesagem coletiva"),
        CampoMapeavelInfo(chave="quantidade_cabecas", rotulo="Qtd. Cabeças Pesadas", obrigatorio=False, descricao="Opcional em pesagem coletiva"),
        CampoMapeavelInfo(chave="observacoes", rotulo="Observações", obrigatorio=False, descricao="Notas da sessão de curral/balança"),
    ),
}

SINONIMOS_POR_TIPO: dict[str, dict[str, tuple[str, ...]]] = {
    "LOTES": {
        "identificacao": ("identificacao", "lote", "nome_lote", "nome", "codigo_lote"),
        "modo_gestao": ("modo_gestao", "modo", "controle", "tipo_gestao"),
        "categoria": ("categoria", "cat"),
        "raca": ("raca", "raca_principal", "breed"),
        "quantidade_cabecas": ("quantidade_cabecas", "cabecas", "qtd_cabecas", "quantidade", "qtd", "animais"),
        "peso_medio_kg": ("peso_medio_kg", "peso_medio", "peso_kg", "peso"),
        "peso_inicial_medio_kg": ("peso_inicial_medio_kg", "peso_inicial", "peso_entrada"),
        "rendimento_carcaca_pct": ("rendimento_carcaca_pct", "rendimento_carcaca", "rendimento", "rc"),
        "valor_aquisicao_total": ("valor_aquisicao_total", "valor_compra", "valor_aquisicao", "custo_aquisicao"),
        "cotacao_arroba_override": ("cotacao_arroba_override", "cotacao", "cotacao_manual", "preco_arroba"),
        "piquete": ("piquete", "piquete_nome", "pasto", "pastagem", "area"),
        "data_formacao": ("data_formacao", "data", "fundacao", "data_criacao"),
        "observacoes": ("observacoes", "obs", "notas"),
    },
    "ANIMAIS": {
        "numero_brinco": ("numero_brinco", "brinco", "brinco_id", "ear_tag", "identificacao"),
        "numero_sisbov": ("numero_sisbov", "sisbov"),
        "microchip": ("microchip", "chip", "rfid"),
        "nome": ("nome", "apelido"),
        "lote": ("lote", "nome_lote", "lote_identificacao"),
        "especie": ("especie",),
        "categoria": ("categoria", "cat"),
        "sexo": ("sexo", "sex"),
        "raca": ("raca", "breed"),
        "pelagem": ("pelagem",),
        "peso_atual_kg": ("peso_atual_kg", "peso_atual", "peso", "peso_kg"),
        "valor_aquisicao": ("valor_aquisicao", "valor_compra", "preco_compra"),
        "data_nascimento": ("data_nascimento", "nascimento", "nasc"),
        "data_entrada": ("data_entrada", "entrada", "data_compra"),
        "status": ("status", "situacao"),
        "observacoes": ("observacoes", "obs", "notas"),
    },
    "PESAGENS": {
        "numero_brinco": ("numero_brinco", "brinco", "ear_tag"),
        "numero_sisbov": ("numero_sisbov", "sisbov"),
        "microchip": ("microchip", "chip", "rfid"),
        "lote": ("lote", "nome_lote", "identificacao_lote"),
        "data_evento": ("data_evento", "data_pesagem", "data"),
        "peso_kg": ("peso_kg", "peso", "peso_medio_kg", "peso_medio", "peso_vivo"),
        "peso_total_kg": ("peso_total_kg", "peso_total", "peso_lote_kg"),
        "quantidade_cabecas": ("quantidade_cabecas", "cabecas", "qtd_cabecas", "cab"),
        "observacoes": ("observacoes", "obs", "notas"),
    },
}

_TEMPLATES_DADOS: dict[str, tuple[str, list[str], list[list[object]]]] = {
    "LOTES": (
        "Lotes",
        [
            "identificacao", "modo_gestao", "categoria", "raca", "quantidade_cabecas",
            "peso_medio_kg", "peso_inicial_medio_kg", "rendimento_carcaca_pct",
            "valor_aquisicao_total", "cotacao_arroba_override", "piquete", "data_formacao", "observacoes",
        ],
        [
            ["Lote Recria 01", "POR_LOTE", "Recria", "Nelore", 50, 320, 260, 50, 110000, "", "Pasto Sede", "2026-08-01", "Desmama 2026"],
            ["Lote Engorda 02", "POR_LOTE", "Novilhos", "Angus", 30, 460, 380, 52, 96000, 320, "Pasto Confinamento", "2026-06-15", "Terminação a pasto"],
        ],
    ),
    "ANIMAIS": (
        "Animais",
        [
            "numero_brinco", "numero_sisbov", "microchip", "nome", "lote", "especie",
            "categoria", "sexo", "raca", "pelagem", "peso_atual_kg", "valor_aquisicao",
            "data_nascimento", "data_entrada", "status", "observacoes",
        ],
        [
            ["BR-1001", "", "", "Estrela", "Lote Matrizes 01", "BOVINO", "VACA_CORTE", "FEMEA", "Nelore", "Branca", 440, 4200, "2022-03-10", "2026-11-01", "ATIVO", "Matriz IATF"],
            ["BR-1002", "", "", "", "Lote Engorda Indiv", "BOVINO", "BOI", "CASTRADO", "Angus", "Preta", 510, 4800, "2023-01-20", "2026-11-01", "ATIVO", "Terminação"],
        ],
    ),
    "PESAGENS": (
        "Pesagens",
        ["numero_brinco", "numero_sisbov", "microchip", "lote", "data_evento", "peso_kg", "peso_total_kg", "quantidade_cabecas", "observacoes"],
        [
            ["BR-1001", "", "", "", "2026-11-20", 465, "", "", "Pesagem de apartação"],
            ["", "", "", "Lote Recria 01", "2026-11-20", "", 17000, 50, "Pesagem coletiva curral"],
        ],
    ),
}


def sugerir_mapeamento_colunas(
    tipo: TipoImportacaoPecuaria,
    colunas_arquivo: list[str],
    mapeamento_custom: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Sugere correspondência entre colunas da planilha e campos do sistema.

    Args:
        tipo: Tipo de importação (LOTES, ANIMAIS, PESAGENS).
        colunas_arquivo: Lista exata de cabeçalhos lidos do arquivo.
        mapeamento_custom: Sobrescrições enviadas pelo usuário na pré-visualização.

    Returns:
        Dicionário campo_sistema -> nome_coluna_arquivo (ou None).
    """
    por_chave_norm = {normalizar_texto_chave(col): col for col in colunas_arquivo if col}
    colunas_validas = set(colunas_arquivo)
    sinonimos = SINONIMOS_POR_TIPO[tipo]
    resultado: dict[str, str | None] = {}
    for campo in CAMPOS_POR_TIPO[tipo]:
        if mapeamento_custom and campo.chave in mapeamento_custom:
            escolhida = mapeamento_custom[campo.chave]
            resultado[campo.chave] = escolhida if escolhida in colunas_validas else None
            continue
        encontrada: str | None = None
        for alias in sinonimos.get(campo.chave, (campo.chave,)):
            if alias in por_chave_norm:
                encontrada = por_chave_norm[alias]
                break
        resultado[campo.chave] = encontrada
    return resultado


def gerar_template_planilha(
    tipo: TipoImportacaoPecuaria,
    formato: Literal["xlsx", "csv"] = "xlsx",
) -> tuple[bytes, str, str]:
    """Gera modelo preenchido com exemplos reais para download pelo produtor.

    Args:
        tipo: Tipo da planilha modelo.
        formato: 'xlsx' ou 'csv'.

    Returns:
        Tupla (bytes, content_type, filename).
    """
    nome_aba, headers, exemplos = _TEMPLATES_DADOS[tipo]
    slug = tipo.lower()
    if formato == "csv":
        return (
            gerar_csv_bytes(headers, exemplos),
            "text/csv; charset=utf-8",
            f"modelo-importacao-{slug}.csv",
        )
    return (
        gerar_xlsx_bytes(nome_aba, headers, exemplos),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"modelo-importacao-{slug}.xlsx",
    )
