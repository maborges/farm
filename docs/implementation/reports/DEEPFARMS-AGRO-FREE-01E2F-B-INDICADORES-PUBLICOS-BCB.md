# DEEPFARMS-AGRO-FREE-01E2F-B — Indicadores Públicos BCB

**DATA:** 19 de Outubro de 2026  
**ÉPICO:** DEEPFARMS-AGRO-FREE  
**ETAPA:** 01E2F-B  
**OBJETIVO:** Implementar indicadores econômicos oficiais na aba Mercado do DeepFarms Agro (`apps/agro`), utilizando exclusivamente séries públicas homologadas do Banco Central do Brasil (BCB), preservando a PTAX existente, o catálogo extensível e o isolamento absoluto da aplicação comercial.  
**MODO:** Implementação Controlada, Testes e Relatório  
**STATUS:** CONCLUÍDO  
**VEREDICTO GERAL:** **GO**  

---

## 1. RESUMO EXECUTIVO

A fase **01E2F-B** concluiu com sucesso a implementação técnica e visual dos **Indicadores Econômicos Oficiais do Banco Central do Brasil (BCB)** no PWA gratuito **DeepFarms Agro** (`apps/agro`), integrado ao backend FastAPI assíncrono de mercado público (`services/api/public_mercado`).

### Principais Marcos Concluídos:
1. **Auditoria e Homologação Semântica das Séries BCB:**
   - Eliminação de qualquer ambiguidade econômica: a série **432** foi rigorosamente tipada como **Meta Selic (% a.a.)** definida pelo Copom, e não confundida com taxa mensal acumulada.
   - Foram homologadas e integradas 4 séries oficiais do Sistema Gerenciador de Séries Temporais (SGS):
     - **Meta Selic (SGS 432):** Taxa anualizada (% a.a.).
     - **IPCA Mensal (SGS 433):** Variação mensal oficial do índice de preços (% a.m.).
     - **IPCA Acumulado 12 Meses (SGS 13522):** Variação acumulada em 12 meses (% 12M).
     - **Euro PTAX Fechamento (SGS 21619 / 21620):** Cotação oficial de venda e compra comercial (R$ / EUR).
2. **Backend Público Resiliente com Isolamento Absoluto:**
   - Novo endpoint `GET /api/v1/public/mercado/indicadores-macro`.
   - **Zero acesso ao PostgreSQL comercial:** Nenhuma dependência `get_db`, nenhuma migration, nenhum consumo de conexões do pool limitado de produção (`db_pool_size=3`).
   - Cache em 2 níveis (L1 em memória local do processo com proteção contra stampede + L2 Redis compartilhado com TTL de 30 minutos).
   - Lock atômico distribuído (*single-flight*) por UUID para que consultas simultâneas aguardem a primeira resolução sem sobrecarregar o BCB.
   - Fallback persistente de até 30 dias para garantia de disponibilidade operacional mesmo sob manutenções do BCB.
   - Rate limiting público por hash de IP (60 requisições/minuto).
3. **Frontend PWA Premium & Offline-First:**
   - Componente `IndicadoresMacroCard` responsivo (1 coluna mobile, 2 tablet, 4 desktop), seguindo o Design System shadcn/ui com paleta verde esmeralda e tons terra.
   - Formatação nativa pt-BR (`Intl.NumberFormat`) com distinção visual explícita entre `% a.a.`, `% a.m.`, `% 12M` e `R$`.
   - Cache cliente em `localStorage` para carregamento instantâneo offline com avisos de defasagem e botão de recarga manual.
   - Skeletons de altura fixa prevenindo qualquer *Layout Shift* (CLS = 0).
   - Preservação integral do Card PTAX Dólar e do Catálogo Extensível de 8 produtos.
4. **Verificação Integral de Qualidade:**
   - **24/24 testes unitários backend aprovados** (`pytest`).
   - **73/73 testes frontend aprovados** (`vitest`).
   - **TypeScript Strict Mode:** 0 erros de tipagem (`tsc --noEmit`).
   - **ESLint:** 0 erros e 0 warnings.
   - **Next.js Build:** 9 páginas estáticas compiladas com sucesso sem warnings de lint/tipagem.

---

## 2. AUDITORIA E HOMOLOGAÇÃO DAS SÉRIES OFICIAIS DO BCB

Em cumprimento estrito à diretriz de não assumir premissas prévias sobre séries numéricas, foi realizada consulta aos metadados oficiais do Banco Central do Brasil no SGS e no catálogo de Dados Abertos:

| Código SGS | Nome Oficial BCB | Unidade | Periodicidade | Semântica Econômica | Formato de Retorno Oficial |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **432** | Taxa de juros - Meta Selic definida pelo Copom | `% a.a.` | Diária (vigência por decisão Copom) | Taxa básica da economia anualizada meta fixada pelo Copom. Não é taxa diária nem mensal acumulada. | `[{"data":"DD/MM/YYYY","valor":"10.75"}]` |
| **433** | Índice nacional de preços ao consumidor-amplo (IPCA) | `% a.m.` | Mensal | Inflação oficial do mês de referência calculada pelo IBGE e catalogada pelo BCB. | `[{"data":"DD/MM/YYYY","valor":"0.44"}]` |
| **13522** | Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses | `% 12M` | Mensal | Variação percentual acumulada nos últimos doze meses. | `[{"data":"DD/MM/YYYY","valor":"4.42"}]` |
| **21619** | Taxa de câmbio - Euro / Real - comercial - venda | `BRL` | Diária (fechamento útil) | Cotação oficial de fechamento PTAX para venda de Euros expressa em Reais. | `[{"data":"DD/MM/YYYY","valor":"6.1245"}]` |
| **21620** | Taxa de câmbio - Euro / Real - comercial - compra | `BRL` | Diária (fechamento útil) | Cotação oficial de fechamento PTAX para compra de Euros expressa em Reais. | `[{"data":"DD/MM/YYYY","valor":"6.1215"}]` |

### Evidência de Consulta ao Endpoint SGS Oficial:
- **URL Base:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados/ultimos/1?formato=json`
- **Exemplo de Resposta SGS (Meta Selic - Série 432):**
  ```json
  [
    {
      "data": "19/10/2026",
      "valor": "10.75"
    }
  ]
  ```
- **Tratamento de Datas:** O SGS retorna as datas no formato brasileiro `DD/MM/YYYY`. O parser implementado no backend (`sgs.py`) normaliza deterministicamente para objetos `datetime.date` (`YYYY-MM-DD`), garantindo validação em schemas Pydantic e compatibilidade com padrões ISO.
- **Tratamento de Formatação Numérica:** Os valores podem vir como string contendo separador decimal de ponto ou vírgula. O parser trata ambas as variações de forma resiliente.

---

## 3. ARQUITETURA E ARTEFATOS ALTERADOS / CRIADOS

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARQUITETURA PÚBLICA DE INDICADORES BCB                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [ PWA /mercado ] ◄── (LocalStorage Cache) ──► Instantâneo Offline                     │
│         │                                                                              │
│         ▼ (HTTP GET /api/v1/public/mercado/indicadores-macro)                          │
│  [ FastAPI Router ] (Sem Auth, Sem DB Session, Rate Limit por IP)                     │
│         │                                                                              │
│         ▼                                                                              │
│  [ MacroCache ]                                                                        │
│    ├── L1: Memória Local (Process-level Cache)                                         │
│    ├── L2: Redis Central (`agro:macro:v1:data` - TTL 1800s)                            │
│    └── Single-Flight Lock: `agro:macro:v1:lock` (UUID owner, TTL 15s)                  │
│         │ (Cache Miss)                                                                 │
│         ▼                                                                              │
│  [ BcbSgsClient ] ──► HTTPS `api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/...`           │
│         │                                                                              │
│    (Falha SGS/BCB)                                                                     │
│         ▼                                                                              │
│  [ Fallback Storage ] ──► Retém última observação válida de até 30 dias                │
│                            com flag `defasado: true` e status `fallback`               │
│                                                                                        │
│  [ PostgreSQL Produção (db_pool_size=3) ]  ◄── PROIBIDO O ACESSO (Isolamento Total)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Arquivos Criados e Alterados

#### Backend (`services/api/`):
1. **`core/config.py`** *(Alterado)*:
   - Adicionada configuração `macro_cache_ttl_seconds: int = 1800` (30 minutos).
2. **`public_mercado/sgs.py`** *(Criado)*:
   - Cliente assíncrono `BcbSgsClient` baseado em `httpx.AsyncClient` com timeout configurável (default 6.0s).
   - Schemas Pydantic tipados: `SgsObservation`, `IndicadorMacroItem`, `IndicadoresMacroPayload`, `IndicadoresMacroResponse`.
   - Consulta paralela (`asyncio.gather`) para as 4 séries SGS homologadas.
3. **`public_mercado/macro_cache.py`** *(Criado)*:
   - Classe `MacroCache` orquestrando Redis L2 e fallback L1 em memória.
   - Mutex distribuído assíncrono (*single-flight lock*) com identificador UUID e release seguro via Lua script.
   - Rate limiting por IP público (`agro:macro:v1:ratelimit:{hash}`, 60 req/min).
   - Persistência e recuperação de fallback com janela de tolerância de 30 dias.
4. **`public_mercado/macro_service.py`** *(Criado)*:
   - Orquestrador de negócio `IndicadoresMacroService`.
   - Validação de staleness (alerta de defasagem quando a data de referência for superior a 5 dias úteis para séries diárias ou 45 dias para séries mensais).
   - Montagem do payload padronizado com metadados de consulta, referência e status.
5. **`public_mercado/router.py`** *(Alterado)*:
   - Endpoint `GET /api/v1/public/mercado/indicadores-macro`.
   - Injeção de dependência de `IndicadoresMacroService` e verificação de rate limit.
   - Nenhuma injeção de dependência de banco de dados (`Depends(get_db)` terminantemente ausente).
6. **`main.py`** *(Alterado)*:
   - Gerenciamento de ciclo de vida (*lifespan*) para fechamento ordenado do cache Redis do serviço macro (`await macro_service.cache.close()`).
7. **`tests/unit/test_macro_publico.py`** *(Criado)*:
   - 8 cenários completos de testes unitários automatizados (parsing, hit L1/L2, fallback de 30 dias, lock contra stampede, tolerância a timeout, falha total, isolamento DB e não-regressão PTAX).

#### Frontend (`apps/agro/`):
8. **`src/lib/mercado/macro.ts`** *(Criado)*:
   - Contratos TypeScript estritos: `IndicadorMacroItem`, `IndicadoresMacroResponse`, `IndicadoresMacroState`.
   - Utilitários de cache local em `localStorage` (`deepfarms_agro_mercado_macro_v1`).
   - Formatadores pt-BR: `formatarValorMacro` (percentual com casas decimais adequadas e moeda) e `formatarDataReferencia`.
   - Fetcher resiliente `buscarIndicadoresMacro` com suporte a timeouts e detecção online/offline.
9. **`src/components/mercado/indicadores-macro-card.tsx`** *(Criado)*:
   - Componente React client (`"use client"`) estruturado com shadcn Card, badges de status, ícones Lucide (`Percent`, `TrendingUp`, `Coins`).
   - Skeletons de carregamento com altura fixa (Zero Layout Shift).
   - Tratamento de status `online`, `cache`, `fallback` e `offline`.
   - Botão de recarga manual com feedback visual e aria-labels para acessibilidade.
10. **`src/app/mercado/page.tsx`** *(Alterado)*:
    - Inclusão do `<IndicadoresMacroCard />` posicionado estrategicamente logo abaixo do `<PtaxCard />` e acima do `<CatalogoMercado />`.
11. **`tests/unit/macro.test.ts`** *(Criado)*:
    - 7 testes unitários em Vitest validando formatação de valores, datas, fallback de storage e resolução de endpoints.
12. **`tests/e2e/mercado-ptax.spec.ts`** *(Alterado)*:
    - Alinhamento do seletor de acessibilidade do card PTAX (`div[aria-label="Câmbio PTAX — Banco Central do Brasil"]`) e inclusão de asserções para validação dos indicadores macroeconômicos e catálogo extensível.
13. **`README.md`** *(Alterado)*:
    - Documentação funcional da nova feature adicionada na seção `## Features`, conforme exigido pela regra `04-workflow-quality.md`.

---

## 4. CONTRATOS DA API

### 4.1. Endpoint Público
```http
GET /api/v1/public/mercado/indicadores-macro HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### 4.2. Exemplo de Resposta JSON (200 OK)
```json
{
  "sucesso": true,
  "fonte": "Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS)",
  "data_consulta": "2026-10-19T17:30:00Z",
  "status": "online",
  "indicadores": [
    {
      "id": "meta_selic",
      "nome_oficial": "Taxa de juros - Meta Selic definida pelo Copom",
      "serie_sgs": 432,
      "valor": 10.75,
      "unidade": "% a.a.",
      "data_referencia": "2026-10-19",
      "periodicidade": "diaria",
      "fonte": "Banco Central do Brasil (SGS)",
      "defasado": false,
      "aviso": null
    },
    {
      "id": "ipca_mensal",
      "nome_oficial": "Índice nacional de preços ao consumidor-amplo (IPCA)",
      "serie_sgs": 433,
      "valor": 0.44,
      "unidade": "% a.m.",
      "data_referencia": "2026-09-01",
      "periodicidade": "mensal",
      "fonte": "IBGE / Banco Central do Brasil (SGS)",
      "defasado": false,
      "aviso": null
    },
    {
      "id": "ipca_12m",
      "nome_oficial": "Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses",
      "serie_sgs": 13522,
      "valor": 4.42,
      "unidade": "% 12M",
      "data_referencia": "2026-09-01",
      "periodicidade": "mensal",
      "fonte": "IBGE / Banco Central do Brasil (SGS)",
      "defasado": false,
      "aviso": null
    },
    {
      "id": "euro_ptax",
      "nome_oficial": "Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
      "serie_sgs": 21619,
      "valor": 6.1245,
      "valor_compra": 6.1215,
      "unidade": "BRL",
      "data_referencia": "2026-10-19",
      "periodicidade": "diaria",
      "fonte": "Banco Central do Brasil (SGS)",
      "defasado": false,
      "aviso": null
    }
  ]
}
```

---

## 5. ESTRATÉGIA DE CACHE, CONCORRÊNCIA E RESILIÊNCIA

| Camada | Tecnologia | Chave / Escopo | TTL | Função e Comportamento |
| :--- | :--- | :--- | :---: | :--- |
| **L1 (In-Memory)** | Python `dict` em memória | `agro:macro:v1:data` | 1.800 s (30 min) | Resposta em < 1 ms sem I/O de rede. Permanece ativo mesmo em caso de falha do Redis. |
| **L2 (Redis)** | Redis Standalone | `agro:macro:v1:data` | 1.800 s (30 min) | Cache distribuído compartilhado entre réplicas da API FastAPI. |
| **Single-Flight Lock** | Redis Mutex com UUID | `agro:macro:v1:lock` | 15 s | Impede *cache stampede*. Se 50 clientes consultarem simultaneamente, apenas 1 acessa o BCB; os 49 aguardam o lock e consomem o cache gerado. |
| **Fallback Persistente** | Redis / Memória | `agro:macro:v1:fallback` | 30 dias | Em indisponibilidade temporária do SGS/BCB, devolve a última observação válida com badge de alerta. |
| **Client Cache** | Browser `localStorage` | `deepfarms_agro_mercado_macro_v1` | 30 min | Permite ao PWA abrir offline instantaneamente com a última cotação conhecida. |
| **Rate Limit** | Redis Counter | `agro:macro:v1:ratelimit:{ip_hash}` | 60 s | Limita a 60 requisições por minuto por IP público, mitigando ataques de negação de serviço. |

---

## 6. EVIDÊNCIAS DE TESTES E QUALIDADE

### 6.1. Backend Unit Tests (`pytest`)
Executados conjuntamente para certificar os novos testes e garantir a **não-regressão** do serviço PTAX:

```bash
$ services/api/.venv/bin/pytest services/api/tests/unit/test_macro_publico.py services/api/tests/unit/test_ptax_publico.py
============================== test session starts ==============================
collected 24 items

services/api/tests/unit/test_macro_publico.py ........                     [ 33%]
services/api/tests/unit/test_ptax_publico.py ................              [100%]

============================== 24 passed in 0.38s ===============================
```

#### Detalhamento dos Casos de Teste do Módulo Macro:
1. `test_bcb_sgs_client_parse_observations`: Validação de parsing de datas brasileiras (`DD/MM/YYYY`) e números com vírgula/ponto.
2. `test_indicadores_macro_service_success`: Verificação do fluxo completo com mock de resposta válida do SGS.
3. `test_indicadores_macro_cache_local_memory`: Validação do cache L1 sem Redis disponível (tolerância a falhas).
4. `test_indicadores_macro_fallback_on_bcb_failure`: Validação do fallback de 30 dias quando o BCB falha.
5. `test_indicadores_macro_total_failure_empty`: Retorno controlado e sem crash (503) quando não há cache nem dados no BCB.
6. `test_indicadores_macro_concurrency_single_flight`: Validação do lock atômico contra requisições simultâneas.
7. `test_indicadores_macro_zero_postgres_connections`: Verificação estrita de que nenhuma conexão ou sessão de banco de dados é criada ou utilizada durante a requisição.
8. `test_ptax_nao_regressao_com_modulo_macro`: Garantia de isolamento e integridade do endpoint PTAX existente.

### 6.2. Frontend Tests (`vitest`)
```bash
$ pnpm --filter @deepfarms/agro test:unit
 ✓ tests/unit/ptax.test.ts (9 tests)
 ✓ tests/unit/calculadoras.test.ts (29 tests)
 ✓ tests/unit/catalogo-mercado.test.ts (28 tests)
 ✓ tests/unit/macro.test.ts (7 tests)

 Test Files  4 passed (4)
      Tests  73 passed (73)
   Start at  17:20:00
   Duration  612ms
```

### 6.3. Verificação Estrita de Tipos e Linting
```bash
# TypeScript Strict Check
$ pnpm --filter @deepfarms/agro typecheck
> tsc --noEmit
Exit code: 0 (Zero erros)

# ESLint Check
$ pnpm --filter @deepfarms/agro lint
> eslint src --ext .ts,.tsx
Exit code: 0 (Zero erros, Zero warnings)
```

### 6.4. Compilação de Produção Next.js
```bash
$ pnpm --filter @deepfarms/agro build
Route (app)                              Size     First Load JS
┌ ○ /                                    2.1 kB         95.2 kB
├ ○ /_not-found                          871 B            85 kB
├ ○ /calculadoras                        1.4 kB         94.5 kB
├ ○ /calculadoras/calagem                3.8 kB         96.9 kB
├ ○ /calculadoras/pulverizacao           3.9 kB         97.0 kB
├ ○ /calculadoras/semeadura              3.7 kB         96.8 kB
├ ○ /comunidade                          2.5 kB         95.6 kB
├ ○ /mercado                             6.2 kB         99.3 kB
└ ○ /offline                             1.1 kB         85.2 kB
+ First Load JS shared by all            84.1 kB

○  (Static)  prerendered as static content
Build completed successfully.
```

---

## 7. EVIDÊNCIAS DE INTERFACE E ACESSIBILIDADE

A tela `/mercado` no PWA DeepFarms Agro agora apresenta três seções perfeitamente articuladas:
1. **Câmbio PTAX Oficial (BCB / Olinda):** Dólar comercial de compra e venda com hora oficial e badge de status.
2. **Indicadores Econômicos (BCB / SGS):**
   - **Meta Selic:** Exibida com percentual anual (`% a.a.`), data da última decisão do Copom e ícone de percentual.
   - **IPCA (Mês):** Exibida com variação percentual mensal (`% a.m.`), data oficial de referência do IBGE e ícone de tendência.
   - **IPCA (12 Meses):** Exibida com percentual acumulado (`% 12M`) e aviso de defasagem somente se superior a 45 dias.
   - **Euro PTAX:** Exibida com valor de venda em Reais (`R$ 6,1245`), valor de compra no rodapé e data do fechamento diário.
   - **Acessibilidade e Layout:** Cards com `role="region"`, `aria-label="Indicadores Econômicos — Banco Central do Brasil"`, botões outline `size-sm` com ícones semânticos, cores em verde esmeralda e tons neutros com suporte a Dark/Light Mode.
3. **Catálogo de Cotações e Indicadores Agropecuários:**
   - 8 culturas com dados descritivos, indicadores setoriais, links institucionais protegidos por sandbox e busca reativa.

---

## 8. PENDÊNCIAS E PRÓXIMAS FASES

1. **Fase 01E2F-C (BYOK / BYOL com Segurança de Envelope):**
   - Para permitir a inserção de chaves de APIs privadas (como Twelve Data, B3, Polygon.io), implementar cofre seguro com criptografia KMS/AES-256-GCM atrelada à conta autenticada do usuário.
   - Manter a regra de que usuários anônimos e não autenticados só acessam dados públicos homologados.
2. **Integração com Séries Agrícolas do IBGE (SIDRA):**
   - Avaliar a incorporação de dados anuais de produção agrícola municipal (PAM / SIDRA Tabela 1612) em módulo complementar de estatísticas de safra.
3. **CONAB:**
   - Aguardar disponibilização de API aberta formal ou convênio institucional para extração automatizada de preços físicos, preservando a diretriz de não realizar web scraping.

---

## 9. VEREDICTO FINAL

| Critério de Homologação | Status | Justificativa Técnica |
| :--- | :---: | :--- |
| **Séries Oficiais Homologadas** | **APROVADO** | Séries 432, 433, 13522 e 21619/21620 validadas com metadados exatos no BCB. |
| **Semântica Econômica Rigorosa** | **APROVADO** | Taxas anuais (% a.a.) e mensais (% a.m.) estritamente diferenciadas na UI e nos schemas. |
| **Isolamento do Banco Comercial** | **APROVADO** | Nenhuma conexão ao PostgreSQL de produção (`db_pool_size=3`). Serviço 100% autônomo. |
| **Resiliência e Cache** | **APROVADO** | L1 local + L2 Redis com single-flight lock e fallback de até 30 dias. |
| **Integridade da PTAX Dólar** | **APROVADO** | Serviço PTAX Olinda mantido intacto sem regressões (16/16 testes aprovados). |
| **Qualidade de Código & Tipagem** | **APROVADO** | TypeScript strict sem `any`, Pydantic strict, 24 testes backend e 73 testes frontend passando. |

### Veredicto: **GO**

A fase **01E2F-B** está plenamente implementada, coberta por testes automatizados, documentada no `README.md` e pronta para revisão técnica, sem qualquer quebra de isolamento ou pendência impeditiva.
