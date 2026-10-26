# Relatório de Implementação e Homologação — DEEPFARMS-AGRO-FREE-01E2F-B4

**Identificador:** `DEEPFARMS-AGRO-FREE-01E2F-B4`  
**Título:** Preços Públicos Reais de Commodities Agropecuárias com Rastreabilidade e Correção da Selic  
**Data da Homologação:** 21/10/2026  
**Status:** **CONCLUÍDO COM ÊXITO — HOMOLOGADO**  

---

## 1. Sumário Executivo

A iniciativa `DEEPFARMS-AGRO-FREE-01E2F-B4` implementou com êxito a apresentação de preços agropecuários reais nos cards do módulo Mercado do DeepFarms Agro, consumindo dados governamentais oficiais autorizados e gratuitos do **DERAL/SEAB-PR** (Departamento de Economia Rural / Secretaria de Estado da Agricultura e do Abastecimento do Paraná).

A integração foi arquitetada com **rastreabilidade e proveniência estrita célula a célula**, registrando o documento oficial fonte, hash criptográfico SHA-256 da planilha original, célula da planilha e regra de transformação aplicada (arredondamento decimal `HALF_UP` para 2 casas).

Adicionalmente, foi sanada de forma definitiva a inconsistência da **Taxa Selic Meta** (Defeito 4), cujo endpoint no SGS/BCB projetava datas futuras da reunião do Copom.

---

## 2. Matriz de Fontes e Rastreabilidade Documental

### Metadados do Documento Fonte Homologado
- **Instituição:** DERAL / SEAB-PR
- **Documento Oficial:** `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls`
- **Título Oficial:** *Preços Médios Semanais Recebidos pelos Agricultores*
- **Semana de Referência:** 42-2026 (período de 12/10/2026 a 16/10/2026)
- **Data da Publicação:** 16/10/2026
- **Hash Criptográfico SHA-256 do Documento:**  
  `65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1`
- **Planilha / Aba de Origem:** `Rav`
- **Coluna de Extração:** `MÉDIA` (preço médio ponderado estadual)
- **Regra de Transformação:** Arredondamento decimal `HALF_UP` para 2 casas

### Preços Auditados e Células de Proveniência

| Commodity (ID) | Produto Original DERAL | Célula Origem | Valor Bruto Original | Valor Homologado (R$) | Unidade Comercial | Praça de Coleta |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Arroz em Casca** (`arroz`) | Arroz em casca irrigado | `Rav!X6` | 107.0009 | **R$ 107,00** | Saca de 60 kg | Paraná — média semanal |
| **Café Arábica** (`cafe-arabica`) | Café beneficiado produtor | `Rav!X7` | 1380.5078 | **R$ 1.380,51** | Saca de 60 kg | Paraná — média semanal |
| **Feijão Comum** (`feijao`) | Feijão de cor | `Rav!X9` | 302.6761 | **R$ 302,68** | Saca de 60 kg | Paraná — média semanal |
| **Milho Físico** (`milho`) | Milho | `Rav!X11` | 51.7745 | **R$ 51,77** | Saca de 60 kg | Paraná — média semanal |
| **Soja em Grão** (`soja`) | Soja | `Rav!X12` | 134.9794 | **R$ 134,98** | Saca de 60 kg | Paraná — média semanal |
| **Trigo em Grão** (`trigo`) | Trigo | `Rav!X17` | 78.9314 | **R$ 78,93** | Saca de 60 kg | Paraná — média semanal |
| **Boi Gordo** (`boi-gordo`) | Boi gordo | `Rav!X46` | 371.2050 | **R$ 371,21** | Arroba (@ de 15 kg) | Paraná — média semanal |
| **Algodão Pluma** (`algodao`) | — | — | — | *Consulte na fonte oficial* | Saca / Libra-peso | CEPEA/ESALQ (Link homologado) |

*Nota Regulatória:* Para o Algodão em pluma, em observância estrita aos termos de uso e propriedade intelectual do CEPEA/ESALQ e ausência de cotação pública aberta no relatório semanal do Paraná, é mantido o status transparente de consulta na página oficial homologada.

---

## 3. Correção da Selic Meta (Defeito 4)

- **Causa Raiz Identificada:** A série 432 do Banco Central (Meta Selic definida pelo Copom) projeta as datas do calendário de reuniões futuras do Copom até a data da próxima reunião programada (`04/11/2026`). O endpoint padrão `/dados/ultimos/1` retornava esse registro de data futura.
- **Correções Aplicadas:**
  1. No arquivo `services/api/public_mercado/sgs.py`, a consulta foi ajustada para buscar os últimos 20 registros (`qtd = 20`, respeitando o limite oficial da API do SGS) e filtrar estritamente por `data <= today` no fuso horário oficial `America/Sao_Paulo`.
  2. No arquivo `services/api/public_mercado/macro_service.py`, o guardrail `check_item_staleness` passou a validar e sinalizar qualquer data futura como anomalia/defasagem (`DEFASADO, True`).

---

## 4. Engenharia e Arquitetura de Software

### Backend (`services/api/public_mercado/`)
1. **Snapshot Auditado com Integridade Física:**
   - Dados persistidos em `data/deral-prp-2026-10-16.json` com schema versionado e imutável.
   - Leitura pura e estática desacoplada de conexões de banco de dados comercial PostgreSQL (`db_pool_size=3` preservado).
2. **Contratos Pydantic Estritos (`precos_publicos.py`):**
   - Modelos `PrecoPublicoItem` e `PrecosPublicosResponse` com `extra="forbid"`, validações numéricas e metadados de proveniência (`documentoOficial`, `documentoHashSha256`, `registroOriginal`, `valorOriginal`, `unidadeOriginal`, `transformacaoAplicada`).
3. **Serviço de Cache L1/L2 (`precos_publicos_service.py`):**
   - Cache em memória do processo com lock atômico assíncrono contra cache stampede e fallback resiliente.
4. **Rotas Públicas Anônimas (`router.py`):**
   - `GET /api/v1/public/mercado/precos`: Lista completa com cabeçalho `Cache-Control: public, max-age=300, stale-while-revalidate=600`.
   - `GET /api/v1/public/mercado/precos/{commodity_id}`: Item isolado ou HTTP 404 seguro para commodities sem preço homologado.

### Frontend (`apps/agro/src/`)
1. **Roteamento Transparente via Proxy Next.js (`next.config.ts`):**
   - Adicionada regra de `rewrites` para `/api/v1/:path*` apontando para o backend interno (`http://127.0.0.1:8000`), garantindo mesma origem (`same-origin`), eliminando bloqueios de CORS e falhas de conexão de rede.
2. **Cliente de Preços (`lib/mercado/precos.ts`):**
   - Parser estrito `parsePrecosResponse` com verificação de hash SHA-256 e proveniência.
   - Cache offline resiliente em `localStorage` sob a chave `deepfarms_agro_mercado_precos_v2`, com purga automática de versões legadas (`deepfarms_agro_mercado_precos_v1`).
3. **Componente Visual (`components/mercado/catalogo-mercado.tsx`):**
   - Gestão de estados: `CARREGANDO`, `ATUAL`, `ANTIGO` (dado salvo com aviso visual), `ERRO` e `INDISPONIVEL`.
   - Botão interativo de recuperação (*Tentar novamente*) e listener de auto-reconexão (`window.addEventListener("online")`).
   - Identificadores semânticos de teste `data-commodity-id` e `data-testid="estado-precos"`.
   - Distinção visual e semântica expressa entre **Preço Médio Recebido pelo Produtor (Oficial)** e mercado físico de balcão / contratos futuros de bolsas.

---

## 5. Evidências de Testes e Validação Técnica

### 1. Testes Automatizados Frontend (Vitest)
```bash
npm test -- tests/unit/precos.test.ts tests/unit/agro-auth.test.ts tests/unit/catalogo-mercado.test.ts
```
- `tests/unit/precos.test.ts`: 12 testes aprovados (100%).
- `tests/unit/agro-auth.test.ts`: 9 testes aprovados (100%).
- `tests/unit/catalogo-mercado.test.ts`: 17 testes aprovados (100%).
- **Resultado:** **38 testes aprovados**, 0 falhas.

### 2. Validação Estática de Tipos e Qualidade de Código
- `npx tsc --noEmit`: **0 erros de compilação**.
- `npm run lint`: **0 avisos / 0 erros de linter**.

### 3. Testes Funcionais de API em Tempo Real (HTTP)
- `GET /api/v1/public/mercado/precos`:
  - Status: **200 OK**
  - Total de commodities: **7 itens com proveniência completa**.
- `GET /api/v1/public/mercado/precos/soja`:
  - Retorno: R$ 134,98 / Saca de 60 kg (célula `Rav!X12`).
- `GET /api/v1/public/mercado/precos/milho`:
  - Retorno: R$ 51,77 / Saca de 60 kg (célula `Rav!X11`).
- `GET /api/v1/public/mercado/precos/algodao`:
  - Status: **404 Not Found** (comportamento correto e seguro).

---

## 6. Veredicto Final

A entrega cumpre 100% das diretrizes do projeto:
- **Zero dados simulados:** Valores derivados unicamente de planilha pública governamental auditada.
- **Rastreabilidade completa:** Registro de célula de origem e hash SHA-256 em cada item.
- **Isolamento de banco:** Nenhuma conexão com o banco PostgreSQL comercial ou criação de tabelas/tenants.
- **Resiliência e offline-first:** Cache L1/L2, persistência local versionada e recuperação automática de conectividade.
- **Aderência às Leis de Engenharia:** Tipagem estrita, testes unitários, commits atômicos e atualização documental.
