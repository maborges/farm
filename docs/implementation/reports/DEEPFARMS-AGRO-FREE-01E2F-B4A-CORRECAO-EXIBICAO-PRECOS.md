# B4A — investigação de exibição de preços

**Data:** 21/10/2026. **Veredicto: NO-GO.** Investigação incompleta; nenhuma correção foi aplicada. O defeito persistente descrito não foi reproduzido, e a instrução exige reproduzi-lo antes de avançar. Os valores da B4 continuam expostos e não devem ser considerados comprovados.

## Reprodução

Chromium Playwright em desktop 1440×900, contexto novo, `/mercado` em `127.0.0.1:3004`, sem interceptação ou mocks. O Next já estava ativo na porta 3004; o FastAPI estava ativo na porta 8000. Na primeira observação, durante a hidratação, os cards mostraram “Consulte na fonte oficial”; não havia resposta de preços registrada ainda. Após carregamento, uma segunda observação registrou HTTP 200 no endereço `http://127.0.0.1:8000/api/v1/public/mercado/precos` e os sete valores nos cards. Portanto, não foi observado HTTP 200 com ausência persistente de preços. A primeira captura foi sobrescrita durante a repetição e não está disponível. A captura posterior não é uma evidência de correção.

- [Screenshot desktop do estado atual](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4A/desktop-estado-atual.png).
- [Network, corpo integral, console e texto da página](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4A/network-console-estado-atual.json). Foram observados HTTP 200 também para PTAX, macro, catálogo e estatísticas IBGE. Na primeira execução houve aviso de divergência de atributo de hidratação no input; na repetição registrada não houve erro de console. A primeira observação não foi preservada em arquivo.

## Fluxo inspecionado

Os dados são constantes em `services/api/public_mercado/precos_publicos.py`; o serviço os carrega em memória e o router FastAPI expõe `/precos`. O frontend usa uma URL absoluta para a porta 8000 local e tem fallback relativo, mas `apps/agro/next.config.ts` não configura rewrite. O parser valida versão, itens, data, timestamp e valor; os IDs retornados correspondem aos produtos observados. O efeito React monta o mapa por ID e renderiza os itens após a resposta. O estado de carregamento é atualizado, mas não é apresentado; a ausência inicial é indistinguível de indisponibilidade. A causa da falha persistente relatada permanece **não determinada**. O service worker registrado usa `deepfarms-agro-v2`, não intercepta APIs e busca bundles Next pela rede primeiro; não foi reproduzido cache antigo no contexto novo. O localStorage pode preservar preços anteriores.

## Rastreabilidade da B4

O relatório B4 e as constantes não indicam documento, data de publicação, linha ou célula. A referência informada para todos é 16/10/2026; os valores e unidades abaixo são os constantes no código, não comprovação de valores originais. Não há transformação documentada. Não se concluiu que sejam falsos, mas não foram verificados e não satisfazem o critério de aceitação.

| Produto | Valor fixado | Fonte alegada | Documento/linha original e publicação |
|---|---:|---|---|
| Soja | R$ 124,80/sc 60 kg | DERAL | Não identificados |
| Milho | R$ 58,40/sc 60 kg | DERAL | Não identificados |
| Café arábica | R$ 1.380,00/sc 60 kg | CONAB | Não identificados |
| Boi gordo | R$ 248,50/@ 15 kg | DERAL | Não identificados |
| Trigo | R$ 74,20/sc 60 kg | DERAL | Não identificados |
| Arroz | R$ 112,00/sc 50 kg | CONAB | Não identificados |
| Feijão | R$ 215,00/sc 60 kg | DERAL | Não identificados |

O [DERAL descreve a metodologia e aponta o relatório semanal](https://www.agricultura.pr.gov.br/deral/precos), cujo arquivo é [prp.xls](https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls). Não foi possível extrair e confrontar a edição de 16/10. A [CONAB publica boletins de café](https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/analises-do-mercado-agropecuario-e-extrativista/analises-de-mercado/historico-semanal/historico-semanal-cafe/cafe-conjuntura-semanal-2026-1); por exemplo, o [boletim de 8 a 12/06/2026](https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/analises-do-mercado-agropecuario-e-extrativista/analises-de-mercado/historico-semanal/copy2_of_historico-semanal-do-algodao/cafe-conjuntura-semanal-2026-1/cafe_-_conjuntura_semanal_-_08-06-2026_a_12-06-2026.pdf) registra na tabela 1, linha Arábica–Patrocínio–MG, semana atual, R$ 1.450,00/sc 60 kg. É outra semana e praça: não comprova nem substitui o valor B4. A data exata de publicação desse PDF não foi confirmada.

## Pendências

Reproduzir a falha persistente no ambiente afetado; remover da exibição valores sem documentação, inclusive possíveis caches locais; implementar e validar correção com dados efetivamente rastreáveis; capturar cada commodity em desktop e mobile; executar backend, frontend, lint, typecheck, build e E2E e verificar Selic, identidade e BYOK. PTAX, IPCA e IBGE apareceram na observação desktop, mas isso não constitui regressão completa. Não houve screenshot mobile ou depois de correção. Não houve alteração de banco, deploy, commit ou push.
