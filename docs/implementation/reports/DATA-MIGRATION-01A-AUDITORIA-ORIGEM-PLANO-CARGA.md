# DATA-MIGRATION-01A — Auditoria da origem e plano de carga

## Veredicto

`DATA-MIGRATION-01A STATUS: GO COM RESSALVAS`

A auditoria foi executada em modo somente leitura no PostgreSQL de origem. Nenhuma tabela, constraint, policy, sequência ou registro foi alterado.

## Resumo executivo

- Origem: `351` tabelas físicas, `154` com registros, `21637` registros exatos;
- Tenants cadastrados: `2`; schema: `farms`;
- Destino: `344` tabelas da baseline;
- DIRECT_COPY: `338`; TRANSFORM: `1`; EXCLUDED: `12`; EMPTY_TARGET: `5`; REVIEW_REQUIRED: `0`;
- FK violations: `0`; Tenant violations: `0`;
- CHECK violations: `0`; UNIQUE violations: `0`; ENUM violations: `0`; NOT NULL violations: `0`.

## Inventário origem × baseline

| tabela | registros | tenant_scoped | tenant_count | destino_baseline | classificação |
| --- | ---: | --- | ---: | --- | --- |
| `admin_audit_log` | 0 | False | — | True | `DIRECT_COPY` |
| `admin_impersonations` | 0 | True | 0 | True | `DIRECT_COPY` |
| `admin_users` | 2 | False | — | True | `DIRECT_COPY` |
| `agricola_devolucoes_embalagens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `agricola_lotes_beneficiamento` | 0 | True | 0 | True | `DIRECT_COPY` |
| `agricola_operacao_tipo_fase` | 9 | False | — | True | `DIRECT_COPY` |
| `agricola_orcamento_itens` | 21 | True | 2 | True | `DIRECT_COPY` |
| `agricola_produto_colhido_cost_allocations` | 0 | True | 0 | True | `DIRECT_COPY` |
| `agricola_produtos_colhidos` | 1 | True | 1 | True | `DIRECT_COPY` |
| `agricola_receituario_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `agricola_receituarios_agronomicos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `agricola_regras_agronomicas` | 2 | True | 0 | True | `DIRECT_COPY` |
| `alembic_version` | 1 | False | — | False | `EXCLUDED` |
| `alert_events` | 0 | True | 0 | True | `DIRECT_COPY` |
| `alert_indicators` | 0 | True | 0 | True | `DIRECT_COPY` |
| `alert_insights` | 0 | True | 0 | True | `DIRECT_COPY` |
| `alert_lifecycle_events` | 0 | True | 0 | True | `DIRECT_COPY` |
| `amb_alertas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `amb_outorgas_hidricas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `amb_registros_car` | 0 | True | 0 | True | `DIRECT_COPY` |
| `amostras` | 0 | True | 0 | False | `EXCLUDED` |
| `analises_solo` | 15 | True | 2 | True | `DIRECT_COPY` |
| `animal_genetica` | 0 | True | 0 | True | `DIRECT_COPY` |
| `assinaturas_tenant` | 2 | True | 2 | True | `DIRECT_COPY` |
| `automacoes_configuracoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `automacoes_execucoes` | 6 | True | 1 | True | `DIRECT_COPY` |
| `balanca_afericoes` | 0 | True | 0 | False | `EXCLUDED` |
| `balanca_avaliacoes_prestador` | 0 | True | 0 | False | `EXCLUDED` |
| `balanca_dispositivos` | 2 | True | 1 | False | `EXCLUDED` |
| `balanca_fisicas` | 0 | True | 0 | False | `EXCLUDED` |
| `balanca_inbound_events` | 0 | True | 0 | True | `DIRECT_COPY` |
| `balanca_operadores` | 1 | True | 1 | False | `EXCLUDED` |
| `balanca_ordens` | 1 | True | 1 | False | `EXCLUDED` |
| `balanca_pesagens` | 1 | True | 1 | False | `EXCLUDED` |
| `balanca_sync_tombstones` | 0 | True | 0 | False | `EXCLUDED` |
| `balanca_webhook_credentials` | 0 | True | 0 | True | `DIRECT_COPY` |
| `billing_solicitacoes_comerciais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `billing_solicitacoes_comerciais_historico` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_areas_registros_ambientais` | 0 | False | — | True | `DIRECT_COPY` |
| `cadastros_areas_rurais` | 41 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_areas_valores_patrimoniais` | 0 | False | — | True | `DIRECT_COPY` |
| `cadastros_arquivos_geo` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_categorias_produto` | 31 | True | 1 | True | `DIRECT_COPY` |
| `cadastros_commodities` | 14 | True | 1 | True | `DIRECT_COPY` |
| `cadastros_commodities_classificacoes` | 33 | False | — | True | `DIRECT_COPY` |
| `cadastros_commodities_cotacoes` | 0 | False | — | True | `DIRECT_COPY` |
| `cadastros_conversao_unidades` | 10 | False | — | True | `DIRECT_COPY` |
| `cadastros_culturas` | 42 | True | 1 | True | `DIRECT_COPY` |
| `cadastros_documentos_exploracao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_equipamentos` | 26 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_equipamentos_calibracoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_exploracoes_rurais` | 3 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_infraestruturas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_marcas` | 34 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_modelos_produto` | 17 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_pessoa_relacionamentos` | 37 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas` | 29 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_pessoas_acesso_log` | 18 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_bancario` | 0 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_consentimentos` | 0 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_contatos` | 38 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_documentos` | 2 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_enderecos` | 1 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_pii` | 24 | False | — | True | `DIRECT_COPY` |
| `cadastros_pessoas_profissional_agronomo` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_produtos` | 52 | True | 1 | True | `DIRECT_COPY` |
| `cadastros_produtos_agricola` | 17 | False | — | True | `DIRECT_COPY` |
| `cadastros_produtos_epi` | 6 | False | — | True | `DIRECT_COPY` |
| `cadastros_produtos_estoque` | 30 | False | — | True | `DIRECT_COPY` |
| `cadastros_propriedades` | 3 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_tipos_irrigacao` | 5 | False | — | True | `DIRECT_COPY` |
| `cadastros_tipos_relacionamento` | 11 | True | 0 | True | `DIRECT_COPY` |
| `cadastros_tipos_servico` | 12 | True | 2 | True | `DIRECT_COPY` |
| `cadastros_tipos_solo` | 3 | False | — | True | `DIRECT_COPY` |
| `caderno_campo_entradas` | 54 | True | 2 | True | `DIRECT_COPY` |
| `caderno_campo_fotos` | 0 | False | — | True | `DIRECT_COPY` |
| `caderno_evento_status_historico` | 54 | True | 2 | True | `DIRECT_COPY` |
| `caderno_exportacoes` | 1 | True | 1 | True | `DIRECT_COPY` |
| `caderno_lotes_comerciais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cafe_lote_beneficiamento_detalhes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cafe_lote_beneficiamento_romaneios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `campo_dispositivos` | 5 | True | 2 | True | `DIRECT_COPY` |
| `campo_sync_tombstones` | 0 | True | 0 | True | `DIRECT_COPY` |
| `campo_tarefas` | 54 | True | 2 | True | `DIRECT_COPY` |
| `carbono_emissoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `carbono_projetos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `carbono_relatorios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `case_ih` | 0 | True | 0 | True | `DIRECT_COPY` |
| `categoria_custom` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_avaliacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_checklists` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_criterios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_evidencias` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_nao_conformidades` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_planos_acao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacao_programas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `certificacoes_propriedade` | 0 | True | 0 | True | `DIRECT_COPY` |
| `chamados_suporte` | 1 | True | 1 | True | `DIRECT_COPY` |
| `cobrancas_asaas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cochos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `comparador_precos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `compras_alocacoes_item` | 19 | False | — | True | `DIRECT_COPY` |
| `compras_cotacoes` | 10 | True | 1 | True | `DIRECT_COPY` |
| `compras_cotacoes_itens` | 21 | False | — | True | `DIRECT_COPY` |
| `compras_devolucoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `compras_devolucoes_itens` | 0 | False | — | True | `DIRECT_COPY` |
| `compras_fornecedores` | 17 | True | 2 | True | `DIRECT_COPY` |
| `compras_itens_pedido` | 24 | False | — | True | `DIRECT_COPY` |
| `compras_pedidos` | 15 | True | 1 | True | `TRANSFORM` |
| `compras_pedidos_confirmacoes` | 6 | True | 1 | True | `DIRECT_COPY` |
| `compras_pedidos_cotacoes` | 0 | False | — | True | `DIRECT_COPY` |
| `compras_recebimentos` | 11 | False | — | True | `DIRECT_COPY` |
| `compras_recebimentos_itens` | 22 | False | — | True | `DIRECT_COPY` |
| `compras_solicitacoes` | 14 | True | 1 | True | `DIRECT_COPY` |
| `compras_solicitacoes_itens` | 34 | False | — | True | `DIRECT_COPY` |
| `configuracao_fazenda` | 0 | True | 0 | True | `DIRECT_COPY` |
| `configuracoes_saas` | 1 | False | — | True | `DIRECT_COPY` |
| `configuracoes_tenant` | 0 | True | 0 | True | `DIRECT_COPY` |
| `confinamento_lotes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `conhecimento_artigos` | 0 | False | — | True | `DIRECT_COPY` |
| `conhecimento_categorias` | 0 | False | — | True | `DIRECT_COPY` |
| `contratos_futuros_v2` | 0 | True | 0 | True | `DIRECT_COPY` |
| `conversas_agronomo` | 0 | True | 0 | True | `DIRECT_COPY` |
| `convites_acesso` | 5 | True | 1 | True | `DIRECT_COPY` |
| `core_sequenciais` | 4 | True | 1 | True | `DIRECT_COPY` |
| `cost_allocations` | 27 | True | 2 | True | `DIRECT_COPY` |
| `crm_atividades` | 3 | False | — | True | `DIRECT_COPY` |
| `crm_leads` | 9 | False | — | True | `DIRECT_COPY` |
| `crm_ofertas_personalizadas` | 0 | False | — | True | `EMPTY_TARGET` |
| `crm_pipeline_estagios` | 5 | False | — | True | `DIRECT_COPY` |
| `crm_planos_comerciais` | 0 | False | — | True | `EMPTY_TARGET` |
| `crm_precificacao_modulo` | 0 | False | — | True | `EMPTY_TARGET` |
| `crm_produtos` | 0 | False | — | True | `EMPTY_TARGET` |
| `cultivo_areas` | 15 | True | 2 | True | `DIRECT_COPY` |
| `cultivos` | 2 | True | 2 | True | `DIRECT_COPY` |
| `culturas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `cupons` | 1 | False | — | True | `DIRECT_COPY` |
| `diagnosticos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `domain_event_outbox` | 0 | True | 0 | True | `DIRECT_COPY` |
| `email_logs` | 0 | True | 0 | True | `DIRECT_COPY` |
| `email_templates` | 2 | False | — | True | `DIRECT_COPY` |
| `epi_entregas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `equipamento_alocacoes` | 8 | True | 1 | True | `DIRECT_COPY` |
| `esg_relatorio_evidencias` | 0 | True | 0 | True | `DIRECT_COPY` |
| `esg_relatorio_indicadores` | 0 | True | 0 | True | `DIRECT_COPY` |
| `esg_relatorios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_contagem_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_contagens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_depositos` | 3 | True | 2 | True | `DIRECT_COPY` |
| `estoque_implantacao_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_implantacao_sessoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_localizacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `estoque_lotes` | 41 | False | — | True | `DIRECT_COPY` |
| `estoque_movimentos` | 173 | True | 1 | True | `DIRECT_COPY` |
| `estoque_requisicao_confirmacoes` | 2 | True | 1 | True | `DIRECT_COPY` |
| `estoque_requisicoes` | 3 | True | 1 | True | `DIRECT_COPY` |
| `estoque_requisicoes_itens` | 4 | False | — | True | `DIRECT_COPY` |
| `estoque_reservas` | 58 | True | 1 | True | `DIRECT_COPY` |
| `estoque_saldos` | 19 | False | — | True | `DIRECT_COPY` |
| `faturas` | 2 | True | 2 | True | `DIRECT_COPY` |
| `fenologia_escalas` | 8 | True | 1 | True | `DIRECT_COPY` |
| `fin_contas_bancarias` | 4 | True | 1 | True | `DIRECT_COPY` |
| `fin_despesas` | 23 | True | 1 | True | `DIRECT_COPY` |
| `fin_itens_ordem_pagamento` | 8 | True | 1 | True | `DIRECT_COPY` |
| `fin_lancamentos_bancarios` | 8 | True | 1 | True | `DIRECT_COPY` |
| `fin_notas_fiscais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `fin_ordens_pagamento` | 2 | True | 1 | True | `DIRECT_COPY` |
| `fin_planos_conta` | 68 | True | 2 | True | `DIRECT_COPY` |
| `fin_rateios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `fin_receitas` | 14 | True | 2 | True | `DIRECT_COPY` |
| `financeiro_comercializacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `financeiro_lancamentos` | 19 | True | 2 | True | `DIRECT_COPY` |
| `financeiro_plano_acoes` | 10 | True | 1 | True | `DIRECT_COPY` |
| `financeiro_safra_cenarios` | 4 | True | 1 | True | `DIRECT_COPY` |
| `frota_abastecimentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_apontamentos_uso` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_checklist_modelos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_checklists_operacionais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_checklists_operacionais_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_checklists_operacionais_respostas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_checklists_realizados` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_documentos_equipamentos` | 1 | True | 1 | True | `DIRECT_COPY` |
| `frota_jornadas_equipamento` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_logs_automacao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_ordens_servico` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_os_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_planos_manutencao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_registros_manutencao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `frota_regras_inteligentes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `growth_landing_eventos` | 0 | False | — | True | `EMPTY_TARGET` |
| `hedge_position_snapshots_v2` | 0 | True | 0 | True | `DIRECT_COPY` |
| `hedge_registros_v2` | 0 | True | 0 | True | `DIRECT_COPY` |
| `historico_bloqueios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `historico_configuracao` | 2 | True | 1 | True | `DIRECT_COPY` |
| `ia_acoes_assistidas_historico` | 7 | True | 2 | True | `DIRECT_COPY` |
| `ia_alertas_historico` | 72 | True | 2 | True | `DIRECT_COPY` |
| `ia_autopilot_config` | 2 | True | 2 | True | `DIRECT_COPY` |
| `ia_compras_recomendacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_creditos_pacotes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_assistente_interacoes` | 1 | True | 1 | True | `DIRECT_COPY` |
| `ia_growth_autopilot_acoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_config` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_config_historico` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_copy_cache` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_eventos` | 21 | True | 1 | True | `DIRECT_COPY` |
| `ia_growth_experimento_eventos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_experimento_variantes` | 0 | False | — | True | `DIRECT_COPY` |
| `ia_growth_experimentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_incentivos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_learning_weights` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_plano_recomendado_log` | 18 | True | 2 | True | `DIRECT_COPY` |
| `ia_growth_sugestoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_growth_user_profiles` | 4 | False | — | True | `DIRECT_COPY` |
| `ia_prompt_versoes_historico` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_prompts_versoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_uso` | 0 | True | 0 | True | `DIRECT_COPY` |
| `ia_ux_telemetria` | 267 | True | 2 | True | `DIRECT_COPY` |
| `ia_ux_thresholds` | 0 | False | — | True | `DIRECT_COPY` |
| `imagens_ndvi` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_arrendamento_parcelas` | 0 | False | — | True | `DIRECT_COPY` |
| `imoveis_arrendamento_reajustes` | 0 | False | — | True | `DIRECT_COPY` |
| `imoveis_arrendamentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_avaliacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_benfeitorias` | 0 | False | — | True | `DIRECT_COPY` |
| `imoveis_cartorios` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_documentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_documentos_historico` | 0 | False | — | True | `DIRECT_COPY` |
| `imoveis_matriculas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_ordens_servico_benfeitoria` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_planos_manutencao_benfeitoria` | 0 | True | 0 | True | `DIRECT_COPY` |
| `imoveis_rurais` | 3 | True | 2 | True | `DIRECT_COPY` |
| `imoveis_sistemas_irrigacao` | 0 | True | 0 | True | `DIRECT_COPY` |
| `insumos_operacao` | 63 | True | 1 | True | `DIRECT_COPY` |
| `integration_credentials` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_external_record_link_history` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_external_record_links` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_features` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_health_snapshots` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_jobs` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_sync_policies` | 0 | True | 0 | True | `DIRECT_COPY` |
| `integration_versions` | 0 | True | 0 | True | `DIRECT_COPY` |
| `john_deere` | 0 | True | 0 | True | `DIRECT_COPY` |
| `login_tentativas` | 107 | False | — | True | `DIRECT_COPY` |
| `lotes_rastreabilidade` | 0 | True | 0 | True | `DIRECT_COPY` |
| `mapas_fertilidade` | 0 | True | 0 | False | `EXCLUDED` |
| `marketplace_integracoes` | 108 | False | — | True | `DIRECT_COPY` |
| `mensagens_chamado` | 8 | False | — | True | `DIRECT_COPY` |
| `modelos_fitossanitarios` | 13 | True | 0 | True | `DIRECT_COPY` |
| `modelos_ml` | 0 | True | 0 | True | `DIRECT_COPY` |
| `modelos_zoosanitarios` | 9 | True | 0 | True | `DIRECT_COPY` |
| `module_usage_stats` | 0 | True | 0 | True | `DIRECT_COPY` |
| `monitoramento_catalogo` | 5 | True | 1 | True | `DIRECT_COPY` |
| `monitoramento_pragas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `mudancas_plano` | 0 | True | 0 | True | `DIRECT_COPY` |
| `notificacoes` | 154 | True | 2 | True | `DIRECT_COPY` |
| `notificacoes_leituras` | 128 | True | 2 | True | `DIRECT_COPY` |
| `notificacoes_preferencias` | 0 | True | 0 | True | `DIRECT_COPY` |
| `operacional_apontamentos_mao_obra` | 0 | True | 0 | True | `DIRECT_COPY` |
| `operacional_qualidade_ajustes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `operacional_qualidade_criterios` | 0 | False | — | True | `DIRECT_COPY` |
| `operacional_qualidade_laudos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `operacional_qualidade_protocolos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `operacional_qualidade_resultados` | 0 | False | — | True | `DIRECT_COPY` |
| `operacoes_agricolas` | 54 | True | 2 | True | `DIRECT_COPY` |
| `operacoes_execucoes` | 51 | True | 2 | True | `DIRECT_COPY` |
| `operation_dependencies` | 0 | False | — | True | `DIRECT_COPY` |
| `operation_template_items` | 46 | False | — | True | `DIRECT_COPY` |
| `operation_templates` | 13 | True | 1 | True | `DIRECT_COPY` |
| `operational_alerts` | 0 | True | 0 | True | `DIRECT_COPY` |
| `pec_animais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `pec_eventos_animal` | 0 | True | 0 | True | `DIRECT_COPY` |
| `pec_lotes` | 2 | True | 1 | True | `DIRECT_COPY` |
| `pec_manejos_lote` | 0 | True | 0 | True | `DIRECT_COPY` |
| `pec_piquetes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `pec_producao_leite` | 0 | True | 0 | True | `DIRECT_COPY` |
| `perfis_acesso` | 11 | True | 1 | True | `DIRECT_COPY` |
| `phase_gate_rules` | 1 | False | — | True | `DIRECT_COPY` |
| `phase_template_checklist_items` | 83 | False | — | True | `DIRECT_COPY` |
| `phase_template_tasks` | 32 | False | — | True | `DIRECT_COPY` |
| `phase_templates` | 21 | True | 1 | True | `DIRECT_COPY` |
| `plano_pricing` | 0 | False | — | True | `DIRECT_COPY` |
| `planos_assinatura` | 4 | False | — | True | `DIRECT_COPY` |
| `planos_operacionais` | 9 | True | 1 | True | `DIRECT_COPY` |
| `planos_operacionais_tarefas` | 40 | True | 1 | True | `DIRECT_COPY` |
| `planos_operacionais_tarefas_insumos` | 150 | True | 1 | True | `DIRECT_COPY` |
| `planos_operacionais_tarefas_mao_obra` | 70 | True | 1 | True | `DIRECT_COPY` |
| `planos_operacionais_tarefas_maquinario` | 20 | True | 1 | True | `DIRECT_COPY` |
| `pragas_doencas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `prescricoes_vra` | 0 | True | 0 | True | `DIRECT_COPY` |
| `previsoes_clima` | 0 | True | 0 | True | `DIRECT_COPY` |
| `previsoes_produtividade` | 0 | True | 0 | True | `DIRECT_COPY` |
| `production_units` | 15 | True | 2 | True | `DIRECT_COPY` |
| `propriedade_imovel` | 3 | True | 2 | True | `DIRECT_COPY` |
| `racas` | 0 | False | — | True | `DIRECT_COPY` |
| `racoes_tmr` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rastreabilidade_passaporte_eventos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rastreabilidade_passaporte_evidencias` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rastreabilidade_passaportes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `receitas_aplicacao` | 1 | True | 1 | True | `DIRECT_COPY` |
| `receitas_aplicacao_insumos` | 4 | True | 1 | True | `DIRECT_COPY` |
| `receitas_aplicacao_mao_obra` | 1 | True | 1 | True | `DIRECT_COPY` |
| `recomendacoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `recommendation_lifecycle_events` | 0 | True | 0 | True | `DIRECT_COPY` |
| `recommendation_results` | 0 | True | 0 | True | `DIRECT_COPY` |
| `registros_clima` | 0 | True | 0 | True | `DIRECT_COPY` |
| `relatorios_tecnicos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_colaboradores` | 2 | True | 1 | True | `DIRECT_COPY` |
| `rh_departamentos` | 1 | True | 1 | True | `DIRECT_COPY` |
| `rh_empreitadas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_esocial_eventos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_lancamentos_diarias` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_seguranca_documentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_seguranca_entregas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `rh_seguranca_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `romaneios_colheita` | 10 | True | 1 | True | `DIRECT_COPY` |
| `safra_cenarios` | 5 | True | 2 | True | `DIRECT_COPY` |
| `safra_cenarios_unidades` | 8 | True | 1 | True | `DIRECT_COPY` |
| `safra_checklist_itens` | 46 | True | 2 | True | `DIRECT_COPY` |
| `safra_fase_historico` | 7 | True | 2 | True | `DIRECT_COPY` |
| `safra_fenologia_registros` | 2 | True | 1 | True | `DIRECT_COPY` |
| `safra_talhao_grupo_itens` | 0 | True | 0 | True | `DIRECT_COPY` |
| `safra_talhao_grupos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `safra_talhoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `safra_tarefa_necessidades` | 190 | True | 1 | True | `DIRECT_COPY` |
| `safra_tarefas` | 58 | True | 2 | True | `DIRECT_COPY` |
| `safras` | 3 | True | 2 | True | `DIRECT_COPY` |
| `sankhya_config` | 1 | True | 1 | True | `DIRECT_COPY` |
| `sankhya_lancamentos_financeiros` | 0 | True | 0 | True | `DIRECT_COPY` |
| `sankhya_nfe` | 0 | True | 0 | True | `DIRECT_COPY` |
| `sankhya_pessoas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `sankhya_produtos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `sankhya_sync_logs` | 15 | True | 1 | True | `DIRECT_COPY` |
| `sankhya_tabelas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `sessoes_ativas` | 10 | True | 2 | True | `DIRECT_COPY` |
| `solo_parametros_cultura` | 56 | True | 1 | True | `DIRECT_COPY` |
| `status_consorcio_area` | 15 | True | 2 | True | `DIRECT_COPY` |
| `sugestoes_acasalamento` | 0 | True | 0 | True | `DIRECT_COPY` |
| `tenant_audit_log` | 17988 | True | 2 | True | `DIRECT_COPY` |
| `tenant_integracoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `tenant_usuarios` | 5 | True | 2 | True | `DIRECT_COPY` |
| `tenants` | 2 | False | — | True | `DIRECT_COPY` |
| `territory_legacy_backup_01h2` | 18 | True | 2 | False | `EXCLUDED` |
| `tokens_recuperacao_senha` | 15 | False | — | True | `DIRECT_COPY` |
| `tratamentos` | 0 | True | 0 | True | `DIRECT_COPY` |
| `unidade_produtiva_usuarios` | 3 | True | 1 | True | `DIRECT_COPY` |
| `unidades_medida` | 24 | True | 0 | True | `DIRECT_COPY` |
| `unidades_medida_conversoes` | 0 | True | 0 | True | `DIRECT_COPY` |
| `unidades_produtivas` | 3 | True | 2 | True | `DIRECT_COPY` |
| `usuarios` | 6 | False | — | True | `DIRECT_COPY` |
| `visitas_tecnicas` | 0 | True | 0 | True | `DIRECT_COPY` |
| `whatsapp` | 0 | True | 0 | True | `DIRECT_COPY` |
| `wizard_implantacoes_checklist_itens` | 0 | False | — | True | `DIRECT_COPY` |
| `wizard_implantacoes_etapas` | 0 | False | — | True | `DIRECT_COPY` |
| `wizard_implantacoes_historico` | 0 | False | — | True | `DIRECT_COPY` |
| `wizard_implantacoes_operacionais` | 0 | True | 0 | True | `DIRECT_COPY` |
| `wizard_implantacoes_pendencias` | 0 | False | — | True | `DIRECT_COPY` |

## Tenants e dados fora do escopo

Tenants presentes na origem: `592b906e-0329-44df-8c58-80ca744ae243` (Grupo AgroSaaS), `7cff0925-417a-41f0-8aba-271b16052477` (Fazenda Modelo).

Tabelas explicitamente excluídas ou operacionais: `alembic_version`, `amostras`, `balanca_afericoes`, `balanca_avaliacoes_prestador`, `balanca_dispositivos`, `balanca_fisicas`, `balanca_operadores`, `balanca_ordens`, `balanca_pesagens`, `balanca_sync_tombstones`, `mapas_fertilidade`, `territory_legacy_backup_01h2`.

Tabelas sem `tenant_id`: `69`; a lista completa permanece no JSON produzido pelo auditor.

## Divergências e violações

Amostra/total de `REVIEW_REQUIRED`:

UNIQUE: []

FK violations: []

Tenant violations: []

## IDs e ordem de carga

Foram encontrados `33` pares tabela/sequência para ajuste posterior com `setval(...)`. UUIDs devem ser preservados exatamente.

### Tabelas críticas — origem

| tabela | registros | tenant_count | min_id | max_id |
| --- | ---: | ---: | ---: | ---: |
| `tenants` | 2 | — | — | — |
| `usuarios` | 6 | — | — | — |
| `tenant_usuarios` | 5 | 2 | — | — |
| `unidades_produtivas` | 3 | 2 | — | — |
| `cadastros_propriedades` | 3 | 2 | — | — |
| `imoveis_rurais` | 3 | 2 | — | — |
| `safras` | 3 | 2 | — | — |
| `cultivo_areas` | 15 | 2 | — | — |
| `operacoes_agricolas` | 54 | 2 | — | — |
| `estoque_movimentos` | 173 | 1 | — | — |
| `compras_pedidos` | 15 | 1 | — | — |
| `financeiro_lancamentos` | 19 | 2 | — | — |
| `tenant_integracoes` | 0 | 0 | — | — |
| `wizard_implantacoes_operacionais` | 0 | 0 | — | — |

A comparação COUNT/MIN/MAX origem × destino ficará para a fase 01B, pois o destino PostgreSQL do piloto não foi consultado nesta auditoria.

A ordem foi derivada do grafo de FKs da baseline. Foram detectados `52` ciclos; a execução deverá usar constraints deferíveis ou carga por grupos controlados antes da fase 01B.

## Estratégia preparada

A próxima fase deve usar COPY/bulk insert, preservar IDs, manter RLS/policies e constraints, executar com papel administrativo controlado e produzir contagens origem × destino. Nenhum dado de dry-run/fixture foi removido automaticamente.

## Pendências para liberar a carga

A fase não está liberada para execução irrestrita enquanto os 52 ciclos de FK não tiverem estratégia operacional aprovada. Resolver/documentar a estratégia antes da execução:

A violação UNIQUE observada anteriormente em `cadastros_produtos` era causada por cinco linhas com `codigo_interno IS NULL`; como UNIQUE do PostgreSQL permite múltiplos NULLs, ela não é uma violação após a correção da simulação. Nenhuma linha foi alterada.

O auditor versionado é `services/api/scripts/data_migration/audit_source.py`. Sua saída JSON deve ser preservada como evidência da execução, sem registrar credenciais, passwords, tokens ou chaves.
