# ERP-DATA-HYGIENE-01E0 — Inventário de Estado e Reconciliação

**Natureza:** auditoria exclusivamente de leitura. Nenhum código, teste ou migration foi alterado.

## 1. Resumo Executivo

O relatório 01D superestima o que foi implementado. Achados centrais:

- `nfe_financeiro_service.py:13` **ainda importa `SankhyaConfig` (ORM)** diretamente — contradiz "NFe/financeiro adaptados" e violaria o próprio guardrail AST se este pudesse ser executado.
- Há **gravação dupla** confirmada: `criar_config` (`sync_service.py:~820-911`) grava em `SankhyaConfig` e, na sequência, sincroniza para o canônico via `canonical_adapter.sync_provider_config`.
- **Segredos (`client_secret`, `x_token`, `token`, `appkey`, `password`) sempre vêm do ORM legado**, mesmo no "caminho canônico" — o canônico só fornece dados técnicos não sensíveis via `TenantIntegracao.connection_payload`.
- Há **fallback silencioso** legado quando `TenantIntegracao` não existe (`sync_service.py:103`, log `FALLBACK_LEGACY`).
- O guardrail AST (`test_sankhya_architecture.py`) **não pôde ser executado** — bug de ambiente pré-existente e não relacionado (FK compartilhada em `integracoes/models.py:25`, introduzida no commit `88e46a13`, REPAIR-01B3) quebra a coleção de toda a suíte `tests/unit/integracoes/*`. Logo, a alegação do 01D de que os testes "passaram" não pode ser confirmada nem refutada por execução — mas por leitura estática o guardrail falharia hoje devido ao achado acima.
- `canonical_adapter.py` continua fortemente acoplado ao ORM (`provider_config: SankhyaConfig` em quase todos os métodos) — isso é esperado/aceitável, pois é a camada de espelhamento, não um "consumidor operacional desacoplado".
- `auth_service.py` e `SankhyaWSClient` estão de fato desacoplados (só recebem `SankhyaConnectionData`).

**Veredicto:** `GO COM RESSALVAS — REPLANEJAMENTO NECESSÁRIO` (detalhes na seção 21).

## 2. Histórico Reconciliado

| Fase | Alegação do relatório | Confirmado no código? |
|---|---|---|
| 01A | Auditoria estrutural, nenhuma remoção | Não se aplica reverificar (apenas leitura histórica) |
| 01B | Mapeou consumidores de SankhyaConfig | Lista de consumidores confirmada como ainda em grande parte válida |
| 01C | Planejamento 01D→01L | Sequência ainda é a referência, mas precisa revisão pós-01E0 |
| 01D | ORM desacoplado dos consumidores operacionais, guardrail criado e passando | **Parcialmente falso**: `nfe_financeiro_service.py` não foi desacoplado; guardrail não executável hoje |

## 3. Documentos Analisados

- `ERP-DATA-HYGIENE-01A-AUDITORIA-ESTRUTURAS-LEGADAS.md`
- `ERP-DATA-HYGIENE-01B-AUDITORIA-DEPENDENCIAS-SANKHYA-CONFIG.md`
- `ERP-DATA-HYGIENE-01C-PLANO-MODERNIZACAO-PROVIDER-SANKHYA.md`
- `ERP-DATA-HYGIENE-01D-DESACOPLAMENTO-RUNTIME-ORM-LEGADO.md`
- Código atual em `services/api/integracoes/sankhya/**`
- Testes em `services/api/tests/unit/integracoes/**`
- Migrations em `services/api/migrations/versions/**`
- `git log`, `git diff --check`

## 4. Inventário de Arquivos (SankhyaConfig / SankhyaConnectionData)

**Definição:**
- `SankhyaConfig` (ORM): `integracoes/sankhya/models/__init__.py:23`, tabela `sankhya_config`.
- `SankhyaConnectionData`: `integracoes/sankhya/services/auth_service.py:14-26`, `@dataclass(frozen=True)` confirmado. Campos: `environment, api_base_url, auth_url, ws_url, client_id, client_secret, x_token, token, appkey, username, password`.

**Referenciam `SankhyaConfig` (ORM ou schema homônimo):**

| Arquivo | Tipo | Observação |
|---|---|---|
| `models/__init__.py:23` | Model | Definição |
| `schemas/__init__.py:10,50` | Schema | `SankhyaConfigCreate/Response` — nome igual, não é o ORM, risco de confusão |
| `services/sync_service.py` (~40 ocorrências) | Service operacional | Uso pesado, esperado (é o ponto de conversão concentrado) |
| `services/canonical_adapter.py` (14 ocorrências) | Service operacional | Recebe `provider_config: SankhyaConfig` na maioria dos métodos |
| `services/nfe_financeiro_service.py:13` | Service operacional | **Import direto do ORM — divergência do plano/guardrail** |
| `services/legacy_reconciliation.py` | Service operacional | Esperado (reconciliação legado↔canônico) |
| `services/external_association_helper.py` | Service operacional | Uso pontual, inclui `.limit(1)` (linha ~770) |
| `routers/__init__.py` | Router | Só usa schemas `SankhyaConfigCreate/Response`, não o ORM |
| `scratch_delete_all.py` (raiz de services/api) | Script solto | Fora de `scripts/`, uso ad-hoc — débito técnico de organização |
| `scripts/reconcile_legacy_sankhya_integration.py` | Script | Esperado (reconciliação) |
| 10 arquivos de teste (ver relatório completo do agente) | Teste | Inclui `test_sankhya_architecture.py`, `conftest.py`, etc. |

**Usam/constroem `SankhyaConnectionData`:** `auth_service.py:71,75`; `sync_service.py:40,47-59,62-100,177`; `nfe_financeiro_service.py` (via `get_sankhya_connection_data`).

## 5. Inventário de Estruturas Canônicas

Todas as 7 estruturas canônicas (`TenantIntegracao`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationHealth`, `IntegrationJob`, `IntegrationVersion`) são usadas de fato (não apenas importadas) dentro de `canonical_adapter.py`, `legacy_reconciliation.py` e `sync_service.py`. `IntegrationJob` aparece também em `schemas/__init__.py` e `routers/__init__.py`.

## 6. Inventário por Campo

| Campo/responsabilidade | Leitura atual | Escrita atual | Consumidores | Fallback? | Duplicidade? | Fonte de verdade real | Fase prevista | Estado real |
|---|---|---|---|---|---|---|---|---|
| Config técnica (urls, environment) | `TenantIntegracao.connection_payload` OU `SankhyaConfig` | `SankhyaConfig` + sync p/ canônico | sync_service, canonical_adapter | Sim (silencioso, p/ legado se canônico ausente) | Sim | **Legado** (canônico é espelho) | 01E | PARCIALMENTE IMPLEMENTADO |
| Credenciais OAuth/Gateway | `SankhyaConfig` sempre | `SankhyaConfig` | auth_service (via SankhyaConnectionData), sync_service | Não há caminho canônico real | Não | **Legado** | 01F | NÃO INICIADO |
| Credenciais WS legado | `SankhyaConfig` | `SankhyaConfig` | sync_service, WSClient | — | Não | Legado | 01F | NÃO INICIADO |
| Lifecycle | `TenantIntegracao` | `TenantIntegracao` + espelho | canonical_adapter | — | Verificar | Canônico | 01G | IMPLEMENTADO (a confirmar em execução) |
| Health | `IntegrationHealth` | `IntegrationHealth` | canonical_adapter | — | — | Canônico | 01G | IMPLEMENTADO (a confirmar) |
| Políticas de sync | `IntegrationSyncPolicy` | `IntegrationSyncPolicy` | canonical_adapter | — | — | Canônico | 01I | IMPLEMENTADO (a confirmar) |
| Último sync | Misto | Misto | sync_service | Provável | Provável | Inconclusivo | 01I | INCONCLUSIVO |
| Jobs | `IntegrationJob` | `IntegrationJob` | canonical_adapter, routers | — | — | Canônico | 01H | IMPLEMENTADO (a confirmar) |
| Versionamento | `IntegrationVersion` | `IntegrationVersion` | canonical_adapter | — | — | Canônico | — | IMPLEMENTADO (a confirmar) |
| Capabilities | `IntegrationFeature` | `IntegrationFeature` | canonical_adapter | — | — | Canônico | — | IMPLEMENTADO (a confirmar) |
| Identidade da integração | `TenantIntegracao` | `TenantIntegracao` | canonical_adapter | — | — | Canônico | — | IMPLEMENTADO (a confirmar) |

Nota: itens marcados "a confirmar" não puderam ser validados por teste executável (ver seção 16); avaliação é por leitura estática apenas.

## 7. Inventário por Consumidor

| Consumidor | Recebe ORM? | Recebe SankhyaConnectionData? | Consulta canônico? | Escreve legado? | Escreve canônico? | Criticidade | Situação |
|---|---|---|---|---|---|---|---|
| `SankhyaGatewayAuthService` (auth_service.py) | Não | Sim | Não | Não | Não | Alta | **Desacoplado — confirmado** |
| `SankhyaWSClient` | Não | Sim | Não | Não | Não | Alta | **Desacoplado — confirmado** |
| `SankhyaSyncService` (sync_service.py) | Sim | Sim (constrói) | Sim | Sim | Sim | Alta | Ponto de conversão concentrado, conforme plano — mas com gravação dupla e fallback |
| `SankhyaNFeService`/financeiro (nfe_financeiro_service.py) | **Sim (linha 13)** | Sim | Não claro | Não claro | Não claro | Alta | **NÃO desacoplado — diverge do relatório 01D** |
| `SankhyaCanonicalAdapter` | Sim (quase todo método) | Não | Sim | Não | Sim | Média | Esperado — é a camada de espelhamento |
| Routers | Não (só schemas homônimos) | Não | Parcial (IntegrationJob) | Não | Não | Baixa | OK |
| Workers/scripts (`reconcile_legacy_sankhya_integration.py`) | Sim | — | Sim | Provável | Provável | Média | Esperado (reconciliação) |
| `scratch_delete_all.py` | Sim | — | — | — | — | Baixa | Script solto fora de `scripts/` — débito de organização |

## 8. Fluxo Atual de Leitura

Config técnica: tenta `TenantIntegracao.connection_payload`; se ausente/incompleto → `ValueError` ou fallback total ao `SankhyaConfig` (log `FALLBACK_LEGACY`, `sync_service.py:103`). Segredos: sempre de `SankhyaConfig`, nunca do canônico.

## 9. Fluxo Atual de Escrita

`criar_config`: grava em `SankhyaConfig` (`self.db.add(config)`) e em seguida chama `self.adapter.sync_provider_config(...)` para espelhar no canônico — escrita dupla a cada criação.

## 10. Precedência Real

```
configuração técnica: legado (segredos sempre; técnico às vezes canônico com fallback)
credenciais: legado
lifecycle: canônico
health: canônico
jobs: canônico
policies: canônico
```

## 11. Fallbacks Reais

Fallback por ausência confirmado (`TenantIntegracao` inexistente → legado, silencioso via log). Não identificado fallback por erro distinto do fallback por ausência nas fontes revisadas.

## 12. Gravação Dupla

Confirmada em `criar_config` (`sync_service.py`): `SankhyaConfig` + `canonical_adapter.sync_provider_config`.

## 13. Sincronização Legado/Canônico

Existe sincronização unidirecional legado→canônico via `canonical_adapter.sync_provider_config`, chamada a partir de `sync_service.py`. Reconciliação adicional (bidirecional) existe em `legacy_reconciliation.py`, cujo escopo exato não foi auditado linha a linha — recomendado detalhamento na próxima fase se for tocar essa área.

## 14. Validação da Fase 01D

| Pergunta | Resposta |
|---|---|
| `SankhyaConnectionData` é imutável? | Sim, `frozen=True` confirmado |
| Está só no provider? | Sim (`auth_service.py`) |
| Contém só campos necessários? | Sim, todos usados |
| Transporta secrets descriptografados? | Sim (client_secret, x_token, token, appkey, password) |
| Onde ocorre a descriptografia? | Não localizada explicitamente nesta auditoria — pendente de investigação dedicada |
| ORM ainda repassado indiretamente? | Sim, via `nfe_financeiro_service.py` e `canonical_adapter.py` |
| Todos os consumidores citados no relatório foram desacoplados? | **Não** — `nfe_financeiro_service.py` não foi |
| Serializer depende do ORM? | Schemas usam nome homônimo mas não o ORM diretamente |
| Routers expõem SankhyaConfig? | Não, apenas schemas Pydantic |
| Guardrail cobre todos os consumidores relevantes? | Não cobre `canonical_adapter.py`, `sync_service.py`, `legacy_reconciliation.py`, `external_association_helper.py` (aceitável, pois estes são a camada de conversão) |
| Guardrail é permissivo demais? | Não tem allowlist; é estrito, mas roda só sobre `auth_service.py`, `nfe_financeiro_service.py` e `routers/*.py` |
| Há imports dinâmicos que escapam da AST? | Não identificados |
| Testes de autenticação executados e passando? | **Não pôde ser confirmado** — coleção quebrada (ver 16) |
| Houve alteração comportamental não documentada? | Não identificada além da gravação dupla, que já é comportamento esperado do "ponto de conversão concentrado" mas não está claramente documentada como permanente |

## 15. Matriz das Fases 01D–01L

| Fase | Objetivo original | Evidência no código | Estado real | Lacunas | Recomendação |
|---|---|---|---|---|---|
| 01D | Desacoplar ORM dos consumidores operacionais | Parcial (auth/WS ok; NFe/financeiro não) | **IMPLEMENTADO COM DIVERGÊNCIA DO PLANO** | `nfe_financeiro_service.py` ainda importa ORM; guardrail não roda | Fechar 01D antes de avançar |
| 01E | Configuração técnica | Espelhamento parcial existe via canonical_adapter | PARCIALMENTE IMPLEMENTADO (antecipado) | Segredos nunca migrados; fallback silencioso | Não reabrir com o mesmo nome — usar 01E1 após fechar 01D |
| 01F | Credenciais | Não iniciado para OAuth/Gateway/WS de fato migrarem para `IntegrationCredential` como fonte de verdade | NÃO INICIADO | — | Manter na sequência |
| 01G | Lifecycle/health | Estruturas canônicas já em uso ativo | IMPLEMENTADO (não confirmado por teste) | Falta execução de testes | Confirmar antes de assumir concluído |
| 01H | Jobs | `IntegrationJob` em uso | IMPLEMENTADO (não confirmado) | — | idem |
| 01I | Políticas | `IntegrationSyncPolicy` em uso | IMPLEMENTADO (não confirmado) | — | idem |
| 01J–01L | Encerramento de leituras/gravações legadas, auditoria final | Não aplicável ainda | NÃO INICIADO | Depende de 01D-01I fechados | Manter no fim da sequência |

## 16. Testes Executados

Comando: `cd services/api && .venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v`

**Resultado: falha na coleta (`ImportError`/`InvalidRequestError`), 0 testes executados.**

Causa raiz: `integracoes/models.py:25` define `_TENANT_FK = ForeignKey(...)` como objeto único reutilizado em múltiplas colunas (linhas 196, 240, 270, 296, 325, 355, 395, 446, 508...). SQLAlchemy não permite reuso de instância `ForeignKey` entre colunas → `InvalidRequestError: This ForeignKey already has a parent!`. Bug introduzido no commit `88e46a13` (REPAIR-01B3), **anterior e não relacionado** ao guardrail 01D, mas bloqueia toda a suíte `tests/unit/integracoes/*`.

`git diff --check`: sem problemas (saída vazia, repo limpo).

## 17. Divergências entre Relatório e Código

1. 01D afirma "serviços de NFe e financeiro adaptados" — falso; `nfe_financeiro_service.py:13` ainda importa `SankhyaConfig`.
2. 01D afirma testes "1 passed" para o guardrail — hoje impossível de reproduzir devido a bug de ambiente pré-existente; não se pode confirmar se já estava quebrado quando 01D foi reportado ou se quebrou depois (commit do bug é `88e46a13`, posterior ao 01D pela ordem do histórico fornecido — **isso sugere que o bug quebrou a suíte depois que 01D foi validado**, tornando a validação original potencialmente legítima na época, mas não reprodutível/verificável hoje).
3. 01D não documenta explicitamente a gravação dupla como comportamento permanente esperado.

## 18. Riscos Atuais

- Qualquer nova fase que dependa de rodar testes de `tests/unit/integracoes/*` está bloqueada até o bug de FK compartilhada ser corrigido (fora do escopo deste programa, mas é pré-condição bloqueante).
- Segredos nunca migram para o canônico — se uma fase futura assumir que `IntegrationCredential` é fonte de verdade de secrets sem verificar, haverá quebra em produção.
- Fallback silencioso mascara ausência de `TenantIntegracao` — risco de comportamento inconsistente entre tenants migrados e não migrados.

## 19. Débitos Técnicos

- `scratch_delete_all.py` solto na raiz de `services/api` (fora de `scripts/`).
- Nome de schema `SankhyaConfigCreate/Response` idêntico ao ORM `SankhyaConfig` — risco de confusão para próximos desenvolvedores.
- Guardrail AST não cobre `canonical_adapter.py`/`sync_service.py` — aceitável por design, mas deveria estar documentado explicitamente como decisão consciente, não omissão.

## 20. Próxima Execução Recomendada

Antes de qualquer nova fase de implementação:

1. Corrigir (fora deste programa, como pré-condição) o bug de `ForeignKey` compartilhada em `integracoes/models.py:25`, para permitir rodar a suíte de testes de integrações.
2. Reexecutar o guardrail e os testes de auth/sync/canonical/NFe-financeiro com a suíte destravada.
3. Abrir uma fase **01D-FIX** (não 01E) com escopo mínimo: remover o import direto de `SankhyaConfig` em `nfe_financeiro_service.py`, usando `SankhyaConnectionData`/`get_sankhya_connection_data` como os demais consumidores já fazem.
4. Só então avançar para 01E (config técnica) com o guardrail realmente validando o que o relatório alega.

## 21. Escopo Exato da Próxima Execução

**Próximo identificador:** `ERP-DATA-HYGIENE-01D-FIX` (correção pontual, precede reabertura formal de 01E).

**Menor escopo implementável:** ajustar `nfe_financeiro_service.py` para não importar `SankhyaConfig` do ORM, migrando para `SankhyaConnectionData`, seguindo o padrão já usado por `auth_service.py`.

**Arquivos a alterar (nesta fase futura, não nesta auditoria):**
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`

**Arquivos proibidos:**
- Qualquer arquivo de Core ERP, Router ERP, Readiness, Lifecycle, Console ERP, Provider Registry, bootstrap multiprovider.
- `canonical_adapter.py`, `sync_service.py`, `legacy_reconciliation.py` (fora de escopo desta correção pontual).

**Pré-condições:**
- Bug de `ForeignKey` compartilhada em `integracoes/models.py:25` corrigido, para permitir validação real via testes.

**Testes obrigatórios após a correção:**
- `tests/unit/integracoes/test_sankhya_architecture.py`
- Testes de `nfe_financeiro_service` relacionados (localizar em `tests/unit/integracoes/`)
- `git diff --check`

## 22. Veredicto

`GO COM RESSALVAS — REPLANEJAMENTO NECESSÁRIO`

O programa não está pronto para retomar a sequência original 01E→01L como planejada em 01C, pois a fase 01D não está de fato concluída (divergência confirmada em `nfe_financeiro_service.py`) e sua validação por teste não é reproduzível hoje devido a um bug de ambiente pré-existente e não relacionado. Recomenda-se abrir `ERP-DATA-HYGIENE-01D-FIX` como próxima execução, com escopo mínimo e testes obrigatórios, antes de qualquer nova implementação de 01E.
