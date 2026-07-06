# CLIMATE-06: Recomendações Operacionais Climáticas no Campo PWA

## Visão Geral
Este relatório detalha a implementação do CLIMATE-06, que leva os dados de inteligência climática de modo offline para os operadores no aplicativo PWA (Campo). O foco desta fase foi entregar recomendações baseadas no clima atual da fazenda para as operações de pulverização, colheita e outras atividades dependentes do clima, de modo que não houvesse impacto arquitetural negativo.

## Estratégia de Implementação

1. **Separação de Preocupações (Frontend Mudo)**
Conforme definido nas restrições, o aplicativo PWA (frontend) não processa lógicas agronômicas. Ele foi desenhado para ser "mudo" em relação à criação das regras climáticas, o que mantém a regra isolada no backend, evitando vazamento de lógica e duplicação de _thresholds_.

2. **Fluxo Desacoplado de Sync (Backend)**
A classe `SyncService.pull` no backend (`services/api/campo/service.py`) foi modificada. Durante a chamada global de sincronização, invocamos a lógica oficial já existente:
`ClimaRecommendationService.get_recomendacoes(fazenda_id)`.
Os resultados gerados no momento do *sync* são serializados e enviados ao PWA, assegurando coesão de dados e aproveitando a conectividade existente.

3. **Armazenamento Offline Persistente (Dexie)**
Foi criado um repositório robusto no IndexedDB (`apps/campo/src/lib/db.ts` na versão 11), capaz de armazenar a entidade `recomendacoes_climaticas`. Esta tabela lida nativamente com queries assíncronas do React. A atualização transacional durante o *pull* sobrepõe com as recomendações atualizadas (via método `.bulkPut()`).

4. **ClimaOperacionalCard**
Construído como um componente atômico, consome o Dexie (usando `useLiveQuery`), interpreta o `tipo_operacao` requisitado (ex: `PULVERIZACAO`, `COLHEITA`), infere a maturidade/validade (`validade_horas` vs. horário atual do relógio local) do dado sincronizado e pinta cores baseadas na `severidade` da restrição climática (Verde/Laranja/Vermelho).

## Impacto
* **Performance:** Nenhuma chamada direta ao `OpenWeather` é acionada do app client, e o tráfego HTTP é reduzido. O dado é cacheado no Dexie.
* **Resiliência:** Operadores que trabalham em zonas rurais isoladas podem acessar a recomendação originada antes do início de seu turno. As operações perigosas recebem alertas explícitos.
* **Escalabilidade:** O frontend está devidamente preparado para exibir quaisquer tipos adicionais de operação, sem nenhuma necessidade de deploy adicional ou lógica redundante no client.

## Testes e Validações
* **Tipagem Front-End:** Verificação via `tsc --noEmit`.
* **Linting:** Cobertura de estilo validada via `eslint`.
* **Testes Back-End:** Passaram nos testes da suíte principal agrícola e verificação estática do `ruff` (no arquivo da feature em questão).
