# DEEPFARMS Agro PWA — MVP-02B2C Mercado

**Escopo:** BCB/PTAX e SGS, IBGE/SIDRA e catálogo público. Preços DERAL dinâmicos fora do MVP inicial.

**Veredicto atualizado no fechamento MVP-02B2D: GO COM RESSALVAS.** Os testes de serviço SGS/SIDRA foram executados com isolamento documentado em `DEEPFARMS-AGRO-PWA-MVP-02B2D-FECHAMENTO-MERCADO.md`. Permanecem confirmações de licenças específicas e decisões de configuração/exposição antes da publicação. Este relatório não autoriza ativação de provedores ou publicação.

## 1. Arquitetura e dependências observadas

As rotas `/api/v1/public/mercado/ptax`, `/indicadores-macro`, `/ibge/catalogo`, `/ibge/municipios/{uf}` e `/ibge/estatisticas` são públicas e não declaram dependência de sessão SQLAlchemy, usuário ou tenant. PTAX, SGS e SIDRA usam clientes HTTP próprios e caches Redis com fallback local configurável. O catálogo IBGE é produzido localmente; consultas de municípios e estatísticas acessam a API do IBGE.

O router consulta configurações e feature flags por meio do cache local de `agro_config_service`. Uma configuração não presente nesse cache resulta no comportamento padrão do código; esse getter não consulta o PostgreSQL. O Redis é utilizado para cache/rate limit compartilhados. Com `PTAX_SINGLE_WORKER_FALLBACK=true` (padrão no código), os serviços degradam para memória local em uma instância/worker; esse fallback não compartilha cotas nem cache entre processos. Com fallback desabilitado e Redis indisponível, rotas podem responder indisponibilidade em vez de servir dados.

As rotas DERAL `/catalogo`, `/precos` e `/precos/{commodity_id}` usam `Depends(get_session)` e sincronizam snapshots com banco. Elas não fazem parte da experiência dinâmica do MVP nesta fase.

## 2. Ajustes de apresentação e confiabilidade

- A página de mercado não busca mais, durante renderização no servidor, o catálogo da rota SQL-backed DERAL. Ela usa `PRODUTOS_CATALOGO` local como catálogo de referências.
- `CatalogoMercado` recebe `mostrarPrecosDeral={false}` na página do MVP. Nesse modo, não lê preços DERAL do armazenamento local nem chama `/precos`; exibe mensagem de que preço dinâmico está fora do escopo. O código de DERAL foi preservado e o backend não foi alterado.
- O parser de fallback direto do BCB agora rejeita boletins com mais de sete dias ou mais de cinco minutos no futuro. Evita classificar uma cotação histórica ou futura como normal/atual.
- Em falha de atualização, dados SGS e SIDRA previamente guardados são marcados como fonte indisponível/desatualizados, em vez de permanecerem apresentados como normais. A interface mostra aviso correspondente. Não se remove cache local útil; seu estado deixa explícito que a fonte não confirmou atualização.
- O catálogo estático contém referências, sem preços simulados. O texto de mercado identifica PTAX como fechamento oficial e apresenta ligações institucionais; os componentes mostram período/data de referência, unidade e estado de disponibilidade.

### Arquivos alterados nesta etapa

- `apps/agro/src/app/mercado/page.tsx`
- `apps/agro/src/components/mercado/catalogo-mercado.tsx`
- `apps/agro/src/components/mercado/indicadores-macro-card.tsx`
- `apps/agro/src/components/mercado/ibge-producao-card.tsx`
- `apps/agro/src/lib/mercado/ptax.ts`
- `apps/agro/src/lib/mercado/macro.ts`
- `apps/agro/src/lib/mercado/ibge.ts`
- `apps/agro/tests/unit/ptax.test.ts`
- `apps/agro/tests/unit/macro.test.ts`
- `apps/agro/tests/unit/ibge.test.ts`
- `services/api/public_mercado/router.py` — importação explícita de `Any` para a anotação de `apply_dynamic_market_config`; não altera comportamento das rotas.
- Este relatório.

## 3. Parsing, períodos e licenciamento

O contrato PTAX contém valores de compra/venda, moeda, data e hora do boletim e fonte. A cotação de fechamento é referência diária, não cotação em tempo real. O dataset oficial do BCB explica a metodologia do fechamento PTAX e declara licença ODbL para o conjunto de boletins cambiais. [Dataset de câmbio do BCB](https://dadosabertos.bcb.gov.br/id/dataset/taxas-de-cambio-todos-os-boletins-diarios)

Os indicadores SGS são séries de frequências diferentes e a interface preserva unidade e data de referência (por exemplo, Selic em `% a.a.`, IPCA em `% a.m.`/`% em 12 meses`, câmbio em BRL). O código avalia defasagem segundo a frequência e tolerâncias específicas, e limita o uso de payload macro em cache. A licença/metadados devem ser conferidos série por série para os códigos usados no produto; a licença de um dataset SGS de exemplo não prova os termos dos demais. O portal de Dados Abertos do BCB mostra metadados de licença por conjunto SGS. [Exemplo de metadados SGS do BCB](https://dadosabertos.bcb.gov.br/dataset/22797-sgs)

SIDRA retorna período, unidade, pesquisa, tabela e URL oficial, com catálogo de produtos e localidades permitidos. PAM/PPM são estatísticas anuais e LSPA é estimativa de acompanhamento com frequência mensal, de acordo com os metadados/código homologado da tabela. Valores de ausência no SIDRA (`-`, `...`, `X`) são interpretados separadamente, sem fabricar observações. O IBGE mantém um Plano de Dados Abertos institucional, mas isso, isoladamente, não substitui a conferência de condições e atribuição da tabela/conjunto SIDRA específico. [Portal SIDRA/IBGE](https://www.ibge.gov.br/sidra) · [Dados Abertos do IBGE](https://www.ibge.gov.br/acesso-informacao/dados-abertos.html)

**Atribuição recomendada para lançamento:** “Fonte: Banco Central do Brasil (BCB), série/conjunto e data de referência”; “Fonte: IBGE, SIDRA, tabela [número], pesquisa e período”. Manter links às páginas oficiais e registrar metadados/licenças das séries e tabelas selecionadas antes de distribuir comercialmente os dados. Não foram feitas chamadas externas nesta fase.

## 4. Configuração mínima

Não foram lidos arquivos `.env` nem inferida a configuração efetiva do host. Os nomes/defaults identificados no código são:

| Variável/campo | Uso | Necessidade para mercado |
|---|---|---|
| `REDIS_URL` (`redis://localhost:6379/0` no código) | Cache/rate limit compartilhado | Opcional apenas em processo/worker único se fallback local estiver habilitado; requerido para compartilhamento efetivo entre processos |
| `PTAX_SINGLE_WORKER_FALLBACK` (`true`) | Permite degradação para memória local quando Redis falha | Deve permanecer explicitamente habilitado se Redis dedicado não fizer parte do lançamento |
| `PTAX_CACHE_TTL_SECONDS` (`900`) | TTL PTAX | Opcional; default disponível |
| `MACRO_CACHE_TTL_SECONDS` (`1800`) | TTL SGS/macro | Opcional; default disponível |
| Configuração dinâmica `sidra_cache_ttl_seconds` (schema default 3600) | TTL SIDRA | Opcional; default disponível |
| `NEXT_PUBLIC_AGRO_API_ORIGIN` (default vazio) | Origem pública da API usada pelo frontend | Opcional quando frontend e API compartilham origem/proxy |

Os TTLs podem também ser ajustados por configuração Agro armazenada no cache local. As opções `mercado_enabled`, `ptax_enabled`, `sgs_enabled` e `sidra_enabled` são configurações dinâmicas (não variáveis de ambiente) e, sem valor carregado no cache, o código assume habilitado. Isso precisa ser avaliado para a implantação concreta. O backend não exige credencial para BCB ou IBGE; nenhuma credencial de provedor foi configurada.

## 5. Testes e verificações

| Verificação | Resultado |
|---|---|
| Vitest direcionado: PTAX, macro, IBGE, catálogo e preços | **PASS — 5 arquivos, 71 testes** |
| TypeScript (`npm run typecheck`) | **PASS** |
| ESLint (`npm run lint`) | **PASS** |
| Build (`npm run build`) | **PASS**; rotas `/mercado`, `/offline`, `/clima`, `/calculadoras` e demais páginas foram geradas estaticamente |
| Pytest backend direcionado PTAX/SGS/SIDRA | **PASS — 39 testes, 3 testes de rota excluídos**; HTTP e readiness Redis simulados, `main` não importado na coleta e `conftest.py` global excluído |
| `py_compile` dos serviços de mercado inspecionados | **PASS** |
| Ruff `--select F821` no router de mercado | **PASS** após corrigir a referência não importada `Any` |
| Ruff amplo nos módulos/arquivos de mercado inspecionados | **Não passa: 180 achados preexistentes** de estilo/imports, nomes de campos JSON e regras diversas; não foram aplicadas correções em massa fora do escopo |
| Serviços, banco e provedores externos | **Não iniciados nem consultados** |

Os testes frontend incluem validação de rejeição de PTAX antiga/futura e helpers que marcam respostas SGS/SIDRA como indisponíveis após falha, além dos testes existentes de parsing e catálogo. As suítes backend de serviço PTAX/SGS/SIDRA passaram com isolamento descrito no relatório MVP-02B2D. A verificação Ruff focada revelou referência `Any` ausente no router; foi corrigida com import simples. A verificação Ruff ampla expôs dívida preexistente e não relacionada, mantida fora do escopo.

## 6. Riscos e pendências

1. **Licenças por série/tabela:** confirmar termos e forma de atribuição para cada código SGS e tabela SIDRA usados na versão de lançamento; não extrapolar licença de um dataset para outro.
2. **Operação de cache:** modo sem Redis é adequado somente para instância/worker único. Mais de um processo sem Redis compartilhado fragmenta cache e rate limit.
3. **Feature flags:** não foi validado o conteúdo de configuração efetivamente carregado. Os defaults do código deixam o mercado e as fontes habilitados quando não há configuração em cache.
4. **Disponibilidade real:** limites, latência e erros de BCB/IBGE não foram medidos porque chamadas runtime externas não foram realizadas.
5. **Dados DERAL:** a página do MVP não faz consulta nem usa cache local de preço DERAL; catálogo é referência institucional. A implementação DERAL permanece preservada e fora da tela de preços dinâmicos do MVP.

## 7. Parecer

**GO COM RESSALVAS** para seguir com a integração pública BCB/SGS e IBGE/SIDRA em ambiente de lançamento de instância única, sem dependência obrigatória de PostgreSQL e com Redis opcional apenas sob fallback local. Os testes SGS/SIDRA foram fechados na fase MVP-02B2D. A conclusão de prontidão para lançamento exige verificar as configurações efetivas do ambiente de destino e fechar a revisão de licenças/atribuição por série e tabela. DERAL dinâmico permanece excluído da interface do MVP inicial.
