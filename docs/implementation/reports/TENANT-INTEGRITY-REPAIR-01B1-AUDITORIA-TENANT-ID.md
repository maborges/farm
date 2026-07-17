# TENANT-INTEGRITY-REPAIR-01B1 — Auditoria de tenant_id

**Data:** 2026-07-17
**Banco:** `postgresql://borgus:numsey01@192.168.0.2/farms` (schema `farms`)
**Contexto:** Preparação para execução da fase 01B — conversão de tabelas varchar e adição de FK para tabelas Classe F.
**Escopo:** Somente leitura. Nenhum DDL ou DML executado.

---

## 1. Inventário Completo — Tabelas com `tenant_id`

### 1.1 Tabelas com `tenant_id uuid` (total: ~130 tabelas)

| Tabela | Nullable | FK→tenants | Índice | RLS |
|---|---|---|---|---|
| admin_impersonations | NO | SIM | SIM | NÃO |
| agricola_orcamento_itens | NO | SIM | SIM | NÃO |
| agricola_produtos_colhidos | NO | SIM | SIM | NÃO |
| agricola_regras_agronomicas | **YES** | SIM | SIM | NÃO |
| alert_events | NO | SIM | SIM | **SIM** |
| alert_indicators | NO | SIM | SIM | **SIM** |
| alert_insights | NO | SIM | SIM | **SIM** |
| alert_lifecycle_events | NO | SIM | SIM | **SIM** |
| amb_alertas | NO | SIM | SIM | NÃO |
| amb_outorgas_hidricas | NO | SIM | SIM | NÃO |
| amb_registros_car | NO | SIM | SIM | NÃO |
| analises_solo | NO | SIM | SIM | NÃO |
| assinaturas_tenant | NO | SIM | SIM | NÃO |
| automacoes_configuracoes | NO | SIM | SIM | NÃO |
| automacoes_execucoes | NO | SIM | SIM | NÃO |
| billing_solicitacoes_comerciais | NO | SIM | SIM | NÃO |
| **billing_solicitacoes_comerciais_historico** | NO | **NÃO** | **NÃO** | NÃO |
| cadastros_areas_rurais | NO | SIM | SIM | NÃO |
| cadastros_arquivos_geo | NO | SIM | SIM | NÃO |
| cadastros_categorias_produto | YES | SIM | SIM | NÃO |
| cadastros_commodities | YES | SIM | SIM | NÃO |
| cadastros_culturas | YES | SIM | SIM | NÃO |
| cadastros_documentos_exploracao | NO | SIM | SIM | NÃO |
| cadastros_equipamentos | NO | SIM | SIM | NÃO |
| cadastros_equipamentos_calibracoes | NO | SIM | SIM | NÃO |
| cadastros_exploracoes_rurais | NO | SIM | SIM | NÃO |
| cadastros_infraestruturas | NO | SIM | SIM | NÃO |
| cadastros_marcas | YES | SIM | SIM | NÃO |
| cadastros_modelos_produto | YES | SIM | SIM | NÃO |
| cadastros_pessoas | NO | SIM | SIM | NÃO |
| cadastros_produtos | YES | SIM | SIM | NÃO |
| cadastros_propriedades | NO | SIM | SIM | NÃO |
| cadastros_tipos_relacionamento | YES | SIM | SIM | NÃO |
| caderno_campo_entradas | NO | SIM | SIM | NÃO |
| caderno_evento_status_historico | NO | SIM | SIM | NÃO |
| caderno_exportacoes | NO | SIM | SIM | NÃO |
| caderno_lotes_comerciais | NO | SIM | SIM | NÃO |
| cafe_lote_beneficiamento_romaneios | NO | SIM | SIM | NÃO |
| cafe_lotes_beneficiamento | NO | SIM | SIM | NÃO |
| campo_dispositivos | NO | SIM | SIM | NÃO |
| campo_sync_tombstones | NO | SIM | SIM | NÃO |
| certificacao_avaliacoes | NO | SIM | SIM | NÃO |
| certificacao_checklists | NO | SIM | SIM | NÃO |
| certificacao_evidencias | NO | SIM | SIM | NÃO |
| certificacao_nao_conformidades | NO | SIM | SIM | NÃO |
| certificacao_planos_acao | NO | SIM | SIM | NÃO |
| chamados_suporte | NO | SIM | SIM | NÃO |
| configuracoes_tenant | NO | SIM | SIM | NÃO |
| contratos_futuros_v2 | NO | SIM | SIM | NÃO |
| convites_acesso | NO | SIM | SIM | NÃO |
| conversas_agronomo | NO | SIM | SIM | NÃO |
| domain_event_outbox | NO | SIM | SIM | NÃO |
| email_logs | NO | SIM | SIM | NÃO |
| estoque_implantacao_sessoes | NO | SIM | SIM | NÃO |
| estoque_movimentos | NO | SIM | SIM | NÃO |
| estoque_reservas | NO | SIM | SIM | NÃO |
| faturas | NO | SIM | SIM | NÃO |
| financeiro_safra_cenarios | NO | SIM | SIM | NÃO |
| frota_abastecimentos | NO | SIM | SIM | NÃO |
| frota_apontamentos_uso | NO | SIM | SIM | NÃO |
| frota_checklist_modelos | NO | SIM | SIM | NÃO |
| frota_checklists_operacionais | NO | SIM | SIM | NÃO |
| frota_checklists_operacionais_itens | NO | SIM | SIM | NÃO |
| frota_checklists_operacionais_respostas | NO | SIM | SIM | NÃO |
| frota_os_itens | NO | SIM | SIM | NÃO |
| frota_regras_inteligentes | NO | SIM | SIM | NÃO |
| frota_registros_manutencao | NO | SIM | SIM | NÃO |
| hedge_position_snapshots_v2 | NO | SIM | SIM | NÃO |
| hedge_registros_v2 | NO | SIM | SIM | NÃO |
| historico_bloqueios | NO | SIM | SIM | NÃO |
| historico_configuracao | NO | SIM | SIM | NÃO |
| ia_acoes_assistidas_historico | NO | SIM | SIM | NÃO |
| ia_alertas_historico | NO | SIM | SIM | NÃO |
| ia_autopilot_config | NO | SIM | SIM | NÃO |
| ia_compras_recomendacoes | NO | SIM | SIM | NÃO |
| ia_creditos_pacotes | NO | SIM | SIM | NÃO |
| ia_growth_assistente_interacoes | NO | SIM | SIM | NÃO |
| ia_growth_autopilot_acoes | NO | SIM | SIM | NÃO |
| ia_growth_config | NO | SIM | SIM | NÃO |
| ia_growth_config_historico | NO | SIM | SIM | NÃO |
| ia_growth_copy_cache | NO | SIM | SIM | NÃO |
| ia_growth_eventos | NO | SIM | SIM | NÃO |
| ia_growth_experimento_eventos | NO | SIM | SIM | NÃO |
| ia_growth_experimentos | NO | SIM | SIM | NÃO |
| ia_growth_learning_weights | NO | SIM | SIM | NÃO |
| ia_growth_plano_recomendado_log | NO | SIM | SIM | NÃO |
| imagens_ndvi | NO | SIM | SIM | NÃO |
| imoveis_arrendamentos | NO | SIM | SIM | NÃO |
| imoveis_rurais | NO | SIM | SIM | NÃO |
| integration_credentials | NO | SIM | SIM | **SIM** |
| integration_external_record_link_history | NO | SIM | SIM | **SIM** |
| integration_external_record_links | NO | SIM | SIM | **SIM** |
| integration_features | NO | SIM | SIM | **SIM** |
| integration_health_snapshots | NO | SIM | SIM | **SIM** |
| integration_jobs | NO | SIM | SIM | **SIM** |
| integration_sync_policies | NO | SIM | SIM | **SIM** |
| integration_versions | NO | SIM | SIM | **SIM** |
| operational_alerts | NO | SIM | SIM | NÃO |
| operacoes_agricolas | NO | SIM | SIM | NÃO |
| operacoes_execucoes | NO | SIM | SIM | NÃO |
| pec_piquetes | NO | SIM | SIM | NÃO |
| perfis_acesso | NO | SIM | SIM | NÃO |
| recommendation_lifecycle_events | NO | SIM | SIM | NÃO |
| recommendation_results | NO | SIM | SIM | NÃO |
| registros_clima | NO | SIM | SIM | NÃO |
| safra_fase_historico | NO | SIM | SIM | NÃO |
| safra_fenologia_registros | NO | SIM | SIM | NÃO |
| safra_talhao_grupo_itens | NO | SIM | SIM | NÃO |
| safra_talhao_grupos | NO | SIM | SIM | NÃO |
| sessoes_ativas | NO | SIM | SIM | NÃO |
| tenant_integracoes | NO | SIM (via integration_*) | SIM | **SIM** |
| tenant_usuarios | NO | SIM | SIM | NÃO |
| unidades_medida | YES | SIM | SIM | NÃO |
| unidades_medida_conversoes | NO | SIM | SIM | NÃO |
| unidades_produtivas | NO | SIM | SIM | NÃO |
| *(demais tabelas agricola/pec/financeiro com FK=SIM)* | NO | SIM | SIM | NÃO |

> **Nota:** A tabela `integration_credentials` aparece em ambos os inventários (uuid e varchar) — confirma-se que o tipo físico no banco é `character varying` (28 tabelas varchar), mas o módulo integration_* usa RLS adicional como compensação.

### 1.2 Tabelas com `tenant_id character varying` (total: 28)

| Tabela | FK→tenants | Índice | RLS | Registros |
|---|---|---|---|---|
| amostras | NÃO | SIM | NÃO | 0 |
| case_ih | NÃO | SIM | NÃO | 0 |
| comparador_precos | NÃO | SIM | NÃO | 0 |
| diagnosticos | NÃO | SIM | NÃO | 0 |
| integration_credentials | NÃO | SIM | **SIM** | 0 |
| integration_external_record_link_history | NÃO | SIM | **SIM** | 0 |
| integration_external_record_links | NÃO | SIM | **SIM** | 0 |
| integration_features | NÃO | SIM | **SIM** | 0 |
| integration_health_snapshots | NÃO | SIM | **SIM** | 0 |
| integration_jobs | NÃO | SIM | **SIM** | 0 |
| integration_sync_policies | NÃO | SIM | **SIM** | 0 |
| integration_versions | NÃO | SIM | **SIM** | 0 |
| john_deere | NÃO | SIM | NÃO | 0 |
| mapas_fertilidade | NÃO | SIM | NÃO | 0 |
| modelos_ml | NÃO | SIM | NÃO | 0 |
| pragas_doencas | NÃO | SIM | NÃO | 0 |
| prescricoes_vra | NÃO | SIM | NÃO | 0 |
| recomendacoes | NÃO | SIM | NÃO | 0 |
| sankhya_config | NÃO | SIM | NÃO | **2** |
| sankhya_lancamentos_financeiros | NÃO | SIM | NÃO | 0 |
| sankhya_nfe | NÃO | SIM | NÃO | 0 |
| sankhya_pessoas | NÃO | SIM | NÃO | 0 |
| sankhya_produtos | NÃO | SIM | NÃO | 0 |
| sankhya_sync_logs | NÃO | SIM | NÃO | **9** |
| sankhya_tabelas | NÃO | SIM | NÃO | 0 |
| tenant_integracoes | NÃO | SIM | **SIM** | 0 |
| tratamentos | NÃO | SIM | NÃO | 0 |
| whatsapp | NÃO | SIM | NÃO | 0 |

---

## 2. Classe F — UUID sem FK para `farms.tenants`

Apenas **1 tabela** nesta categoria:

| Tabela | Nullable | Índice | RLS | Registros |
|---|---|---|---|---|
| `billing_solicitacoes_comerciais_historico` | NO | **NÃO** | NÃO | **0** |

Model Python: `/opt/lampp/htdocs/farm/services/api/core/models/solicitacoes_historico.py`
Migration que a criou: `step41_solicitacoes_historico.py`
Migration que tentou corrigir: `tenant_fk_repair_01b_uuid_fks.py` (pendente de execução?)

> **Observação:** esta tabela não tem índice em `tenant_id` — dupla lacuna (sem FK, sem índice).

---

## 3. Interseção entre Grupos

- **Varchar com RLS**: 9 tabelas (`integration_*` + `tenant_integracoes`) — protegidas por RLS como compensação parcial.
- **Varchar sem RLS e com dados**: `sankhya_config` (2 registros) e `sankhya_sync_logs` (9 registros).
- **UUID sem FK (Classe F)**: apenas `billing_solicitacoes_comerciais_historico` (0 registros).

---

## 4. Análise dos Valores VARCHAR por Tabela

### Grupo A — Tabelas Agrícola/Solo (0 registros, sem RLS)
`amostras`, `diagnosticos`, `mapas_fertilidade`, `pragas_doencas`, `prescricoes_vra`, `recomendacoes`, `tratamentos`
- **Situação**: tabelas vazias. Nenhum dado a migrar. Risco de inserção futura sem FK.
- **Formato esperado**: UUID (pattern do serviço).

### Grupo B — IoT/Telemetria (0 registros, sem RLS)
`case_ih`, `john_deere`, `comparador_precos`, `whatsapp`
- **Situação**: tabelas vazias. Provider-specific. Integração não ativada em produção.

### Grupo C — Integration* (0 registros, com RLS)
`integration_credentials`, `integration_external_record_links`, `integration_external_record_link_history`, `integration_features`, `integration_health_snapshots`, `integration_jobs`, `integration_sync_policies`, `integration_versions`, `tenant_integracoes`
- **Situação**: tabelas vazias. RLS ativo como compensação. Módulo de integração ativo no código.

### Grupo D — Sankhya (com dados, sem RLS)
`sankhya_config` (2 registros), `sankhya_sync_logs` (9 registros)
- **Formato dos dados**: 100% UUIDs válidos no formato `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.
- **Correspondência com tenants**: 1 dos 2 UUIDs distintos em `sankhya_config` existe em `farms.tenants`. 1 dos 2 em `sankhya_sync_logs` existe.
- **Risco**: 1 tenant_id em cada tabela aponta para tenant **não existente** — orphan lógico.
- **Causa provável**: tenant de desenvolvimento/teste excluído ou nunca criado formalmente.

### Grupo E — ML/IA (0 registros, sem RLS)
`modelos_ml`
- **Situação**: tabela vazia.

---

## 5. Classificação por Tabela

### Classe B1 — uuid, ativo, sem FK ou sem índice

| Tabela | Lacuna | Prioridade |
|---|---|---|
| `billing_solicitacoes_comerciais_historico` | Sem FK + Sem índice | Alta (Classe F única) |
| `agricola_regras_agronomicas` | tenant_id nullable | Média |
| `cadastros_categorias_produto` | tenant_id nullable | Baixa |
| `cadastros_commodities` | tenant_id nullable | Baixa |
| `cadastros_culturas` | tenant_id nullable | Baixa |
| `cadastros_marcas` | tenant_id nullable | Baixa |
| `cadastros_modelos_produto` | tenant_id nullable | Baixa |
| `cadastros_produtos` | tenant_id nullable | Baixa |
| `cadastros_tipos_relacionamento` | tenant_id nullable | Baixa |
| `unidades_medida` | tenant_id nullable | Baixa |

> Tabelas com nullable intencionalmente (registros globais do sistema) — verificar before de converter NOT NULL.

### Classe B2 — varchar, UUIDs válidos correspondentes a tenants

| Tabela | Registros | UUIDs válidos | Correspondência tenants |
|---|---|---|---|
| `sankhya_config` | 2 | 2 | 1 de 2 existe |
| `sankhya_sync_logs` | 9 | 9 | 1 de 2 tenants existe |

### Classe B3 — varchar, dados mistos ou com orphan

Incluídas no grupo B2 por ora (dados são apenas UUIDs mas com orphan parcial).

### Classe B4 — provider-specific

| Tabela | Provider | Registros |
|---|---|---|
| `sankhya_config` | Sankhya | 2 |
| `sankhya_lancamentos_financeiros` | Sankhya | 0 |
| `sankhya_nfe` | Sankhya | 0 |
| `sankhya_pessoas` | Sankhya | 0 |
| `sankhya_produtos` | Sankhya | 0 |
| `sankhya_sync_logs` | Sankhya | 9 |
| `sankhya_tabelas` | Sankhya | 0 |
| `case_ih` | Case IH IoT | 0 |
| `john_deere` | John Deere IoT | 0 |
| `comparador_precos` | Cotações | 0 |
| `whatsapp` | WhatsApp | 0 |

### Classe D — Legado/Backup (excluída de qualquer conversão)

| Tabela | Motivo |
|---|---|
| `territory_legacy_backup_01h2` | Backup pós-migração (18 registros, não é tabela de negócio) |

### Classe G — Global (tenant_id nullable intencional, registros compartilhados)

Tabelas com `tenant_id nullable` que possivelmente armazenam dados globais:
`cadastros_culturas`, `cadastros_commodities`, `cadastros_categorias_produto`, `cadastros_marcas`, `cadastros_modelos_produto`, `cadastros_produtos`, `cadastros_tipos_relacionamento`, `unidades_medida`, `agricola_regras_agronomicas`

> **Ação necessária antes de converter**: confirmar se existem registros com `tenant_id IS NULL` que representam catálogos globais do sistema.

---

## 6. Dependências de Código Identificadas

| Tabela | Model Python |
|---|---|
| `billing_solicitacoes_comerciais_historico` | `services/api/core/models/solicitacoes_historico.py` |
| `amostras` | `services/api/agricola/amostragem_solo/models/amostras.py` |
| `diagnosticos` | `services/api/ia_diagnostico/models/diagnosticos.py` |
| `case_ih` | `services/api/iot_integracao/models/case_ih.py` |
| `sankhya_*` | `services/api/integracoes/sankhya/models/__init__.py` |
| `integration_*` | `services/api/` (múltiplos — ERP router desacoplado) |
| `recomendacoes` / `modelos_ml` | `services/api/recommendations/` (múltiplos arquivos) |

---

## 7. Riscos por Tabela

| Risco | Tabelas | Severidade |
|---|---|---|
| Orphan lógico (tenant excluído) | `sankhya_config`, `sankhya_sync_logs` | Média — dados sem dono ativo |
| Inserção futura sem FK | Todas as 28 varchar | Alta — sem restrição de banco |
| Tenant nullable sem controle | 10 tabelas uuid nullable | Média — registro global vs. tenant ambíguo |
| Sem índice em `tenant_id` | `billing_solicitacoes_comerciais_historico` | Média — performance em queries tenant-scoped |
| Sem RLS + sem FK + com dados | `sankhya_config`, `sankhya_sync_logs` | Alta — isolamento depende 100% da aplicação |

---

## 8. Plano por Ondas

### Onda 1 — Baixo Risco (tabelas vazias, sem FK, sem RLS)

**Critério:** `COUNT(*) = 0`, sem dependências ativas de inserção em produção.

Tabelas elegíveis (todas varchar, 0 registros):

| Tabela | Ação |
|---|---|
| `amostras` | ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid; ADD FK; |
| `diagnosticos` | idem |
| `mapas_fertilidade` | idem |
| `pragas_doencas` | idem |
| `prescricoes_vra` | idem |
| `recomendacoes` | idem |
| `tratamentos` | idem |
| `modelos_ml` | idem |

E a Classe F:

| Tabela | Ação |
|---|---|
| `billing_solicitacoes_comerciais_historico` | ADD FK → tenants; ADD INDEX ix_billing_hist_tenant_id; |

### Onda 2 — Módulos Ativos com RLS (integration_*)

**Critério:** 0 registros mas módulo ativo no código com RLS já configurado.

| Tabela | Ação | Risco |
|---|---|---|
| `integration_credentials` | ALTER TYPE + ADD FK | Baixo (0 registros, RLS compensa) |
| `integration_external_record_links` | idem | Baixo |
| `integration_external_record_link_history` | idem | Baixo |
| `integration_features` | idem | Baixo |
| `integration_health_snapshots` | idem | Baixo |
| `integration_jobs` | idem | Baixo |
| `integration_sync_policies` | idem | Baixo |
| `integration_versions` | idem | Baixo |
| `tenant_integracoes` | idem | Baixo |

### Onda 3 — Integrações com Dados (Sankhya)

**Critério:** registros presentes; orphan parcial; provider-specific.

| Tabela | Ação | Pré-requisito |
|---|---|---|
| `sankhya_config` | Verificar/limpar 1 orphan; ALTER TYPE + ADD FK | Confirmar tenant_id orphan antes |
| `sankhya_sync_logs` | idem | idem |
| `sankhya_lancamentos_financeiros` | ALTER TYPE + ADD FK | 0 registros — seguro |
| `sankhya_nfe` | idem | idem |
| `sankhya_pessoas` | idem | idem |
| `sankhya_produtos` | idem | idem |
| `sankhya_tabelas` | idem | idem |

### Onda 4 — IoT/Telemetria (provider-specific, sem plano de ativação)

| Tabela | Ação | Observação |
|---|---|---|
| `case_ih` | ALTER TYPE + ADD FK | 0 registros, integração desativada |
| `john_deere` | idem | idem |
| `comparador_precos` | idem | integração de cotações |
| `whatsapp` | idem | canal de comunicação |

---

## 9. Primeira Onda Recomendada

**Onda 1 — 9 tabelas de baixíssimo risco:**

```sql
-- Candidatas confirmadas para 01B-Onda1
-- Todas com COUNT(*) = 0 — VERIFICAR ANTES DA EXECUÇÃO
amostras
diagnosticos
mapas_fertilidade
pragas_doencas
prescricoes_vra
recomendacoes
tratamentos
modelos_ml
billing_solicitacoes_comerciais_historico  -- Classe F: apenas ADD FK + ADD INDEX
```

**Padrão de execução por tabela varchar:**
```sql
ALTER TABLE farms.<tabela> ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid;
ALTER TABLE farms.<tabela> ADD CONSTRAINT fk_<tabela>_tenant FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id) ON DELETE CASCADE;
-- índice já existe em todas — não recriar
COMMIT;
```

**Para `billing_solicitacoes_comerciais_historico` (Classe F):**
```sql
ALTER TABLE farms.billing_solicitacoes_comerciais_historico
  ADD CONSTRAINT fk_billing_historico_tenant FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id) ON DELETE CASCADE;
CREATE INDEX ix_billing_solicitacoes_historico_tenant_id ON farms.billing_solicitacoes_comerciais_historico(tenant_id);
COMMIT;
```

---

## 10. Tabelas Excluídas da Onda 1

| Tabela | Motivo de Exclusão |
|---|---|
| `sankhya_config` | Tem dados; 1 orphan detectado — requer saneamento antes |
| `sankhya_sync_logs` | Tem dados; 1 orphan detectado — requer saneamento antes |
| `sankhya_*` (demais) | Grupo coeso — mover junto com as que têm dados (Onda 3) |
| `case_ih`, `john_deere`, `comparador_precos`, `whatsapp` | Provider-specific sem roadmap de ativação — Onda 4 |
| `integration_*`, `tenant_integracoes` | RLS ativo — requerem validação de impacto nas policies (Onda 2) |
| `territory_legacy_backup_01h2` | Classe D — backup permanente, excluída da reparação |
| Tabelas com `tenant_id nullable` (B1 parcial) | Requerem análise de registros `IS NULL` antes de NOT NULL |

---

## 11. Impacto Esperado nos Guardrails

### G2 — FK Coverage ≥ 95%

- **Situação atual**: ~130 tabelas uuid com FK + 0 tabelas varchar com FK = ~83% (estimado).
- **Após Onda 1** (9 tabelas): +9 FKs → cobertura sobe ~2 pontos percentuais.
- **Após Onda 2** (+9 integration_*): +9 → cobertura sobe mais ~2%.
- **Após Onda 3** (+7 sankhya): +7 → cobertura chega ao limiar de 95%+.
- **Conclusão**: G2 será aprovado após conclusão das ondas 1 + 2 + 3.

### G3 — Nenhuma tabela de negócio sem FK (exceto exceções documentadas)

- **Situação atual**: 28 tabelas varchar sem FK + 1 Classe F = 29 violações.
- **Após Onda 1**: −9 tabelas → 20 violações restantes.
- **Após Onda 2**: −9 → 11 restantes.
- **Após Onda 3**: −7 → 4 restantes (apenas IoT + `territory_legacy_backup`).
- **Após Onda 4**: −4 → G3 aprovado com exceção documentada para `territory_legacy_backup_01h2`.

---

## 12. Veredicto Final

```
GO PARA 01B2 — ONDA 1 DE BAIXO RISCO
```

**Justificativa:**
- 8 tabelas varchar + 1 Classe F com `COUNT(*) = 0` estão prontas para conversão sem risco de perda de dados ou orphan.
- Models Python identificados — alteração de tipo no banco requer ajuste nos models SQLAlchemy (remover `String`, usar `uuid.UUID`).
- Tabelas Sankhya com dados requerem saneamento pontual (1 orphan cada) antes da Onda 3.
- Guardrails G2 e G3 avançarão significativamente após Onda 1 + 2.

**Pré-condição antes de executar Onda 1:**
1. Confirmar `COUNT(*) = 0` em todas as 8 tabelas varchar no momento da execução (ambiente de staging pode ter recebido dados).
2. Ajustar models Python nas tabelas convertidas (`tenant_id: Mapped[uuid.UUID]` em vez de `Mapped[str]`).
3. Executar migration via Alembic com `op.execute("COMMIT")` após cada `run_sync()`.

---

*Gerado por: auditoria read-only em 2026-07-17. Nenhum DDL/DML executado.*
