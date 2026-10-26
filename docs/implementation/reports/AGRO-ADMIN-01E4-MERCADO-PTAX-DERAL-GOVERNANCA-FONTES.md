# Relatório de Implementação: AGRO-ADMIN-01E4 — Mercado, PTAX, DERAL e Governança de Fontes Oficiais

**Data:** 24 de Outubro de 2026  
**Status:** CONCLUÍDO E HOMOLOGADO  
**Ambiente:** Desenvolvimento / Backoffice DeepFarms Agro  
**Veredicto Técnico:** **GO**

---

## 1. Inventário dos Serviços e Consumidores Existentes

Antes e durante o ciclo de desenvolvimento da AGRO-ADMIN-01E4, realizamos auditoria forense nos serviços públicos e administrativos para assegurar total retrocompatibilidade e preservação dos contratos públicos:

| Serviço / Domínio | Arquivo / Módulo | Consumidores Principais | Modo de Operação |
| :--- | :--- | :--- | :--- |
| **BCB PTAX** | `services/api/public_mercado/ptax.py` | Aba Mercado (`PtaxCard`), Conversão Cambial nos Cards de Commodities | Consulta Olinda BCB, L1 memória + L2 Redis, tolerância a feriados/fins de semana com fallback retroativo de 7 dias |
| **BCB Séries SGS** | `services/api/public_mercado/sgs.py` | Aba Mercado (Meta Selic, IPCA mensal, IPCA 12M) | Séries 432, 433, 13522 via API BCB SGS, cache L1 + L2 (TTL 30 min), fallback de até 30 dias |
| **IBGE SIDRA** | `services/api/public_mercado/sidra.py` | Aba Mercado (`IbgeCard`), PAM, PPM, LSPA | Consulta API SIDRA agregada por UF/Município, cache L1 + L2 (TTL 24h a 7 dias), rate-limiting por IP |
| **DERAL / SEAB-PR** | `services/api/public_mercado/precos_publicos.py` | Aba Mercado (`CommoditiesGrid`), 21 preços reais auditados | Snapshot semanal oficial, cache em memória L1 com lock single-flight, resolução de snapshot ativo |
| **Catálogo de Metadados** | `services/api/public_mercado/precos_publicos.py` | Endpoint `/catalogo`, conversão cambial, PWA Campo | 22 commodities canônicas (21 cotações reais DERAL + 1 link institucional CONAB/MAPA) |
| **Configurações SaaS** | `services/api/core/models/configuracao_saas.py` | `AgroConfigService`, `DeralSnapshotService` | Tabela `configuracoes_saas` no PostgreSQL compartilhado, revisionamento otimista, sem migrações |
| **Auditoria Administrativa** | `services/api/core/models/admin_audit_log.py` | `AdminAuditService` | Tabela `admin_audit_logs`, FK resiliente para admin global, mascaramento de segredos |

---

## 2. Arquivos Criados e Modificados

### 2.1 Arquivos Criados
1. `services/api/core/services/deral_snapshot_service.py`
   - Serviço corporativo de gerenciamento de snapshots DERAL.
   - Pipeline de validação: tamanho (100 B a 5 MB), formato (.json, .xlsx, .xls), hash SHA-256 sobre bytes brutos, schema Pydantic, 21 commodities canônicas obrigatórias, proibição de nulos/negativos/NaN.
   - Persistência transacional em `ConfiguracaoSaaS` (`agro:deral:snap:{id}` e índice `agro:deral:snapshots:index`).
   - Ativação atômica, histórico de snapshots e capacidade de rollback operacional.
   - Registro compulsório em `AdminAuditLog` e sincronização com `AgroConfigService`.
2. `services/api/core/services/market_sources_service.py`
   - Serviço de diagnóstico e telemetria de governança das 4 fontes oficiais (PTAX, SGS, SIDRA, DERAL).
   - Aferição de status de conectividade, tempo de resposta, limites de staleness e metadados.
3. `services/api/core/routers/backoffice_agro_mercado.py`
   - Roteador administrativo FastAPI com prefixo `/backoffice/agro/mercado`.
   - 7 endpoints governados com RBAC (`backoffice:agro:market:view` e `backoffice:agro:market:update`).
4. `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/mercado/page.tsx`
   - Painel administrativo Next.js 16 para governança de mercado.
   - Construído rigorosamente com shadcn/ui, botões outline sm, inputs small, rounded-sm, paleta esmeralda/terra, Sonner toast.
   - 4 cards de status de fontes com badges de staleness, modal de parâmetros operacionais de cache, tabela de histórico de snapshots, cópia de hash SHA-256, modal de upload de arquivos e modal de inspeção das 21 commodities.
5. `services/api/tests/unit/core/test_backoffice_agro_01e4.py`
   - Suíte com 13 testes unitários e de integração validando RBAC, concorrência, upload, integridade, ativação, rollback e contratos.
6. `docs/implementation/reports/AGRO-ADMIN-01E4-MERCADO-PTAX-DERAL-GOVERNANCA-FONTES.md`
   - Este relatório de homologação técnica e conformidade arquitetural.

### 2.2 Arquivos Modificados
1. `services/api/core/schemas/agro_config_schemas.py`
   - Adicionadas entidades tipadas: `AgroMercadoConfig` expandido com flags de habilitação, TTLs específicos e controle de snapshot; `MarketSourceStatusItem`, `MarketSourcesStatusResponse`, `DeralSnapshotMetadata`, `DeralSnapshotDetailResponse`, `DeralSnapshotsListResponse`, `DeralSnapshotUploadResponse`, `DeralSnapshotActivationRequest`, `DeralSnapshotRollbackRequest`, `MarketConfigUpdateRequest`. Todos com `extra="forbid"`.
2. `services/api/core/services/agro_config_service.py`
   - Implementada trava de segurança em `update_config`: proíbe alteração direta de `deral_active_snapshot` ou `active_snapshot_id` através do endpoint de configurações genéricas, exigindo o fluxo atômico de ativação validado.
3. `services/api/core/constants.py`
   - Registradas as permissões de governança: `PERM_MARKET_VIEW = "backoffice:agro:market:view"` e `PERM_MARKET_UPDATE = "backoffice:agro:market:update"`.
4. `services/api/core/dependencies.py`
   - Sanitizado `require_any_permission` para aceitar argumentos desempacotados ou listas, evitando erros de tipo em dependências FastAPI.
5. `services/api/public_mercado/precos_publicos.py`
   - Atualizado `_carregar_snapshot` para buscar snapshot ativo em memória do `DeralSnapshotService` ou override de cache antes do fallback estático bundled (`deral-prp-2026-10-16.json`).
   - Implementada função de invalidação de cache L1 de preços públicos.
6. `services/api/public_mercado/precos_publicos_service.py`
   - Exposto método `invalidate_cache()` no serviço público e helper de injeção.
7. `services/api/main.py`
   - Registrado o roteador `backoffice_agro_mercado.router` no prefixo `/api/v1`.
8. `apps/web/src/lib/sidebar-config.ts`
   - Adicionado item "Mercado & Fontes" no menu do Backoffice com ícone `TrendingUp`.
9. `README.md`
   - Registrada a feature AGRO-ADMIN-01E4 na seção `## Features` conforme norma AGRO-04.

---

## 3. Endpoints Administrativos Criados

Todos os endpoints operam sob o prefixo `/api/v1/backoffice/agro/mercado`:

| Método | Endpoint | Permissão RBAC | Descrição Técnica |
| :--- | :--- | :--- | :--- |
| `GET` | `/status` | `backoffice:agro:market:view` | Retorna status de conectividade, latência, TTL e staleness das 4 fontes (PTAX, SGS, SIDRA, DERAL). |
| `PUT` | `/config` | `backoffice:agro:market:update` | Atualiza parâmetros operacionais de cache e limites de defasagem com controle otimista de versão (`expected_revision`). |
| `GET` | `/deral/snapshots` | `backoffice:agro:market:view` | Lista histórico de snapshots persistidos com hash SHA-256, metadados e indicação do snapshot ativo. |
| `GET` | `/deral/snapshots/{id}` | `backoffice:agro:market:view` | Retorna detalhes completos do snapshot, metadados e as cotações das 21 commodities canônicas. |
| `POST` | `/deral/upload` | `backoffice:agro:market:update` | Recebe arquivo (`.json`, `.xlsx`, `.xls`), valida conformidade rígida e persiste novo snapshot inativo. |
| `POST` | `/deral/snapshots/{id}/activate` | `backoffice:agro:market:update` | Ativa snapshot atomicamente, atualiza ponteiro em `AgroConfigService`, invalida L1 cache e grava auditoria. |
| `POST` | `/deral/snapshots/{id}/rollback` | `backoffice:agro:market:update` | Executa reversão operacional para snapshot anterior com validação transacional e auditoria. |

---

## 4. Modelo de Storage e Versionamento Multi-Worker

### 4.1 Desacoplamento do Filesystem Efêmero
- Em ambientes conteinerizados (Docker / Kubernetes / ECS), a gravação direta de arquivos na pasta `services/api/public_mercado/data/` é efêmera e não sincroniza entre múltiplos nós ou réplicas da API.
- O storage de snapshots foi arquitetado sobre a tabela já existente `configuracoes_saas` no PostgreSQL compartilhado:
  - **Índice Global:** Chave `agro:deral:snapshots:index` armazena a lista de metadados (`id`, `data_referencia`, `periodo_apuracao`, `sha256`, `total_commodities`, `created_at`, `created_by`, `status`).
  - **Payload do Snapshot:** Chave `agro:deral:snap:{snapshot_id}` armazena o envelope completo com metadados e as 21 commodities validadas.
  - **Zero Migrations:** Nenhuma alteração de DDL ou migration Alembic foi requerida, cumprindo a diretriz de isolamento de infraestrutura.

### 4.2 Concorrência Otimista e Integridade Transacional
- Todas as mutações no índice e nos snapshots utilizam a transação corrente do SQLAlchemy (`await session.commit()`).
- O chaveamento de snapshot atualiza a chave `agro:mercado:config` com controle otimista de versão (`expected_revision`), prevenindo condições de corrida quando múltiplos administradores operam o console simultaneamente.

---

## 5. Pipeline de Ingestão e Validação DERAL

O pipeline de ingestão (`DeralSnapshotService.upload_snapshot`) executa um funil rigoroso de validação em etapas sucessivas:

```
[Upload do Arquivo (.json / .xlsx / .xls)]
             │
             ▼
[Validação de Tamanho (100 B <= size <= 5 MB)]  ── Falha ──> HTTP 400 Bad Request
             │
             ▼
[Cálculo de Hash SHA-256 sobre Bytes Brutos]
             │
             ▼
[Decodificação e Validação Estrutural JSON]     ── Falha ──> HTTP 422 Unprocessable Entity
             │
             ▼
[Verificação do Catálogo Canônico (21 Itens)]   ── Falha ──> HTTP 422 (Itens ausentes listados)
             │
             ▼
[Validação Numérica de Preços (> 0, não-NaN)]   ── Falha ──> HTTP 422 (Preços inválidos)
             │
             ▼
[Persistência em PostgreSQL (ConfiguracaoSaaS)]
             │
             ▼
[Registro Atômico em AdminAuditLog]
```

### 5.1 Regras Mandatórias de Validação:
1. **Commodities Canônicas Obrigatórias (21):**
   `soja`, `milho`, `trigo`, `arroz`, `feijao`, `cafe-arabica`, `boi-gordo`, `boi-magro`, `vaca-em-pe`, `frango-vivo`, `suino`, `leite`, `ovos`, `feijao-preto`, `aveia-branca`, `canola`, `cevada`, `amendoim`, `mandioca-industrial`, `erva-mate`, `cana-de-acucar`.
   *(Nota: O item `algodao` é excluído desta validação pois é categorizado como link homologado CONAB, sem cotação numérica direta DERAL).*
2. **Rejeição Estrita de Anomalias Numéricas:**
   - Preços nulos, strings vazias, valores NaN ou negativos (`<= 0`) são imediatamente rejeitados com HTTP 422.
3. **Imutabilidade de Preços Oficiais:**
   - O Backoffice **NÃO possui** e **NUNCA terá** formulário de edição manual de preços individuais. Todos os preços devem vir comprovados a partir do upload de documento oficial íntegro.

---

## 6. Evidências de Proveniência e Integridade Criptográfica

1. **Hash SHA-256 de Proveniência:**
   - Todo snapshot importado calcula e armazena o resumo criptográfico SHA-256 (`hashlib.sha256(file_bytes).hexdigest()`) antes de qualquer parsing.
   - O hash é exibido com botão de cópia rápida na interface do Backoffice, permitindo auditoria cruzada imediata com o arquivo oficial baixado da SEAB/DERAL.
2. **Proteção contra Injeção Indireta de Snapshots:**
   - O `AgroConfigService.update_config` verifica se a chave sendo editada é `agro:mercado:config`.
   - Se um operador tentar alterar `deral_active_snapshot` diretamente via `PUT /backoffice/agro/configuracoes/agro:mercado:config`, a requisição é interceptada e abortada com `ValueError` / HTTP 422:
     > *"O snapshot ativo do DERAL não pode ser alterado por esta rota genérica. Utilize o endpoint de ativação/rollback atômico."*
   - O chaveamento só é aceito se vier com a flag interna `_allow_snapshot_switch=True`, injetada exclusivamente pelo `DeralSnapshotService`.

---

## 7. Estratégia de Publicação Atômica, Invalidação e Rollback

### 7.1 Ativação Atômica
Ao chamar `POST /backoffice/agro/mercado/deral/snapshots/{id}/activate`:
1. O snapshot é verificado no banco e seu envelope é validado.
2. O índice `agro:deral:snapshots:index` é atualizado marcando o snapshot como `ATIVO` e os demais como `INATIVO`.
3. A chave `agro:mercado:config` tem o ponteiro `deral_active_snapshot` atualizado transacionalmente com bloqueio pessimista (`with_for_update`).
4. O cache L1 em memória de `public_mercado.precos_publicos` é imediatamente invalidado (`PrecosPublicosService.invalidate_cache()`).
5. Um registro detalhado de auditoria é gravado em `AdminAuditLog` (`action="market_deral_snapshot_activated"`).

### 7.2 Rollback Operacional
Ao chamar `POST /backoffice/agro/mercado/deral/snapshots/{id}/rollback`:
1. O operador informa o ID do snapshot anterior que deseja restaurar e a justificativa obrigatória.
2. O pipeline executa a reversão atômica com as mesmas garantias de integridade e invalidação imediata de cache L1.
3. O log de auditoria registra a ação `market_deral_snapshot_rollback` com a justificativa técnica.

---

## 8. Integração com Configurações Dinâmicas e Resolução Pública

1. **Carregamento Dinâmico em Tempo de Execução:**
   - Em `services/api/public_mercado/precos_publicos.py`, a função `_carregar_snapshot` consulta prioritariamente o snapshot ativo em memória do `DeralSnapshotService` ou o override ativo de cache.
   - Caso nenhum snapshot tenha sido importado via banco, o sistema faz fallback transparente para o snapshot estático bundled `deral-prp-2026-10-16.json`, garantindo zero interrupção para os usuários do aplicativo público.
2. **Zero Conexões Comerciais em Leituras Públicas:**
   - O tráfego de leitura de milhares de produtores em `GET /api/v1/public/mercado/precos` e `/catalogo` é atendido 100% a partir da memória L1 do processo FastAPI, sem consumir nenhuma conexão do pool restrito do PostgreSQL comercial (`db_pool_size=3`).

---

## 9. RBAC e Trilha de Auditoria Compulsória

### 9.1 Matriz de Permissões RBAC

| Permissão | Ações Autorizadas | Perfis Típicos |
| :--- | :--- | :--- |
| `backoffice:agro:market:view` | Visualizar status das fontes, histórico de snapshots, inspecionar cotações | Suporte Técnico, Analista de Mercado, Administrador Agro |
| `backoffice:agro:market:update` | Upload de snapshots, ativação atômica, rollback, alteração de parâmetros operacionais de cache e staleness | Administrador Agro, Diretor Técnico |

Usuários não autenticados ou produtores rurais comuns recebem HTTP 401 Unauthorized / HTTP 403 Forbidden ao tentar acessar qualquer rota sob `/backoffice/agro/mercado`.

### 9.2 Trilha de Auditoria (`AdminAuditLog`)
Todas as ações de mutação (upload, ativação, rollback e alteração de parâmetros) registram:
- `admin_user_id`: Identificador do administrador responsável.
- `action`: Código da ação (`market_deral_snapshot_uploaded`, `market_deral_snapshot_activated`, `market_deral_snapshot_rollback`, `market_config_updated`).
- `target_type`: `deral_snapshot` ou `market_config`.
- `target_id`: ID do snapshot ou chave de configuração.
- `ip_address`: Endereço IP de origem.
- `user_agent`: Identificador do navegador/cliente HTTP.
- `payload`: Dados estruturados da operação (nome do arquivo, tamanho, SHA-256, total de commodities, justificativa).

---

## 10. Resultados dos Testes Automatizados

Comando executado:
```bash
./.venv/bin/pytest tests/unit/core/test_backoffice_agro_01e4.py -v
```

### 10.1 Suíte Específica AGRO-ADMIN-01E4:

| # | Cenário Testado | Função de Teste | Status |
| :---: | :--- | :--- | :---: |
| 1 | RBAC nos endpoints administrativos (401/403 vs 200) | `test_01_rbac_market_endpoints` | **PASSED** |
| 2 | Atualização de parâmetros operacionais de cache | `test_02_update_market_config_operational_parameters` | **PASSED** |
| 3 | Concorrência otimista e conflito de versão (409) | `test_03_optimistic_concurrency_conflict` | **PASSED** |
| 4 | Bloqueio de injeção direta de snapshot em config genérica | `test_04_block_direct_snapshot_injection_in_generic_config` | **PASSED** |
| 5 | Rejeição de arquivo JSON corrompido no upload | `test_05_upload_corrupt_json_fails` | **PASSED** |
| 6 | Rejeição de snapshot com commodities faltantes | `test_06_upload_missing_required_commodities_fails` | **PASSED** |
| 7 | Rejeição de extensão não homologada (.txt, .exe) | `test_07_upload_invalid_file_extension_fails` | **PASSED** |
| 8 | Rejeição de snapshot com preço negativo ou zero | `test_08_upload_negative_price_fails` | **PASSED** |
| 9 | Upload válido com persistência e hash SHA-256 | `test_09_upload_valid_snapshot_sha256_persistence` | **PASSED** |
| 10 | Ativação atômica e invalidação do cache L1 | `test_10_atomic_activation_and_l1_invalidation` | **PASSED** |
| 11 | Rollback operacional para snapshot anterior | `test_11_rollback_to_previous_snapshot` | **PASSED** |
| 12 | Telemetria e status das fontes de mercado | `test_12_get_sources_status_and_metrics` | **PASSED** |
| 13 | Preservação integral do contrato público `/precos` | `test_13_preserve_public_mercado_contract` | **PASSED** |

**Resultado:** 13 passed em 1.54s (100% de sucesso).

### 10.2 Bateria de Regressão Consolidada:
```bash
./.venv/bin/pytest tests/unit/core/test_backoffice_agro_01e4.py \
                  tests/unit/core/test_backoffice_agro_01e3a.py \
                  tests/unit/core/test_backoffice_agro_01e2.py \
                  tests/unit/test_precos_publicos.py \
                  tests/unit/test_ptax_publico.py \
                  tests/unit/test_macro_publico.py \
                  tests/unit/test_ibge_sidra_publico.py -v
```
**Resultado da Regressão:** **72 passed, 0 failed** em 3.97s.

### 10.3 Verificação de Tipos TypeScript (Frontend Web):
```bash
pnpm --filter web exec tsc --noEmit
```
**Resultado:** Exit code 0 (zero erros de tipagem, estrita conformidade com Next.js 16 e shadcn/ui).

---

## 11. Pendências de Homologação Real

1. **Instância Real PostgreSQL com Múltiplos Nós:**
   - Em produção, a tabela `configuracoes_saas` atuará como coordenadora distribuída entre todos os pods Uvicorn. Validar se a sincronização de eventos via Redis canal `agro:config:events` propaga a invalidação do L1 de preços para todos os workers em menos de 100 ms.
2. **Automação da Ingestão DERAL (Implementada em 25/10/2026):**
   - O `background_worker` consulta a fonte oficial HTTPS a cada seis horas, valida a planilha BIFF8 por cabeçalho, período, rótulo, unidade, 21 IDs e valores positivos, registra SHA-256 e mantém os bytes brutos.
   - Uma versão mais recente é aprovada pelo ator técnico inativo `deral-sync@system.invalid` e ativada pela mesma sequência transacional/auditada do Backoffice. Datas iguais ou anteriores não substituem o snapshot ativo; falhas preservam a versão vigente.
   - O parser localiza produtos por rótulo/unidade em vez de coordenadas de linha fixas. A API consulta o ponteiro ativo do banco no máximo uma vez por minuto e invalida o cache L1 quando outro processo publica uma nova semana.
   - O serviço `background-worker` já está definido em `docker-compose.prod.yml`; ambientes que executam somente a API precisam iniciar o worker `background_worker` para manter a consulta periódica.

---

## 12. Riscos Residuais e Mitigações

| Risco Residual | Severidade | Mitigação Implementada |
| :--- | :---: | :--- |
| **Upload de snapshot com preços defasados** | Média | A tela exibe a data de apuração e a interface alerta quando a apuração tem mais de 10 dias. O operador pode acionar o rollback imediato em caso de engano. |
| **Tentativa de adulteração de preços** | Crítica | A edição manual de preços individuais é impossível pela arquitetura da API. Apenas documentos com hash SHA-256 e envelope oficial são processados. |
| **Concorrência entre administradores** | Baixa | Proteção por `expected_revision` em `PUT /config` e bloqueio transacional nas operações de snapshot garantem que edições concorrentes sejam rejeitadas com HTTP 409. |
| **Indisponibilidade do banco de dados** | Baixa | A API pública de mercado consome a memória L1 do processo FastAPI, continuando a servir dados cacheados mesmo se o PostgreSQL estiver temporariamente inacessível. |

---

## 13. Veredicto Técnico

# **GO**

A fase **AGRO-ADMIN-01E4** cumpriu integralmente todos os requisitos funcionais, de integridade governamental, segurança criptográfica, concorrência e resiliência propostos.

> **Parada Mandatória de Execução:** Conforme solicitado, a execução foi interrompida nesta etapa e o relatório final foi entregue. A fase **AGRO-ADMIN-01E5** NÃO foi iniciada e aguarda a decisão e autorização explícita do usuário.
