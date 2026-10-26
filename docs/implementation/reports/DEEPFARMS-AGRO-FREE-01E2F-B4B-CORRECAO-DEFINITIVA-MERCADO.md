# B4B — correção de preços no Mercado

**Data:** 21/10/2026. **Veredicto: NO-GO.** O endereço efetivamente usado pelo produtor não foi informado e a falha persistente não foi reproduzida nesse ambiente. A regressão também apresentou falhas; não há homologação de produção.

## Diagnóstico e correções

Na observação inicial registrada em B4A, os preços apareceram após a hidratação em 127.0.0.1:3004, mas o navegador pediu a API diretamente em 127.0.0.1:8000. Esse endereço aponta para o próprio dispositivo em acesso remoto; é um risco comprovado de configuração, não uma causa comprovada da ocorrência relatada. A resposta inicial HTTP 200 e os dados de Network estão no [registro anterior](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4A/network-console-estado-atual.json). A captura inicial antes da resposta não foi preservada. Não foi estabelecida a URL do usuário, nem validado Nginx de produção.

O frontend usa URL centralizada e rewrite Next para API de mesma origem, com destino interno configurável. O Service Worker passou para v3, exclui API de cache e remove caches antigos; o armazenamento de preços v1/v2 é descartado. O parser exige metadados de proveniência; o carregamento tem prazo, tentativa de recuperação e estados de erro, dado antigo e indisponibilidade. O backend restringe a resposta aos cinco registros cuja classificação foi conferida; a data de publicação não comprovada é nula e a data final do período é a referência. O limite de resultados da Selic foi ajustado ao limite aceito pelo SGS. Os arquivos principais são `apps/agro/next.config.ts`, `src/lib/api-url.ts`, `src/lib/mercado/precos.ts`, `src/components/mercado/catalogo-mercado.tsx`, `public/sw.js`, `services/api/public_mercado/precos_publicos.py`, `precos_publicos_service.py`, `sgs.py` e `services/api/scripts/ingest_deral_precos.py`.

## Auditoria da fonte

Fonte: [DERAL/SEAB-PR, arquivo prp.xls](https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls), aba `Rav`, coluna X “MÉDIA”, preços médios semanais recebidos pelo produtor, Paraná, período 12–16/10/2026, semana 42. O arquivo copiado durante a auditoria está [preservado](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/deral-prp-2026-10-16.xls); SHA-256 `65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1`. A data de publicação não foi identificada. Transformação: arredondamento decimal HALF_UP para duas casas; sem conversão de unidade.

| Card | Registro original | Valor e unidade originais | Resultado |
|---|---|---|---|
| Soja | Rav!X12 | 134,9794 / 60 kg | R$ 134,98 / saca 60 kg |
| Milho | Rav!X11 | 51,7745 / 60 kg | R$ 51,77 / saca 60 kg |
| Boi gordo | Rav!X46 | 371,205 / arroba | R$ 371,21 / arroba |
| Arroz em casca | Rav!X6 | 107,0009 / 60 kg | R$ 107,00 / saca 60 kg |
| Trigo | Rav!X17 | 78,9314 / 60 kg | R$ 78,93 / saca 60 kg |
| Café Arábica | Rav!X7 | 1380,5078 / 60 kg, “Café beneficiado produtor” | Indisponível: a célula não identifica Arábica |
| Feijão carioca | Rav!X9 | 302,6761 / 60 kg, “Feijao de cor” | Indisponível: variedade não comprovada |

Os valores fixos anteriores da B4, inclusive as referências alegadas à CONAB, não possuem documento e célula que os comprovem; não são exibidos. Os demais registros recentemente adicionados ao snapshot também ficam indisponíveis até conferência da correspondência específica com os cards. A planilha é um preço médio histórico, não preço instantâneo.

O comando de ingestão `ingest_deral_precos.py` consulta o arquivo oficial e valida cabeçalhos, rótulos e unidades antes de produzir snapshot. Atualização é manual e exige revisão e publicação do snapshot pela equipe; não há agendamento automático. O arquivo de atualização alternativo presente no workspace não foi homologado para esta finalidade.

## Evidências e regressão

O [Network final](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/final-network-console-checks.json) registra HTTP 200 via `127.0.0.1:3006/api/v1/public/mercado/precos`, sem requisições à porta 8000 pelo navegador; carregamento inicial, recarga, navegação, interrupção e recuperação de rede foram exercitados sem interceptação do endpoint. O console registra erros de rede durante o offline deliberado. Capturas: [soja desktop](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/final-desktop-soja.png), [milho desktop](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/final-desktop-milho.png), [boi desktop](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/final-desktop-boi-gordo.png), [café indisponível desktop](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/final-desktop-cafe-arabica.png) e [visão móvel](evidencias/DEEPFARMS-AGRO-FREE-01E2F-B4B/10-final-mobile.png). As capturas individuais móveis também estão no mesmo diretório. A resposta contém cinco itens e dataPublicacao nula.

Testes frontend: 114 passaram; lint sem erros com oito avisos; typecheck passou antes de alteração concorrente e o build final compilou. Regressão backend: 48 passaram e dois falharam porque testes esperam 21 preços, incluindo classificações não comprovadas. E2E: 22 passaram, um falhou por exigir preço Arábica sem prova, antes da última alteração textual. Os testes de identidade E2E usam simulação; os testes isolados de identidade e BYOK passaram, sem comprovar cadastro real no ambiente do usuário. Mudanças no módulo Mercado foram observadas durante a execução e devem ser reconciliadas antes da homologação.

## Cadastro individual

Foi reproduzido no navegador, sem criar conta, um HTTP 422 para senha curta. A API retorna uma lista de erros, mas o cliente exibia “Falha ao criar conta individual” por esperar texto simples. O formulário foi ajustado para indicar limites e o cliente para explicar campos inválidos sem exibir dados enviados. Essa reprodução não identifica necessariamente o problema do usuário; é necessária a URL efetiva e o status/resposta da tentativa afetada. Nenhuma conta ou tenant foi criado.

## Ações necessárias

Informar a URL efetiva do produtor e reproduzir nela o erro de conta e o carregamento do Mercado; reconciliar os testes que exigem preços sem classificação comprovada e a atualização de snapshot; executar build e E2E final com API real e registrar rede, desktop, dispositivo móvel e recuperação. Não houve deploy, commit, push nem alteração do banco comercial.
