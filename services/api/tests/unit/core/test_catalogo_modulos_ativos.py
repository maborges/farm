"""
Testes unitários do controle de ativação do catálogo de módulos:
1. Módulos inativos não aparecem nos pacotes (modulos_inclusos filtrados).
2. Extensões IoT e ERP inativas não podem ser selecionadas/contratadas.
3. O módulo CORE é sempre mantido e não pode ser desativado.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.constants import (
    EXTENSOES_CONTRATADAS_A_PARTE,
    ModuloMetadata,
    Modulos,
    carregar_overrides_catalogo_modulos,
)


class TestFiltroModulosAtivos:
    """Valida o filtro de módulos ativos aplicado aos pacotes."""

    def test_modulo_sem_override_esta_ativo(self):
        assert ModuloMetadata.is_modulo_ativo(Modulos.AGRICOLA_PLANEJAMENTO) is True

    def test_modulo_com_override_inativo_e_removido_do_pacote(self):
        overrides = {Modulos.PECUARIA_LEITE: {"ativo": False}}
        modulos = [Modulos.CORE, Modulos.PECUARIA_REBANHO, Modulos.PECUARIA_LEITE]

        resultado = ModuloMetadata.filtrar_modulos_ativos(modulos, overrides)

        assert Modulos.PECUARIA_LEITE not in resultado
        assert Modulos.PECUARIA_REBANHO in resultado

    def test_core_sempre_mantido_mesmo_com_override_inativo(self):
        overrides = {Modulos.CORE: {"ativo": False}}

        assert ModuloMetadata.is_modulo_ativo(Modulos.CORE, overrides) is True
        assert Modulos.CORE in ModuloMetadata.filtrar_modulos_ativos([], overrides)

    def test_extensoes_a_parte_nao_entram_nos_pacotes(self):
        modulos = [Modulos.CORE, *EXTENSOES_CONTRATADAS_A_PARTE]

        resultado = ModuloMetadata.filtrar_modulos_ativos(modulos, {})

        assert all(ext not in resultado for ext in EXTENSOES_CONTRATADAS_A_PARTE)

    def test_modulo_inexistente_e_considerado_inativo(self):
        assert ModuloMetadata.is_modulo_ativo("MODULO_FANTASMA") is False

    def test_lista_vazia_retorna_apenas_core(self):
        assert ModuloMetadata.filtrar_modulos_ativos([], {}) == [Modulos.CORE]


class TestExtensoesIotErpAtivacao:
    """Valida o status das extensões IoT e ERP."""

    def test_extensoes_ativas_por_padrao(self):
        extensoes = ModuloMetadata.obter_extensoes_a_parte({})

        assert {e["id"] for e in extensoes} == set(EXTENSOES_CONTRATADAS_A_PARTE)
        assert all(e["ativo"] is True for e in extensoes)

    def test_extensao_iot_inativa_reportada_como_indisponivel(self):
        overrides = {Modulos.EXTENSAO_IOT_SENSORES: {"ativo": False}}

        extensoes = {e["id"]: e for e in ModuloMetadata.obter_extensoes_a_parte(overrides)}

        assert extensoes[Modulos.EXTENSAO_IOT_SENSORES]["ativo"] is False
        assert extensoes[Modulos.EXTENSAO_ERP_BRIDGE]["ativo"] is True

    def test_preco_anual_extensao_aplica_20_porcento(self):
        extensoes = {e["id"]: e for e in ModuloMetadata.obter_extensoes_a_parte({})}

        assert extensoes[Modulos.EXTENSAO_IOT_SENSORES]["preco_anual"] == pytest.approx(5750.4)


class TestCarregarOverridesCatalogo:
    """Valida a leitura dos overrides persistidos no Backoffice."""

    async def test_sem_sessao_retorna_vazio(self):
        assert await carregar_overrides_catalogo_modulos(None) == {}

    async def test_le_overrides_da_configuracao(self):
        config = MagicMock()
        config.valor = {Modulos.EXTENSAO_ERP_BRIDGE: {"ativo": False}}
        session = MagicMock()
        session.scalar = AsyncMock(return_value=config)

        overrides = await carregar_overrides_catalogo_modulos(session)

        assert overrides[Modulos.EXTENSAO_ERP_BRIDGE]["ativo"] is False

    async def test_falha_na_leitura_retorna_vazio(self):
        session = MagicMock()
        session.scalar = AsyncMock(side_effect=RuntimeError("db offline"))

        assert await carregar_overrides_catalogo_modulos(session) == {}

