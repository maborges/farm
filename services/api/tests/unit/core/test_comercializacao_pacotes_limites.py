"""
Testes unitários para o modelo de comercialização por pacotes:
1. Limite de tamanho da propriedade (hectares) em UnidadeProdutivaService e AreaRuralService
2. Controle de licenças de acesso simultâneo (SessaoAtiva) e cadastro livre de equipe
3. Composição da mensalidade (preço base do pacote + tabela de preços de acessos adicionais por pacote)
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from core.exceptions import BusinessRuleError
from core.models.billing import PlanoAssinatura
from core.models.plan_changes import PlanoPricing


class TestLimiteHectaresPropriedade:
    """Valida o bloqueio por limite_hectares do plano em UnidadeProdutivaService."""

    async def test_check_limite_hectares_abaixo_do_limite_permite(self):
        from core.services.unidade_produtiva_service import UnidadeProdutivaService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        svc = UnidadeProdutivaService(session=session, tenant_id=tenant_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                res.scalar_one_or_none = MagicMock(return_value=Decimal("500.00"))
            else:
                res.scalar_one = MagicMock(return_value=Decimal("300.00"))
            return res

        session.execute = mock_execute

        await svc._check_limite_hectares(Decimal("150.00"))

    async def test_check_limite_hectares_acima_do_limite_bloqueia(self):
        from core.services.unidade_produtiva_service import UnidadeProdutivaService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        svc = UnidadeProdutivaService(session=session, tenant_id=tenant_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                res.scalar_one_or_none = MagicMock(return_value=Decimal("500.00"))
            else:
                res.scalar_one = MagicMock(return_value=Decimal("400.00"))
            return res

        session.execute = mock_execute

        with pytest.raises(BusinessRuleError) as exc_info:
            await svc._check_limite_hectares(Decimal("150.00"))

        assert "500" in str(exc_info.value)
        assert "hectares" in str(exc_info.value).lower() or "ha" in str(exc_info.value).lower()

    async def test_check_limite_hectares_plano_ilimitado_permite(self):
        from core.services.unidade_produtiva_service import UnidadeProdutivaService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        svc = UnidadeProdutivaService(session=session, tenant_id=tenant_id)

        res = MagicMock()
        res.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=res)

        await svc._check_limite_hectares(Decimal("99999.00"))


class TestLimiteHectaresTalhoesAreaRural:
    """Valida que a soma de talhões (AreaRural) respeita o limite da propriedade e do pacote."""

    async def test_talhao_excede_limite_hectares_do_plano_bloqueia(self):
        from core.cadastros.propriedades.models import AreaRural
        from core.cadastros.propriedades.service import AreaRuralService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        up_id = uuid.uuid4()
        svc = AreaRuralService(AreaRural, session, tenant_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                # 1ª consulta: área total da UnidadeProdutiva (ex: None ou 1000 ha)
                res.first = MagicMock(return_value=(Decimal("1000.00"), None))
            elif call_count == 2:
                # 2ª consulta: soma atual do mesmo tipo na UnidadeProdutiva (300 ha)
                res.scalar_one = MagicMock(return_value=Decimal("300.00"))
            elif call_count == 3:
                # 3ª consulta: limite_hectares do plano (500 ha)
                res.scalar_one_or_none = MagicMock(return_value=Decimal("500.00"))
            else:
                # 4ª consulta: soma atual do mesmo tipo no tenant inteiro (450 ha)
                res.scalar_one = MagicMock(return_value=Decimal("450.00"))
            return res

        session.execute = mock_execute

        with pytest.raises(BusinessRuleError) as exc_info:
            await svc._validar_limite_hectares_area(
                unidade_produtiva_id=up_id,
                tipo="TALHAO",
                nova_area_ha=Decimal("100.00"),
            )

        assert "500" in str(exc_info.value)

    async def test_talhao_excede_area_da_propriedade_bloqueia(self):
        from core.cadastros.propriedades.models import AreaRural
        from core.cadastros.propriedades.service import AreaRuralService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        up_id = uuid.uuid4()
        svc = AreaRuralService(AreaRural, session, tenant_id)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                # 1ª consulta: área total da UnidadeProdutiva (200 ha)
                res.first = MagicMock(return_value=(Decimal("200.00"), None))
            else:
                # 2ª consulta: soma atual dos talhões na propriedade (180 ha)
                res.scalar_one = MagicMock(return_value=Decimal("180.00"))
            return res

        session.execute = mock_execute

        with pytest.raises(BusinessRuleError) as exc_info:
            await svc._validar_limite_hectares_area(
                unidade_produtiva_id=up_id,
                tipo="TALHAO",
                nova_area_ha=Decimal("50.00"),
            )

        assert "200" in str(exc_info.value)


class TestControleAcessoSimultaneo:
    """Valida controle de sessões simultâneas e liberação de cadastro de equipe."""

    async def test_bloqueia_login_quando_licencas_simultaneas_esgotadas(self):
        from core.services.auth_service import AuthService

        session = AsyncMock()
        svc = AuthService(session)
        tenant_id = uuid.uuid4()
        usuario_id = uuid.uuid4()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count in (1, 2):
                # 1: UPDATE sessoes expiradas; 2: UPDATE sessoes anteriores do próprio usuário
                return res
            elif call_count == 3:
                # 3: Assinatura (usuarios_contratados=2, limite_usuarios_maximo=5, limite_usuarios_minimo=2)
                res.first = MagicMock(return_value=(2, 5, 2))
                return res
            else:
                # 4: Contagem de sessões ativas simultâneas no tenant = 2 (atingiu o limite de 2)
                res.scalar_one = MagicMock(return_value=2)
                return res

        session.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await svc._verificar_disponibilidade_licenca_simultanea(tenant_id, usuario_id)

        assert exc_info.value.status_code == 403
        assert "licença" in exc_info.value.detail.lower() or "simultâneo" in exc_info.value.detail.lower()

    async def test_permite_login_quando_ha_licenca_simultanea_disponivel(self):
        from core.services.auth_service import AuthService

        session = AsyncMock()
        svc = AuthService(session)
        tenant_id = uuid.uuid4()
        usuario_id = uuid.uuid4()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count in (1, 2):
                return res
            elif call_count == 3:
                res.first = MagicMock(return_value=(3, 5, 2))
                return res
            else:
                res.scalar_one = MagicMock(return_value=2)
                return res

        session.execute = mock_execute

        await svc._verificar_disponibilidade_licenca_simultanea(tenant_id, usuario_id)


class TestComposicaoMensalidadePacoteAcessosAdicionais:
    """Valida a composição da mensalidade: preço do pacote + acessos contratados a mais."""

    async def test_preco_apenas_pacote_sem_acessos_adicionais(self):
        from core.services.plan_pricing_service import PlanoPricingService

        session = AsyncMock()
        svc = PlanoPricingService(session)
        plano_id = uuid.uuid4()

        plano = PlanoAssinatura(
            id=plano_id,
            nome="Pacote Básico",
            preco_mensal=Decimal("497.00"),
            preco_anual=Decimal("4970.00"),
            limite_usuarios_minimo=2,
            limite_usuarios_maximo=10,
            limite_hectares=Decimal("500.00"),
            ativo=True,
        )

        res_plano = MagicMock()
        res_plano.scalar_one_or_none = MagicMock(return_value=plano)
        session.execute = AsyncMock(return_value=res_plano)

        valor_total, detalhamento = await svc.calcular_preco_total(
            plano_id=plano_id,
            quantidade_usuarios=2,
            ciclo="MENSAL",
        )

        assert valor_total == Decimal("497.00")
        assert len(detalhamento) == 1
        assert detalhamento[0]["valor_faixa"] == 497.0

    async def test_preco_composto_pacote_mais_acessos_adicionais_em_faixas(self):
        from core.services.plan_pricing_service import PlanoPricingService

        session = AsyncMock()
        svc = PlanoPricingService(session)
        plano_id = uuid.uuid4()

        # Pacote inclui 2 acessos por R$ 497,00/mês
        plano = PlanoAssinatura(
            id=plano_id,
            nome="Pacote Básico",
            preco_mensal=Decimal("497.00"),
            preco_anual=Decimal("4970.00"),
            limite_usuarios_minimo=2,
            limite_usuarios_maximo=20,
            limite_hectares=Decimal("500.00"),
            ativo=True,
        )

        # Tabela de preços de quantidade contratada a mais (por pacote):
        # 1 a 3 acessos adicionais: R$ 50,00/mês cada
        # 4 a 10 acessos adicionais: R$ 40,00/mês cada
        faixas = [
            PlanoPricing(
                id=uuid.uuid4(),
                plano_id=plano_id,
                faixa_inicio=1,
                faixa_fim=3,
                preco_por_usuario_mensal=Decimal("50.00"),
                preco_por_usuario_anual=Decimal("500.00"),
                ativo=True,
            ),
            PlanoPricing(
                id=uuid.uuid4(),
                plano_id=plano_id,
                faixa_inicio=4,
                faixa_fim=10,
                preco_por_usuario_mensal=Decimal("40.00"),
                preco_por_usuario_anual=Decimal("400.00"),
                ativo=True,
            ),
        ]

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                res.scalar_one_or_none = MagicMock(return_value=plano)
            else:
                scalars_mock = MagicMock()
                scalars_mock.all = MagicMock(return_value=faixas)
                res.scalars = MagicMock(return_value=scalars_mock)
            return res

        session.execute = mock_execute

        # Contratando 7 acessos totais -> 2 inclusos no pacote + 5 adicionais
        # 5 adicionais = 3 na faixa 1-3 (3 * 50 = 150) + 2 na faixa 4-10 (2 * 40 = 80) = R$ 230,00
        # Total esperado = R$ 497,00 + R$ 230,00 = R$ 727,00
        valor_total, detalhamento = await svc.calcular_preco_total(
            plano_id=plano_id,
            quantidade_usuarios=7,
            ciclo="MENSAL",
        )

        assert valor_total == Decimal("727.00")
        assert len(detalhamento) == 3
        assert detalhamento[0]["valor_faixa"] == 497.0
        assert detalhamento[1]["usuarios_nesta_faixa"] == 3
        assert detalhamento[1]["valor_faixa"] == 150.0
        assert detalhamento[2]["usuarios_nesta_faixa"] == 2
        assert detalhamento[2]["valor_faixa"] == 80.0


class TestMudancaPlanoExpansaoFazendaFatura:
    """Valida a composição da diferença de mensalidade/anuidade e geração de fatura ao expandir fazenda e/ou usuários."""

    async def test_simulacao_upgrade_tamanho_propriedade_e_usuarios_compoe_diferenca_mensal_e_proporcional(self):
        """
        Cenário:
        - Assinante tem Pacote P (500 ha, R$ 490/mês, 2 acessos inclusos, 2 contratados -> R$ 490,00).
        - Faz upgrade por expansão de fazenda para Pacote M (1.500 ha, R$ 990/mês, 3 acessos inclusos)
          e contrata 5 acessos simultâneos (3 inclusos + 2 extras a R$ 60/mês cada = R$ 1.110,00).
        - Faltam 15 dias em um ciclo de 30 dias.
        - Diferença mensal composta = 1110 - 490 = R$ 620,00.
        - Valor proporcional da fatura imediata = 620 * 15 / 30 = R$ 310,00.
        """
        from datetime import datetime, timedelta, timezone
        from core.services.mudanca_plano_service import MudancaPlanoService

        tenant_id = uuid.uuid4()
        plano_p_id = uuid.uuid4()
        plano_m_id = uuid.uuid4()
        assinatura_id = uuid.uuid4()

        session = AsyncMock()
        svc = MudancaPlanoService(session, tenant_id=tenant_id)

        agora = datetime.now(timezone.utc)
        assinatura = MagicMock()
        assinatura.id = assinatura_id
        assinatura.tenant_id = tenant_id
        assinatura.plano_id = plano_p_id
        assinatura.usuarios_contratados = 2
        assinatura.ciclo_pagamento = "MENSAL"
        assinatura.status = "ATIVA"
        assinatura.data_proxima_renovacao = agora + timedelta(days=15)

        plano_p = MagicMock()
        plano_p.id = plano_p_id
        plano_p.nome = "Pacote 500 ha"
        plano_p.ativo = True
        plano_p.preco_mensal = Decimal("490.00")
        plano_p.preco_anual = Decimal("4900.00")
        plano_p.limite_hectares = Decimal("500.00")
        plano_p.limite_usuarios_minimo = 2
        plano_p.limite_usuarios_maximo = 10
        plano_p.modulos_inclusos = ["CORE"]

        plano_m = MagicMock()
        plano_m.id = plano_m_id
        plano_m.nome = "Pacote 1500 ha"
        plano_m.ativo = True
        plano_m.preco_mensal = Decimal("990.00")
        plano_m.preco_anual = Decimal("9900.00")
        plano_m.limite_hectares = Decimal("1500.00")
        plano_m.limite_usuarios_minimo = 3
        plano_m.limite_usuarios_maximo = 20
        plano_m.modulos_inclusos = ["CORE", "A1_PLANEJAMENTO"]

        faixa_m = MagicMock()
        faixa_m.faixa_inicio = 1
        faixa_m.faixa_fim = 10
        faixa_m.preco_por_usuario_mensal = Decimal("60.00")
        faixa_m.preco_por_usuario_anual = Decimal("600.00")

        svc._obter_assinatura = AsyncMock(return_value=assinatura)
        svc._obter_plano = AsyncMock(side_effect=lambda pid: plano_p if pid == plano_p_id else plano_m)
        svc._validar_compatibilidade_hectares_destino = AsyncMock(return_value=Decimal("480.00"))
        svc.pricing_service.calcular_diferenca_planos = AsyncMock(
            return_value={
                "valor_atual": Decimal("490.00"),
                "detalhes_atual": [
                    {
                        "tipo": "PACOTE_BASE",
                        "faixa_inicio": 1,
                        "faixa_fim": 2,
                        "usuarios_nesta_faixa": 2,
                        "preco_unitario": 490.0,
                        "valor_faixa": 490.0,
                    }
                ],
                "valor_novo": Decimal("1110.00"),
                "detalhes_novo": [
                    {
                        "tipo": "PACOTE_BASE",
                        "faixa_inicio": 1,
                        "faixa_fim": 3,
                        "usuarios_nesta_faixa": 3,
                        "preco_unitario": 990.0,
                        "valor_faixa": 990.0,
                    },
                    {
                        "tipo": "ACESSO_ADICIONAL",
                        "faixa_inicio": 1,
                        "faixa_fim": 10,
                        "usuarios_nesta_faixa": 2,
                        "preco_unitario": 60.0,
                        "valor_faixa": 120.0,
                    },
                ],
                "diferenca": Decimal("620.00"),
                "percentual_diferenca": 126.53,
                "ciclo": "MENSAL",
            }
        )

        resultado = await svc.simular_mudanca(
            plano_destino_id=plano_m_id,
            usuarios_destino=5,
        )

        assert resultado["tipo_mudanca"] == "UPGRADE_COMPLETO"
        assert resultado["valor_atual_mensal"] == 490.0
        assert resultado["valor_novo_mensal"] == 1110.0
        assert resultado["diferenca_mensal"] == 620.0
        assert resultado["valor_proporcional"] == 310.0
        assert len(resultado["detalhes_novo"]) == 2

    async def test_bloqueia_mudanca_para_pacote_com_limite_hectares_menor_que_area_atual(self):
        """
        Se o assinante possui 800 ha de propriedades ativas cadastradas e tenta mudar
        para um pacote cujo limite_hectares é 500 ha, deve lançar BusinessRuleError.
        """
        from core.services.mudanca_plano_service import MudancaPlanoService

        tenant_id = uuid.uuid4()
        session = AsyncMock()
        svc = MudancaPlanoService(session, tenant_id=tenant_id)

        plano_destino = MagicMock()
        plano_destino.nome = "Pacote 500 ha"
        plano_destino.limite_hectares = Decimal("500.00")

        res_soma = MagicMock()
        res_soma.scalar_one = MagicMock(return_value=Decimal("800.00"))
        session.execute = AsyncMock(return_value=res_soma)

        with pytest.raises(BusinessRuleError) as exc_info:
            await svc._validar_compatibilidade_hectares_destino(plano_destino)

        assert "800.00" in str(exc_info.value)
        assert "500.00" in str(exc_info.value)

    async def test_solicitar_mudanca_gera_fatura_complementar_com_diferenca(self):
        """
        Ao solicitar um upgrade (de tamanho de propriedade e/ou quantidade de acessos),
        além do registro MudancaPlano deve ser gerada a Fatura complementar com o valor
        da diferença apurada para pagamento.
        """
        from datetime import datetime, timedelta, timezone
        from core.models.billing import Fatura
        from core.services.mudanca_plano_service import MudancaPlanoService

        tenant_id = uuid.uuid4()
        usuario_id = uuid.uuid4()
        plano_origem_id = uuid.uuid4()
        plano_destino_id = uuid.uuid4()
        assinatura_id = uuid.uuid4()

        session = AsyncMock()
        added_objects = []
        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        # Sem fatura aberta em trial
        res_fatura = MagicMock()
        res_fatura.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=res_fatura)

        svc = MudancaPlanoService(session, tenant_id=tenant_id)
        agora = datetime.now(timezone.utc)
        assinatura = MagicMock()
        assinatura.id = assinatura_id
        assinatura.tenant_id = tenant_id
        assinatura.plano_id = plano_origem_id
        assinatura.usuarios_contratados = 2
        assinatura.ciclo_pagamento = "MENSAL"
        assinatura.status = "ATIVA"
        assinatura.data_proxima_renovacao = agora + timedelta(days=15)

        svc._validar_mudanca_pendente = AsyncMock(return_value=None)
        svc._obter_assinatura = AsyncMock(return_value=assinatura)
        svc.simular_mudanca = AsyncMock(
            return_value={
                "tipo_mudanca": "UPGRADE_COMPLETO",
                "dias_restantes_ciclo": 15,
                "valor_atual_mensal": 490.0,
                "valor_novo_mensal": 1110.0,
                "diferenca_mensal": 620.0,
                "valor_proporcional": 310.0,
                "ciclo": "MENSAL",
            }
        )

        await svc.solicitar_mudanca(
            plano_destino_id=plano_destino_id,
            usuarios_destino=5,
            usuario_solicitante_id=usuario_id,
        )

        faturas_criadas = [obj for obj in added_objects if isinstance(obj, Fatura)]
        assert len(faturas_criadas) == 1
        assert Decimal(str(faturas_criadas[0].valor)) == Decimal("310.00")
        assert faturas_criadas[0].status == "ABERTA"


class TestNovaPoliticaCincoPerfisAllInHectaresEquivalentes:
    """
    Valida a nova política comercial:
    - 5 perfis (Familiar, Pequeno Produtor, Médio Produtor, Grande Produtor, Grupo) com 100% dos módulos
    - Desconto anual no pacote (2 meses grátis) + 20% OFF nas licenças adicionais de acesso simultâneo
    - Hectares Equivalentes: isenção ambiental (APP/RL), múltiplas culturas, consórcio/safrinha sem duplicação e ILP
    - Aplicativo Campo isento de acesso simultâneo
    - Integração Stripe com line_items compostos
    """

    def test_cinco_pacotes_oficiais_possuem_todos_os_modulos_e_tier_enterprise(self):
        from core.constants import ALL_MODULES
        from scripts.initial_load.seed_plans import PLANOS_INICIAIS

        nomes = [p["nome"] for p in PLANOS_INICIAIS]
        assert nomes == [
            "Familiar",
            "Pequeno Produtor",
            "Médio Produtor",
            "Grande Produtor",
            "Grupo",
        ]
        for plano in PLANOS_INICIAIS:
            assert plano["plan_tier"] == "ENTERPRISE"
            assert set(plano["modulos_inclusos"]) == set(ALL_MODULES)
            assert plano["preco_anual"] == plano["preco_mensal"] * Decimal("10")

    async def test_desconto_20_porcento_anual_em_licencas_adicionais_de_usuario(self):
        from core.services.plan_pricing_service import PlanoPricingService
        from scripts.initial_load.seed_plans import PLANOS_INICIAIS

        session = AsyncMock()
        svc = PlanoPricingService(session)

        # Médio Produtor: R$ 1.197/mês (R$ 11.970/ano), inclui 5 acessos, máx 15
        # Adicionais: faixa 1-5 = R$ 110/mês ou R$ 1.056/ano (20% OFF sobre R$ 1.320)
        dados_medio = next(p for p in PLANOS_INICIAIS if p["nome"] == "Médio Produtor")
        plano_medio = PlanoAssinatura(**dados_medio)

        res_plano = MagicMock()
        res_plano.scalar_one_or_none = MagicMock(return_value=plano_medio)
        scalars_empty = MagicMock()
        scalars_empty.all = MagicMock(return_value=[])
        res_empty = MagicMock()
        res_empty.scalars = MagicMock(return_value=scalars_empty)

        session.execute = AsyncMock(side_effect=[res_plano, res_empty, res_plano, res_empty])

        # 8 acessos simultâneos = 5 inclusos + 3 adicionais
        total_mensal, _ = await svc.calcular_preco_total(plano_medio.id, 8, "MENSAL")
        total_anual, det_anual = await svc.calcular_preco_total(plano_medio.id, 8, "ANUAL")

        # Mensal: 1197 + (3 * 110) = 1527.00
        assert total_mensal == Decimal("1527.00")
        # Anual: 11970 + (3 * 1056) = 11970 + 3168 = 15138.00
        assert total_anual == Decimal("15138.00")
        assert det_anual[1]["preco_unitario"] == 1056.0

    async def test_area_ambiental_app_e_reserva_legal_isentas_do_limite_do_pacote(self):
        from core.cadastros.propriedades.models import AreaRural
        from core.cadastros.propriedades.service import AreaRuralService

        session = AsyncMock()
        tenant_id = uuid.uuid4()
        up_id = uuid.uuid4()
        svc = AreaRuralService(AreaRural, session, tenant_id)

        # Propriedade tem 1.000 ha totais; APP tem 0 ha cadastrados
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            res = MagicMock()
            if call_count == 1:
                res.first = MagicMock(return_value=(Decimal("1000.00"), None))
            else:
                res.scalar_one = MagicMock(return_value=Decimal("0.00"))
            return res

        session.execute = mock_execute

        # Mesmo que o pacote fosse Familiar (100 ha), cadastrar 250 ha de RESERVA_LEGAL ou APP é 100% isento e não consulta nem bloqueia no plano
        await svc._validar_limite_hectares_area(
            unidade_produtiva_id=up_id,
            tipo="RESERVA_LEGAL",
            nova_area_ha=Decimal("250.00"),
        )
        await svc._validar_limite_hectares_area(
            unidade_produtiva_id=up_id,
            tipo="APP",
            nova_area_ha=Decimal("100.00"),
        )
        assert call_count == 0

    def test_hectares_equivalentes_multicultura_consorcio_safrinha_e_ilp(self):
        from core.services.plan_pricing_service import PlanoPricingService

        # Fazenda com 1.000 ha físicos, sendo 200 ha de Reserva Legal/APP (isentos -> 800 ha líquidos)
        # Talhão 1 (500 ha): Soja (verão, 1.0x) + Milho Safrinha (inverno, 1.0x) + Braquiária consorciada (0.5x)
        #   -> NÃO duplica área física! Deve contar 500 ha * 1.0 = 500 HEq.
        # Talhão 2 (100 ha): Café Arábica (2.5x) -> 250 HEq.
        # Talhão 3 (200 ha): Pastagem (0.5x) -> 100 HEq.
        # Pecuária integrada (ILP): 1.200 cabeças (como 800 ha produtivos suportam até 1.600 cabeças a 2 cab/ha, 0 HEq extra!)
        resultado = PlanoPricingService.calcular_hectares_equivalentes_operacao(
            {
                "area_total_ha": Decimal("1000.00"),
                "area_ambiental_ha": Decimal("200.00"),
                "cabecas_pecuaria": 1200,
                "talhoes_culturas": [
                    {"talhao_id": "T1", "safra_id": "S26", "area_ha": 500, "cultura": "SOJA", "consorciado": False},
                    {"talhao_id": "T1", "safra_id": "S26", "area_ha": 500, "cultura": "MILHO", "consorciado": False},
                    {"talhao_id": "T1", "safra_id": "S26", "area_ha": 500, "cultura": "BRAQUIARIA", "consorciado": True},
                    {"talhao_id": "T2", "safra_id": "S26", "area_ha": 100, "cultura": "CAFE", "consorciado": False},
                    {"talhao_id": "T3", "safra_id": "S26", "area_ha": 200, "cultura": "PASTAGEM", "consorciado": False},
                ],
            }
        )

        assert resultado["hectares_fisicos_total"] == 1000.0
        assert resultado["hectares_ambientais_isentos"] == 200.0
        assert resultado["hectares_produtivos_liquidos"] == 800.0
        # 500 (T1) + 250 (T2) + 100 (T3) = 850 HEq
        assert resultado["hectares_equivalentes_agricola"] == 850.0
        assert resultado["hectares_equivalentes_pecuaria_excedente"] == 0.0
        assert resultado["hectares_equivalentes_total"] == 850.0

    async def test_acesso_aplicativo_campo_isento_de_simultaneidade(self):
        from core.services.auth_service import AuthService

        session = AsyncMock()
        svc = AuthService(session)

        # Mesmo sem mocks de banco, escopo_produto='campo' retorna imediatamente sem consumir SessaoAtiva
        await svc._verificar_disponibilidade_licenca_simultanea(
            tenant_id=uuid.uuid4(),
            usuario_id=uuid.uuid4(),
            escopo_produto="campo",
        )
        session.execute.assert_not_called()

    def test_stripe_montar_line_items_compostos_pacote_e_usuarios_adicionais(self):
        from core.services.stripe_service import StripeService

        detalhamento = [
            {
                "tipo": "PACOTE_BASE",
                "faixa_inicio": 1,
                "faixa_fim": 5,
                "usuarios_nesta_faixa": 5,
                "preco_unitario": 11970.0,
                "valor_faixa": 11970.0,
            },
            {
                "tipo": "ACESSO_ADICIONAL",
                "faixa_inicio": 1,
                "faixa_fim": 5,
                "usuarios_nesta_faixa": 3,
                "preco_unitario": 1056.0,
                "valor_faixa": 3168.0,
            },
        ]
        items = StripeService.montar_line_items_compostos(
            detalhamento_preco=detalhamento,
            nome_plano="Médio Produtor",
            ciclo="ANUAL",
        )
        assert len(items) == 2
        assert items[0]["price_data"]["unit_amount"] == 1197000
        assert items[0]["price_data"]["recurring"]["interval"] == "year"
        assert items[0]["quantity"] == 1
        assert items[1]["price_data"]["unit_amount"] == 105600
        assert items[1]["quantity"] == 3

    def test_extensoes_iot_e_erp_contratadas_a_parte_fora_de_all_modules(self):
        from core.constants import (
            ALL_MODULES,
            EXTENSOES_CONTRATADAS_A_PARTE,
            TABELA_EXTENSOES_A_PARTE,
            Modulos,
        )

        assert Modulos.EXTENSAO_IOT_SENSORES in EXTENSOES_CONTRATADAS_A_PARTE
        assert Modulos.EXTENSAO_ERP_BRIDGE in EXTENSOES_CONTRATADAS_A_PARTE
        assert Modulos.EXTENSAO_IOT_SENSORES not in ALL_MODULES
        assert Modulos.EXTENSAO_ERP_BRIDGE not in ALL_MODULES
        assert TABELA_EXTENSOES_A_PARTE[Modulos.EXTENSAO_IOT_SENSORES]["preco_mensal"] == 599.0
        assert TABELA_EXTENSOES_A_PARTE[Modulos.EXTENSAO_ERP_BRIDGE]["preco_mensal"] == 1299.0

    async def test_webhook_stripe_renovacao_paga_e_suspensao_por_inadimplencia(self, monkeypatch):
        from core.routers import stripe_webhooks

        tenant = MagicMock()
        tenant.id = uuid.uuid4()
        tenant.ativo = False

        assinatura = MagicMock()
        assinatura.id = uuid.uuid4()
        assinatura.tenant_id = tenant.id
        assinatura.ciclo_pagamento = "MENSAL"
        assinatura.status = "SUSPENSA"
        assinatura.stripe_subscription_id = "sub_contrato_123"
        assinatura.data_bloqueio = None
        assinatura.data_proxima_renovacao = None

        fatura = MagicMock()
        fatura.status = "ABERTA"
        fatura.valor = Decimal("497.00")

        db_mock = AsyncMock()
        res_sub = MagicMock()
        res_sub.scalar_one_or_none = MagicMock(return_value=assinatura)
        db_mock.execute = AsyncMock(return_value=res_sub)
        db_mock.get = AsyncMock(return_value=tenant)

        class DummySessionCtx:
            async def __aenter__(self):
                return db_mock

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(stripe_webhooks, "async_session_maker", lambda: DummySessionCtx())
        monkeypatch.setattr(
            stripe_webhooks,
            "_load_subscription_invoices",
            AsyncMock(return_value=[fatura]),
        )

        # 1. Pagamento recorrente (invoice.paid) -> renova contrato e ativa tenant
        ok_paid = await stripe_webhooks._handle_invoice_paid(
            {"subscription": "sub_contrato_123", "amount_paid": 49700}
        )
        assert ok_paid is True
        assert assinatura.status == "ATIVA"
        assert tenant.ativo is True
        assert fatura.status == "PAGA"
        assert assinatura.data_proxima_renovacao is not None

        # 2. Inadimplência recorrente (invoice.payment_failed) -> suspende contrato e tenant
        fatura.status = "ABERTA"
        ok_failed = await stripe_webhooks._handle_invoice_payment_failed(
            {"subscription": "sub_contrato_123", "amount_due": 49700}
        )
        assert ok_failed is True
        assert assinatura.status == "SUSPENSA"
        assert assinatura.data_bloqueio is not None
        assert tenant.ativo is False
        assert fatura.status == "VENCIDA"





