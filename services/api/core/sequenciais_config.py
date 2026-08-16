"""Registry central de códigos de referência (sequenciais legíveis).

Estes códigos cumprem, para efeitos de comunicação humana (telefone, e-mail,
WhatsApp com fornecedor/cliente), o mesmo papel que o `id` (UUID) cumpre como
chave primária no banco: identificam de forma única e definitiva um registro
dentro do tenant. Diferença: são curtos, sequenciais e "faláveis".

Para adicionar uma nova entidade com código de referência, basta registrar
uma entrada aqui — nenhuma migration nova é necessária além da tabela
genérica `core_sequenciais` (já existente). Ver core/services/sequencial_service.py.

Formato gerado: "{prefixo}-{ano}-{numero:0Nd}" (escopo ANO) ou
"{prefixo}-{numero:0Nd}" (escopo GLOBAL).
"""

SEQUENCIAL_CONFIG: dict[str, dict] = {
    "compras_solicitacao": {"prefixo": "SOL", "escopo": "ANO", "digitos": 6, "label": "Solicitação de compra"},
    "compras_cotacao": {"prefixo": "COT", "escopo": "ANO", "digitos": 6, "label": "Cotação de compra"},
    "compras_pedido": {"prefixo": "PED", "escopo": "ANO", "digitos": 6, "label": "Pedido de compra"},
    "estoque_requisicao": {"prefixo": "REQ", "escopo": "ANO", "digitos": 6, "label": "Requisição de material"},
    "manutencao_benfeitoria_os": {"prefixo": "OSB", "escopo": "ANO", "digitos": 6, "label": "Ordem de serviço de manutenção de benfeitoria"},
}
