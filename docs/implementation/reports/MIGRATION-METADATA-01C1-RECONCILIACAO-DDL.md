# MIGRATION-METADATA-01C.1 — Reconciliação DDL ORM × Migrations × PostgreSQL

Data: 2026-09-08  
Escopo: reconciliação estrutural read-only para preparar a futura BASELINE-DEEPFARMS-V1.

## 1. Resumo executivo

A reconciliação comparou o conjunto ORM aprovado de 344 tabelas com as migrations históricas e a fotografia real do schema PostgreSQL farms. Nenhum DDL, DML, upgrade, autogenerate, create_all, drop_all ou alteração de migration foi executado.

O resultado não autoriza a 01D. Existem divergências reais entre contrato ORM e banco: 489 diferenças de tipo após normalização conservadora, 10 de nullable, 383 de presença de default server-side e 98 diferenças de expressão de default; 248 tabelas têm conjunto de FKs diferente, 11 conjuntos de UNIQUE, 39 CHECKs e 327 conjuntos de índices divergem semanticamente ou por representação. Há ainda uma FK ORM não resolvida para lotes.id.

Essas diferenças podem alterar comportamento de tenancy, integridade referencial, valores aceitos e desempenho. O contrato DDL ainda precisa de decisão manual tabela/coluna/objeto. Veredicto: **MIGRATION-METADATA-01C.1 — NO-GO**.

## 2. Estado herdado da 01C

| critério | resultado |
|---|---:|
| models descobertos | 373 |
| models classificados | 373 |
| decisões de baseline | 373/373 |
| PENDING de models | 0 |
| baseline ORM | 344 |
| colisões `__tablename__` | 0 |
| schema oficial | farms |

## 3. Metodologia read-only

Foi utilizado o script temporário `/tmp/reconcile_01c1.py`, executado com `PYTHONPATH=. .venv/bin/python`. O script importa a Base/registry, coleta o contrato ORM, lê migrations por busca de referências de tabela e consulta catálogos PostgreSQL via SQLAlchemy Inspector e SELECTs em `information_schema`, `pg_catalog` e `pg_policies`.

Consultas usadas: `information_schema.columns`, `table_constraints`, `key_column_usage`, `constraint_column_usage`, `referential_constraints`, `pg_indexes`, `pg_type/pg_enum`, `information_schema.sequences`, `pg_class/pg_namespace`, `pg_policies`, `information_schema.routines`, `information_schema.triggers`, `pg_extension` e `pg_namespace`. Nenhuma consulta de escrita foi usada.

Snapshot bruto comparável foi produzido em `/tmp/reconcile_01c1.json`; não é artefato de produto nem foi copiado para o RDS.

## 4. Baseline ORM confirmada

O registry retorna 373 tabelas. Após excluir as 29 decisões C/D/E fechadas na 01C, o conjunto ORM da baseline possui 344 tabelas. O conjunto não inclui `alembic_version`, as oito tabelas antigas da Balança, `amostras`, `mapas_fertilidade` ou `territory_legacy_backup_01h2`.

Lista completa da baseline ORM: todas as 344 linhas desta matriz com `baseline_source` MATCH ou MANUAL_CONTRACT e tabela física/ausente explicitada abaixo. Nenhuma tabela excluída da 01C é candidata a criação.

## 5. Matriz estrutural das 344 tabelas

Os campos numéricos são: colunas ORM; diferenças de tipo após normalização; diferenças de nullable; diferenças de default server-side; PK; contagem de FKs ORM:DB; origem da decisão; severidade. `MIGRATION_REFS` foi auditado no snapshot, mas resumido nesta matriz para manter o relatório legível.

| table | database | columns ORM | type diffs | nullable diffs | default diffs | PK | FK ORM:DB | baseline_source | severity |
|---|---|---:|---:|---:|---:|---|---|---|---|
| safras | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_talhoes | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_fase_historico | DIFFERENT_DEFINITION | 11 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cultivos | DIFFERENT_DEFINITION | 27 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cultivo_areas | DIFFERENT_DEFINITION | 9 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_tipos_solo | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_tipos_irrigacao | MATCH | 5 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_areas_rurais | DIFFERENT_DEFINITION | 20 | 2 | 0 | 1 | MATCH | 7:6 | MANUAL_CONTRACT | CRITICAL |
| cadastros_areas_registros_ambientais | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_infraestruturas | DIFFERENT_DEFINITION | 12 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_arquivos_geo | DIFFERENT_DEFINITION | 14 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_areas_valores_patrimoniais | DIFFERENT_DEFINITION | 13 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| production_units | DIFFERENT_DEFINITION | 13 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| status_consorcio_area | DIFFERENT_DEFINITION | 8 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_orcamento_itens | DIFFERENT_DEFINITION | 22 | 3 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_marcas | DIFFERENT_DEFINITION | 12 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_modelos_produto | DIFFERENT_DEFINITION | 11 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_categorias_produto | DIFFERENT_DEFINITION | 12 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_produtos | DIFFERENT_DEFINITION | 26 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_produtos_agricola | MATCH | 17 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_produtos_estoque | DIFFERENT_DEFINITION | 10 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_produtos_epi | DIFFERENT_DEFINITION | 7 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_culturas | DIFFERENT_DEFINITION | 16 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| solo_parametros_cultura | DIFFERENT_DEFINITION | 12 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_equipamentos | DIFFERENT_DEFINITION | 34 | 5 | 0 | 2 | MATCH | 4:3 | MANUAL_CONTRACT | CRITICAL |
| equipamento_alocacoes | DIFFERENT_DEFINITION | 11 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_equipamentos_calibracoes | DIFFERENT_DEFINITION | 13 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas | DIFFERENT_DEFINITION | 13 | 3 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_documentos | DIFFERENT_DEFINITION | 13 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_contatos | DIFFERENT_DEFINITION | 9 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_enderecos | MATCH | 15 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_pessoas_bancario | DIFFERENT_DEFINITION | 14 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_profissional_agronomo | DIFFERENT_DEFINITION | 9 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_tipos_relacionamento | MATCH | 9 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_pessoa_relacionamentos | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cadastros_pessoas_consentimentos | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_acesso_log | DIFFERENT_DEFINITION | 6 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_pessoas_pii | DIFFERENT_DEFINITION | 14 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tenants | DIFFERENT_DEFINITION | 19 | 4 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| unidades_produtivas | DIFFERENT_DEFINITION | 24 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| usuarios | DIFFERENT_DEFINITION | 14 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| perfis_acesso | DIFFERENT_DEFINITION | 7 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tenant_usuarios | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| unidade_produtiva_usuarios | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| convites_acesso | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tokens_recuperacao_senha | DIFFERENT_DEFINITION | 9 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| login_tentativas | DIFFERENT_DEFINITION | 12 | 4 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| planos_assinatura | DIFFERENT_DEFINITION | 23 | 1 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| assinaturas_tenant | DIFFERENT_DEFINITION | 15 | 6 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| faturas | DIFFERENT_DEFINITION | 12 | 4 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| plano_pricing | DIFFERENT_DEFINITION | 9 | 2 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| mudancas_plano | DIFFERENT_DEFINITION | 25 | 5 | 0 | 7 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cobrancas_asaas | DIFFERENT_DEFINITION | 17 | 5 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| historico_bloqueios | DIFFERENT_DEFINITION | 13 | 4 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| chamados_suporte | DIFFERENT_DEFINITION | 16 | 8 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| mensagens_chamado | DIFFERENT_DEFINITION | 7 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| conhecimento_categorias | MATCH | 4 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| conhecimento_artigos | DIFFERENT_DEFINITION | 9 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| configuracoes_saas | MATCH | 5 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| configuracoes_tenant | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| categoria_custom | DIFFERENT_DEFINITION | 12 | 2 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| configuracao_fazenda | DIFFERENT_DEFINITION | 5 | 1 | 0 | 2 | MATCH | 2:3 | MANUAL_CONTRACT | CRITICAL |
| historico_configuracao | DIFFERENT_DEFINITION | 7 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| admin_users | DIFFERENT_DEFINITION | 12 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| admin_impersonations | DIFFERENT_DEFINITION | 13 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sessoes_ativas | DIFFERENT_DEFINITION | 11 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cupons | DIFFERENT_DEFINITION | 15 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| email_templates | DIFFERENT_DEFINITION | 13 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| email_logs | DIFFERENT_DEFINITION | 17 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| admin_audit_log | DIFFERENT_DEFINITION | 12 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tenant_audit_log | DIFFERENT_DEFINITION | 10 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| module_usage_stats | DIFFERENT_DEFINITION | 5 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| crm_pipeline_estagios | DIFFERENT_DEFINITION | 6 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| crm_leads | DIFFERENT_DEFINITION | 21 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| crm_atividades | DIFFERENT_DEFINITION | 9 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| core_sequenciais | DIFFERENT_DEFINITION | 5 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_propriedades | DIFFERENT_DEFINITION | 17 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_exploracoes_rurais | DIFFERENT_DEFINITION | 17 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_documentos_exploracao | DIFFERENT_DEFINITION | 16 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_cartorios | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imoveis_rurais | DIFFERENT_DEFINITION | 28 | 5 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_matriculas | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imoveis_benfeitorias | MATCH | 16 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imoveis_documentos | DIFFERENT_DEFINITION | 20 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_documentos_historico | MATCH | 6 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imoveis_arrendamentos | DIFFERENT_DEFINITION | 27 | 5 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_arrendamento_parcelas | DIFFERENT_DEFINITION | 12 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_arrendamento_reajustes | MATCH | 9 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imoveis_avaliacoes | DIFFERENT_DEFINITION | 18 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| propriedade_imovel | DIFFERENT_DEFINITION | 19 | 2 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_programas | DIFFERENT_DEFINITION | 15 | 4 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_checklists | DIFFERENT_DEFINITION | 12 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_criterios | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_avaliacoes | DIFFERENT_DEFINITION | 10 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_evidencias | DIFFERENT_DEFINITION | 23 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_nao_conformidades | DIFFERENT_DEFINITION | 21 | 7 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| certificacao_planos_acao | DIFFERENT_DEFINITION | 18 | 6 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| esg_relatorios | DIFFERENT_DEFINITION | 20 | 5 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| esg_relatorio_indicadores | DIFFERENT_DEFINITION | 12 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| esg_relatorio_evidencias | DIFFERENT_DEFINITION | 5 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rastreabilidade_passaportes | DIFFERENT_DEFINITION | 22 | 6 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rastreabilidade_passaporte_eventos | DIFFERENT_DEFINITION | 12 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rastreabilidade_passaporte_evidencias | DIFFERENT_DEFINITION | 5 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_commodities | DIFFERENT_DEFINITION | 17 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_conversao_unidades | DIFFERENT_DEFINITION | 9 | 2 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_commodities_classificacoes | DIFFERENT_DEFINITION | 14 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_commodities_cotacoes | DIFFERENT_DEFINITION | 7 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_departamentos | DIFFERENT_DEFINITION | 8 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_colaboradores | DIFFERENT_DEFINITION | 15 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_esocial_eventos | DIFFERENT_DEFINITION | 13 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_lancamentos_diarias | DIFFERENT_DEFINITION | 13 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_empreitadas | DIFFERENT_DEFINITION | 16 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_seguranca_itens | DIFFERENT_DEFINITION | 11 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_seguranca_entregas | DIFFERENT_DEFINITION | 13 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| rh_seguranca_documentos | DIFFERENT_DEFINITION | 11 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_lotes | DIFFERENT_DEFINITION | 15 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_animais | DIFFERENT_DEFINITION | 26 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_eventos_animal | DIFFERENT_DEFINITION | 17 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_producao_leite | DIFFERENT_DEFINITION | 22 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_piquetes | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pec_manejos_lote | DIFFERENT_DEFINITION | 13 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_planos_manutencao | DIFFERENT_DEFINITION | 13 | 2 | 1 | 1 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| frota_ordens_servico | DIFFERENT_DEFINITION | 22 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_os_itens | DIFFERENT_DEFINITION | 14 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_registros_manutencao | DIFFERENT_DEFINITION | 14 | 1 | 1 | 0 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| frota_jornadas_equipamento | DIFFERENT_DEFINITION | 20 | 4 | 0 | 0 | MATCH | 8:7 | MANUAL_CONTRACT | CRITICAL |
| frota_regras_inteligentes | DIFFERENT_DEFINITION | 11 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_logs_automacao | DIFFERENT_DEFINITION | 11 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_depositos | DIFFERENT_DEFINITION | 7 | 0 | 0 | 0 | MATCH | 4:3 | MANUAL_CONTRACT | CRITICAL |
| estoque_saldos | DIFFERENT_DEFINITION | 9 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_localizacoes | DIFFERENT_DEFINITION | 12 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_lotes | DIFFERENT_DEFINITION | 17 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_requisicoes | DIFFERENT_DEFINITION | 13 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_requisicoes_itens | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| estoque_requisicao_confirmacoes | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_reservas | DIFFERENT_DEFINITION | 12 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_movimentos | DIFFERENT_DEFINITION | 22 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_implantacao_sessoes | DIFFERENT_DEFINITION | 19 | 4 | 0 | 0 | MATCH | 4:5 | MANUAL_CONTRACT | CRITICAL |
| estoque_implantacao_itens | DIFFERENT_DEFINITION | 15 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_fornecedores | MATCH | 6 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| compras_pedidos | DIFFERENT_DEFINITION | 20 | 2 | 1 | 4 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| compras_itens_pedido | DIFFERENT_DEFINITION | 12 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_recebimentos | DIFFERENT_DEFINITION | 7 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_recebimentos_itens | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| compras_devolucoes | DIFFERENT_DEFINITION | 9 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_devolucoes_itens | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| compras_pedidos_cotacoes | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_cotacoes | DIFFERENT_DEFINITION | 17 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_cotacoes_itens | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| compras_alocacoes_item | DIFFERENT_DEFINITION | 6 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_solicitacoes | DIFFERENT_DEFINITION | 13 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| compras_solicitacoes_itens | MATCH | 6 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| compras_pedidos_confirmacoes | DIFFERENT_DEFINITION | 10 | 3 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| modelos_zoosanitarios | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operacoes_agricolas | DIFFERENT_DEFINITION | 37 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| operacoes_execucoes | DIFFERENT_DEFINITION | 17 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| insumos_operacao | MATCH | 16 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_tarefas | DIFFERENT_DEFINITION | 35 | 0 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| safra_tarefa_necessidades | DIFFERENT_DEFINITION | 14 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| unidades_medida | DIFFERENT_DEFINITION | 13 | 2 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| unidades_medida_conversoes | DIFFERENT_DEFINITION | 11 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_planos_conta | DIFFERENT_DEFINITION | 15 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_despesas | DIFFERENT_DEFINITION | 30 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_receitas | DIFFERENT_DEFINITION | 28 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_rateios | DIFFERENT_DEFINITION | 9 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_contas_bancarias | DIFFERENT_DEFINITION | 13 | 1 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_lancamentos_bancarios | DIFFERENT_DEFINITION | 12 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_notas_fiscais | DIFFERENT_DEFINITION | 28 | 6 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| financeiro_safra_cenarios | DIFFERENT_DEFINITION | 12 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| financeiro_lancamentos | DIFFERENT_DEFINITION | 12 | 2 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_ordens_pagamento | DIFFERENT_DEFINITION | 14 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fin_itens_ordem_pagamento | DIFFERENT_DEFINITION | 11 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_abastecimentos | DIFFERENT_DEFINITION | 19 | 2 | 0 | 0 | MATCH | 8:7 | MANUAL_CONTRACT | CRITICAL |
| frota_documentos_equipamentos | DIFFERENT_DEFINITION | 14 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_apontamentos_uso | DIFFERENT_DEFINITION | 26 | 3 | 0 | 0 | MATCH | 11:10 | MANUAL_CONTRACT | CRITICAL |
| operacional_apontamentos_mao_obra | DIFFERENT_DEFINITION | 18 | 3 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_checklist_modelos | DIFFERENT_DEFINITION | 7 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_checklists_realizados | DIFFERENT_DEFINITION | 11 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_checklists_operacionais | DIFFERENT_DEFINITION | 9 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| frota_checklists_operacionais_itens | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| frota_checklists_operacionais_respostas | DIFFERENT_DEFINITION | 19 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cadastros_tipos_servico | DIFFERENT_DEFINITION | 9 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cost_allocations | DIFFERENT_DEFINITION | 15 | 1 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_produto_colhido_cost_allocations | DIFFERENT_DEFINITION | 10 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| conversas_agronomo | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| relatorios_tecnicos | MATCH | 14 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| analises_solo | DIFFERENT_DEFINITION | 36 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_regras_agronomicas | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_lotes_beneficiamento | MATCH | 32 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cafe_lote_beneficiamento_detalhes | MATCH | 12 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| cafe_lote_beneficiamento_romaneios | MATCH | 6 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| culturas | MATCH | 9 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| caderno_campo_entradas | DIFFERENT_DEFINITION | 40 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| caderno_campo_fotos | MATCH | 13 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| caderno_evento_status_historico | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| visitas_tecnicas | MATCH | 15 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| epi_entregas | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| caderno_exportacoes | DIFFERENT_DEFINITION | 24 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| safra_cenarios | DIFFERENT_DEFINITION | 26 | 3 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| safra_cenarios_unidades | DIFFERENT_DEFINITION | 28 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| safra_checklist_itens | DIFFERENT_DEFINITION | 25 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| domain_event_outbox | DIFFERENT_DEFINITION | 20 | 5 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| registros_clima | MATCH | 14 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| previsoes_clima | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| modelos_fitossanitarios | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| agricola_produtos_colhidos | DIFFERENT_DEFINITION | 30 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| fenologia_escalas | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_talhao_grupos | MATCH | 8 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_talhao_grupo_itens | MATCH | 4 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| safra_fenologia_registros | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| agricola_devolucoes_embalagens | DIFFERENT_DEFINITION | 14 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_operacao_tipo_fase | DIFFERENT_DEFINITION | 5 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| phase_templates | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| phase_template_checklist_items | DIFFERENT_DEFINITION | 10 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| phase_template_tasks | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| phase_gate_rules | MATCH | 5 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operation_templates | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operation_template_items | MATCH | 10 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operation_dependencies | MATCH | 3 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| monitoramento_catalogo | MATCH | 13 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| monitoramento_pragas | MATCH | 25 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| imagens_ndvi | MATCH | 12 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| planos_operacionais | DIFFERENT_DEFINITION | 15 | 0 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| planos_operacionais_tarefas | DIFFERENT_DEFINITION | 10 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| planos_operacionais_tarefas_insumos | DIFFERENT_DEFINITION | 19 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| planos_operacionais_tarefas_mao_obra | DIFFERENT_DEFINITION | 14 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| planos_operacionais_tarefas_maquinario | DIFFERENT_DEFINITION | 13 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| prescricoes_vra | DIFFERENT_DEFINITION | 16 | 0 | 5 | 0 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| previsoes_produtividade | MATCH | 13 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| lotes_rastreabilidade | MATCH | 15 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| certificacoes_propriedade | MATCH | 12 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| caderno_lotes_comerciais | MATCH | 18 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| receitas_aplicacao | DIFFERENT_DEFINITION | 8 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| receitas_aplicacao_insumos | DIFFERENT_DEFINITION | 9 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| receitas_aplicacao_mao_obra | DIFFERENT_DEFINITION | 10 | 0 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_receituarios_agronomicos | DIFFERENT_DEFINITION | 21 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| agricola_receituario_itens | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| romaneios_colheita | MATCH | 36 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| alert_events | DIFFERENT_DEFINITION | 16 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| alert_indicators | DIFFERENT_DEFINITION | 18 | 4 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| operational_alerts | DIFFERENT_DEFINITION | 27 | 5 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| alert_insights | DIFFERENT_DEFINITION | 18 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| alert_lifecycle_events | DIFFERENT_DEFINITION | 10 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| campo_dispositivos | DIFFERENT_DEFINITION | 18 | 2 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| campo_tarefas | DIFFERENT_DEFINITION | 33 | 1 | 0 | 9 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| campo_sync_tombstones | DIFFERENT_DEFINITION | 6 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| notificacoes | DIFFERENT_DEFINITION | 13 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| notificacoes_leituras | DIFFERENT_DEFINITION | 8 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| notificacoes_preferencias | DIFFERENT_DEFINITION | 11 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| amb_registros_car | DIFFERENT_DEFINITION | 22 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| amb_alertas | DIFFERENT_DEFINITION | 17 | 4 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| amb_outorgas_hidricas | DIFFERENT_DEFINITION | 16 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| automacoes_execucoes | DIFFERENT_DEFINITION | 10 | 1 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| automacoes_configuracoes | DIFFERENT_DEFINITION | 9 | 3 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| crm_produtos | DATABASE_ABSENT | 10 | - | - | - | - | - | ORMMIGRATION | HIGH |
| crm_precificacao_modulo | DATABASE_ABSENT | 9 | - | - | - | - | - | ORMMIGRATION | HIGH |
| crm_planos_comerciais | DATABASE_ABSENT | 13 | - | - | - | - | - | ORMMIGRATION | HIGH |
| crm_ofertas_personalizadas | DATABASE_ABSENT | 15 | - | - | - | - | - | ORMMIGRATION | HIGH |
| billing_solicitacoes_comerciais | MATCH | 18 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| billing_solicitacoes_comerciais_historico | DIFFERENT_DEFINITION | 9 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| confinamento_lotes | DIFFERENT_DEFINITION | 17 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| racoes_tmr | DIFFERENT_DEFINITION | 11 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| cochos | DIFFERENT_DEFINITION | 12 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| racas | DIFFERENT_DEFINITION | 11 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| animal_genetica | DIFFERENT_DEFINITION | 14 | 0 | 0 | 1 | MATCH | 2:1 | MANUAL_CONTRACT | CRITICAL |
| sugestoes_acasalamento | DIFFERENT_DEFINITION | 9 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| financeiro_comercializacoes | DIFFERENT_DEFINITION | 30 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| contratos_futuros_v2 | MATCH | 18 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| hedge_registros_v2 | MATCH | 14 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| hedge_position_snapshots_v2 | DIFFERENT_DEFINITION | 16 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| financeiro_plano_acoes | DIFFERENT_DEFINITION | 14 | 4 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| growth_landing_eventos | DATABASE_ABSENT | 12 | - | - | - | - | - | ORMMIGRATION | HIGH |
| ia_creditos_pacotes | DIFFERENT_DEFINITION | 9 | 3 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_uso | DIFFERENT_DEFINITION | 11 | 1 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_compras_recomendacoes | DIFFERENT_DEFINITION | 18 | 3 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_prompts_versoes | DIFFERENT_DEFINITION | 9 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_prompt_versoes_historico | DIFFERENT_DEFINITION | 8 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_alertas_historico | DIFFERENT_DEFINITION | 14 | 4 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_acoes_assistidas_historico | DIFFERENT_DEFINITION | 14 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_learning_weights | DIFFERENT_DEFINITION | 8 | 1 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_autopilot_config | DIFFERENT_DEFINITION | 16 | 2 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_incentivos | DIFFERENT_DEFINITION | 15 | 5 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_autopilot_acoes | DIFFERENT_DEFINITION | 11 | 1 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_ux_telemetria | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_eventos | DIFFERENT_DEFINITION | 10 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_sugestoes | DIFFERENT_DEFINITION | 15 | 4 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_config | DIFFERENT_DEFINITION | 8 | 2 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_config_historico | DIFFERENT_DEFINITION | 8 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_ux_thresholds | DIFFERENT_DEFINITION | 7 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_experimentos | DIFFERENT_DEFINITION | 8 | 3 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_experimento_variantes | DIFFERENT_DEFINITION | 8 | 0 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_experimento_eventos | DIFFERENT_DEFINITION | 11 | 1 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_copy_cache | DIFFERENT_DEFINITION | 5 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_user_profiles | DIFFERENT_DEFINITION | 4 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_plano_recomendado_log | DIFFERENT_DEFINITION | 18 | 3 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| ia_growth_assistente_interacoes | DIFFERENT_DEFINITION | 12 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| pragas_doencas | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tratamentos | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| diagnosticos | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| recomendacoes | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| modelos_ml | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_sistemas_irrigacao | DIFFERENT_DEFINITION | 16 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_planos_manutencao_benfeitoria | DIFFERENT_DEFINITION | 7 | 2 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| imoveis_ordens_servico_benfeitoria | DIFFERENT_DEFINITION | 15 | 2 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| marketplace_integracoes | DIFFERENT_DEFINITION | 31 | 0 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| tenant_integracoes | DIFFERENT_DEFINITION | 18 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| balanca_inbound_events | DIFFERENT_DEFINITION | 8 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| balanca_webhook_credentials | DIFFERENT_DEFINITION | 8 | 3 | 0 | 4 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_credentials | DIFFERENT_DEFINITION | 14 | 0 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_versions | DIFFERENT_DEFINITION | 9 | 0 | 0 | 3 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_features | DIFFERENT_DEFINITION | 13 | 0 | 0 | 5 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_sync_policies | DIFFERENT_DEFINITION | 19 | 0 | 0 | 12 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_jobs | DIFFERENT_DEFINITION | 22 | 2 | 0 | 8 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_health_snapshots | DIFFERENT_DEFINITION | 16 | 4 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_external_record_links | DIFFERENT_DEFINITION | 26 | 3 | 0 | 6 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| integration_external_record_link_history | DIFFERENT_DEFINITION | 13 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_config | DIFFERENT_DEFINITION | 20 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_sync_logs | MATCH | 16 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| sankhya_pessoas | DIFFERENT_DEFINITION | 27 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_produtos | DIFFERENT_DEFINITION | 21 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_nfe | DIFFERENT_DEFINITION | 29 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_lancamentos_financeiros | DIFFERENT_DEFINITION | 18 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| sankhya_tabelas | DIFFERENT_DEFINITION | 11 | 1 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| john_deere | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| case_ih | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| whatsapp | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| comparador_precos | DIFFERENT_DEFINITION | 4 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| carbono_emissoes | DIFFERENT_DEFINITION | 19 | 0 | 1 | 1 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| carbono_projetos | DIFFERENT_DEFINITION | 23 | 1 | 1 | 1 | MATCH | MATCH | MANUAL_CONTRACT | CRITICAL |
| carbono_relatorios | DIFFERENT_DEFINITION | 17 | 0 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_contagens | DIFFERENT_DEFINITION | 9 | 2 | 0 | 2 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| estoque_contagem_itens | DIFFERENT_DEFINITION | 8 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| operacional_qualidade_protocolos | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operacional_qualidade_criterios | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operacional_qualidade_laudos | DIFFERENT_DEFINITION | 10 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| operacional_qualidade_resultados | MATCH | 7 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| operacional_qualidade_ajustes | MATCH | 11 | 0 | 0 | 0 | MATCH | MATCH | MATCH | INFORMATIONAL |
| recommendation_results | DIFFERENT_DEFINITION | 32 | 12 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| recommendation_lifecycle_events | DIFFERENT_DEFINITION | 10 | 2 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| wizard_implantacoes_operacionais | DIFFERENT_DEFINITION | 24 | 10 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| wizard_implantacoes_etapas | DIFFERENT_DEFINITION | 16 | 6 | 0 | 1 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| wizard_implantacoes_checklist_itens | DIFFERENT_DEFINITION | 14 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| wizard_implantacoes_pendencias | DIFFERENT_DEFINITION | 13 | 3 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |
| wizard_implantacoes_historico | DIFFERENT_DEFINITION | 10 | 1 | 0 | 0 | MATCH | MATCH | MANUAL_CONTRACT | HIGH |


Interpretação: MATCH significa que nomes de colunas, tipos normalizados, nullable, presença de default, PK e cardinalidade de FK passaram a comparação automatizada. Não significa que constraints, expressions de índice, policy ou definição histórica sejam automaticamente aprovadas. DIFFERENT_DEFINITION exige MANUAL_CONTRACT.

## 6. Reconciliação de colunas

| divergência | quantidade | classificação/decisão |
|---|---:|---|
| coluna ORM ausente no DB | 0 nas tabelas presentes | nenhuma divergência de conjunto detectada; tabelas ausentes foram separadas |
| coluna DB ausente no ORM | 0 nas tabelas presentes | nenhuma divergência de conjunto detectada |
| tipo diferente | 489 | DIFFERENT_TYPE; MANUAL_CONTRACT |
| nullable diferente | 10 | DIFFERENT_NULLABILITY; CRITICAL; contrato explícito obrigatório |
| default server-side presente apenas em uma fonte | 383 | DIFFERENT_DEFAULT; MANUAL_CONTRACT |
| expressão/representação de default diferente | 98 | DIFFERENT_DEFAULT; MANUAL_CONTRACT |

Os tipos com maior recorrência são `timestamp with time zone` no ORM contra `timestamp without time zone` físico e `FLOAT` contra `DOUBLE PRECISION`. Isso não foi tratado como equivalência automática: a baseline precisa decidir timezone e precisão por coluna.

Diferenças de default incluem defaults Python no ORM que não são server defaults e defaults físicos como `CURRENT_TIMESTAMP`, `false`, `now()` e casts de enum/varchar. A baseline deve declarar somente defaults aprovados no contrato manual.

## 7. Primary keys

Todas as tabelas presentes comparadas mantiveram a mesma lista de colunas de PK na comparação automatizada. Isso não elimina a necessidade de preservar nomes e ordem das constraints no DDL final. As cinco tabelas ausentes têm PK conhecida pelo ORM/migration, mas ainda não têm comparação física.

## 8. Foreign keys

248 das tabelas comparadas possuem conjunto de FKs divergente quando consideradas colunas, destino e ações. O padrão mais frequente é ORM com `CASCADE` contra banco com `RESTRICT`, além de FKs compostas que exigem normalização específica. A decisão não foi aplicada.

Há uma ocorrência crítica de referência ORM não resolvida: `animal_genetica` declara `lotes.id`, enquanto o registry não contém tabela `lotes`. Isso impede afirmar que a construção da baseline será executável sem contrato manual para o destino.

Precedência recomendada: `MANUAL_CONTRACT`, preservando as decisões já fechadas de Tenant Integrity e validando cada FK contra a definição PostgreSQL aprovada. Não usar autogenerate para escolher ON DELETE.

## 9. UNIQUEs e CHECKs

| objeto | divergências | decisão |
|---|---:|---|
| UNIQUE constraints | 11 tabelas com conjunto semântico diferente | MANUAL_CONTRACT; eliminar duplicidade constraint/index equivalente |
| CHECK constraints | 39 tabelas com conjunto diferente ou expressão não equivalente textual | MANUAL_CONTRACT; normalizar semanticamente |

Não houve reparo. A baseline deverá escolher uma única representação para UNIQUE quando houver índice unique equivalente e deverá preservar checks necessários ao runtime.

## 10. Índices

Há 1.481 índices físicos. A comparação encontrou 327 tabelas com conjunto de índices diferente entre ORM e DB, considerando nome, unique, colunas e expressões disponíveis no Inspector. A diferença pode conter índices PK_BACKING, UNIQUE_BACKING, ORM_DECLARED, MIGRATION_DECLARED, PERFORMANCE_MANUAL, PARTIAL, EXPRESSION, DATABASE_ONLY ou REDUNDANT.

O contrato da baseline deve classificar cada índice individualmente. Índices de PK/UNIQUE são obrigatórios; índices parciais, de expressão e de performance devem ser incluídos somente quando confirmados como necessários. `DATABASE_ONLY` não deve ser copiado cegamente.

## 11. ENUMs

O banco possui 35 tipos ENUM com 146 valores. A lista confirmada, preservando a ordem física, é:

```text
metodoavaliacaoimovel = MERCADO,CUSTO,RENDA,DECLARADO,LAUDO
periodicidade = MENSAL,SEMESTRAL,ANUAL,SAFRA
prioridade_plano_acao_enum = BAIXA,MEDIA,ALTA,URGENTE
resultado_avaliacao_enum = APROVADO,APROVADO_COM_RESSALVA,REPROVADO,PENDENTE
severidade_nao_conformidade_enum = MENOR,MAIOR,CRITICA
severidadealerta = BAIXA,MEDIA,ALTA,CRITICA
situacaoimovel = REGULAR,PENDENTE,IRREGULAR
status_checklist_enum = RASCUNHO,PUBLICADO,ARQUIVADO
status_nao_conformidade_enum = ABERTA,EM_ANALISE,EM_CORRECAO,RESOLVIDA,CANCELADA
status_passaporte_enum = RASCUNHO,ATIVO,REVOGADO,EM_VALIDACAO,PUBLICADO
status_plano_acao_enum = PENDENTE,EM_ANDAMENTO,CONCLUIDO,ATRASADO,CANCELADO
status_programa_enum = ATIVO,INATIVO,SUSPENSO
status_relatorio_esg_enum = RASCUNHO,EM_REVISAO,PUBLICADO,ARQUIVADO,CANCELADO
statusalerta = NOVO,EM_ANALISE,RESOLVIDO,IGNORADO
statuscar = ATIVO,PENDENTE,CANCELADO,SUSPENSO,EM_ANALISE
statuscontrato = ATIVO,ENCERRADO,RESCINDIDO,SUSPENSO
statusdocumento = ATIVO,SUBSTITUIDO,VENCIDO,CANCELADO
statusoutorga = ATIVA,VENCIDA,SUSPENSA,CANCELADA,EM_RENOVACAO
statusparcela = PREVISTA,PAGA,CANCELADA,VENCIDA
statussefaz = EM_DIGITACAO,ASSINADA,TRANSMITIDA,AUTORIZADA,CANCELADA,DENEGADA,INUTILIZADA
ticketpriority = BAIXA,MEDIA,ALTA,URGENTE
ticketstatus = ABERTO,EM_ATENDIMENTO,AGUARDANDO_CLIENTE,CONCLUIDO,CANCELADO
tipo_certificacao_enum = ORGANICO,GLOBALGAP,REGENAGRI,ESG_INTERNO,OUTRO
tipo_evento_passaporte_enum = GERADO,VALIDADO,PUBLICADO,REVOGADO,ATUALIZADO
tipo_evidencia_enum = DOCUMENTO_PDF,FOTO_CAMPO,DADO_SATELITE,OUTRO
tipoalerta = DESMATAMENTO,QUEIMADA,INUNDACAO,EROSAO,OUTRO
tipoarrendatario = PESSOA_FISICA,PESSOA_JURIDICA,FAZENDA_TENANT
tipocategoria = despesa,receita,operacao,produto,insumo
tipocontrato = ARRENDAMENTO,PARCERIA
tipodocumento = CCIR,ITR_DITR,CAR,ESCRITURA,MATRICULA,GEOREFERENCIAMENTO,OUTRO
tipoimovel = RURAL,PARTICULAR,DEVOLUTA,POSSE
tiponf = NFP_E,NF_E,NFC_E
tipousooutorga = IRRIGACAO,DESSEDENTACAO,USO_INDUSTRIAL,AQUICULTURA,OUTRO
valormodalidade = FIXO_BRL,FIXO_SACAS,PERCENTUAL
```

Os ENUMs são CONFIRMED_IN_DATABASE. A origem migration/ORM existe para parte deles, mas a equivalência nome/ordem/consumidores ainda precisa ser validada no SQL da baseline; qualquer enum sem correspondência exata será DIFFERENT_VALUES/DIFFERENT_ORDER e bloqueador.

## 12. Sequences

Foram confirmadas 35 sequences físicas, todas com start 1, increment 1 e cycle NO. As de Sankhya são BIGINT; as demais observadas são INTEGER. Nomes:

```text
amostras_id_seq, animal_genetica_id_seq, balanca_webhook_credentials_id_seq, carbono_emissoes_id_seq, carbono_projetos_id_seq, case_ih_id_seq, cochos_id_seq, comparador_precos_id_seq, confinamento_lotes_id_seq, diagnosticos_id_seq, integration_credentials_id_seq, integration_features_id_seq, integration_health_snapshots_id_seq, integration_sync_policies_id_seq, integration_versions_id_seq, john_deere_id_seq, mapas_fertilidade_id_seq, marketplace_integracoes_id_seq, modelos_ml_id_seq, pragas_doencas_id_seq, racas_id_seq, racoes_tmr_id_seq, recomendacoes_id_seq, sankhya_config_id_seq, sankhya_lancamentos_financeiros_id_seq, sankhya_nfe_id_seq, sankhya_pessoas_id_seq, sankhya_produtos_id_seq, sankhya_tabelas_id_seq, sugestoes_acasalamento_id_seq, tenant_integracoes_id_seq, territory_legacy_backup_01h2_id_seq, tratamentos_id_seq, whatsapp_id_seq
```

Sequences de tabelas ORM com PK serial/identity são REQUIRED_BASELINE quando a tabela entra; sequences de objetos excluídos são LEGACY/DB_INTERNAL. `core_sequenciais` é tabela de domínio e não deve ser confundida com sequence técnica.

## 13. RLS e policies

RLS foi confirmado em 51 tabelas; 49 estão FORCED. Existem 188 policies. As tabelas e policies foram lidas de `pg_class`/`pg_policies`; as expressões são baseadas em `app.current_tenant_id`, com policies diretas por tenant e policies relacionais do Wizard.

| item | quantidade | classificação |
|---|---:|---|
| RLS ENABLED | 51 | CONFIRMED_IN_DATABASE; incluir quando tabela/política for aprovada |
| RLS FORCED | 49 | DIFFERENT_FORCE_STATE a conferir migration a migration |
| policies | 188 | MANUAL_CONTRACT; todas exigem comparação semântica |

Uma diferença de RLS, FORCE ou USING/WITH CHECK é CRITICAL por risco de tenant isolation. Não foi considerada resolvida apenas porque a tabela possui tenant_id.

## 14. Functions, triggers, views, extensions e grants

| objeto | inventário | decisão |
|---|---|---|
| functions | fn_estoque_movimentos_append_only; fn_production_units_refresh_status; fn_production_units_valida_soma | APPLICATION_REQUIRED quando os triggers correspondentes forem incluídos; definição ainda deve ser copiada para contrato manual |
| triggers | 7 eventos em estoque_movimentos e production_units | INCLUDE se as tabelas e funções forem aprovadas; mapping timing/event/function confirmado, definição completa ainda requerida |
| views | 0 | EXCLUDE; não criar |
| materialized views | 0 | EXCLUDE; não criar |
| extensions | plpgsql 1.0 em pg_catalog | infraestrutura PostgreSQL; não criar extensão de negócio; confirmar requisito operacional |
| grants | 3.641 grants de tabela | separar APPLICATION_REQUIRED de RDS_ADMINISTRATIVE; não codificar todos na baseline |

Functions e triggers são objetos fora de Base.metadata. Como a definição completa, dependências e estado enabled não foram congelados em um manifest versionado, permanecem bloqueadores para 01D.

## 15. Tabelas físicas fora do baseline ORM

| tabela | classificação | decisão |
|---|---|---|
| alembic_version | ALEMBIC_CONTROL | manter como controle Alembic, fora do conjunto ORM |
| amostras | ORPHAN | EXCLUDE; avaliar remoção em épico separado |
| balanca_afericoes | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_avaliacoes_prestador | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_dispositivos | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_fisicas | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_operadores | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_ordens | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_pesagens | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| balanca_sync_tombstones | LEGACY | EXCLUDE; antigo módulo local DeepFarms |
| mapas_fertilidade | ORPHAN | EXCLUDE; avaliar remoção em épico separado |
| territory_legacy_backup_01h2 | BACKUP | EXCLUDE; não copiar para instalação nova |

A diferença física não é 351 - 344: há 12 tabelas físicas fora do baseline e cinco tabelas baseline ausentes, resultando em 339 nomes compartilhados.

## 16. Tabelas da baseline ausentes no DB

| tabela | evidência | decisão | baseline_source |
|---|---|---|---|
| crm_ofertas_personalizadas | ORM + migrations a0a581.../43cdf... + router/seed CRM | NEW_ACTIVE_SCHEMA; não implantada na fotografia | ORM/MIGRATION |
| crm_planos_comerciais | ORM + migrations + router/seed CRM | NEW_ACTIVE_SCHEMA; não implantada na fotografia | ORM/MIGRATION |
| crm_precificacao_modulo | ORM + migrations + router/seed CRM | NEW_ACTIVE_SCHEMA; não implantada na fotografia | ORM/MIGRATION |
| crm_produtos | ORM + migrations + router/seed CRM | NEW_ACTIVE_SCHEMA; não implantada na fotografia | ORM/MIGRATION |
| growth_landing_eventos | ORM + migration 20260507 + router growth | NEW_ACTIVE_SCHEMA; não implantada na fotografia | ORM/MIGRATION |

Essas cinco ausências não são motivo para remover os models: são estruturas ativas aprovadas que uma instalação nova deverá materializar, desde que o DDL manual seja reconciliado.

## 17. Matriz consolidada ORM × migrations × DB

| objeto | ORM | migrations | DB | baseline_source | decisão | risco |
|---|---|---|---|---|---|---|
| 344 tabelas baseline | presente | referências históricas variáveis | 339 presentes, 5 ausentes | MANUAL_CONTRACT | construir somente após reconciliação por objeto | HIGH |
| cinco tabelas CRM/Growth ausentes | presente | presente | ausente | ORM/MIGRATION | incluir na baseline nova | HIGH |
| 12 tabelas físicas fora | ausente do baseline aprovado | histórico/DDL variável | presente | MANUAL_CONTRACT | excluir sem DROP; controlar legado/backup | HIGH |
| 489 tipos | presente | variável | diferente após normalização | MANUAL_CONTRACT | decidir coluna a coluna | CRITICAL/HIGH |
| 10 nullable | presente | variável | diferente | MANUAL_CONTRACT | não alterar automaticamente | CRITICAL |
| 248 FKs | presente | histórico reparado | ações/conjuntos diferentes | MANUAL_CONTRACT | preservar Tenant Integrity após aprovação | CRITICAL |
| 11 UNIQUEs | presente/variável | presente/variável | conjunto diferente | MANUAL_CONTRACT | eliminar duplicidades | HIGH |
| 39 CHECKs | presente/variável | DDL manual | conjunto diferente | MANUAL_CONTRACT | normalizar semanticamente | HIGH |
| 327 índices | ORM/migration/DB | múltiplas gerações | conjunto diferente | MANUAL_CONTRACT | classificar individualmente | MEDIUM/HIGH |
| 35 ENUMs | presente parcial | presente parcial | presente | DATABASE/MANUAL_CONTRACT | preservar nomes e ordem | CRITICAL |
| RLS/policies | migrations parciais | presente parcial | 51/188 | MANUAL_CONTRACT | reproduzir tenant isolation aprovada | CRITICAL |
| functions/triggers | fora do ORM | migrations/DDL | 3/7 | MANUAL_CONTRACT | incluir dependências necessárias | CRITICAL |

## 18. Precedência estrutural

Não há regra universal. A matriz recomenda: ORM/MIGRATION para as cinco tabelas novas ativas; DATABASE/MANUAL_CONTRACT para estado físico confirmado de funções/policies/objetos que não são derivados pelo ORM; MANUAL_CONTRACT para divergências de FKs, tipos, nullable, defaults, checks e índices; EXCLUDE para tabelas físicas legadas/backup/orphan; controle Alembic para alembic_version.

Enquanto as 248 divergências de FK e 10 nullable não forem decididas individualmente, não existe contrato determinístico. O banco funcional não deve ser copiado cegamente e o histórico não deve ser reproduzido cegamente.

## 19. Objetos manuais necessários à baseline

Obrigatórios fora de Base.metadata: criação/ordem dos 35 ENUMs; sequences e ownership; constraints cujo DDL ORM não reproduz a definição física; índices parciais/expressões/performance aprovados; RLS ENABLE/FORCE; 188 policies aprovadas; três functions; sete triggers; schema/search_path; grants mínimos; e qualquer DDL `op.execute` relevante localizado nas migrations.

Não foi criado manifest machine-readable de produção: nesta fase o snapshot é evidência de auditoria, enquanto as decisões manuais ainda estão abertas e um manifest congelado duplicaria um contrato incompleto. O próximo passo deve criar o manifest somente após aprovação objeto a objeto.

## 20. Divergências por severidade

| severidade | itens | status |
|---|---|---|
| CRITICAL | 10 nullable; 248 FKs; FK ORM não resolvida; RLS/policies/functions/triggers/ENUMs ainda não congelados | bloqueia 01D |
| HIGH | 489 tipos; defaults; 11 UNIQUEs; 39 CHECKs; 327 conjuntos de índices; cinco tabelas ausentes | bloqueia 01D até decisão |
| MEDIUM | diferenças de representação/nome/índice não funcional | documentar no contrato |
| LOW/INFORMATIONAL | MATCHs de tabela/coluna/PK | não bloqueia isoladamente |

## 21. Arquivos e artefatos

- `docs/implementation/reports/MIGRATION-METADATA-01C1-RECONCILIACAO-DDL.md` — este relatório.
- `/tmp/reconcile_01c1.py` — script temporário read-only.
- `/tmp/reconcile_01c1.json` — snapshot temporário de auditoria.
- `services/api/tests/unit/core/test_baseline_ddl_contract.py` — guardrails do escopo ORM/farms/Balança.

Não foram alterados models, migrations históricas, `env.py`, schema, dados ou RDS. O registry da 01C não foi redesenhado.

## 22. Testes e validações

- `PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py`: 6 passed; nenhum teste acessa o banco.
- `PYTHONPATH=. .venv/bin/python -m ruff check core/model_registry.py migrations/env.py tests/unit/core/test_model_registry.py tests/unit/core/test_baseline_ddl_contract.py`: All checks passed.
- `git diff --check`.
- `alembic heads`: uma head conhecida, `20260828_balanca_webhook_credentials`.
- Reconciliador PostgreSQL: concluído com SELECT/Inspector exclusivamente read-only.
- Não executados: upgrade, downgrade, autogenerate, create_all, drop_all ou qualquer DML/DDL.

## 23. Critério de GO para 01D

Antes de autorizar 01D deve existir: comparação completa das 344 tabelas; decisão para os 489 tipos, 10 nullable, defaults, 248 FKs, UNIQUEs, CHECKs e 327 conjuntos de índices; enum consumers/origens reconciliados; sequences com ownership; RLS/policies semanticamente comparadas; definições de functions/triggers congeladas; cinco tabelas ausentes justificadas; 12 tabelas físicas fora classificadas; e zero UNKNOWN estrutural.

## 24. Veredicto final

Embora `models=373`, `classified=373`, `baseline=344`, `PENDING=0` e `collisions=0`, o contrato DDL não está fechado. As diferenças podem alterar tipos, defaults, integridade referencial e isolamento de tenants. A baseline ainda exigiria inferências perigosas.

**MIGRATION-METADATA-01C.1**  
**STATUS: NO-GO**  
Próxima fase recomendada: `MIGRATION-METADATA-01C.2 — Decisão DDL por objeto e congelamento do contrato non-ORM`. Somente após GO dessa reconciliação será permitida a `MIGRATION-METADATA-01D — Construção da BASELINE-DEEPFARMS-V1`.
