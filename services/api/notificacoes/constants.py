"""Mapeamento de visibilidade de notificações por RBAC.

Notificacao é tenant-wide por desenho (sem destinatário — `usuario_id` sempre
None na criação). Este módulo define qual permissão de tenant é necessária
para um usuário VER uma notificação de um dado `tipo`, evitando que qualquer
usuário do tenant enxergue notificações de domínios que não lhe dizem
respeito (ex.: operador de campo vendo alertas financeiros).

Tipos ausentes deste mapeamento são de propósito geral e permanecem SEMPRE
visíveis (ex.: RECOMENDACAO, PLANO_ACAO, RESUMO_DIARIO) — não é preciso
listá-los aqui, o tratamento padrão de `permissao_necessaria_para_tipo` já
retorna None (= visível) para qualquer tipo não mapeado.

Owner do tenant (`is_owner=True`) sempre vê tudo — `resolver_permissao_usuario`
já trata isso internamente, não há lógica especial adicional aqui.
"""

# Tipos exatos (sem prefixo múltiplo) -> permissão necessária.
# Checados primeiro, antes dos prefixos, para não colidir com nenhum prefixo.
TIPO_EXATO_PERMISSAO_VISIBILIDADE: dict[str, str] = {
    "ALERTA_FINANCEIRO": "financeiro:*",
    "DIARIA_PENDENTE": "rh:*",
    "ALERTA_AGRICOLA": "agricola:*",
    "ALERTA_NDE": "agricola:*",
    "NDVI_BAIXO": "agricola:*",
    "PREVISAO_CHUVA": "agricola:*",
    "VENCIMENTO_APLICACAO": "agricola:*",
    "CARENCIA_DEFENSIVO": "agricola:*",
    "OPORTUNIDADE": "operacional:*",
    "WORKFLOW_OPERACIONAL": "operacional:*",
}

# Prefixos de tipo -> permissão necessária. Checados por `tipo.startswith(prefixo)`.
TIPO_PREFIXO_PERMISSAO_VISIBILIDADE: dict[str, str] = {
    "FINANCEIRO_": "financeiro:*",
    "HEDGE_": "financeiro:*",
    "CAMPO_": "campo:*",
    "ESG_": "certificacoes_esg:*",
    "PECUARIA_": "pecuaria:*",
    "AGRICULTURA_": "agricola:*",
    "CLIMA_": "agricola:*",
    "ESTOQUE_": "operacional:*",
}


def permissao_necessaria_para_tipo(tipo: str) -> str | None:
    """Retorna a permissão de tenant necessária para VER uma notificação deste tipo.

    Retorna None quando o tipo não está mapeado — nesse caso a notificação é
    sempre visível a qualquer usuário do tenant (comportamento atual, mantido
    para tipos de propósito geral como RECOMENDACAO/PLANO_ACAO/RESUMO_DIARIO).
    """
    if not tipo:
        return None
    permissao_exata = TIPO_EXATO_PERMISSAO_VISIBILIDADE.get(tipo)
    if permissao_exata is not None:
        return permissao_exata
    for prefixo, permissao in TIPO_PREFIXO_PERMISSAO_VISIBILIDADE.items():
        if tipo.startswith(prefixo):
            return permissao
    return None
