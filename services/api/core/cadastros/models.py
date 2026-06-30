# Compatibilidade legada. Não usar como fonte canônica em novos fluxos.
# ProdutoCatalogo permanece apenas como alias histórico de Produto.
from core.cadastros.produtos.models import (
    Produto as ProdutoCatalogo,
    ProdutoAgricola as ProdutoAgricolaDetalhe,
    ProdutoEstoque as ProdutoEstoqueDetalhe,
)

__all__ = ["ProdutoCatalogo", "ProdutoAgricolaDetalhe", "ProdutoEstoqueDetalhe"]
