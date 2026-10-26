# Relatório de Auditoria de Fontes Públicas e Planejamento da Expansão do Mercado

**Identificador:** `DEEPFARMS-AGRO-FREE-01E2F-B5A`  
**Título:** Auditoria de Fontes Públicas e Planejamento da Expansão do Mercado Agropecuário  
**Data da Auditoria:** 21/10/2026  
**Modelo de Execução:** GPT-5.6 Codex — Sol  
**Nível de Raciocínio:** High  
**Modalidade:** Auditoria somente leitura, sem implementação  
**Veredicto:** **GO COM RESSALVAS**  

---

## 1. Sumário Executivo

A presente auditoria técnica e regulatória foi conduzida no âmbito do produto **DeepFarms Agro** com o objetivo de analisar a arquitetura atual do módulo de Mercado (entregue na iniciativa B4), avaliar a integridade dos dados expostos em `localhost:3004/mercado` e projetar a expansão do catálogo de commodities agropecuárias sem comprometer o modelo 100% gratuito, anônimo e sem infraestrutura proprietária paga.

### Principais Conclusões:
1. **Preservação e Verificação da B4:** Foi comprovado empiricamente, via inspeção binária célula a célula no arquivo oficial `prp.xls` da Semana 42-2026 (publicado em 16/10/2026 pelo DERAL/SEAB-PR, hash SHA-256 `65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1`), que os sete preços exibidos nos cards (`soja`, `milho`, `cafe-arabica`, `boi-gordo`, `trigo`, `arroz`, `feijao`) são autênticos, rastreáveis e correspondem rigorosamente às células `Rav!X6` a `Rav!X46`. A integridade da B4 está assegurada e deve ser mantida como base inegociável.
2. **DERAL/SEAB-PR como Fonte Primária de Alta Confiabilidade:** O DERAL disponibiliza semanalmente 45 produtos agropecuários reais na aba `Rav` de sua planilha oficial. Permite expansão imediata para novas culturas (aveia, cevada, canola, feijão preto, amendoim, cana-de-açúcar, boi magro, vaca em pé, leite cru, frango vivo, suíno e ovos) sob regime de dados públicos abertos com proveniência total.
3. **Impedimentos Técnicos Severos na CONAB:** A auditoria identificou dois impeditivos críticos de engenharia na CONAB:
   - O domínio `portaldeinformacoes.conab.gov.br` apresenta falha crítica de TLS/SSL (certificado emitido exclusivamente para `acesseleiloes.conab.gov.br`), o que impede requisições HTTPS programáticas em clientes seguros sem desativação de validação de certificados.
   - O portal de consulta de preços (`consultaprecosdemercado.conab.gov.br`) implementa proteção ativa via Google reCAPTCHA v3 (`6LekNFYp...`) em seu endpoint POST de pesquisa, inviabilizando coleta automatizada por backend sem contorno de mecanismos antibot ou acordos institucionais de API.
4. **IEA-SP como Fonte Complementar Estratégica para São Paulo e Fibras:** O IEA-SP disponibiliza 52 cotações ativas diárias no portal `PrecosDiarios/Recebidos`, incluindo **Algodão em Pluma** (ausente no DERAL), Cana para Indústria, Café Tipo 6 e Boi Gordo. Contudo, seu sistema baseia-se em formulários ASP.NET Core protegidos por tokens AntiForgery (`.AspNetCore.Antiforgery`) e restringe consultas de séries temporais a usuários autenticados, demandando ingestão por snapshot estático homologado em vez de web scraping dinâmico.
5. **Direcionamento da B5B:** A proposta arquitetural para a B5B migra o catálogo de uma lista estática de 8 cards no código TypeScript para um **Catálogo Orientado a Dados (Data-Driven Catalog)** servido pela API pública, mantendo compatibilidade retroativa total, separando links institucionais de links de download de planilhas e preservando a ausência de conexões com banco comercial PostgreSQL.

---

## 2. Diagnóstico da Implementação Existente (B4 / B4A)

### 2.1. Localização e Definição dos Produtos Atuais
- **Catálogo do Frontend (`apps/agro/src/lib/mercado/catalogo.ts`):**  
  Os 8 produtos atuais estão definidos estaticamente na constante `PRODUTOS_CATALOGO` (linhas 100-416). São eles:
  1. `soja` ("Soja em Grão" — Categoria: `GRAOS_CEREAIS_OLEAGINOSAS`)
  2. `milho` ("Milho Físico" — Categoria: `GRAOS_CEREAIS_OLEAGINOSAS`)
  3. `boi-gordo` ("Boi Gordo" — Categoria: `PECUARIA`)
  4. `cafe-arabica` ("Café Arábica" — Categoria: `CAFE_CULTURAS_ESPECIFICAS`)
  5. `trigo` ("Trigo em Grão" — Categoria: `GRAOS_CEREAIS_OLEAGINOSAS`)
  6. `arroz` ("Arroz em Casca" — Categoria: `GRAOS_CEREAIS_OLEAGINOSAS`)
  7. `algodao` ("Algodão em Pluma" — Categoria: `FIBRAS_OUTROS`)
  8. `feijao` ("Feijão Comum (Carioca)" — Categoria: `GRAOS_CEREAIS_OLEAGINOSAS`)

- **Snapshot de Preços do Backend (`services/api/public_mercado/data/deral-prp-2026-10-16.json`):**  
  O snapshot contém **7 produtos** com preços extraídos do relatório DERAL Semana 42-2026. O oitavo produto (`algodao`) não possui preço nesse snapshot porque o algodão em pluma não é cotado na pesquisa de preços médios recebidos pelo produtor do Paraná.

### 2.2. Modelo de Renderização dos Cards: Manual vs. Derivado da API
A arquitetura B4 adota um modelo híbrido com acoplamento estrutural:
1. **Estrutura Base Manual:** A página `apps/agro/src/app/mercado/page.tsx` instancia `<CatalogoMercado initialProdutos={PRODUTOS_CATALOGO} />`. A quantidade de cards exibida na tela é orientada exclusivamente pela lista estática `PRODUTOS_CATALOGO`.
2. **Mesclagem Dinâmica de Preços:** No cliente (`apps/agro/src/components/mercado/catalogo-mercado.tsx`), um hook `React.useEffect` dispara uma requisição `fetch` assíncrona para `/api/v1/public/mercado/precos` (resolvida via proxy reverso Next.js configurado em `next.config.ts`).
3. **Mapeamento de Preço:** A resposta da API é mapeada em um dicionário `precosMap: Record<string, PrecoPublicoItem>` indexado pelo `id` da commodity.
   - Quando `precosMap[produto.id]` existe (caso dos 7 itens do DERAL), o card renderiza o container verde com badge *"Preço Público Real"*, o valor formatado (ex: R$ 134,98), a unidade de comercialização e a referência temporal.
   - Quando `precosMap[produto.id]` inexiste (caso do `algodao`), o card renderiza *"Link Homologado"*, o texto *"Preço oficial indisponível"* e o botão direciona para a instituição homologada no catálogo (CEPEA/ESALQ).
4. **Resiliência Offline:** O cliente armazena o envelope de preços no `localStorage` sob a chave `deepfarms_agro_mercado_precos_v2`. Em caso de falha de conexão, os preços salvos são recuperados com a sinalização de *"ANTIGO"* / *"dado salvo"*.

### 2.3. Funcionamento de Categorias, Filtros e Links Externos
- **Categorias:** O catálogo define 4 categorias em `CATEGORIAS_MERCADO`:
  - `GRAOS_CEREAIS_OLEAGINOSAS` (5 produtos)
  - `CAFE_CULTURAS_ESPECIFICAS` (1 produto)
  - `PECUARIA` (1 produto)
  - `FIBRAS_OUTROS` (1 produto)
  As categorias são apresentadas como botões de filtro (pills) com contadores automáticos obtidos por `obterContagemPorCategoria()`.
- **Busca Textual:** A função pura `filtrarProdutos()` normaliza termos com `normalize("NFD").replace(/[\u0300-\u036f]/g, "")` e realiza busca insensível a maiúsculas e diacríticos sobre `nome`, `descricao`, `classificacaoAgronomica`, `pracaReferencia` e `fontePrincipalNome`.
- **Links Externos Institucionais:** A função `isUrlInstitucionalSegura()` valida estritamente URLs usando `URL` do navegador, exigindo protocolo `https:` e allow-list de domínios governamentais e de pesquisa autorizados (`cepea.org.br`, `cepea.esalq.usp.br`, `b3.com.br`, `gov.br`, `conab.gov.br`, `agricultura.pr.gov.br`).

### 2.4. Ciclo de Vida do Snapshot DERAL
1. **Origem:** O arquivo físico `services/api/public_mercado/data/deral-prp-2026-10-16.json` contém schema versionado (`schemaVersion: 1`), URL da planilha oficial, hash SHA-256 da planilha original, metadados da semana e a lista de itens.
2. **Leitura e Contrato Pydantic:** O módulo `precos_publicos.py` carrega o arquivo em tempo de inicialização via `_carregar_snapshot()`. Cada item é validado com `PrecoPublicoItem` (`extra="forbid"`, verificações numéricas e expressões regulares para hash e data).
3. **Camada de Serviço e Cache:** `PrecosPublicosService` implementa cache L1 em memória com `asyncio.Lock` para prevenção de cache stampede e fallback resiliente. Não há nenhuma escrita ou leitura em banco relacional comercial.
4. **Atualização Atual:** A geração do arquivo JSON foi realizada de forma estática durante a B4. Não existe rotina autônoma de download periódico do DERAL no repositório.

### 2.5. Auditoria de Célula e Proveniência dos Sete Preços Atuais
Durante esta auditoria, o arquivo oficial `prp.xls` da Semana 42-2026 foi baixado diretamente do portal da Secretaria de Agricultura do Paraná (`https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls`) e auditado em nível de stream binário BIFF8:
- **Tamanho do Arquivo:** 337.920 bytes
- **Hash Criptográfico SHA-256 Verificado:** `65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1` (100% idêntico ao registrado no snapshot do sistema).
- **Aba de Coleta:** `Rav` (Preços Médios Semanais Recebidos pelos Agricultores)
- **Coluna de Extração:** Coluna 23 (`Col X`), correspondente à `MÉDIA` estadual ponderada.

| Commodity (`id`) | Nome Original DERAL | Célula Origem | Registro BIFF8 | Valor Original Bruto | Valor Arredondado (R$) | Unidade Comercial |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `arroz` | Arroz em casca irrigado | `Rav!X6` | `NUMBER (0x0203)` | 107.0009 | **R$ 107,00** | Saca de 60 kg |
| `cafe-arabica` | Café beneficiado produtor | `Rav!X7` | `NUMBER (0x0203)` | 1380.5078 | **R$ 1.380,51** | Saca de 60 kg |
| `feijao` | Feijão de cor | `Rav!X9` | `NUMBER (0x0203)` | 302.6761 | **R$ 302,68** | Saca de 60 kg |
| `milho` | Milho | `Rav!X11` | `NUMBER (0x0203)` | 51.7745 | **R$ 51,77** | Saca de 60 kg |
| `soja` | Soja | `Rav!X12` | `NUMBER (0x0203)` | 134.9794 | **R$ 134,98** | Saca de 60 kg |
| `trigo` | Trigo | `Rav!X17` | `NUMBER (0x0203)` | 78.9314 | **R$ 78,93** | Saca de 60 kg |
| `boi-gordo` | Boi gordo | `Rav!X46` | `MULRK (0x00BD)` | 371.2050 | **R$ 371,21** | Arroba (@ de 15 kg) |

**Conclusão da Auditoria B4:** A implementação da B4 é legítima, matematicamente verificada e auditada célula a célula no arquivo original. Não existem números inventados ou cotações simuladas.

---

## 3. Auditoria Detalhada das Fontes Oficiais

### 3.1. DERAL / SEAB-PR (Departamento de Economia Rural do Paraná)
- **Página Institucional:** `https://www.agricultura.pr.gov.br/deral/precos`
- **Documento Semanal Oficial:** `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls`
- **Metodologia de Coleta:** Levantamento dos preços à vista recebidos pelos produtores, livres de impostos (Funrural), coletados semanalmente junto a núcleos regionais e ponderados pela relação entre a produção do núcleo e a produção estadual.
- **Frequência de Publicação:** Semanal (sextas-feiras, no encerramento da apuração estatística).
- **Formato Técnico:** Planilha Microsoft Excel 97-2004 (`.xls`), binário BIFF8 encapsulado em OLE2 Compound File.
- **Produtos Efetivamente Disponíveis (45 commodities auditadas em `prp.xls`):**
  - *Culturas de Verão:* Amendoim em casca (25 kg, X5: R$ 75,00), Arroz irrigado (60 kg, X6: R$ 107,00), Café beneficiado produtor (60 kg, X7: R$ 1.380,51), Café em coco (kg/renda, X8: R$ 22,42), Feijão de cor (60 kg, X9: R$ 302,68), Feijão preto (60 kg, X10: R$ 230,59), Milho (60 kg, X11: R$ 51,77), Soja (60 kg, X12: R$ 134,98).
  - *Culturas de Inverno:* Aveia branca (60 kg, X14: R$ 47,23), Canola (60 kg, X15: R$ 134,80), Cevada (60 kg, X16: R$ 92,23), Trigo (60 kg, X17: R$ 78,93).
  - *Hortaliças e Frutas:* Alface (9 kg, X19: R$ 28,88), Alho nobre (kg, X20: R$ 17,00), Batata-salsa (kg, X21: R$ 2,38), Cenoura (20 kg, X23: R$ 46,69), Tomate (kg, X31: R$ 135,10), Laranja Indústria (40,8 kg, X36: R$ 15,45), Laranja Pêra Mesa (cx, X37: R$ 30,54), Banana Nanica (kg, X34: R$ 28,18).
  - *Cana e Outras Culturas:* Cana-de-açúcar para Indústria (t, X41: R$ 100,21), Erva-mate verde (@, X42: R$ 19,35), Fumo galpão (kg, X43: R$ 203,40), Mandioca industrial (t, X44: R$ 580,26).
  - *Pecuária:* Boi gordo (@ 15 kg, X46: R$ 371,21), Boi magro engorda (cabeça, X47: R$ 4.343,72), Frango vivo (kg, X49: R$ 4,95), Leite cru (litro, X50: R$ 2,81), Ovos grande (30 dz, X51: R$ 145,94), Ovos médio (30 dz, X52: R$ 140,69), Suíno (kg, X53: R$ 5,56), Vaca em pé (@ 15 kg, X54: R$ 329,70).
- **Possibilidade de Extração Automatizada:** **ALTA**. A URL do arquivo semanal é estável (`/Precos/prp.xls`) e permite download headless por tarefas em segundo plano com verificação de integridade via SHA-256 e parsing de células BIFF8 (utilizando `xlrd` ou parser nativo em Python).
- **Condições de Reutilização e Aspectos Jurídicos:** Dados abertos de órgão governamental estadual, regidos pela Lei Federal de Acesso à Informação (Lei nº 12.527/2011) e Decreto Estadual do Paraná nº 9.382/2018. A reutilização é livre para disseminação pública, exigindo-se atribuição formal da fonte ("DERAL/SEAB-PR") e preservação da fidedignidade dos valores.
- **Limitações e Riscos:** A cobertura geográfica limita-se ao Estado do Paraná. Não reflete cotações portuárias (FOB Paranaguá) nem praças de Mato Grosso, Goiás ou São Paulo.

---

### 3.2. CONAB (Companhia Nacional de Abastecimento)
- **Páginas Auditadas:**
  - Institucional: `https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios`
  - Portal de Informações: `https://portaldeinformacoes.conab.gov.br/`
  - Sistema de Consulta de Preços de Mercado: `https://consultaprecosdemercado.conab.gov.br/#/home`
- **Produtos Disponíveis:** Banco histórico com mais de 112 commodities agropecuárias em todas as 27 unidades da federação (grãos, fibras, café, frutas, legumes, pecuária e insumos).
- **Frequência de Publicação:** Diária e Semanal para preços de atacado/produtor; mensal para safras e estoques.
- **Formato Técnico:** Aplicação SPA Angular (frontend web), chamadas AJAX POST em JSON e relatórios em PDF/XLS sob demanda.
- **Avaliação de Riscos Técnicos e Viabilidade de Automação:** **BAIXA / CRÍTICA**.
  1. *Defeito Grave de Certificado TLS:* O endpoint `https://portaldeinformacoes.conab.gov.br/` opera com certificado SSL Let's Encrypt inválido cujo Subject Alternative Name (SAN) cobre apenas `acesseleiloes.conab.gov.br`. Qualquer requisição automatizada padrão falha com erro `x509: certificate is valid for acesseleiloes.conab.gov.br, not portaldeinformacoes.conab.gov.br`. Ignorar validação de certificados violaria as diretrizes estritas de segurança (`mandatory-secure-web-skills`).
  2. *Proteção por Captcha:* O sistema moderno de consulta `https://consultaprecosdemercado.conab.gov.br/` requer a validação de token do Google reCAPTCHA v3 (`6LekNFYpAAAAAIv0GQfg05Aj2qc49zBU0PQQyEMG`) antes de submeter requisições para `consulta/precos/pesquisar`. A automação sem interação humana direta configuraria engenharia reversa de controle antibot, incompatível com uma arquitetura estável.
- **Condições de Reutilização:** Dados públicos federais (Política de Dados Abertos do Executivo Federal — Decreto nº 8.777/2016). Os dados podem ser utilizados com citação, mas a ausência de uma API REST pública documentada sem barreiras de CAPTCHA impede a extração contínua em tempo real.
- **Recomendação:** A CONAB deve ser mantida como **Referência Institucional Homologada** (com links de consulta segura e séries históricas oficiais) até que um convênio de API ou endpoint de dados abertos sem CAPTCHA esteja operacional.

---

### 3.3. IEA-SP (Instituto de Economia Agrícola de São Paulo)
- **Páginas Auditadas:**
  - Banco de Dados de Preços Diários Recebidos: `https://infoiea.agricultura.sp.gov.br/BancoDeDados/PrecosDiarios/Recebidos`
  - Sistema de Preços Médios Mensais: `https://infoiea.agricultura.sp.gov.br/nia1/precos_medios.aspx?cod_sis=2`
- **Produtos Disponíveis (52 produtos ativos auditados no portal):**
  - *Fibras:* **Algodão em pluma** (Código 1905, unidade: arroba 15 kg — ativo), Algodão em caroço (Código 1101).
  - *Pecuária:* Boi gordo (Cód. 1411), Boi gordo China (Cód. 1999), Boi gordo rastreado (Cód. 1917), Boi magro (Cód. 1410), Bezerro nelore (Códs. 1446, 1447), Vaca gorda (Cód. 1412), Novilha para abate (Cód. 1450), Frango vivo (Cód. 1426), Suíno carne (Cód. 1403), Leite cru resfriado (Cód. 1421), Ovos grande/extra/médio (Códs. 1916, 1915, 1430).
  - *Grãos e Café:* Soja (Cód. 1126), Milho (Cód. 1124), Trigo (Cód. 1130), Arroz (Cód. 1105), Amendoim em casca (Cód. 1102), Feijão carioca (Cód. 1113), Café beneficiado tipo 6 duro (Cód. 1053), Café cereja descascado (Cód. 1055).
  - *Cana e Derivados:* Cana para Indústria (Cód. 1109, unidade: tonelada — ativo).
  - *Hortifrúti:* Laranja para indústria (Cód. 1311, cx 40,8 kg), Laranja para mesa (Cód. 1312), Banana nanica/prata (Códs. 1107, 1108), Batata (Cód. 1106), Cebola (Cód. 1111), Tomate de mesa (Cód. 1128).
- **Unidades de Comercialização:** Saca de 60 kg, arroba de 15 kg, tonelada, caixa de 40,8 kg, dúzia, litro.
- **Abrangência Geográfica:** Estado de São Paulo, discriminado pela média estadual e por 40 Escritórios de Desenvolvimento Regional (EDRs), como Barretos, Araçatuba, Campinas, Franca, Itapetininga, Ribeirão Preto e Sorocaba.
- **Frequência de Publicação:** Diária (cotações de mercado físico apuradas diariamente) e médias mensais.
- **Formato Técnico e Automação:** **MÉDIA**.
  - O portal `PrecosDiarios/Recebidos` opera em ASP.NET Core MVC com proteção de formulário via `__RequestVerificationToken` e cookie `.AspNetCore.Antiforgery`.
  - Para usuários anônimos, a consulta diária permite apenas consultar uma única data por vez (`startDate == endDate`). Consultas por período exigem login de usuário cadastrado.
  - O portal `precos_medios.aspx` opera sob ASP.NET 2.0 WebForms legado, exigindo submissão de `__VIEWSTATE`, `__EVENTVALIDATION` e checkboxes HTML para emissão do relatório em tabela.
- **Condições de Reutilização e Aspectos Jurídicos:** Órgão de pesquisa do Governo do Estado de São Paulo. Dados públicos com base na LAI (Lei nº 12.527/2011 e Decreto Estadual SP nº 58.052/2012). Uso livre com obrigatoriedade de citação da fonte ("IEA / Secretaria de Agricultura e Abastecimento de SP").
- **Papel Estratégico para o DeepFarms:** O IEA-SP é a única fonte pública governamental aberta auditada que fornece cotação para o **Algodão em Pluma** (suprindo a lacuna deixada pelo CEPEA/B3) e **Cana para Indústria**.

---

## 4. Matriz de Expansão de Commodities

A matriz abaixo classifica as oportunidades de expansão nas 8 categorias obrigatórias. Para cada produto, distingue-se rigorosamente entre:
- **Produto Pesquisado:** Interesse comercial e agronômico mapeado.
- **Produto Disponível na Fonte:** Presença confirmada de cotação oficial na fonte primária.
- **Produto Tecnicamente Integrável:** Viabilidade de extração, estruturação e publicação via pipeline autônomo sem violação de termos de uso ou CAPTCHAs.

### Classificação de Prioridades:
- **P0 (Base Existente):** Produtos homologados da B4 (preservação estrita).
- **P1 (Expansão Imediata B5B):** Produtos presentes no relatório DERAL Semana 42 com extração 100% comprovada.
- **P2 (Expansão Secundária B5B):** Produtos com alta relevância em São Paulo (IEA-SP) ou culturas regionais adicionais.
- **P3 (Consulta Institucional):** Produtos balizados por índices privados (CEPEA/B3/CONAB) sem feed aberto, operando com link institucional seguro.

| Categoria | ID Proposto | Nome Comercial | Fonte Oficial Candidata | Tipo de Preço | Unidade | Abrangência | Freq. | Disp. Comprovada | Reutilização | Prioridade | Status Técnico |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Grãos e Cereais** | `soja` | Soja em Grão | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X12`) | Domínio Público | **P0** | Integrado (B4) |
| **Grãos e Cereais** | `milho` | Milho Físico | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X11`) | Domínio Público | **P0** | Integrado (B4) |
| **Grãos e Cereais** | `trigo` | Trigo em Grão | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X17`) | Domínio Público | **P0** | Integrado (B4) |
| **Grãos e Cereais** | `arroz` | Arroz em Casca | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X6`) | Domínio Público | **P0** | Integrado (B4) |
| **Grãos e Cereais** | `aveia-branca` | Aveia Branca | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X14`: R$ 47,23) | Domínio Público | **P1** | Integrável B5B |
| **Grãos e Cereais** | `cevada` | Cevada Cervejeira | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X16`: R$ 92,23) | Domínio Público | **P1** | Integrável B5B |
| **Grãos e Cereais** | `canola` | Canola Grão | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X15`: R$ 134,80) | Domínio Público | **P1** | Integrável B5B |
| **Grãos e Cereais** | `amendoim` | Amendoim em Casca | DERAL/SEAB-PR | Médio Produtor | Saca 25 kg | PR (Estadual) | Semanal | Sim (`Rav!X5`: R$ 75,00) | Domínio Público | **P1** | Integrável B5B |
| **Grãos e Cereais** | `sorgo` | Sorgo Granífero | IEA-SP | Médio Produtor | Saca 60 kg | SP (Estadual) | Mensal | Sim (IEA Cód. 84) | Domínio Público | **P2** | Sob Análise (HTML) |
| **Café** | `cafe-arabica` | Café Arábica Beneficiado | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X7`) | Domínio Público | **P0** | Integrado (B4) |
| **Café** | `cafe-coco` | Café em Coco | DERAL/SEAB-PR | Médio Produtor | kg/renda | PR (Estadual) | Semanal | Sim (`Rav!X8`: R$ 22,42) | Domínio Público | **P1** | Integrável B5B |
| **Café** | `cafe-tipo6-sp` | Café Tipo 6 Duro (SP) | IEA-SP | Médio Produtor | Saca 60 kg | SP (Mogiana/Franca) | Diária | Sim (IEA Cód. 1053) | Domínio Público | **P2** | Sob Análise (HTML) |
| **Pecuária** | `boi-gordo` | Boi Gordo | DERAL/SEAB-PR | Médio Produtor | Arroba (@ 15 kg) | PR (Estadual) | Semanal | Sim (`Rav!X46`) | Domínio Público | **P0** | Integrado (B4) |
| **Pecuária** | `boi-magro` | Boi Magro Engorda | DERAL/SEAB-PR | Médio Produtor | Cabeça | PR (Estadual) | Semanal | Sim (`Rav!X47`: R$ 4.343,72) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `vaca-em-pe` | Vaca em Pé (Abate) | DERAL/SEAB-PR | Médio Produtor | Arroba (@ 15 kg) | PR (Estadual) | Semanal | Sim (`Rav!X54`: R$ 329,70) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `frango-vivo` | Frango Vivo | DERAL/SEAB-PR | Médio Produtor | kg | PR (Estadual) | Semanal | Sim (`Rav!X49`: R$ 4,95) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `suino` | Suíno Vivo | DERAL/SEAB-PR | Médio Produtor | kg | PR (Estadual) | Semanal | Sim (`Rav!X53`: R$ 5,56) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `leite` | Leite Cru Produtor | DERAL/SEAB-PR | Médio Produtor | Litro | PR (Estadual) | Semanal | Sim (`Rav!X50`: R$ 2,81) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `ovo-grande` | Ovos Tipo Grande | DERAL/SEAB-PR | Médio Produtor | Caixa 30 dz | PR (Estadual) | Semanal | Sim (`Rav!X51`: R$ 145,94) | Domínio Público | **P1** | Integrável B5B |
| **Pecuária** | `bezerro-sp` | Bezerro Nelore (SP) | IEA-SP | Médio Produtor | Cabeça | SP (Barretos/Araçatuba) | Diária | Sim (IEA Cód. 1446) | Domínio Público | **P2** | Sob Análise (HTML) |
| **Leguminosas** | `feijao` | Feijão Carioca (Cor) | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X9`) | Domínio Público | **P0** | Integrado (B4) |
| **Leguminosas** | `feijao-preto` | Feijão Preto | DERAL/SEAB-PR | Médio Produtor | Saca 60 kg | PR (Estadual) | Semanal | Sim (`Rav!X10`: R$ 230,59) | Domínio Público | **P1** | Integrável B5B |
| **Fibras** | `algodao` | Algodão em Pluma | IEA-SP / CEPEA | Preço Físico / Ref. | Arroba (@) / lb | SP (CIF) / Nacional | Diária | Sim (IEA Cód. 1905) | Domínio Público (IEA) | **P2** | Link Homologado / Snapshot IEA |
| **Hortifrúti** | `tomate` | Tomate de Mesa | DERAL/SEAB-PR | Médio Produtor | Caixa / kg | PR (Estadual) | Semanal | Sim (`Rav!X31`: R$ 135,10) | Domínio Público | **P2** | Integrável B5B |
| **Hortifrúti** | `batata-salsa` | Batata-salsa (Mandioquinha) | DERAL/SEAB-PR | Médio Produtor | kg | PR (Estadual) | Semanal | Sim (`Rav!X21`: R$ 2,38) | Domínio Público | **P2** | Integrável B5B |
| **Hortifrúti** | `cenoura` | Cenoura | DERAL/SEAB-PR | Médio Produtor | Caixa 20 kg | PR (Estadual) | Semanal | Sim (`Rav!X23`: R$ 46,69) | Domínio Público | **P2** | Integrável B5B |
| **Hortifrúti** | `laranja-industria` | Laranja para Indústria | DERAL/SEAB-PR | Médio Produtor | Caixa 40,8 kg | PR (Estadual) | Semanal | Sim (`Rav!X36`: R$ 15,45) | Domínio Público | **P2** | Integrável B5B |
| **Hortifrúti** | `laranja-mesa` | Laranja Pêra de Mesa | DERAL/SEAB-PR | Médio Produtor | Caixa | PR (Estadual) | Semanal | Sim (`Rav!X37`: R$ 30,54) | Domínio Público | **P2** | Integrável B5B |
| **Cana e Derivados** | `cana-de-acucar` | Cana para Indústria | DERAL/SEAB-PR | Médio Produtor | Tonelada | PR (Estadual) | Semanal | Sim (`Rav!X41`: R$ 100,21) | Domínio Público | **P1** | Integrável B5B |
| **Cana e Derivados** | `cana-sp` | Cana para Indústria (SP) | IEA-SP | Médio Produtor | Tonelada | SP (Estadual) | Mensal | Sim (IEA Cód. 1109) | Domínio Público | **P2** | Sob Análise (HTML) |
| **Outros Produtos** | `mandioca-industrial`| Mandioca Industrial | DERAL/SEAB-PR | Médio Produtor | Tonelada | PR (Estadual) | Semanal | Sim (`Rav!X44`: R$ 580,26) | Domínio Público | **P1** | Integrável B5B |
| **Outros Produtos** | `erva-mate` | Erva-mate Folha Verde | DERAL/SEAB-PR | Médio Produtor | Arroba (@ 15 kg) | PR (Sul/União Vitória) | Semanal | Sim (`Rav!X42`: R$ 19,35) | Domínio Público | **P1** | Integrável B5B |
| **Outros Produtos** | `fumo-galpao` | Fumo em Folha Galpão | DERAL/SEAB-PR | Médio Produtor | kg | PR (Estadual) | Semanal | Sim (`Rav!X43`: R$ 203,40) | Domínio Público | **P2** | Integrável B5B |
| **Outros Produtos** | `casulo-seda` | Casulo do Bicho-da-seda | DERAL/SEAB-PR | Médio Produtor | kg | PR (Noroeste) | Semanal | Sim (`Rav!X48`: R$ 39,78) | Domínio Público | **P2** | Integrável B5B |

---

## 5. Proposta Arquitetural B5B (Planejamento Sem Implementação)

### 5.1. Catálogo Orientado a Dados (Data-Driven Catalog)
Atualmente, o frontend depende do array estático `PRODUTOS_CATALOGO` codificado em TypeScript. Para adicionar produtos sem alterar componentes e arquivos `.tsx`, a arquitetura B5B estabelece que:
1. **Endpoint Unificado de Metadados e Cotações:**  
   O backend fornecerá a rota `GET /api/v1/public/mercado/catalogo`, que retornará tanto os metadados cadastrais quanto o status de preço atual de cada item.
2. **Schema Estrito do Catálogo (OpenAPI / Pydantic):**
```python
class VariantePreco(BaseModel):
    varianteId: str  # Ex: "deral-pr-media", "iea-sp-barretos"
    siglaFonte: str
    fonteOficial: str
    tipoPreco: str
    pracaReferencia: str
    unidade: str
    moeda: str = "BRL"
    valor: float | None = None
    dataReferencia: str | None = None
    documentoOficial: str | None = None
    documentoHashSha256: str | None = None
    registroOriginal: str | None = None
    estadoDisponibilidade: Literal["DISPONIVEL", "DEFASADO", "LINK_HOMOLOGADO"]
    urlConsultaInstitucional: str
    urlDocumentoDownload: str | None = None

class CommodityCatalogoItem(BaseModel):
    id: str  # Ex: "soja", "algodao", "boi-gordo"
    nome: str
    categoria: CategoriaCommodity
    classificacaoAgronomica: str
    descricao: str
    destaque: bool = False
    variantes: list[VariantePreco]
```

### 5.2. Identificação Estável e Variantes Comerciais
- Uma commodity agronômica (`id: "soja"`) pode possuir diferentes variantes de mercado (ex: Média Semanal do Paraná via DERAL e Cotação de Paranaguá via CEPEA).
- A identificação do produto permanece imutável, permitindo aos componentes de interface agrupar ou alternar entre praças locais e médias estaduais sem misturar grandezas metodologicamente distintas.

### 5.3. Segregação de Praças e Não-Mistura de Índices
- **Regra de Ouro Metodológica:** Uma média ponderada estadual (ex: DERAL-PR) NUNCA deve ser calculada ou apresentada conjuntamente como se fosse a cotação spot de uma praça específica (ex: FOB Paranaguá ou Barretos/SP).
- A UI exibirá a praça com badge geográfico explícito e chip distintivo: `[Média Estadual - PR]` vs `[Praça Barretos - SP]` vs `[Referência Nacional - CONAB]`.

### 5.4. Atualização Periódica de Snapshots e Prevenção de Defasagem
1. **Pipeline de Ingestão Desacoplado (CLI / Cron Script):**  
   Um script Python autônomo (`scripts/ingest_deral_snapshot.py`) será executado semanalmente (às sextas-feiras às 18:00 BRT). Ele:
   - Baixará o arquivo oficial `prp.xls`.
   - Calculará o hash SHA-256 e comparará com o snapshot ativo.
   - Caso haja novo hash, efetuará o parsing das células da aba `Rav`.
   - Validará todos os limites numéricos contra o schema `PrecosPublicosResponse`.
   - Gravará o arquivo atômico versionado `services/api/public_mercado/data/deral-prp-YYYY-MM-DD.json`.
   - Atualizará o ponteiro do snapshot sem derrubar o servidor ou alterar banco de dados comercial.
2. **Detecção de Defasagem (Staleness Guardrail):**
   - O backend comparará `dataReferencia` com a data corrente. Caso a defasagem ultrapasse 10 dias úteis (tempo suficiente para feriados prolongados), a API sinalizará `estadoDisponibilidade = "DEFASADO"`, alertando o usuário no card.

### 5.5. Tratamento de Produtos sem Preço Aberto
- Produtos de alta liquidez que não possuam feed governamental diário livre de CAPTCHA (como Algodão ou Café Arábica de Minas Gerais) manterão o status `"LINK_HOMOLOGADO"`.
- O card apresentará claramente: *"Preço de balcão e futuros sob licença privada — Consulte os canais credenciados"*, acompanhado do link direto para a instituição de referência.

### 5.6. Migração Suave e Compatibilidade Retroativa com a B4
- As rotas legadas `GET /api/v1/public/mercado/precos` e `GET /api/v1/public/mercado/precos/{commodity_id}` serão mantidas intactas, alimentando-se da mesma fonte interna de dados.
- O endpoint novo `GET /api/v1/public/mercado/catalogo` encapsulará os produtos B4 e permitirá ao frontend adotar a renderização data-driven progressivamente.
- O storage do navegador migrará suavemente para `deepfarms_agro_mercado_precos_v3`, sem quebrar clientes que possuam `deepfarms_agro_mercado_precos_v2`.

---

## 6. Experiência de Consulta às Fontes (UX e Prevenção de Download Inesperado)

### 6.1. O Problema Atual na B4
Atualmente, no componente `catalogo-mercado.tsx`, quando o card possui preço real, o botão exibe *"Consultar no DERAL/SEAB-PR"* apontando diretamente para `precoReal.linkOficial`, que no payload atual é a URL direta da planilha: `https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls`.
**Impacto Negativo:** O usuário clica esperando acessar uma página web informativa com gráficos ou tabelas, e o navegador inicia imediatamente o download inesperado de um arquivo binário `.xls` de 330 KB.

### 6.2. Solução Arquitetural Projetada para a B5B
A interface do card de commodity deve conter uma **separação de três níveis de transparência**:

1. **Botão Principal de Ação (Página Institucional):**  
   - Rótulo: *"Acessar Portal da Fonte (DERAL)"*  
   - Ícone: `ExternalLink`  
   - Destino: Página HTML navegável da instituição (`https://www.agricultura.pr.gov.br/deral/precos`).  
   - Efeito: Abre a página informativa em nova aba (`target="_blank" rel="noopener noreferrer"`).
2. **Link Secundário de Auditoria e Download do Arquivo Fonte:**  
   - Rótulo: *"Baixar planilha oficial auditada (.xls - 337 KB)"*  
   - Ícone: `FileSpreadsheet` ou `Download`  
   - Destino: Arquivo bruto (`.../prp.xls`).  
   - Atributos: `download` explícito e indicação clara de que se trata de arquivo para download.
3. **Modal/Tooltip de Metodologia e Proveniência Célula a Célula:**  
   - Ícone: `Info` ou `ShieldCheck`  
   - Conteúdo exposto:
     - Registro de origem: Célula `Rav!X12`
     - Período de apuração: 12/10/2026 a 16/10/2026
     - Hash criptográfico de validação: `65582dc4...7dde1`
     - Metodologia: *"Preço médio semanal ponderado pela produção regional, livre de tributos."*

Com essa separação, o produtor rural ou consultor agronômico obtém acesso imediato à página web da fonte, tem transparência sobre a metodologia e só realiza o download do arquivo Excel se desejar auditar a planilha por conta própria.

---

## 7. Análise de Riscos Técnicos e Jurídicos

| Risco Identificado | Categoria | Severidade | Probabilidade | Estratégia de Mitigação Arquitetural |
| :--- | :---: | :---: | :---: | :--- |
| **Violação de Termos de Uso (CEPEA / B3)** | Jurídico | Crítica | Média | **Proibição estrita de web scraping.** Manter apenas links externos institucionais e metadados cadastrais para indicadores privados. |
| **Falha de Certificado TLS (CONAB)** | Técnico | Alta | Certeza (100%) | **Bloqueio de ingestão automatizada.** Não consumir `portaldeinformacoes.conab.gov.br` via HTTPS enquanto persistir o certificado divergente de `acesseleiloes`. |
| **Bloqueio Antibot / reCAPTCHA v3 (CONAB)** | Técnico | Alta | Certeza (100%) | **Não tentar bypass de CAPTCHA.** Utilizar a CONAB apenas como link de referência institucional ou via datasets abertos estáticos em `dados.gov.br`. |
| **Quebra de Scraping HTML (IEA-SP)** | Técnico | Média | Alta | **Evitar scraping direto em runtime.** Utilizar snapshots versionados offline validados por schema e hash antes da publicação. |
| **Download Inesperado de Planilhas (UX)** | UX | Média | Certeza (100%) | **Segregação na B5B** entre URL de navegação institucional (`linkOficial`) e URL de auditoria de download (`documentoOficial`). |
| **Desatualização Temporal (Feriados / Férias DERAL)** | Operacional | Baixa | Média | **Guardrail de Defasagem:** Alerta visual de `DEFASADO` quando o snapshot exceder 10 dias úteis, sem interrupção do sistema. |
| **Conexão Indevida ao Banco Comercial PostgreSQL** | Arquitetura | Crítica | Baixa | **Manter separação física.** Todo o catálogo público deve residir exclusivamente no filesystem estático e no cache Redis/L1 em memória. |

---

## 8. Plano de Implementação por Etapas (Proposta B5B)

A implementação da iniciativa B5B será dividida em 5 etapas rigorosas, mantendo o isolamento de ambientes e sem risco de regressão:

### Etapa 1: Refatoração dos Contratos de Dados no Backend
- Criar os modelos Pydantic v2 do Catálogo Orientado a Dados em `services/api/public_mercado/precos_publicos.py` (`CommodityCatalogoItem`, `VariantePreco`, `CatalogoMercadoResponse`).
- Separar nos contratos `urlConsultaInstitucional` (HTML) de `urlDocumentoDownload` (XLS/PDF).
- Expor a nova rota `GET /api/v1/public/mercado/catalogo`.
- Garantir testes unitários em `services/api/tests/unit/test_catalogo_mercado.py`.

### Etapa 2: Expansão do Catálogo DERAL para 18 Commodities (P1)
- Expandir o snapshot homologado para contemplar as culturas de maior relevância auditadas:
  - Grãos: Soja, Milho, Trigo, Arroz, Aveia branca, Cevada, Canola.
  - Café: Café arábica beneficiado, Café em coco.
  - Leguminosas: Feijão carioca, Feijão preto.
  - Pecuária: Boi gordo, Boi magro, Vaca em pé, Frango vivo, Suíno, Leite cru, Ovos grande.
  - Cana e Outros: Cana para indústria, Mandioca industrial, Erva-mate.
- Manter proveniência estrita (todas com célula registrada na aba `Rav`).

### Etapa 3: Script Headless de Atualização Semanal do DERAL
- Desenvolver `services/api/scripts/atualizar_snapshot_deral.py`.
- Implementar download seguro com timeout, cálculo de hash SHA-256, conferência de cabeçalhos e validação Pydantic antes de salvar o arquivo em `data/`.
- Execução isolada em pipeline ou manual, sem expor endpoints de escrita na API pública.

### Etapa 4: Frontend Dinâmico e Refatoração dos Cards
- Migrar `CatalogoMercado` para consumir `initialProdutos` via Server Component RSC (`page.tsx`) com revalidação assíncrona TanStack Query.
- Atualizar a barra de navegação com as novas 8 categorias de mercado:
  1. Grãos e Cereais
  2. Café
  3. Pecuária
  4. Leguminosas
  5. Fibras
  6. Hortifrúti
  7. Cana-de-Açúcar e Derivados
  8. Outros Produtos Agropecuários
- Implementar a nova UX de consulta às fontes com separação entre portal institucional e download do XLS original.

### Etapa 5: Testes de Regressão e Homologação E2E
- Atualizar suite de testes Vitest (`catalogo-mercado.test.ts`, `precos.test.ts`).
- Executar testes E2E do Playwright (`mercado-precos-reais.spec.ts`) assegurando que:
  - Os 7 preços da B4 continuam perfeitamente renderizados.
  - As novas commodities aparecem nas categorias corretas.
  - O botão de consulta não dispara download não intencional.
  - O modo offline preserva a integridade de exibição.

---

## 9. Critérios de Testes e Homologação para a B5B

1. **Critério de Integridade Numérica:**  
   Todo valor exibido como "Preço Público Real" deve ter hash SHA-256 e célula de origem auditáveis na planilha do órgão emissor. Tolerância zero para dados sintéticos ou valores simulados.
2. **Critério de Rastreabilidade e UX:**  
   O clique no botão de consulta institucional deve direcionar exclusivamente para a página web da fonte (HTTP 200). Links diretos para arquivos binários (`.xls`, `.xlsx`, `.pdf`) devem ter aviso visual expresso e ícone específico de download.
3. **Critério de Segurança Web:**  
   Nenhum tráfego para APIs de terceiros com certificados inválidos (caso de `portaldeinformacoes.conab.gov.br`) ou que violem CORS e cabeçalhos de segurança será permitido.
4. **Critério de Isolamento de Banco:**  
   O módulo de mercado não deve realizar nenhuma consulta, conexão pool ou transação no banco PostgreSQL da aplicação comercial.
5. **Critério de Compatibilidade Retroativa:**  
   Qualquer cliente consumindo `/api/v1/public/mercado/precos` ou acessando `/mercado` deve continuar visualizando os 7 preços originais do DERAL sem qualquer regressão visual ou funcional.

---

## 10. Veredicto da Auditoria

### **GO COM RESSALVAS**

**Justificativa Técnica:**
- **Aprovação para Avanço:** A expansão do catálogo de mercado do DeepFarms Agro é plenamente viável, oportuna e de alto valor agronômico, suportada pela riqueza de dados públicos auditados do **DERAL/SEAB-PR** (45 commodities com células comprovadas) e pelo catálogo do **IEA-SP** (52 produtos, viabilizando o Algodão em Pluma).
- **Ressalvas Obrigatórias:**
  1. **Exclusão de Scraping Dinâmico da CONAB:** O portal de informações da CONAB não deve ser integrado via requisições diretas em runtime devido à invalidade de seu certificado SSL e à barreira de reCAPTCHA v3. A CONAB permanecerá como link de referência institucional até que haja API oficial aberta.
  2. **Ingestão por Snapshot Homologado:** Tanto o DERAL quanto o IEA-SP devem ser integrados por meio de pipelines de snapshots estáticos pré-validados, garantindo que o usuário final receba dados ultrarrápidos em cache L1, sem lentidão de scraping ou instabilidade externa de portais do governo.
  3. **Correção Imediata da UX de Links:** Na B5B, é mandatório separar o link do portal institucional (`deral/precos`) do link de download da planilha (`prp.xls`) para eliminar a frustração de downloads indesejados.

> **Determinação Final:** Não iniciar a implementação de código da B5B nesta sessão. O presente relatório encerra a etapa de auditoria `DEEPFARMS-AGRO-FREE-01E2F-B5A` e fica submetido para validação arquitetural.
