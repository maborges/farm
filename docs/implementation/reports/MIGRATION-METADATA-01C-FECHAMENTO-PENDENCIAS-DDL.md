# MIGRATION-METADATA-01C — Fechamento de Pendências e Inventário DDL PostgreSQL

Data: 2026-09-08  
Escopo: auditoria e decisões estruturais. A introspecção PostgreSQL foi exclusivamente read-only; nenhuma alteração foi executada.

## 1. Resumo executivo

A 01C fecha os 34 models que estavam PENDING na 01B, incorpora evidência de runtime, migrations, documentação e histórico Git, e congela o contrato estrutural candidato da futura baseline. O registry não foi redesenhado: continua usando a única Base oficial.

Resultado: 5 models promovidos para ACTIVE_BASELINE, 12 classificados CODE_ONLY_NOT_DEPLOYED, 8 SUPERSEDED e 9 DEAD/ORPHAN MODEL. Nenhum permanece PENDING. A baseline ORM proposta passa de 339 para 344 tabelas.

As oito tabelas antigas da Balança foram resolvidas como DEEPFARMS_LEGACY: pertenciam ao antigo módulo local removido no commit 8db70174, cujas models e migrations foram deletadas na migração para a arquitetura HTTP. Permanecem fora da baseline, sem DROP.

**MIGRATION-METADATA-01C — STATUS: NO-GO**. Embora as decisões dos 34 estejam fechadas, a comparação de definições completas ORM × migrations × database ainda exige especificação/validação DDL formal antes de criar a baseline; há divergências históricas, RLS/policies e objetos físicos que não podem ser inferidos por autogenerate.

## 2. Estado herdado da 01B

| item | valor 01B | resultado 01C |
|---|---:|---:|
| models descobertos | 373 | 373 |
| models classificados | 373 | 373 |
| registry | 373 | 373 |
| baseline ORM | 339 | 344 |
| PENDING | 34 | 0 |
| colisões | 0 | 0 |

## 3. Decisão individual dos 34 PENDING

| tabela | classe | módulo | decisão | evidência consolidada |
|---|---|---|---|---|
| api_keys | ApiKeys | core/api_publica/models/api_keys.py | C — CODE_ONLY_NOT_DEPLOYED | Classe placeholder; main registra router, mas não há schema/service de persistência funcional; migration histórica existe; não há tabela física. |
| api_logs | ApiLogs | core/api_publica/models/api_logs.py | C — CODE_ONLY_NOT_DEPLOYED | Classe placeholder; router histórico sem fluxo persistente comprovado; migration existe; não há tabela física. |
| api_versions | ApiVersions | core/api_publica/models/api_versions.py | C — CODE_ONLY_NOT_DEPLOYED | Classe placeholder sem feature persistente comprovada; migration histórica existe; não há tabela física. |
| arracoamentos | Arracoamento | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Somente model enterprise e migration histórica; nenhum router/service/runtime atual localizado; não há tabela física. |
| balanco_hidrico | BalancoHidrico | agricola/ndvi_avancado/models/balanco_hidrico.py | D — SUPERSEDED | Model esqueleto; runtime climático usa RegistroClima/PrevisaoClima; migration histórica existe; não há tabela física. |
| benchmarks | Benchmarks | enterprise/models/benchmarks.py | C — CODE_ONLY_NOT_DEPLOYED | Router existe, mas endpoints são placeholders que retornam vazio; sem service/schema persistente; não há tabela física. |
| colaborador_apontamentos | ColaboradorApontamento | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Nenhum router/service/runtime atual localizado; apontamento operacional moderno existe; migration histórica; sem tabela física. |
| contratos_futuros | ContratoFuturo | financeiro/hedge/models.py | D — SUPERSEDED | Model atual grava contratos_futuros_v2; o nome antigo não é usado pelo service; DB possui apenas contratos_futuros_v2. |
| crm_ofertas_personalizadas | OfertaPersonalizada | core/models/crm_ofertas.py | A — ACTIVE_BASELINE | Router backoffice, migrations e script seed_crm_ofertas.py referenciam o conjunto; ausência física indica não implantação neste ambiente. |
| crm_planos_comerciais | PlanoComercial | core/models/crm_ofertas.py | A — ACTIVE_BASELINE | Router backoffice, migrations e seed de catálogo referenciam o conjunto; ausência física não elimina o contrato ativo. |
| crm_precificacao_modulo | PrecificacaoModulo | core/models/crm_ofertas.py | A — ACTIVE_BASELINE | Migrations, router backoffice e seed de catálogo; é parte do CRM de ofertas aprovado. |
| crm_produtos | ModuloOferta | core/models/crm_ofertas.py | A — ACTIVE_BASELINE | Migrations, router backoffice e seed de catálogo; é parte do CRM de ofertas aprovado. |
| enterprise_esg_relatorios | ESGRelatorio | enterprise/models/sprints_27_33.py | D — SUPERSEDED | Geração enterprise antiga; DB/runtime usam esg_relatorios e esg_relatorio_indicadores canônicos; sem tabela antiga. |
| esg_indicadores | ESGIndicador | enterprise/models/sprints_27_33.py | D — SUPERSEDED | Geração enterprise antiga; a relação canônica está em esg_relatorio_indicadores; migration antiga sem tabela física. |
| estacoes_meteorologicas | EstacoesMeteorologicas | agricola/ndvi_avancado/models/estacoes_meteorologicas.py | D — SUPERSEDED | Model esqueleto sem router/service; arquitetura climática atual usa registros/previsões; migration histórica; sem tabela física. |
| growth_landing_eventos | LandingEvento | growth/models.py | A — ACTIVE_BASELINE | Router growth e migration 20260507_growth_landing_eventos; tracking de landing é feature atual; ausência física é deployment incompleto. |
| hedge_registros | HedgeRegistro | financeiro/hedge/models.py | D — SUPERSEDED | A classe enterprise antiga conflita semanticamente; service atual usa hedge_registros_v2 e migration de restauração v2; DB possui v2. |
| ilpf_modulos | ILPFModulo | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Somente geração enterprise e migrations; nenhum runtime/endpoint atual localizado; sem tabela física. |
| imagens_satelite | ImagensSatelite | agricola/ndvi_avancado/models/imagens_satelite.py | D — SUPERSEDED | Model esqueleto sem runtime; o produto usa imagens_ndvi; migration histórica; sem tabela física. |
| integracao_new_holland | IntegracaoNewHolland | iot_integracao/new_holland/models/__init__.py | C — CODE_ONLY_NOT_DEPLOYED | Model e migration de integração existem, mas não há router/service de persistência atual; não é carbono nem Balança. |
| maquinas_new_holland | MaquinaNewHolland | iot_integracao/new_holland/models/__init__.py | C — CODE_ONLY_NOT_DEPLOYED | Model e migration existem; sem endpoint/service atual de materialização; feature não aprovada para instalação nova. |
| marketplace_avaliacoes | MarketplaceAvaliacao | iot_integracao/new_holland/models/__init__.py | C — CODE_ONLY_NOT_DEPLOYED | Model/migration e teste contratual existem, mas não há fluxo runtime exposto; não promover automaticamente. |
| mrv_projetos | MRVProjeto | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Somente model enterprise e migration histórica; nenhum runtime atual localizado; sem tabela física. |
| mrv_relatorios | MRVRelatorio | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Somente model enterprise e migration histórica; nenhum runtime atual localizado; sem tabela física. |
| ndvi_registros | NdviRegistros | agricola/ndvi_avancado/models/ndvi_registros.py | D — SUPERSEDED | Model esqueleto; produto físico atual usa imagens_ndvi e demais estruturas canônicas; migration histórica; sem tabela física. |
| pesagens | Pesagem | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | O runtime de pecuária usa EventoAnimal/PesagemService e a integração HTTP; a classe enterprise não é usada para persistência. |
| pontos | Pontos | enterprise/models/pontos.py | C — CODE_ONLY_NOT_DEPLOYED | Router enterprise existe, mas é placeholder; referências a pontos no financeiro são conceitos/campos, não uso da classe; sem tabela física. |
| powerbi | Powerbi | enterprise/models/powerbi.py | C — CODE_ONLY_NOT_DEPLOYED | Router e service existem como scaffolding, sem persistência funcional; sem tabela física. |
| preditivo | Preditivo | enterprise/models/preditivo.py | C — CODE_ONLY_NOT_DEPLOYED | Router/service enterprise são scaffolding; predição atual usa serviço de IA sem esta tabela; sem tabela física. |
| sap | Sap | enterprise/models/sap.py | C — CODE_ONLY_NOT_DEPLOYED | Router/service enterprise são scaffolding; integração SAP não tem persistência funcional atual; sem tabela física. |
| sdks | Sdks | core/api_publica/models/sdks.py | C — CODE_ONLY_NOT_DEPLOYED | Router retorna coleção vazia/objeto vazio e não possui schema/service; migration histórica; sem tabela física. |
| sensores_iot | SensorIoT | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Nenhum runtime atual da classe; integrações IoT canônicas são específicas e não dependem dela; sem tabela física. |
| sensores_leituras | SensorLeitura | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Nenhum runtime atual da classe; sem router/service/teste funcional; sem tabela física. |
| tanques_rede | TanqueRede | enterprise/models/sprints_27_33.py | E — DEAD/ORPHAN MODEL | Somente geração enterprise e migrations; nenhum runtime atual localizado; sem tabela física. |

Categorias: A=ACTIVE_BASELINE; B=SUPPORTED_LEGACY_BASELINE; C=CODE_ONLY_NOT_DEPLOYED; D=SUPERSEDED; E=DEAD/ORPHAN MODEL. Todos continuam registry=INCLUDE; somente A entra na baseline entre estes 34.

## 4. Grupos analisados

API pública: api_keys, api_logs, api_versions e sdks são scaffolding/routers incompletos, sem persistência funcional comprovada; ficam C.

NDVI/clima: balanco_hidrico, estacoes_meteorologicas, imagens_satelite e ndvi_registros são models esqueleto/geração antiga; runtime atual usa registros_clima, previsoes_clima, previsoes_produtividade e imagens_ndvi. Ficam D.

CRM/Growth: o CRM possui models, migrations, router backoffice e seed de catálogo; growth possui router e migration de landing tracking. Os cinco ficam A.

Enterprise: a presença em sprints_27_33.py não foi tratada automaticamente como ativa. A análise separou routers placeholder, gerações substituídas e models sem runtime. Nenhuma remoção foi feita.

New Holland: integracao_new_holland, maquinas_new_holland e marketplace_avaliacoes foram mantidos visíveis, mas não aprovados para criação nova sem fluxo runtime de persistência. Ficam C e não foram misturados com carbono.

## 5. Balança antiga e pesagens

| tabela | destino final | evidência | baseline |
|---|---|---|---|
| balanca_afericoes | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_avaliacoes_prestador | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_dispositivos | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_fisicas | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_operadores | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_ordens | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_pesagens | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |
| balanca_sync_tombstones | DEEPFARMS_LEGACY | model/migration no módulo local removido por 8db70174 | EXCLUDE |

O commit 8db70174 removeu `services/api/balanca/models.py`, as migrations 20260816/20260817 e a aplicação local `apps/balanca`. A arquitetura atual é DeepFarms → HTTP → Plataforma Balança. As tabelas atuais do DeepFarms são balanca_inbound_events e balanca_webhook_credentials.

`pesagens` não é equivalente a `balanca_pesagens`. `pesagens` era a classe enterprise antiga e não é usada pelo PesagemService atual; o runtime pecuário grava o fluxo canônico de EventoAnimal e integra por HTTP. `balanca_pesagens` era a tabela do módulo local removido. Não existe conversão ou dependência atual encontrada.

## 6. DDL físico do schema farms

Comando executado, exclusivamente read-only: `PYTHONPATH=. .venv/bin/python /tmp/inspect_01c.py`, que executa somente SELECT em catálogos PostgreSQL.

| objeto | contagem | status |
|---|---:|---|
| schema farms | 1 | CONFIRMED_IN_DATABASE; owner borgus |
| tabelas | 351 | CONFIRMED_IN_DATABASE |
| colunas | 4.764 | CONFIRMED_IN_DATABASE |
| constraints | 4.418 | CONFIRMED_IN_DATABASE |
| índices | 1.481 | CONFIRMED_IN_DATABASE |
| ENUM entries | 146 em 35 tipos | CONFIRMED_IN_DATABASE |
| sequences | 35 | CONFIRMED_IN_DATABASE |
| tabelas com RLS | 51 ENABLED; 49 FORCED | CONFIRMED_IN_DATABASE |
| policies | 188 | CONFIRMED_IN_DATABASE |
| extensions | 1 (`plpgsql`, em pg_catalog) | CONFIRMED_IN_DATABASE |
| functions no schema | 3 | CONFIRMED_IN_DATABASE |
| triggers | 7 | CONFIRMED_IN_DATABASE |
| views | 0 | CONFIRMED_IN_DATABASE |
| materialized views | 0 | CONFIRMED_IN_DATABASE |
| grants de tabela | 3.641 | CONFIRMED_IN_DATABASE |

Owner do schema: `borgus`. O schema oficial é `farms`; o código do Alembic mantém `CREATE SCHEMA IF NOT EXISTS farms` e `SET search_path TO farms`. A introspecção confirmou que a extensão instalada é somente plpgsql; PostGIS não foi assumido.

### 6.1 Tabelas físicas

O inventário completo dos 351 nomes físicos retornado pelo catálogo foi:

```text
admin_audit_log, admin_impersonations, admin_users, agricola_devolucoes_embalagens, agricola_lotes_beneficiamento, agricola_operacao_tipo_fase, agricola_orcamento_itens, agricola_produto_colhido_cost_allocations, agricola_produtos_colhidos, agricola_receituario_itens, agricola_receituarios_agronomicos, agricola_regras_agronomicas, alembic_version, alert_events, alert_indicators, alert_insights, alert_lifecycle_events, amb_alertas, amb_outorgas_hidricas, amb_registros_car, amostras, analises_solo, animal_genetica, assinaturas_tenant, automacoes_configuracoes, automacoes_execucoes, balanca_afericoes, balanca_avaliacoes_prestador, balanca_dispositivos, balanca_fisicas, balanca_inbound_events, balanca_operadores, balanca_ordens, balanca_pesagens, balanca_sync_tombstones, balanca_webhook_credentials, billing_solicitacoes_comerciais, billing_solicitacoes_comerciais_historico, cadastros_areas_registros_ambientais, cadastros_areas_rurais, cadastros_areas_valores_patrimoniais, cadastros_arquivos_geo, cadastros_categorias_produto, cadastros_commodities, cadastros_commodities_classificacoes, cadastros_commodities_cotacoes, cadastros_conversao_unidades, cadastros_culturas, cadastros_documentos_exploracao, cadastros_equipamentos, cadastros_equipamentos_calibracoes, cadastros_exploracoes_rurais, cadastros_infraestruturas, cadastros_marcas, cadastros_modelos_produto, cadastros_pessoa_relacionamentos, cadastros_pessoas, cadastros_pessoas_acesso_log, cadastros_pessoas_bancario, cadastros_pessoas_consentimentos, cadastros_pessoas_contatos, cadastros_pessoas_documentos, cadastros_pessoas_enderecos, cadastros_pessoas_pii, cadastros_pessoas_profissional_agronomo, cadastros_produtos, cadastros_produtos_agricola, cadastros_produtos_epi, cadastros_produtos_estoque, cadastros_propriedades, cadastros_tipos_irrigacao, cadastros_tipos_relacionamento, cadastros_tipos_servico, cadastros_tipos_solo, caderno_campo_entradas, caderno_campo_fotos, caderno_evento_status_historico, caderno_exportacoes, caderno_lotes_comerciais, cafe_lote_beneficiamento_detalhes, cafe_lote_beneficiamento_romaneios, campo_dispositivos, campo_sync_tombstones, campo_tarefas, carbono_emissoes, carbono_projetos, carbono_relatorios, case_ih, categoria_custom, certificacao_avaliacoes, certificacao_checklists, certificacao_criterios, certificacao_evidencias, certificacao_nao_conformidades, certificacao_planos_acao, certificacao_programas, certificacoes_propriedade, chamados_suporte, cobrancas_asaas, cochos, comparador_precos, compras_alocacoes_item, compras_cotacoes, compras_cotacoes_itens, compras_devolucoes, compras_devolucoes_itens, compras_fornecedores, compras_itens_pedido, compras_pedidos, compras_pedidos_confirmacoes, compras_pedidos_cotacoes, compras_recebimentos, compras_recebimentos_itens, compras_solicitacoes, compras_solicitacoes_itens, configuracao_fazenda, configuracoes_saas, configuracoes_tenant, confinamento_lotes, conhecimento_artigos, conhecimento_categorias, contratos_futuros_v2, conversas_agronomo, convites_acesso, core_sequenciais, cost_allocations, crm_atividades, crm_leads, crm_pipeline_estagios, cultivo_areas, cultivos, culturas, cupons, diagnosticos, domain_event_outbox, email_logs, email_templates, epi_entregas, equipamento_alocacoes, esg_relatorio_evidencias, esg_relatorio_indicadores, esg_relatorios, estoque_contagem_itens, estoque_contagens, estoque_depositos, estoque_implantacao_itens, estoque_implantacao_sessoes, estoque_localizacoes, estoque_lotes, estoque_movimentos, estoque_requisicao_confirmacoes, estoque_requisicoes, estoque_requisicoes_itens, estoque_reservas, estoque_saldos, faturas, fenologia_escalas, fin_contas_bancarias, fin_despesas, fin_itens_ordem_pagamento, fin_lancamentos_bancarios, fin_notas_fiscais, fin_ordens_pagamento, fin_planos_conta, fin_rateios, fin_receitas, financeiro_comercializacoes, financeiro_lancamentos, financeiro_plano_acoes, financeiro_safra_cenarios, frota_abastecimentos, frota_apontamentos_uso, frota_checklist_modelos, frota_checklists_operacionais, frota_checklists_operacionais_itens, frota_checklists_operacionais_respostas, frota_checklists_realizados, frota_documentos_equipamentos, frota_jornadas_equipamento, frota_logs_automacao, frota_ordens_servico, frota_os_itens, frota_planos_manutencao, frota_registros_manutencao, frota_regras_inteligentes, hedge_position_snapshots_v2, hedge_registros_v2, historico_bloqueios, historico_configuracao, ia_acoes_assistidas_historico, ia_alertas_historico, ia_autopilot_config, ia_compras_recomendacoes, ia_creditos_pacotes, ia_growth_assistente_interacoes, ia_growth_autopilot_acoes, ia_growth_config, ia_growth_config_historico, ia_growth_copy_cache, ia_growth_eventos, ia_growth_experimento_eventos, ia_growth_experimento_variantes, ia_growth_experimentos, ia_growth_incentivos, ia_growth_learning_weights, ia_growth_plano_recomendado_log, ia_growth_sugestoes, ia_growth_user_profiles, ia_prompt_versoes_historico, ia_prompts_versoes, ia_uso, ia_ux_telemetria, ia_ux_thresholds, imagens_ndvi, imoveis_arrendamento_parcelas, imoveis_arrendamento_reajustes, imoveis_arrendamentos, imoveis_avaliacoes, imoveis_benfeitorias, imoveis_cartorios, imoveis_documentos, imoveis_documentos_historico, imoveis_matriculas, imoveis_ordens_servico_benfeitoria, imoveis_planos_manutencao_benfeitoria, imoveis_rurais, imoveis_sistemas_irrigacao, insumos_operacao, integration_credentials, integration_external_record_link_history, integration_external_record_links, integration_features, integration_health_snapshots, integration_jobs, integration_sync_policies, integration_versions, john_deere, login_tentativas, lotes_rastreabilidade, mapas_fertilidade, marketplace_integracoes, mensagens_chamado, modelos_fitossanitarios, modelos_ml, modelos_zoosanitarios, module_usage_stats, monitoramento_catalogo, monitoramento_pragas, mudancas_plano, notificacoes, notificacoes_leituras, notificacoes_preferencias, operacional_apontamentos_mao_obra, operacional_qualidade_ajustes, operacional_qualidade_criterios, operacional_qualidade_laudos, operacional_qualidade_protocolos, operacional_qualidade_resultados, operacoes_agricolas, operacoes_execucoes, operation_dependencies, operation_template_items, operation_templates, operational_alerts, pec_animais, pec_eventos_animal, pec_lotes, pec_manejos_lote, pec_piquetes, pec_producao_leite, perfis_acesso, phase_gate_rules, phase_template_checklist_items, phase_template_tasks, phase_templates, plano_pricing, planos_assinatura, planos_operacionais, planos_operacionais_tarefas, planos_operacionais_tarefas_insumos, planos_operacionais_tarefas_mao_obra, planos_operacionais_tarefas_maquinario, pragas_doencas, prescricoes_vra, previsoes_clima, previsoes_produtividade, production_units, propriedade_imovel, racas, racoes_tmr, rastreabilidade_passaporte_eventos, rastreabilidade_passaporte_evidencias, rastreabilidade_passaportes, receitas_aplicacao, receitas_aplicacao_insumos, receitas_aplicacao_mao_obra, recomendacoes, recommendation_lifecycle_events, recommendation_results, registros_clima, relatorios_tecnicos, rh_colaboradores, rh_departamentos, rh_empreitadas, rh_esocial_eventos, rh_lancamentos_diarias, rh_seguranca_documentos, rh_seguranca_entregas, rh_seguranca_itens, romaneios_colheita, safra_cenarios, safra_cenarios_unidades, safra_checklist_itens, safra_fase_historico, safra_fenologia_registros, safra_talhao_grupo_itens, safra_talhao_grupos, safra_talhoes, safra_tarefa_necessidades, safra_tarefas, safras, sankhya_config, sankhya_lancamentos_financeiros, sankhya_nfe, sankhya_pessoas, sankhya_produtos, sankhya_sync_logs, sankhya_tabelas, sessoes_ativas, solo_parametros_cultura, status_consorcio_area, sugestoes_acasalamento, tenant_audit_log, tenant_integracoes, tenant_usuarios, tenants, territory_legacy_backup_01h2, tokens_recuperacao_senha, tratamentos, unidade_produtiva_usuarios, unidades_medida, unidades_medida_conversoes, unidades_produtivas, usuarios, visitas_tecnicas, whatsapp, wizard_implantacoes_checklist_itens, wizard_implantacoes_etapas, wizard_implantacoes_historico, wizard_implantacoes_operacionais, wizard_implantacoes_pendencias
```

### 6.2 ENUMs e valores

```text
metodoavaliacaoimovel = MERCADO, CUSTO, RENDA, DECLARADO, LAUDO
periodicidade = MENSAL, SEMESTRAL, ANUAL, SAFRA
prioridade_plano_acao_enum = BAIXA, MEDIA, ALTA, URGENTE
resultado_avaliacao_enum = APROVADO, APROVADO_COM_RESSALVA, REPROVADO, PENDENTE
severidade_nao_conformidade_enum = MENOR, MAIOR, CRITICA
severidadealerta = BAIXA, MEDIA, ALTA, CRITICA
situacaoimovel = REGULAR, PENDENTE, IRREGULAR
status_checklist_enum = RASCUNHO, PUBLICADO, ARQUIVADO
status_nao_conformidade_enum = ABERTA, EM_ANALISE, EM_CORRECAO, RESOLVIDA, CANCELADA
status_passaporte_enum = RASCUNHO, ATIVO, REVOGADO, EM_VALIDACAO, PUBLICADO
status_plano_acao_enum = PENDENTE, EM_ANDAMENTO, CONCLUIDO, ATRASADO, CANCELADO
status_programa_enum = ATIVO, INATIVO, SUSPENSO
status_relatorio_esg_enum = RASCUNHO, EM_REVISAO, PUBLICADO, ARQUIVADO, CANCELADO
statusalerta = NOVO, EM_ANALISE, RESOLVIDO, IGNORADO
statuscar = ATIVO, PENDENTE, CANCELADO, SUSPENSO, EM_ANALISE
statuscontrato = ATIVO, ENCERRADO, RESCINDIDO, SUSPENSO
statusdocumento = ATIVO, SUBSTITUIDO, VENCIDO, CANCELADO
statusoutorga = ATIVA, VENCIDA, SUSPENSA, CANCELADA, EM_RENOVACAO
statusparcela = PREVISTA, PAGA, CANCELADA, VENCIDA
statussefaz = EM_DIGITACAO, ASSINADA, TRANSMITIDA, AUTORIZADA, CANCELADA, DENEGADA, INUTILIZADA
ticketpriority = BAIXA, MEDIA, ALTA, URGENTE
ticketstatus = ABERTO, EM_ATENDIMENTO, AGUARDANDO_CLIENTE, CONCLUIDO, CANCELADO
tipo_certificacao_enum = ORGANICO, GLOBALGAP, REGENAGRI, ESG_INTERNO, OUTRO
tipo_evento_passaporte_enum = GERADO, VALIDADO, PUBLICADO, REVOGADO, ATUALIZADO
tipo_evidencia_enum = DOCUMENTO_PDF, FOTO_CAMPO, DADO_SATELITE, OUTRO
tipoalerta = DESMATAMENTO, QUEIMADA, INUNDACAO, EROSAO, OUTRO
tipoarrendatario = PESSOA_FISICA, PESSOA_JURIDICA, FAZENDA_TENANT
tipocategoria = despesa, receita, operacao, produto, insumo
tipocontrato = ARRENDAMENTO, PARCERIA
tipodocumento = CCIR, ITR_DITR, CAR, ESCRITURA, MATRICULA, GEOREFERENCIAMENTO, OUTRO
tipoimovel = RURAL, PARTICULAR, DEVOLUTA, POSSE
tiponf = NFP_E, NF_E, NFC_E
tipousooutorga = IRRIGACAO, DESSEDENTACAO, USO_INDUSTRIAL, AQUICULTURA, OUTRO
valormodalidade = FIXO_BRL, FIXO_SACAS, PERCENTUAL
```

### 6.3 Sequences

```text
amostras_id_seq, animal_genetica_id_seq, balanca_webhook_credentials_id_seq, carbono_emissoes_id_seq, carbono_projetos_id_seq, carbono_relatorios_id_seq, case_ih_id_seq, cochos_id_seq, comparador_precos_id_seq, confinamento_lotes_id_seq, diagnosticos_id_seq, integration_credentials_id_seq, integration_features_id_seq, integration_health_snapshots_id_seq, integration_sync_policies_id_seq, integration_versions_id_seq, john_deere_id_seq, mapas_fertilidade_id_seq, marketplace_integracoes_id_seq, modelos_ml_id_seq, pragas_doencas_id_seq, racas_id_seq, racoes_tmr_id_seq, recomendacoes_id_seq, sankhya_config_id_seq, sankhya_lancamentos_financeiros_id_seq, sankhya_nfe_id_seq, sankhya_pessoas_id_seq, sankhya_produtos_id_seq, sankhya_tabelas_id_seq, sugestoes_acasalamento_id_seq, tenant_integracoes_id_seq, territory_legacy_backup_01h2_id_seq, tratamentos_id_seq, whatsapp_id_seq
```

### 6.4 RLS e policies

RLS ENABLED foi confirmado nas tabelas:

```text
alert_events, alert_indicators, alert_insights, alert_lifecycle_events, amb_alertas, amb_outorgas_hidricas, amb_registros_car, balanca_inbound_events, balanca_webhook_credentials, carbono_emissoes, carbono_projetos, carbono_relatorios, certificacao_avaliacoes, certificacao_checklists, certificacao_criterios, certificacao_evidencias, certificacao_nao_conformidades, certificacao_planos_acao, certificacao_programas, configuracao_fazenda, domain_event_outbox, esg_relatorio_evidencias, esg_relatorio_indicadores, esg_relatorios, integration_credentials, integration_external_record_link_history, integration_external_record_links, integration_features, integration_health_snapshots, integration_jobs, integration_sync_policies, integration_versions, modelos_fitossanitarios, modelos_zoosanitarios, operational_alerts, previsoes_clima, propriedade_imovel, rastreabilidade_passaporte_eventos, rastreabilidade_passaporte_evidencias, rastreabilidade_passaportes, recommendation_lifecycle_events, recommendation_results, registros_clima, tenant_integracoes, wizard_implantacoes_checklist_itens, wizard_implantacoes_etapas, wizard_implantacoes_historico, wizard_implantacoes_operacionais, wizard_implantacoes_pendencias
```

RLS FORCED foi confirmado nas tabelas:

```text
alert_events, alert_indicators, alert_insights, alert_lifecycle_events, amb_alertas, amb_outorgas_hidricas, amb_registros_car, balanca_inbound_events, balanca_webhook_credentials, carbono_emissoes, carbono_projetos, carbono_relatorios, certificacao_avaliacoes, certificacao_checklists, certificacao_criterios, certificacao_evidencias, certificacao_nao_conformidades, certificacao_planos_acao, certificacao_programas, configuracao_fazenda, domain_event_outbox, esg_relatorio_evidencias, esg_relatorio_indicadores, esg_relatorios, integration_credentials, integration_external_record_link_history, integration_external_record_links, integration_features, integration_health_snapshots, integration_jobs, integration_sync_policies, integration_versions, modelos_fitossanitarios, modelos_zoosanitarios, operational_alerts, previsoes_clima, rastreabilidade_passaporte_eventos, rastreabilidade_passaporte_evidencias, rastreabilidade_passaportes, recommendation_lifecycle_events, recommendation_results, registros_clima, tenant_integracoes, wizard_implantacoes_checklist_itens, wizard_implantacoes_etapas, wizard_implantacoes_historico, wizard_implantacoes_operacionais, wizard_implantacoes_pendencias
```

Policies confirmadas (188):

```text
alert_events:alert_events_delete_tenant, alert_events:alert_events_insert_tenant, alert_events:alert_events_select_tenant, alert_events:alert_events_update_tenant, alert_indicators:alert_indicators_delete_tenant, alert_indicators:alert_indicators_insert_tenant, alert_indicators:alert_indicators_select_tenant, alert_indicators:alert_indicators_update_tenant, alert_insights:alert_insights_delete_tenant, alert_insights:alert_insights_insert_tenant, alert_insights:alert_insights_select_tenant, alert_insights:alert_insights_update_tenant, alert_lifecycle_events:alert_lifecycle_events_delete_tenant, alert_lifecycle_events:alert_lifecycle_events_insert_tenant, alert_lifecycle_events:alert_lifecycle_events_select_tenant, alert_lifecycle_events:alert_lifecycle_events_update_tenant, amb_alertas:amb_alertas_tenant_delete, amb_alertas:amb_alertas_tenant_insert, amb_alertas:amb_alertas_tenant_select, amb_alertas:amb_alertas_tenant_update, amb_outorgas_hidricas:amb_outorgas_hidricas_tenant_delete, amb_outorgas_hidricas:amb_outorgas_hidricas_tenant_insert, amb_outorgas_hidricas:amb_outorgas_hidricas_tenant_select, amb_outorgas_hidricas:amb_outorgas_hidricas_tenant_update, amb_registros_car:amb_registros_car_tenant_delete, amb_registros_car:amb_registros_car_tenant_insert, amb_registros_car:amb_registros_car_tenant_select, amb_registros_car:amb_registros_car_tenant_update, balanca_inbound_events:balanca_inbound_events_tenant, balanca_webhook_credentials:balanca_webhook_credentials_tenant, carbono_emissoes:carbono_emissoes_tenant_delete, carbono_emissoes:carbono_emissoes_tenant_insert, carbono_emissoes:carbono_emissoes_tenant_select, carbono_emissoes:carbono_emissoes_tenant_update, carbono_projetos:carbono_projetos_tenant_delete, carbono_projetos:carbono_projetos_tenant_insert, carbono_projetos:carbono_projetos_tenant_select, carbono_projetos:carbono_projetos_tenant_update, carbono_relatorios:carbono_relatorios_tenant_delete, carbono_relatorios:carbono_relatorios_tenant_insert, carbono_relatorios:carbono_relatorios_tenant_select, carbono_relatorios:carbono_relatorios_tenant_update, certificacao_avaliacoes:certificacao_avaliacoes_delete_tenant, certificacao_avaliacoes:certificacao_avaliacoes_insert_tenant, certificacao_avaliacoes:certificacao_avaliacoes_select_tenant, certificacao_avaliacoes:certificacao_avaliacoes_update_tenant, certificacao_checklists:certificacao_checklists_delete_tenant, certificacao_checklists:certificacao_checklists_insert_tenant, certificacao_checklists:certificacao_checklists_select_tenant, certificacao_checklists:certificacao_checklists_update_tenant, certificacao_criterios:certificacao_criterios_delete_tenant, certificacao_criterios:certificacao_criterios_insert_tenant, certificacao_criterios:certificacao_criterios_select_tenant, certificacao_criterios:certificacao_criterios_update_tenant, certificacao_evidencias:certificacao_evidencias_delete_tenant, certificacao_evidencias:certificacao_evidencias_insert_tenant, certificacao_evidencias:certificacao_evidencias_select_tenant, certificacao_evidencias:certificacao_evidencias_update_tenant, certificacao_nao_conformidades:certificacao_nao_conformidades_delete_tenant, certificacao_nao_conformidades:certificacao_nao_conformidades_insert_tenant, certificacao_nao_conformidades:certificacao_nao_conformidades_select_tenant, certificacao_nao_conformidades:certificacao_nao_conformidades_update_tenant, certificacao_planos_acao:certificacao_planos_acao_delete_tenant, certificacao_planos_acao:certificacao_planos_acao_insert_tenant, certificacao_planos_acao:certificacao_planos_acao_select_tenant, certificacao_planos_acao:certificacao_planos_acao_update_tenant, certificacao_programas:certificacao_programas_delete_tenant, certificacao_programas:certificacao_programas_insert_tenant, certificacao_programas:certificacao_programas_select_tenant, certificacao_programas:certificacao_programas_update_tenant, configuracao_fazenda:configuracao_fazenda_delete_tenant, configuracao_fazenda:configuracao_fazenda_insert_tenant, configuracao_fazenda:configuracao_fazenda_select_tenant, configuracao_fazenda:configuracao_fazenda_update_tenant, domain_event_outbox:farms_domain_event_outbox_delete_tenant, domain_event_outbox:farms_domain_event_outbox_insert_tenant, domain_event_outbox:farms_domain_event_outbox_select_tenant, domain_event_outbox:farms_domain_event_outbox_update_tenant, esg_relatorio_evidencias:esg_relatorio_evidencias_delete_tenant, esg_relatorio_evidencias:esg_relatorio_evidencias_insert_tenant, esg_relatorio_evidencias:esg_relatorio_evidencias_select_tenant, esg_relatorio_evidencias:esg_relatorio_evidencias_update_tenant, esg_relatorio_indicadores:esg_relatorio_indicadores_delete_tenant, esg_relatorio_indicadores:esg_relatorio_indicadores_insert_tenant, esg_relatorio_indicadores:esg_relatorio_indicadores_select_tenant, esg_relatorio_indicadores:esg_relatorio_indicadores_update_tenant, esg_relatorios:esg_relatorios_delete_tenant, esg_relatorios:esg_relatorios_insert_tenant, esg_relatorios:esg_relatorios_select_tenant, esg_relatorios:esg_relatorios_update_tenant, integration_credentials:farms_integration_credentials_delete_tenant, integration_credentials:farms_integration_credentials_insert_tenant, integration_credentials:farms_integration_credentials_select_tenant, integration_credentials:farms_integration_credentials_update_tenant, integration_external_record_link_history:farms_integration_external_record_link_history_delete_tenant, integration_external_record_link_history:farms_integration_external_record_link_history_insert_tenant, integration_external_record_link_history:farms_integration_external_record_link_history_select_tenant, integration_external_record_link_history:farms_integration_external_record_link_history_update_tenant, integration_external_record_links:farms_integration_external_record_links_delete_tenant, integration_external_record_links:farms_integration_external_record_links_insert_tenant, integration_external_record_links:farms_integration_external_record_links_select_tenant, integration_external_record_links:farms_integration_external_record_links_update_tenant, integration_features:farms_integration_features_delete_tenant, integration_features:farms_integration_features_insert_tenant, integration_features:farms_integration_features_select_tenant, integration_features:farms_integration_features_update_tenant, integration_health_snapshots:farms_integration_health_snapshots_delete_tenant, integration_health_snapshots:farms_integration_health_snapshots_insert_tenant, integration_health_snapshots:farms_integration_health_snapshots_select_tenant, integration_health_snapshots:farms_integration_health_snapshots_update_tenant, integration_jobs:farms_integration_jobs_delete_tenant, integration_jobs:farms_integration_jobs_insert_tenant, integration_jobs:farms_integration_jobs_select_tenant, integration_jobs:farms_integration_jobs_update_tenant, integration_sync_policies:farms_integration_sync_policies_delete_tenant, integration_sync_policies:farms_integration_sync_policies_insert_tenant, integration_sync_policies:farms_integration_sync_policies_select_tenant, integration_sync_policies:farms_integration_sync_policies_update_tenant, integration_versions:farms_integration_versions_delete_tenant, integration_versions:farms_integration_versions_insert_tenant, integration_versions:farms_integration_versions_select_tenant, integration_versions:farms_integration_versions_update_tenant, modelos_fitossanitarios:modelos_fitossanitarios_delete, modelos_fitossanitarios:modelos_fitossanitarios_insert, modelos_fitossanitarios:modelos_fitossanitarios_select, modelos_fitossanitarios:modelos_fitossanitarios_update, modelos_zoosanitarios:modelos_zoosanitarios_delete, modelos_zoosanitarios:modelos_zoosanitarios_insert, modelos_zoosanitarios:modelos_zoosanitarios_select, modelos_zoosanitarios:modelos_zoosanitarios_update, operational_alerts:operational_alerts_delete_tenant, operational_alerts:operational_alerts_insert_tenant, operational_alerts:operational_alerts_select_tenant, operational_alerts:operational_alerts_update_tenant, previsoes_clima:previsoes_clima_delete_tenant, previsoes_clima:previsoes_clima_insert_tenant, previsoes_clima:previsoes_clima_select_tenant, previsoes_clima:previsoes_clima_update_tenant, propriedade_imovel:propriedade_imovel_delete_policy, propriedade_imovel:propriedade_imovel_insert_policy, propriedade_imovel:propriedade_imovel_select_policy, propriedade_imovel:propriedade_imovel_update_policy, rastreabilidade_passaporte_eventos:rastreabilidade_passaporte_eventos_delete_tenant, rastreabilidade_passaporte_eventos:rastreabilidade_passaporte_eventos_insert_tenant, rastreabilidade_passaporte_eventos:rastreabilidade_passaporte_eventos_select_tenant, rastreabilidade_passaporte_eventos:rastreabilidade_passaporte_eventos_update_tenant, rastreabilidade_passaporte_evidencias:rastreabilidade_passaporte_evidencias_delete_tenant, rastreabilidade_passaporte_evidencias:rastreabilidade_passaporte_evidencias_insert_tenant, rastreabilidade_passaporte_evidencias:rastreabilidade_passaporte_evidencias_select_tenant, rastreabilidade_passaporte_evidencias:rastreabilidade_passaporte_evidencias_update_tenant, rastreabilidade_passaportes:rastreabilidade_passaportes_delete_tenant, rastreabilidade_passaportes:rastreabilidade_passaportes_insert_tenant, rastreabilidade_passaportes:rastreabilidade_passaportes_select_tenant, rastreabilidade_passaportes:rastreabilidade_passaportes_update_tenant, recommendation_lifecycle_events:recommendation_lifecycle_events_delete_tenant, recommendation_lifecycle_events:recommendation_lifecycle_events_insert_tenant, recommendation_lifecycle_events:recommendation_lifecycle_events_select_tenant, recommendation_lifecycle_events:recommendation_lifecycle_events_update_tenant, recommendation_results:recommendation_results_delete_tenant, recommendation_results:recommendation_results_insert_tenant, recommendation_results:recommendation_results_select_tenant, recommendation_results:recommendation_results_update_tenant, registros_clima:registros_clima_delete_tenant, registros_clima:registros_clima_insert_tenant, registros_clima:registros_clima_select_tenant, registros_clima:registros_clima_update_tenant, tenant_integracoes:farms_tenant_integracoes_delete_tenant, tenant_integracoes:farms_tenant_integracoes_insert_tenant, tenant_integracoes:farms_tenant_integracoes_select_tenant, tenant_integracoes:farms_tenant_integracoes_update_tenant, wizard_implantacoes_checklist_itens:farms_wizard_implantacoes_checklist_itens_delete_tenant, wizard_implantacoes_checklist_itens:farms_wizard_implantacoes_checklist_itens_insert_tenant, wizard_implantacoes_checklist_itens:farms_wizard_implantacoes_checklist_itens_select_tenant, wizard_implantacoes_checklist_itens:farms_wizard_implantacoes_checklist_itens_update_tenant, wizard_implantacoes_etapas:farms_wizard_implantacoes_etapas_delete_tenant, wizard_implantacoes_etapas:farms_wizard_implantacoes_etapas_insert_tenant, wizard_implantacoes_etapas:farms_wizard_implantacoes_etapas_select_tenant, wizard_implantacoes_etapas:farms_wizard_implantacoes_etapas_update_tenant, wizard_implantacoes_historico:farms_wizard_implantacoes_historico_insert_tenant, wizard_implantacoes_historico:farms_wizard_implantacoes_historico_select_tenant, wizard_implantacoes_operacionais:farms_wizard_implantacoes_operacionais_delete_tenant, wizard_implantacoes_operacionais:farms_wizard_implantacoes_operacionais_insert_tenant, wizard_implantacoes_operacionais:farms_wizard_implantacoes_operacionais_select_tenant, wizard_implantacoes_operacionais:farms_wizard_implantacoes_operacionais_update_tenant, wizard_implantacoes_pendencias:farms_wizard_implantacoes_pendencias_delete_tenant, wizard_implantacoes_pendencias:farms_wizard_implantacoes_pendencias_insert_tenant, wizard_implantacoes_pendencias:farms_wizard_implantacoes_pendencias_select_tenant, wizard_implantacoes_pendencias:farms_wizard_implantacoes_pendencias_update_tenant
```

As expressões USING/WITH CHECK, comandos, roles e permissividade foram lidos de pg_policies e devem ser transcritos sem simplificação na especificação DDL. Tenant Integrity e o isolamento por tenant permanecem preservados; esta fase não redesenha policies.

### 6.5 Functions, triggers, views, extensions e grants

Functions confirmadas: fn_estoque_movimentos_append_only, fn_production_units_refresh_status, fn_production_units_valida_soma.

Triggers confirmados: estoque_movimentos:tg_estoque_movimentos_append_only, estoque_movimentos:tg_estoque_movimentos_append_only, production_units:tg_production_units_refresh_status, production_units:tg_production_units_refresh_status, production_units:tg_production_units_refresh_status, production_units:tg_production_units_valida_soma, production_units:tg_production_units_valida_soma.

Views: nenhuma. Materialized views: nenhuma.

Extension confirmada: plpgsql 1.0 em pg_catalog. Grants relevantes contabilizados: 3.641 concessões de tabela; a baseline deve selecionar somente grants necessários à aplicação, não privilégios administrativos do ambiente.

## 7. BASELINE NON-ORM OBJECT SET

O conjunto non-ORM confirmado para a futura baseline é: schema farms; 35 tipos ENUM e seus valores/ordem; 35 sequences e ownership; PK/FK/UNIQUE/CHECK; índices, inclusive parciais e expressões; RLS ENABLE/FORCE e 188 policies aprovadas; as três functions e sete triggers; extension obrigatória somente se a decisão de infraestrutura a exigir; e grants mínimos da aplicação. Não há views/materialized views.

Os detalhes de PK/FK/constraints/índices foram inventariados no PostgreSQL, mas ainda precisam ser comparados definição a definição com ORM e migrations para congelar o SQL final. Portanto, este conjunto está inventariado, mas não está autorizado a ser gerado automaticamente.

## 8. Comparação ORM × migrations × database

| caso | ORM | migrations | database | classificação |
|---|---|---|---|---|
| 339 models não pendentes do registry | presente | histórico variável | presente ou não conforme fotografia | UNKNOWN/MATCH a validar por definição |
| 5 modelos CRM/Growth promovidos | presente | presente | ausente | MIGRATION_ONLY; deployment físico ainda não aplicado |
| 12 models CODE_ONLY_NOT_DEPLOYED | presente | geralmente presente | ausente | MIGRATION_ONLY; excluído por decisão de produto |
| 8 models SUPERSEDED | geração antiga presente | histórico presente | ausência do nome antigo / v2 ou estrutura canônica presente | DIFFERENT_DEFINITION/SUPERSEDED |
| 9 DEAD/ORPHAN | presente | histórico ou nenhuma | ausente | ORM_ONLY ou MIGRATION_ONLY; excluído |
| 8 balanca_* antigas | ausente no ORM atual | migrations removidas no Git | presente | DATABASE_ONLY; DEEPFARMS_LEGACY |
| amostras/mapas_fertilidade | sem model atual aprovado | DDL/histórico | presente | DATABASE_ONLY |
| alembic_version | controle, não domínio | controle Alembic | presente | MATCH como objeto de controle |

Não foram feitas correções automáticas para diferenças de nullable, tipos, constraints ou policies. Ausência de uma migration atual não foi interpretada como ausência física.

## 9. BASELINE ORM TABLE SET congelado

Contagem final proposta: **344 tabelas ORM**. A lista completa é:

```text
admin_audit_log, admin_impersonations, admin_users, agricola_devolucoes_embalagens, agricola_lotes_beneficiamento, agricola_operacao_tipo_fase, agricola_orcamento_itens, agricola_produto_colhido_cost_allocations, agricola_produtos_colhidos, agricola_receituario_itens, agricola_receituarios_agronomicos, agricola_regras_agronomicas, alert_events, alert_indicators, alert_insights, alert_lifecycle_events, amb_alertas, amb_outorgas_hidricas, amb_registros_car, analises_solo, animal_genetica, assinaturas_tenant, automacoes_configuracoes, automacoes_execucoes, balanca_inbound_events, balanca_webhook_credentials, billing_solicitacoes_comerciais, billing_solicitacoes_comerciais_historico, cadastros_areas_registros_ambientais, cadastros_areas_rurais, cadastros_areas_valores_patrimoniais, cadastros_arquivos_geo, cadastros_categorias_produto, cadastros_commodities, cadastros_commodities_classificacoes, cadastros_commodities_cotacoes, cadastros_conversao_unidades, cadastros_culturas, cadastros_documentos_exploracao, cadastros_equipamentos, cadastros_equipamentos_calibracoes, cadastros_exploracoes_rurais, cadastros_infraestruturas, cadastros_marcas, cadastros_modelos_produto, cadastros_pessoa_relacionamentos, cadastros_pessoas, cadastros_pessoas_acesso_log, cadastros_pessoas_bancario, cadastros_pessoas_consentimentos, cadastros_pessoas_contatos, cadastros_pessoas_documentos, cadastros_pessoas_enderecos, cadastros_pessoas_pii, cadastros_pessoas_profissional_agronomo, cadastros_produtos, cadastros_produtos_agricola, cadastros_produtos_epi, cadastros_produtos_estoque, cadastros_propriedades, cadastros_tipos_irrigacao, cadastros_tipos_relacionamento, cadastros_tipos_servico, cadastros_tipos_solo, caderno_campo_entradas, caderno_campo_fotos, caderno_evento_status_historico, caderno_exportacoes, caderno_lotes_comerciais, cafe_lote_beneficiamento_detalhes, cafe_lote_beneficiamento_romaneios, campo_dispositivos, campo_sync_tombstones, campo_tarefas, carbono_emissoes, carbono_projetos, carbono_relatorios, case_ih, categoria_custom, certificacao_avaliacoes, certificacao_checklists, certificacao_criterios, certificacao_evidencias, certificacao_nao_conformidades, certificacao_planos_acao, certificacao_programas, certificacoes_propriedade, chamados_suporte, cobrancas_asaas, cochos, comparador_precos, compras_alocacoes_item, compras_cotacoes, compras_cotacoes_itens, compras_devolucoes, compras_devolucoes_itens, compras_fornecedores, compras_itens_pedido, compras_pedidos, compras_pedidos_confirmacoes, compras_pedidos_cotacoes, compras_recebimentos, compras_recebimentos_itens, compras_solicitacoes, compras_solicitacoes_itens, configuracao_fazenda, configuracoes_saas, configuracoes_tenant, confinamento_lotes, conhecimento_artigos, conhecimento_categorias, contratos_futuros_v2, conversas_agronomo, convites_acesso, core_sequenciais, cost_allocations, crm_atividades, crm_leads, crm_ofertas_personalizadas, crm_pipeline_estagios, crm_planos_comerciais, crm_precificacao_modulo, crm_produtos, cultivo_areas, cultivos, culturas, cupons, diagnosticos, domain_event_outbox, email_logs, email_templates, epi_entregas, equipamento_alocacoes, esg_relatorio_evidencias, esg_relatorio_indicadores, esg_relatorios, estoque_contagem_itens, estoque_contagens, estoque_depositos, estoque_implantacao_itens, estoque_implantacao_sessoes, estoque_localizacoes, estoque_lotes, estoque_movimentos, estoque_requisicao_confirmacoes, estoque_requisicoes, estoque_requisicoes_itens, estoque_reservas, estoque_saldos, faturas, fenologia_escalas, fin_contas_bancarias, fin_despesas, fin_itens_ordem_pagamento, fin_lancamentos_bancarios, fin_notas_fiscais, fin_ordens_pagamento, fin_planos_conta, fin_rateios, fin_receitas, financeiro_comercializacoes, financeiro_lancamentos, financeiro_plano_acoes, financeiro_safra_cenarios, frota_abastecimentos, frota_apontamentos_uso, frota_checklist_modelos, frota_checklists_operacionais, frota_checklists_operacionais_itens, frota_checklists_operacionais_respostas, frota_checklists_realizados, frota_documentos_equipamentos, frota_jornadas_equipamento, frota_logs_automacao, frota_ordens_servico, frota_os_itens, frota_planos_manutencao, frota_registros_manutencao, frota_regras_inteligentes, growth_landing_eventos, hedge_position_snapshots_v2, hedge_registros_v2, historico_bloqueios, historico_configuracao, ia_acoes_assistidas_historico, ia_alertas_historico, ia_autopilot_config, ia_compras_recomendacoes, ia_creditos_pacotes, ia_growth_assistente_interacoes, ia_growth_autopilot_acoes, ia_growth_config, ia_growth_config_historico, ia_growth_copy_cache, ia_growth_eventos, ia_growth_experimento_eventos, ia_growth_experimento_variantes, ia_growth_experimentos, ia_growth_incentivos, ia_growth_learning_weights, ia_growth_plano_recomendado_log, ia_growth_sugestoes, ia_growth_user_profiles, ia_prompt_versoes_historico, ia_prompts_versoes, ia_uso, ia_ux_telemetria, ia_ux_thresholds, imagens_ndvi, imoveis_arrendamento_parcelas, imoveis_arrendamento_reajustes, imoveis_arrendamentos, imoveis_avaliacoes, imoveis_benfeitorias, imoveis_cartorios, imoveis_documentos, imoveis_documentos_historico, imoveis_matriculas, imoveis_ordens_servico_benfeitoria, imoveis_planos_manutencao_benfeitoria, imoveis_rurais, imoveis_sistemas_irrigacao, insumos_operacao, integration_credentials, integration_external_record_link_history, integration_external_record_links, integration_features, integration_health_snapshots, integration_jobs, integration_sync_policies, integration_versions, john_deere, login_tentativas, lotes_rastreabilidade, marketplace_integracoes, mensagens_chamado, modelos_fitossanitarios, modelos_ml, modelos_zoosanitarios, module_usage_stats, monitoramento_catalogo, monitoramento_pragas, mudancas_plano, notificacoes, notificacoes_leituras, notificacoes_preferencias, operacional_apontamentos_mao_obra, operacional_qualidade_ajustes, operacional_qualidade_criterios, operacional_qualidade_laudos, operacional_qualidade_protocolos, operacional_qualidade_resultados, operacoes_agricolas, operacoes_execucoes, operation_dependencies, operation_template_items, operation_templates, operational_alerts, pec_animais, pec_eventos_animal, pec_lotes, pec_manejos_lote, pec_piquetes, pec_producao_leite, perfis_acesso, phase_gate_rules, phase_template_checklist_items, phase_template_tasks, phase_templates, plano_pricing, planos_assinatura, planos_operacionais, planos_operacionais_tarefas, planos_operacionais_tarefas_insumos, planos_operacionais_tarefas_mao_obra, planos_operacionais_tarefas_maquinario, pragas_doencas, prescricoes_vra, previsoes_clima, previsoes_produtividade, production_units, propriedade_imovel, racas, racoes_tmr, rastreabilidade_passaporte_eventos, rastreabilidade_passaporte_evidencias, rastreabilidade_passaportes, receitas_aplicacao, receitas_aplicacao_insumos, receitas_aplicacao_mao_obra, recomendacoes, recommendation_lifecycle_events, recommendation_results, registros_clima, relatorios_tecnicos, rh_colaboradores, rh_departamentos, rh_empreitadas, rh_esocial_eventos, rh_lancamentos_diarias, rh_seguranca_documentos, rh_seguranca_entregas, rh_seguranca_itens, romaneios_colheita, safra_cenarios, safra_cenarios_unidades, safra_checklist_itens, safra_fase_historico, safra_fenologia_registros, safra_talhao_grupo_itens, safra_talhao_grupos, safra_talhoes, safra_tarefa_necessidades, safra_tarefas, safras, sankhya_config, sankhya_lancamentos_financeiros, sankhya_nfe, sankhya_pessoas, sankhya_produtos, sankhya_sync_logs, sankhya_tabelas, sessoes_ativas, solo_parametros_cultura, status_consorcio_area, sugestoes_acasalamento, tenant_audit_log, tenant_integracoes, tenant_usuarios, tenants, tokens_recuperacao_senha, tratamentos, unidade_produtiva_usuarios, unidades_medida, unidades_medida_conversoes, unidades_produtivas, usuarios, visitas_tecnicas, whatsapp, wizard_implantacoes_checklist_itens, wizard_implantacoes_etapas, wizard_implantacoes_historico, wizard_implantacoes_operacionais, wizard_implantacoes_pendencias
```

Ficam EXCLUDE da baseline ORM os 29 models abaixo, mas todos continuam no registry e no inventário:

```text
api_keys, api_logs, api_versions, arracoamentos, balanco_hidrico, benchmarks, colaborador_apontamentos, contratos_futuros, enterprise_esg_relatorios, esg_indicadores, estacoes_meteorologicas, hedge_registros, ilpf_modulos, imagens_satelite, integracao_new_holland, maquinas_new_holland, marketplace_avaliacoes, mrv_projetos, mrv_relatorios, ndvi_registros, pesagens, pontos, powerbi, preditivo, sap, sdks, sensores_iot, sensores_leituras, tanques_rede
```

As oito tabelas físicas antigas da Balança, amostras, mapas_fertilidade, territory_legacy_backup_01h2 e alembic_version não são incluídas nessa contagem ORM: alembic_version é objeto de controle; as demais ficam fora por decisão de legado/órfão/backup. Nenhuma exclusão implica DROP.

## 10. Registry e guardrails

O registry existente foi apenas atualizado em suas decisões: BASELINE_DECISIONS agora contém 34/34 decisões finais; BASELINE_EXCLUDED_TABLES deriva dessas decisões; baseline_candidate_tables() retorna 344; LEGACY_BALANCA_TABLES impede entrada acidental das oito tabelas antigas.

Testes atualizados comprovam: descoberta cobre todos os models, zero colisões, idempotência, contagem determinística 344, 34 decisões finais e exclusão das oito tabelas antigas da Balança.

## 11. Bootstrap e seed

`Base.metadata.create_all()` e `Base.metadata.drop_all()` continuam proibidos no bootstrap de produção/piloto. seed.py, init_postgres_schema.py e sync_db.py não foram redesenhados; não foram executados. A baseline futura deverá cuidar da estrutura, seguida por seed institucional, catálogo e demo/dev em fluxos separados.

## 12. Arquivos alterados

- `services/api/core/model_registry.py` — decisões finais e conjunto ORM congelado.
- `services/api/tests/unit/core/test_model_registry.py` — guardrails 01C.
- `docs/implementation/reports/MIGRATION-METADATA-01C-FECHAMENTO-PENDENCIAS-DDL.md` — contrato desta fase.

Não foram alteradas migrations históricas, banco, dados ou RDS. O script temporário de introspecção está em `/tmp/inspect_01c.py` e não pertence ao produto.

## 13. Testes e validações

- `PYTHONPATH=. .venv/bin/pytest -q tests/unit/core/test_model_registry.py`: 4 passed.
- `PYTHONPATH=. .venv/bin/python -m ruff check core/model_registry.py migrations/env.py tests/unit/core/test_model_registry.py`: All checks passed.
- A verificação ampla `ruff check ... tests/unit/core/` encontrou 146 problemas preexistentes em outros testes de core; não foram alterados nesta fase. Os arquivos alterados da 01C passaram no lint direcionado.
- `git diff --check`.
- `alembic heads`: uma head, `20260828_balanca_webhook_credentials`.
- Introspecção PostgreSQL read-only: concluída; nenhum DDL/DML.
- Não executados: upgrade, downgrade, autogenerate, create_all, drop_all.

## 14. Riscos restantes

- O contrato físico completo precisa ser convertido em DDL baseline revisado, principalmente políticas RLS, funções, triggers, sequences e diferenças de constraints/índices.
- O banco funcional contém 351 tabelas, incluindo objetos que não devem ser copiados automaticamente.
- As cinco tabelas promovidas estão ausentes na fotografia física e precisam de decisão de implantação já refletida no contrato, não de cópia de banco.
- A baseline ainda não foi criada nem validada contra PostgreSQL vazio.

## 15. Veredicto

Critérios: models descobertos 373; classificados 373; decisão de baseline 373/373; PENDING 0; collisions 0; ownership da Balança resolvido como DEEPFARMS_LEGACY; DDL físico inventariado; comparação iniciada, mas definição final ainda não congelada linha a linha.

Como ainda existe risco de divergência estrutural em constraints, índices, RLS/policies e DDL histórico, o contrato não está suficientemente fechado para autorizar a criação da baseline.

**MIGRATION-METADATA-01C**  
**STATUS: NO-GO**  
Próxima fase necessária: `MIGRATION-METADATA-01C.1 — Reconciliação DDL definição a definição e aprovação do contrato non-ORM`. Somente após essa aprovação poderá iniciar `MIGRATION-METADATA-01D — Construção e Validação da BASELINE-DEEPFARMS-V1`.
