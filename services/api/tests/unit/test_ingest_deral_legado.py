"""Proteção contra reativação acidental do fluxo DERAL legado."""

from __future__ import annotations

import pytest

from scripts.ingest_deral_precos import main


def test_fluxo_legado_encerra_sem_gravar() -> None:
    """O entrypoint legado deve orientar para o atualizador canônico."""
    with pytest.raises(SystemExit) as erro:
        main()
    assert erro.value.code == 2
