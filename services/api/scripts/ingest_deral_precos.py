"""Compatibilidade segura para o comando legado de ingestão DERAL.

Este módulo não grava snapshots. Use ``scripts/atualizar_snapshot_deral.py``,
que valida e publica os 21 preços homologados de forma atômica.
"""

from __future__ import annotations

import sys


def main() -> None:
    """Interrompe o fluxo legado antes de qualquer leitura ou escrita."""
    print(
        "Fluxo legado desativado: use scripts/atualizar_snapshot_deral.py.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
