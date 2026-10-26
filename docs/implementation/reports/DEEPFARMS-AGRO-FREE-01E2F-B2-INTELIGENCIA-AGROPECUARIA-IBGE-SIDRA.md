# Relatório de Implementação: DEEPFARMS-AGRO-FREE-01E2F-B2 — Inteligência Agropecuária IBGE/SIDRA

## 1. Sumário Executivo

A fase **DEEPFARMS-AGRO-FREE-01E2F-B2** foi concluída com êxito, implementando a camada pública e gratuita de estatísticas agropecuárias oficiais do **Instituto Brasileiro de Geografia e Estatística (IBGE)** através da API SIDRA.

A solução atende aos produtores rurais com séries históricas e estimativas oficiais de área plantada, área colhida, quantidade produzida, rendimento médio de lavouras e efetivo de rebanhos/produção animal, preservando rigorosamente:
1. Os indicadores PTAX e macroeconômicos do Banco Central (BCB) previamente homologados.
2. O catálogo extensível de referências de mercado e commodities.
3. O isolamento absoluto da infraestrutura e banco comercial (`db_pool_size=3` do PostgreSQL permanece intocado).
4. As políticas de segurança contra abusos, SSRF e ataques de concorrência (*cache stampede*).

---

## 2. Esclarecimento da Ressalva B1 (Série Selic com Data Futura)

Na homologação B1, foi identificada uma observação da taxa Selic (série SGS 432) com data de referência de 04/11/2026 frente à data de execução corrente.
- **Investigação Oficial:** A série SGS 432 representa a *Meta Selic definida pelo Copom*. No calendário de divulgação do Banco Central do Brasil, a série projeta o horizonte de vigência deliberado na ata da última reunião do Comitê de Política Monetária até a reunião subsequente.
- **Validação de Código:** O validador semântico `check_item_staleness` no backend já computa `(ref_date - obs_date).days`. Quando `days < 0` (data de vigência projetada pelo Copom para o ciclo corrente), o sistema atribui status `NORMAL` e `estaDesatualizado = False`. Não há defeito ou anomalia no algoritmo de coleta; o comportamento reflete fielmente a semântica oficial do Banco Central.

---

## 3. Fontes Homologadas e Metadados Oficiais IBGE/SIDRA

Foram catalogados e homologados **23 produtos agropecuários** e **27 UFs**, integrados a 4 tabelas oficiais do SIDRA:

| Pesquisa | Tabela SIDRA | Periodicidade | Abrangência | Variáveis Oficiais | Produtos Atendidos |
|---|---|---|---|---|---|
| **PAM** (Produção Agrícola Municipal) | **5457** | Anual (1974–2024+) | Brasil, UF, Município | 8331 (Área plantada ou destinada à colheita - ha)<br>216 (Área colhida - ha)<br>214 (Quantidade produzida - t)<br>112 (Rendimento médio - kg/ha) | 13 lavouras: Soja, Milho, Café, Cana-de-açúcar, Trigo, Arroz, Feijão, Algodão, Sorgo, Laranja, Cacau, Banana, Mandioca |
| **LSPA** (Levantamento Sistemático da Produção Agrícola) | **6588** | Mensal (Safra em andamento) | Brasil, UF | 109 (Área plantada - ha)<br>216 (Área colhida - ha)<br>35 (Produção - t)<br>36 (Rendimento médio - kg/ha) | Lavouras com previsão mensal (Soja, Milho 1ª/2ª safra, Café, Cana, Trigo, Arroz, Feijão, Algodão, Sorgo, Laranja, Cacau, Banana) |
| **PPM** (Efetivo dos Rebanhos) | **3939** | Anual | Brasil, UF, Município | 105 (Efetivo dos rebanhos - Cabeças) | 7 rebanhos: Bovinos, Suínos, Galináceos, Ovinos, Caprinos, Bubalinos, Equinos |
| **PPM** (Origem Animal) | **74** | Anual | Brasil, UF, Município | 106 (Produção de origem animal) | 3 produções: Leite (Mil litros), Ovos de galinha (Mil dúzias), Mel de abelha (kg) |

### Semântica dos Símbolos Especiais SIDRA
- `-` (traço): Representa valor **zero** (trabalhado e convertido para `0.0` no backend e exibido como zero).
- `...` (três pontos): Dado não disponível ou inibido por critério de sigilo/não divulgação (convertido para `None` e tratado no frontend como `"Dado inibido / s/ dado"`).
- `X`: Dado omitido a fim de evitar individualização de informante (convertido para `None`).

---

## 4. Arquitetura de Backend e Segurança

### 4.1. Camada de Domínio e Clientes
- **`services/api/public_mercado/sidra.py`**:
  - Dicionários imutáveis `PRODUTOS` e `UFS` contendo o mapeamento estrito de parâmetros.
  - Rejeição imediata de parâmetros fora da lista permitida (mitigação de SSRF; URLs de agregação SIDRA são construídas exclusivamente por funções internas).
  - Regra de negócio: LSPA não possui granularidade municipal no IBGE (rejeitado com `ValueError` quando solicitado para `MUNICIPIO`).
  - Parsing resiliente de JSON com limite de tamanho de payload (máximo de 2 MB) e controle de timeouts HTTP (10s).
- **`services/api/public_mercado/sidra_cache.py`**:
  - Cache em 2 níveis: L2 Redis compartilhado com fallback transparente para L1 memória local do processo (`single_worker_fallback=True`).
  - Lock distribuído atômico por chave de consulta (`agro:sidra:v1:lock:{query_key}`), impedindo concorrência duplicada e sobrecarga aos servidores do IBGE.
  - Rate-limiting anônimo por IP de 60 requisições/minuto.
  - Armazenamento de fallback persistente (`agro:sidra:v1:last:{query_key}`) preservado para tolerância a falhas.
- **`services/api/public_mercado/sidra_service.py`**:
  - Orquestração dos métodos `get_catalogo()`, `get_municipios(uf)` (cache de 7 dias) e `get_estatisticas(...)`.
  - Avaliação de defasagem (staleness) por periodicidade (>2 anos para PAM/PPM anual; >3 meses para LSPA mensal).
  - Detecção de localidade sem registros (`SEM_DADOS`).

### 4.2. Rotas e Exposição FastAPI
- **`services/api/public_mercado/router.py`**:
  - `GET /api/v1/public/mercado/ibge/catalogo` (Cache-Control: `public, max-age=3600, stale-while-revalidate=86400`)
  - `GET /api/v1/public/mercado/ibge/municipios/{uf}` (Cache-Control: `public, max-age=86400, stale-while-revalidate=604800`)
  - `GET /api/v1/public/mercado/ibge/estatisticas` (Cache-Control: `public, max-age=300, stale-while-revalidate=600`)
- **`services/api/main.py`**:
  - `SessionHeartbeatMiddleware` e `TenantRLSMiddleware` atualizados para isentar prefixo `/api/v1/public/mercado`.
  - Hook de encerramento (`lifespan`) fecha pools de conexão do Redis/cache de forma graciosa.

---

## 5. Implementação no Frontend (DeepFarms Agro PWA)

### 5.1. Módulo de Contrato e Cache Local
- **`apps/agro/src/lib/mercado/ibge.ts`**:
  - Tipagem TypeScript estrita de todos os modelos de resposta e indicadores.
  - Cache offline instantâneo em `localStorage` sob chave envelopada versionada (`deepfarms_agro_mercado_ibge_v1_{key}`).
  - Formatação regional pt-BR de números e períodos (`formatarValorIbge`, `formatarPeriodoIbge`).

### 5.2. Componente de Interface
- **`apps/agro/src/components/mercado/ibge-producao-card.tsx`**:
  - Seletores intuitivos de Cultura/Atividade (23 opções), Abrangência Territorial (Brasil, Estado, Município) e Regime (PAM consolidado anual ou LSPA estimativa mensal).
  - Cards de métricas com indicação de período de referência e recorte.
  - Badges de disponibilidade: `NORMAL` (verde esmeralda), `DEFASADO` (âmbar), `SEM_DADOS` (cinza) e `Offline` (com ícone WifiOff).
  - Skeletons animados garantindo **Zero Layout Shift (CLS = 0)** durante carregamentos.
  - Link direto para a tabela correspondente no portal oficial SIDRA.
  - Aviso legal e regulatório explícito: *"Estatística oficial de produção e área divulgada pelo IBGE. Não é cotação nem preço de comercialização."*

---

## 6. Matriz de Testes e Certificação

Todos os testes automatizados da plataforma foram executados e aprovados:

| Camada | Escopo | Ferramenta | Quantidade | Status |
|---|---|---|---|---|
| **Backend** | PTAX, SGS Macro e IBGE SIDRA | `pytest` | 37 testes | **APROVADO** (100% sucesso) |
| **Frontend** | Unitários (IBGE, Macro, PTAX, Calculadoras, Catálogo) | `vitest` | 81 testes (5 suítes) | **APROVADO** (100% sucesso) |
| **Frontend** | Verificação de Tipos | `tsc --noEmit` | - | **APROVADO** (0 erros) |
| **Frontend** | Qualidade e Estilo | `eslint` | - | **APROVADO** (0 avisos/erros) |
| **Frontend** | Build de Produção Next.js 16 | `next build --webpack` | 9 rotas estáticas | **APROVADO** (0 erros) |
| **E2E** | Mercado, PTAX e IBGE SIDRA | `playwright` | 8 testes | **APROVADO** (100% sucesso) |

---

## 7. Próximos Passos Recomendados

1. **Fase 01E2F-C (Provedores Individuais BYOK / BYOL):**
   - Configuração de credenciais individuais no Backoffice por tenant para consumo de provedores com cotação em tempo real e licença de redistribuição individual (ex: CEPEA/ESALQ, B3, Agromensageiro).
2. **Histórico Gráfico no PWA:**
   - Adição opcional de componente de gráfico de evolução temporal de área vs. produtividade dos últimos 5 anos utilizando a série de pontos já retornada pelo endpoint `/estatisticas`.
