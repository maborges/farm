# AGRO-COLLECTOR-00 — Levantamento Técnico Empírico das Fontes Oficiais (Fase 0)

**Código:** `AGRO-COLLECTOR-00`  
**Documento Pai:** [AGRO-COLLECTOR-01 — Arquitetura do Agente Coletor](file:///opt/lampp/htdocs/farm/docs/architecture/AGRO-COLLECTOR-01-ARQUITETURA-AGENTE-DADOS.md)  
**Data da Sondagem ao Vivo:** 22/11/2026 (UTC `2026-11-22T03:05Z` – `03:12Z`)  
**Modalidade:** Inspeção HTTPS estrita (`verify=True`, `User-Agent: DeepFarms-AgroBot/1.0`, respeito a `robots.txt`, sem contorno de CAPTCHA/WAF e sem alterações em código de produção)  

---

## 1. Sumário Executivo

A **Fase 0** testou ao vivo todos os endpoints candidatos da Onda 1 e reforços estaduais para validar formato real, TLS, política de `robots.txt`, presença de bloqueios antibot/Power BI, periodicidade efetiva e bibliotecas disponíveis no `.venv`.

### Principais Descobertas

1. **Fontes determinísticas prontas para a Fase 1A (zero custo de IA, zero CAPTCHA):**
   - **DERAL / SEAB-PR (`deral_pr`):** confirmado 100% operacional via `.xls` BIFF8 (`Semana 46-2026`, `09/11/2026 a 13/11/2026`, `48` produtos válidos e `20` núcleos regionais).
   - **IEA / SAA-SP (`iea_sp`):** **viável em Nível 1 Determinístico via HTTP/HTML puro!** Apesar de exigir cookie de sessão + token `__RequestVerificationToken` (padrão ASP.NET Core AntiForgery), **não possui CAPTCHA nem login** para consultas de 1 dia útil. Em teste ao vivo para `18/11/2026`, retornou tabela HTML limpa com preços diários por EDR e catálogo de **52 produtos** (`49` ativos), incluindo **Algodão em pluma (`1905`)**, Soja (`1126`), Milho (`1124`), Boi gordo (`1411`), Café (`1053`) e Cana para Indústria (`1109`) em **40 EDRs** paulistas.
2. **Fontes em PDF estruturado prontas para o Extrator IA Nível 2 na Fase 1B:**
   - **EMATER-RS / ASCAR (`emater_rs`):** além do *Informativo Conjuntural* (`conj_19112026.pdf`, `3,41 MB`), publica o boletim semanal dedicado **"Cotações Agropecuárias"** (`preco_19112026.pdf`, Boletim 2467 de `19/11/2026`, `1,08 MB`, streams de texto extraíveis). Ressalva: `robots.txt` retornou HTTP 403 enquanto as páginas e PDFs retornam HTTP 200.
   - **SEAPA-MG (`seapa_mg`):** novo reforço aprovado empiricamente! A URL antiga (`/agricultura/paginas/cotacoes`) retorna `404`, mas a página ativa (`https://www.mg.gov.br/agricultura/documento/precos-correntes-0`) responde `HTTP 200` com `robots.txt` permissivo e link direto para o PDF semanal atualizado (`precos-correntes-de-produtos-selecionado-17-11-2026.pdf`, `734 KB`, streams de texto extraíveis).
3. **Fontes bloqueadas para coleta automatizada direta (`LINK_HOMOLOGADO_APENAS`):**
   - **CONAB (`conab_nacional`):** revalidado o diagnóstico das auditorias [DEEPFARMS-AGRO-FREE-01E2D2](file:///opt/lampp/htdocs/farm/docs/implementation/reports/DEEPFARMS-AGRO-FREE-01E2D2-CERTIFICACAO-DATASETS-CONAB.md) e [DEEPFARMS-AGRO-FREE-01E2F-B5A](file:///opt/lampp/htdocs/farm/docs/implementation/reports/DEEPFARMS-AGRO-FREE-01E2F-B5A-AUDITORIA-FONTES-EXPANSAO-MERCADO.md). Os subdomínios de preços (`portaldeinformacoes.conab.gov.br`, `consultaprecosdemercado.conab.gov.br`, `conabemnumeros.conab.gov.br`, `consultaweb.conab.gov.br`) continuam falhando com erro TLS `Hostname mismatch` sob `verify=True`; `dados.gov.br` exige token `Bearer` (`HTTP 401`); `dados.agricultura.gov.br` tem `0` datasets da CONAB; e `gov.br/conab` exibe painéis Power BI (com PDFs apenas de Cesta Básica). **Nota:** o link institucional `/assuntos/informacoes-agropecuarias/precos-agropecuarios` usado em rotas antigas retorna `404` — a URL ativa é `/atuacao/informacoes-agropecuarias/precos-agropecuarios`.
   - **EPAGRI / CEPA-SC (`epagri_sc`):** tanto `cepa.epagri.sc.gov.br/index.php/precos-agricola/` quanto `www.infoagro.sc.gov.br/precos/precos-agropecuarias/` incorporam painéis Power BI (`POWERBI_EMBED`, sem tabelas HTML ou CSV/XLS diretos; página do CEPA também possui `RECAPTCHA`). No portal `dados.sc.gov.br`, `robots.txt` contém `Disallow: /api/` e a busca por `epagri` sofreu `RemoteProtocolError` com queda de conexão antes do término da resposta.

---

## 2. Tabela Consolidada de Veredictos

| Slug / Órgão | URL Principal Verificada | HTTP / TLS | `robots.txt` | Barreiras | Formato / Freq. Real | Cobertura | Veredicto |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`deral_pr`** (DERAL/SEAB-PR) | `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls` | `200` / TLS OK | `200` (livre p/ `/system/files/`) | Nenhuma | `.xls` BIFF8 / Semanal | PR (48 itens, 20 núcleos) | **GO — Nível 1 (Fase 1A)** |
| **`iea_sp`** (IEA/SAA-SP) | `https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos` | `200` / TLS OK | `404` | Token AntiForgery ASP.NET (sem CAPTCHA/login p/ 1 dia) | Tabela HTML AJAX / Diária (dias úteis) | SP (49 itens ativos, 40 EDRs, incl. Algodão) | **GO — Nível 1 (Fase 1A)** |
| **`emater_rs`** (EMATER-RS/ASCAR) | `https://www.emater.tche.br/site/info-agro/precos_semanais.php` | `200` / TLS OK | `403` | Nenhuma nas páginas/PDFs (`robots.txt` 403) | `.pdf` com texto extraível / Semanal | RS (Boletim Cotações Agropecuárias) | **GO COM RESSALVAS — Nível 2 IA (Fase 1B)** |
| **`seapa_mg`** (SEAPA-MG) | `https://www.mg.gov.br/agricultura/documento/precos-correntes-0` | `200` / TLS OK | `200` (permissivo) | Nenhuma | `.pdf` com texto extraível / Semanal | MG (Preços Correntes selecionados) | **GO — Nível 2 IA (Fase 1B)** |
| **`incaper_es`** (INCAPER-ES) | `https://incaper.es.gov.br/sispreco` | `200` / TLS OK | `404` | Nenhuma (porém último PDF 2026 visto é de Jul/2026) | `.pdf` / Irregular em 2026 | ES (Sispreço) | **GO COM RESSALVAS — Onda 2** |
| **`sefaz_ms`** (SEFAZ-MS VRP) | `https://consultavalorsefaz.ms.gov.br/` | `200` / TLS OK | `404` | SPA Angular; endpoints internos não mapeados e natureza fiscal | SPA JSON / Pauta Fiscal | MS | **PENDENTE / Onda 2** |
| **`epagri_sc`** (EPAGRI/Infoagro-SC) | `https://www.infoagro.sc.gov.br/precos/precos-agropecuarias/` | `200` / TLS OK | `200` (`Disallow: /api/` em `dados.sc`) | `POWERBI_EMBED`, `RECAPTCHA` (CEPA), queda HTTP em `dados.sc` | Painel Power BI | SC | **NO-GO (`LINK_HOMOLOGADO_APENAS`)** |
| **`conab_nacional`** (CONAB/MAPA) | `https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios` | `200` na página; subdomínios TLS erro | `401` em `dados.gov.br` | TLS `Hostname mismatch`, `POWERBI_EMBED`, `401 Bearer` | Power BI / SPAs com erro TLS | Nacional | **NO-GO (`LINK_HOMOLOGADO_APENAS`)** |

---

## 3. Evidências Detalhadas por Fonte

### 3.1. DERAL / SEAB-PR (`deral_pr`)
- **Portal:** `https://www.agricultura.pr.gov.br/deral/precos` (`HTTP 200`, `78.062` bytes).
- **Planilha:** `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls` (`HTTP 200`, `application/vnd.ms-excel`, `230.912` bytes).
- **Inspeção via `xlrd 2.0.2`:**
  - Aba única: `Rav`
  - Título `Rav!A1`: `PREÇOS MÉDIOS SEMANAIS RECEBIDOS PELOS AGRICULTORES`
  - Semana: `SEMANA: 46-2026` | Período: `PERÍODO: 09/11/2026 a 13/11/2026`
  - `20` núcleos regionais (Apucarana, Campo Mourão, Cascavel, Cornélio Procópio, Curitiba, Francisco Beltrão, Guarapuava, Irati, Ivaiporã, Jacarezinho, Laranjeiras do Sul, Londrina, Maringá, Paranaguá, Paranavaí, Pato Branco, Ponta Grossa, Toledo, Umuarama, União da Vitória) e `48` produtos com média numérica positiva.

### 3.2. IEA / SAA-SP (`iea_sp`)
- **Página principal:** `https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos` (`HTTP 200`, `60.371` bytes, servidor `Microsoft-IIS/10.0`).
- **Mecanismo técnico comprovado:**
  - O formulário realiza `POST` AJAX para a própria URL com `X-Requested-With: XMLHttpRequest`, `__RequestVerificationToken` (obtido no `GET` inicial junto do cookie de sessão), `startDate`, `endDate` (iguais quando anônimo), `produtos` (códigos repetidos) e `edrs` (`01`..`41`).
  - **Importante:** na primeira sondagem para `19/11/2026`, o servidor retornou *"Não há preços no período informado."* (feriado/janela sem apuração). Na consulta para **`18/11/2026`** (dia útil anterior), retornou `HTTP 200` com `<table class="table margT20">` contendo 15 linhas para os 6 produtos consultados:
    - `ANIMAL | Boi gordo | Andradina | 18/11/2026 | 395,00 | @`
    - `VEGETAL | Café benef. tipo 6 duro | Franca | 18/11/2026 | 1.735,00 | sc.60 kg`
    - `VEGETAL | Milho | Assis | 18/11/2026 | 54,00 | sc.60 kg`
    - `VEGETAL | Soja | Itapeva | 18/11/2026 | 143,00 | sc.60 kg`
  - **Catálogo embutido:** 52 produtos (`49` `ATIVO`), incluindo `1905` (*Algodão em pluma*), `1101` (*Algodão em caroço*), `1126` (*Soja*), `1124` (*Milho*), `1411` (*Boi gordo*), `1053` (*Café benef. tipo 6 duro*), `1109` (*Cana para Indústria*), `1113` (*Feijão carioca*), `1105` (*Arroz em casca*), `1130` (*Trigo*).
  - **Regra para o coletor da Fase 1A:** retroagir até 5 dias úteis caso o dia atual retorne `"Não há preços no período informado"`, e consolidar a média estadual + EDRs individuais em `agro_market_observations`.
  - Nota: o endpoint `/BancoDeDados/PrecosDiarios/Recebidos/Spreadsheet` retornou HTML curto (`160` bytes, redirecionamento/aviso de autenticação), portanto a coleta oficial anônima deve usar exclusivamente a resposta HTML da tabela `POST /Recebidos`.

### 3.3. EMATER-RS / ASCAR (`emater_rs`)
- **Índice de Cotações:** `https://www.emater.tche.br/site/info-agro/precos_semanais.php` (`HTTP 200`, `78.747` bytes).
- **Boletim semanal dedicado (descoberta-chave):** links no formato `https://www.emater.tche.br/site/arquivos_pdf/precos/preco_DDMMAAAA.pdf` — edição mais recente verificada: **`preco_19112026.pdf`** (*Cotações Agropecuárias - Boletim 2467*, `19/11/2026`, `1.081.633` bytes, `ETag: "108121-66091330ed048"`, `22` streams PDF com `9` streams de texto extraível).
- **Informativo Conjuntural:** `conj_19112026.pdf` (`3.416.477` bytes, `HTTP 200`, `ETag: "34219d-660a5cc37c8e1"`).
- **Atenção operacional:** `robots.txt` retornou `HTTP 403`; manter periodicidade conservadora (1x por semana após publicação) e documentar contato institucional com a EMATER-RS caso necessário.

### 3.4. SEAPA-MG (`seapa_mg`)
- **Página oficial ativa:** `https://www.mg.gov.br/agricultura/documento/precos-correntes-0` (`HTTP 200`; atenção: a URL `/agricultura/paginas/cotacoes` retorna `404`).
- **Arquivo semanal atual:** `precos-correntes-de-produtos-selecionado-17-11-2026.pdf` (`HTTP 200`, `733.897` bytes, `application/pdf`, `35` streams sendo `25` com texto extraível).
- `robots.txt` (`https://www.mg.gov.br/robots.txt`) responde `200` e permite acesso a `/agricultura/documento/` e `/system/files/`.

### 3.5. CONAB, EPAGRI-SC, INCAPER-ES e SEFAZ-MS
- **CONAB (`conab_nacional`):** todos os sistemas dinâmicos (`portaldeinformacoes`, `consultaprecosdemercado`, `conabemnumeros`, `consultaweb`) falharam na validação estrita de certificado TLS (`Hostname mismatch`); `dados.gov.br` exige autenticação `Bearer` (`401`); `dados.agricultura.gov.br` não lista datasets CONAB (embora exponha datasets abertos do **AGROFIT** e **ZARC**, úteis para futuras fases!). **Recomendação:** não coletar via scraping; manter como `LINK_HOMOLOGADO_APENAS` corrigindo o link institucional em [cotacoes_regiao_service.py](file:///opt/lampp/htdocs/farm/services/api/public_mercado/cotacoes_regiao_service.py#L281) e [precos_publicos.py](file:///opt/lampp/htdocs/farm/services/api/public_mercado/precos_publicos.py#L572) de `/assuntos/...` (404) para `https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios`.
- **EPAGRI / CEPA-SC (`epagri_sc`):** `cepa.epagri.sc.gov.br/index.php/precos-agricola/` e `infoagro.sc.gov.br/precos/precos-agropecuarias/` dependem de `POWERBI_EMBED`, e `dados.sc.gov.br` proíbe `/api/` no `robots.txt` além de derrubar a conexão em `package_search?q=epagri`. **Recomendação:** manter como `LINK_HOMOLOGADO_APENAS` até eventual contato institucional (`cepa@epagri.sc.gov.br`).
- **INCAPER-ES (`incaper_es`):** tem 122 PDFs públicos históricos, porém em 2026 os arquivos listados chegam apenas até julho/2026 (`preco-medio-semanal-julho.pdf`). Fica para Onda 2 se voltar a atualizar regularmente.
- **SEFAZ-MS (`sefaz_ms`):** SPA Angular com API privada/não documentada e foco tributário (VRP). Mantida fora da Onda 1.

---

## 4. Onda 1 Ajustada com Base nas Evidências Reais

| Fase | Escopo de Coletores Reais | Estados Cobertos | Estratégia Técnica |
| :--- | :--- | :---: | :--- |
| **Fase 1A** | **DERAL/SEAB-PR** (`.xls` BIFF8) + **IEA/SAA-SP** (tabela HTML diária via `POST` AntiForgery sem CAPTCHA) | **PR** (20 núcleos) + **SP** (40 EDRs, incl. Algodão) | **100% Determinístico (Nível 1)** — zero custos de IA e zero novas dependências obrigatórias no `.venv` |
| **Fase 1B** | **EMATER-RS** (`preco_*.pdf` semanal) + **SEAPA-MG** (`precos-correntes-*.pdf` semanal) + **Parceiros Autorizados** (cooperativas/sindicatos configuráveis no Backoffice) | **RS** + **MG** + praças parceiras (ex.: MT, GO, BA, MS) | **Nível 2 Extrator IA (`chamar_ia`)** + verificação literal de evidência + fila de revisão 1-clique no Backoffice |
| **Links Externos** | **CONAB/MAPA**, **EPAGRI/CEPA-SC**, **CEPEA/ESALQ**, **B3** | Nacional / SC | `LINK_HOMOLOGADO_APENAS` (links institucionais seguros corrigidos) |

---

## 5. Inventário de Dependências Python (`services/api/.venv`)

Verificado diretamente no ambiente virtual `services/api/.venv`:

| Biblioteca | Status no `.venv` | Uso no Agente Coletor |
| :--- | :--- | :--- |
| `httpx` | **Instalada (`0.28.1`)** | Fetcher assíncrono seguro HTTPS anti-SSRF (Fases 1A e 1B) |
| `xlrd` | **Instalada (`2.0.2`)** | Parser BIFF8 `.xls` do DERAL-PR (Fase 1A) |
| `charset_normalizer` | **Instalada (`3.4.5`)** | Detecção de encoding em CSVs/HTMLs (Fase 1A) |
| `html.parser` / `csv` / `gzip` / `hashlib` | **Stdlib Python 3.12** | Parsing da tabela HTML do IEA-SP, hash SHA-256 e compressão `gzip` (Fase 1A — **zero deps novas**) |
| `pypdf` / `pdfplumber` / `pdfminer` | **Não instaladas** | Necessárias na **Fase 1B** para extrair texto dos PDFs da EMATER-RS e SEAPA-MG (passarão por validação prévia de segurança antes de entrar no `pyproject.toml`) |
| `openpyxl` / `bs4` / `lxml` / `pandas` / `selectolax` | **Não instaladas** | Opcionais (avaliar apenas se algum parceiro usar `.xlsx` na Fase 1B) |

---

## 6. Mapa de Fixtures Oficiais Capturadas (TDD Offline)

Todas as amostras reais gravadas em `services/api/tests/fixtures/agro_collector/` somam **2,2 MB** no total (cada binário respeitando o teto de 2 MB):

| Fonte | Arquivo(s) Salvo(s) | Tamanho | SHA-256 |
| :--- | :--- | :---: | :--- |
| **`deral_pr`** | [prp.xls](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/deral_pr/prp.xls) + [manifest.json](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/deral_pr/manifest.json) | `226 KB` | `e25b3b1431df5ed4f6e3a2c77c0e13654a6a65c309af35202d2abc946ea1d8f1` |
| **`iea_sp`** | [precos_diarios_recebidos.html](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/iea_sp/precos_diarios_recebidos.html), [precos_diarios_resultado_amostra.html](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/iea_sp/precos_diarios_resultado_amostra.html) + [manifest.json](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/iea_sp/manifest.json) | `59 KB` + `7,0 KB` | `78be2e53...` / `0d2d6eff...` |
| **`emater_rs`** | [precos_semanais.html](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/emater_rs/precos_semanais.html), [preco_19112026.pdf](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/emater_rs/preco_19112026.pdf) + [manifest.json](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/emater_rs/manifest.json) | `77 KB` + `1,1 MB` | `1616f155...` / `7b5c1399...` |
| **`emater_rs_conjuntural`** | [manifest.json](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/emater_rs_conjuntural/manifest.json) *(PDF `conj_19112026.pdf` de 3,26 MiB omitido do Git por exceder 2 MB)* | `489 B` | `2862a61a7d703b20b959b8102e75ce1f3a660b5db14d968ab10358bbe88afed0` |
| **`seapa_mg`** | [precos-correntes-de-produtos-selecionado-17-11-2026.pdf](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/seapa_mg/precos-correntes-de-produtos-selecionado-17-11-2026.pdf) + [manifest.json](file:///opt/lampp/htdocs/farm/services/api/tests/fixtures/agro_collector/seapa_mg/manifest.json) | `717 KB` | `32725a8e0c597b56295a50637f843004e3761b7ad5a9736a3db981ac549bba55` |
