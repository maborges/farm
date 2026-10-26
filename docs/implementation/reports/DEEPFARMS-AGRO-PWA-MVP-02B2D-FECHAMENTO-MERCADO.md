# DEEPFARMS Agro PWA — MVP-02B2D Fechamento Técnico do Mercado

**Escopo:** fechamento de testes backend SGS/SIDRA, inventário de fontes e licenças, e configuração operacional do mercado público. Sem alteração de serviços, banco ou infraestrutura.

**Veredicto: GO COM RESSALVAS** para a preparação técnica do módulo público de mercado. O teste direcionado passou. A liberação pública ainda depende de decisão documentada sobre as rotas DERAL que seguem acessíveis no backend e de confirmação dos termos de reutilização dos conjuntos sem licença específica comprovada neste inventário.

## 1. Isolamento e causa do bloqueio de coleta

Os módulos `tests/unit/test_macro_publico.py` e `tests/unit/test_ibge_sidra_publico.py` importavam `main.app` no escopo do módulo. `main` importa um grafo amplo da aplicação e executa trabalho durante a importação, incluindo criação do diretório local de estáticos. Isso fazia a coleta carregar a aplicação monolítica antes de selecionar os testes. O teste também não precisava inicializar a API para exercer os serviços SGS/SIDRA.

O `tests/conftest.py` global é um risco independente: ele importa modelos e possui fixture que pode executar `Base.metadata.create_all`, executar DML de dados de teste e, se `DATABASE_URL` não indicar PostgreSQL, usar o fallback `192.168.0.2/farms`. Esse arquivo foi excluído com `--confcutdir=tests/unit`; nenhum teste do relatório o carregou.

Foi aplicada uma separação mínima apenas nos testes:

- O import de `main.app` foi movido para dentro dos três testes de endpoint, de modo que a coleta dos testes de serviço não importe a aplicação global.
- Os fixtures `memory_macro_cache` e `memory_sidra_cache` usam `redis_ready = AsyncMock(return_value=False)`. O construtor cria somente o cliente Redis; a readiness simulada evita `PING`/socket.
- As suítes selecionadas usam clientes HTTP simulados. Os três testes de rota que importariam `main` foram excluídos da execução. Nenhum endpoint, startup FastAPI, banco, Redis ou provedor real foi chamado.

Isso não altera a inicialização global FastAPI nem o comportamento de produção.

## 2. Inventário de fontes e reutilização

### 2.1 BCB e SGS

As datas abaixo são as datas/períodos retornados pela fonte e exibidos pelo app; o backend consulta as observações mais recentes disponíveis. Não se fixa antecipadamente uma referência futura.

| Identificador | Série/medida apresentada | Frequência e unidade | Fonte e referência exibida | Licença/condições confirmadas |
|---|---|---|---|---|
| PTAX USD fechamento | Compra e venda USD/BRL; boletim oficial, não intraday | Diária; BRL por USD | [Dataset BCB de boletins cambiais](https://dadosabertos.bcb.gov.br/id/dataset/taxas-de-cambio-todos-os-boletins-diarios); data/hora do boletim | O catálogo oficial do BCB declara ODbL para o dataset de boletins. Preservar crédito ao BCB, origem/link, data e obrigações ODbL aplicáveis. |
| SGS 432 | Meta Selic definida pelo Copom | Diária; `% a.a.` | [Dataset BCB SGS 432](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom); data da observação | O catálogo oficial declara ODbL para este dataset. A série pode conter datas projetadas pelo calendário Copom; o backend filtra observações futuras. |
| SGS 433 | IPCA, variação mensal | Mensal; `% a.m.` | [Metadados oficiais SGS 433](https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada=433); mês de referência | O conjunto individual e sua licença não foram encontrados/verificados no catálogo durante esta auditoria. **Pendente**; não presumir ODbL a partir da série 432. A origem estatística é IBGE, com disponibilização no SGS/BCB. |
| SGS 13522 | IPCA acumulado em 12 meses | Mensal; `% em 12 meses` | [Metadados oficiais SGS 13522](https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada=13522); mês final da janela de 12 meses | Licença específica não comprovada nesta auditoria. **Pendente**. A atribuição deve citar IBGE como produtor e BCB/SGS como série/publicação, além do período. |
| SGS 21619 | Euro, venda | Diária; valor de venda em BRL/EUR segundo contrato/código atual | [Metadados oficiais SGS 21619](https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada=21619); data da observação | Licença específica não comprovada nesta auditoria. **Pendente**. Atribuir BCB/SGS e data. |
| SGS 21620 | Euro, compra | Diária; valor de compra em BRL/EUR segundo contrato/código atual | [Metadados oficiais SGS 21620](https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada=21620); data da observação | Licença específica não comprovada nesta auditoria. **Pendente**. Atribuir BCB/SGS e data. |

O dataset cambial documenta que o fechamento PTAX é a média das taxas dos boletins do dia. É uma cotação de referência publicada, não preço em tempo real. [Metodologia e licença do dataset de câmbio](https://dadosabertos.bcb.gov.br/id/dataset/taxas-de-cambio-todos-os-boletins-diarios). Para séries SGS, o portal possui metadados de licença por dataset; o resultado oficial encontrado para 432 não prova a licença das séries 433, 13522, 21619 e 21620. [Exemplo oficial de página SGS com metadados e licença](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom).

### 2.2 IBGE/SIDRA

O catálogo do backend permite 23 produtos. Eles usam quatro tabelas compartilhadas; para cada tabela, categorias e variáveis variam por produto. O frontend apresenta o nome da pesquisa, número da tabela, URL SIDRA, variável/unidade e último período recebido.

| Tabela | Pesquisa e uso | Frequência/unidade no contrato | Referência do app | Reutilização/atribuição |
|---|---|---|---|---|
| 5457 | PAM — produção, área plantada/colhida e rendimento para lavouras | Anual; hectares, toneladas, kg/ha | Ano observado retornado | [Tabela 5457/PAM](https://sidra.ibge.gov.br/tabela/5457); a página da pesquisa confirma periodicidade anual e alcance territorial. Crédito recomendado: IBGE, PAM, SIDRA, tabela 5457 e ano. Licença/termos explícitos por tabela não foram confirmados; pendente de validação jurídica/editorial antes de redistribuição. |
| 6588 | LSPA — estimativas para culturas elegíveis | Mensal; hectares, toneladas, kg/ha | Período mensal/ano-safra retornado; estimativas sujeitas a revisão | [Tabela 6588/LSPA](https://sidra.ibge.gov.br/tabela/6588); a página oficial lista a série histórica e seus períodos. Crédito recomendado: IBGE, LSPA, SIDRA, tabela 6588 e período. Licença/termos explícitos por tabela não confirmados. |
| 3939 | PPM — efetivo de rebanhos | Anual; cabeças | Ano observado retornado | [Tabela 3939/PPM](https://sidra.ibge.gov.br/tabela/3939); as definições/categorias do catálogo da aplicação são do contrato SIDRA. Crédito recomendado: IBGE, PPM, SIDRA, tabela 3939 e ano. Licença/termos explícitos por tabela não confirmados. |
| 74 | PPM — produção de origem animal (leite, ovos, mel) | Anual; mil litros, mil dúzias e kg, respectivamente, conforme mapeamento do app | Ano observado retornado | [Tabela 74/PPM](https://sidra.ibge.gov.br/tabela/74). Crédito recomendado: IBGE, PPM, SIDRA, tabela 74 e ano. Licença/termos explícitos por tabela não confirmados. |

A página oficial da PAM lista a tabela 5457 e descreve periodicidade anual, cobertura territorial e mudanças históricas de unidade; a página oficial da LSPA lista a tabela 6588 e a série histórica mensal de estimativas. [Catálogo oficial da PAM](https://sidra.ibge.gov.br/pesquisa/pam/tabelas/), [catálogo oficial da LSPA](https://sidra.ibge.gov.br/home/lspa/paraiba). As páginas de tabela 3939 e 74 são os links oficiais fixados no código, mas o conteúdo individual/licença não pôde ser lido por esta ferramenta; os metadados de tabela e termos específicos permanecem pendentes.

O IBGE mantém um Plano de Dados Abertos, cuja definição institucional de licença aberta prevê crédito de autoria e, quando aplicável, compartilhamento sob a mesma licença. Isso não foi tratado como concessão automática para cada tabela SIDRA usada. [Plano de Dados Abertos do IBGE 2024–2025](https://www.ibge.gov.br/np_download/novoportal/documentos_institucionais/Plano_de_Dados_Abertos_IBGE_2024_2025.pdf), [seção institucional de Dados Abertos](https://www.ibge.gov.br/acesso-informacao/dados-abertos.html).

**Atribuição mínima recomendada na interface:** “Fonte: IBGE, [PAM/LSPA/PPM], SIDRA, tabela N, período” com link para a tabela; e “Fonte: BCB, SGS N, período” para os indicadores BCB. Essa é uma recomendação editorial de rastreabilidade, não uma afirmação de licença não verificada.

## 3. Configuração e feature flags

### Redis e processo

- O modo sem Redis depende de `PTAX_SINGLE_WORKER_FALLBACK=true` (default de código) e de **um único worker FastAPI**. O cache, lock de concorrência e rate limit são locais ao processo. Não usar múltiplos workers como se fossem cache/cota compartilhados.
- Se a publicação usar um Redis, `REDIS_URL` deve apontar ao Redis dessa implantação e ser configurado como recurso compartilhado; credenciais e estado não foram inspecionados nesta tarefa.
- `REDIS_URL` tem default `redis://localhost:6379/0`; `PTAX_CACHE_TTL_SECONDS` default 900; `MACRO_CACHE_TTL_SECONDS` default 1800. O TTL SIDRA vem da configuração Agro, default 3600 no schema. Nenhum arquivo `.env` foi lido.

### Flags e riscos de ativação inesperada

`AgroFeatureFlagsConfig` define por padrão `clima_enabled=true`, `mercado_enabled=true`, `byok_enabled=true`, `ibge_enabled=true` e `calculadoras_enabled=true`. A configuração de mercado define `ptax_enabled=true`, `sgs_enabled=true`, `sidra_enabled=true` e `deral_enabled=true` por padrão. O router lê valores do cache local; sem valor carregado, suas condições tratam o módulo/fonte como habilitado. Portanto, defaults seguros para ambiente público precisam ser definidos na configuração operacional, e a confirmação do que foi carregado é um pré-requisito de publicação.

Para o escopo de mercado deste MVP, a configuração pretendida é PTAX/SGS/SIDRA habilitados e `deral_enabled=false`; recursos fora do MVP, como BYOK, devem estar explicitamente desabilitados onde aplicável. Não foi alterada nem lida configuração persistida.

**Limitação real das flags:** os handlers de PTAX e SGS consultam as flags correspondentes; o catálogo IBGE as consulta, mas as rotas IBGE de municípios/estatísticas não fazem a mesma checagem. No DERAL, `/precos` tem checagem de `deral_enabled`, porém `/catalogo` só verifica o módulo geral e `/precos/{commodity_id}` não verifica `deral_enabled`. O frontend do MVP não chama as rotas DERAL, mas a API pública ainda as expõe. Como a tarefa proíbe alterar DERAL/backend, isso fica como bloqueio de decisão para publicação se o requisito for que DERAL não seja acessível fora da interface.

## 4. Testes realizados

### Backend

Comando executado a partir de `services/api`:

```bash
PYTHONPATH=. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest \
  -p pytest_asyncio.plugin --confcutdir=tests/unit \
  tests/unit/public_mercado/test_ptax.py \
  tests/unit/test_macro_publico.py \
  tests/unit/test_ibge_sidra_publico.py -q \
  -k 'not test_07_endpoint_publico_e_isolamento_postgresql and not test_08_nao_regressao_ptax and not test_endpoints_fastapi_sem_auth'
```

**Resultado: 39 passed, 3 deselected.** Os testes de serviço usam HTTP mockado e readiness Redis simulada como indisponível, com fallback local. O plugin pytest de descoberta automática foi desabilitado; somente `pytest_asyncio.plugin` foi carregado. `--confcutdir=tests/unit` evitou carregar `tests/conftest.py`. Os três testes excluídos importam `main` e exercitam rotas FastAPI; não fazem parte desta prova sem serviços.

### Frontend

- `npm test -- --run tests/unit/ptax.test.ts tests/unit/macro.test.ts tests/unit/ibge.test.ts tests/unit/catalogo-mercado.test.ts tests/unit/precos.test.ts` — **71 testes aprovados**.
- `npm run typecheck` — **PASS**.
- `npm run lint` — **PASS**.
- `npm run build` — **PASS**, build Next estático concluído.

Esses comandos foram executados em `apps/agro`. Não houve requisição runtime para BCB/SIDRA, tentativa de conexão PostgreSQL/Redis, migration ou inicialização de serviço. A pesquisa documental consultou páginas oficiais, não APIs de dados dos provedores.

## 5. Pendências e veredicto

1. Confirmar os termos/licença específicos das séries SGS 433, 13522, 21619 e 21620 no catálogo oficial ou com o responsável pelos dados.
2. Confirmar os termos de reutilização por tabela para SIDRA 5457, 6588, 3939 e 74 antes de redistribuição comercial; manter atribuição e ligação oficial.
3. Decidir se basta ocultar DERAL da UI ou se sua API pública também precisa ficar inacessível; as flags existentes não cobrem todas as rotas.
4. Configurar explicitamente as feature flags do ambiente de publicação e confirmar o valor efetivo carregado; defaults de código habilitam mercado, IBGE e BYOK.
5. Se Redis não estiver disponível, operar com um único worker; escalar para múltiplos processos exige cache/rate limit compartilhado.

**Veredicto: GO COM RESSALVAS.** A validação unitária do mercado BCB/SGS e IBGE/SIDRA está aprovada sem dependência de PostgreSQL, Redis ou tráfego externo. O frontend compila e passa pelas verificações requeridas. A publicação ainda depende das confirmações legais pendentes, de configuração explícita das flags e da decisão sobre a exposição das rotas DERAL fora da interface.
