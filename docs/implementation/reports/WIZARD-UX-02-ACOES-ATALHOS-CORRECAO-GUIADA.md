# Relatório de Execução — WIZARD-UX-02

## 1. Diagnóstico da Limitação Anterior
O Wizard possuía componentes de exibição da maturidade (capacidades, status), mas faltava atitude ativa para guiar o usuário. Em cenários onde havia itens faltantes no checklist ou pendências críticas que bloqueavam o Go-Live, o painel exibia "Motivos de bloqueio do backend" de forma técnica e pouco orientada para a ação. Além disso, o empty state não incentivava apropriadamente o início da implantação.

## 2. Ações Adicionadas
- **Próximas ações recomendadas**: Foi inserido um novo componente (`WizardRecommendedActions`) logo abaixo do `WizardSummaryCard`. Ele consolida, de forma visual e direta (em formato de Cards), os itens mais importantes a serem executados: as pendências críticas abertas e os itens obrigatórios faltantes no checklist.
- O componente seleciona e exibe de 3 a 5 ações, priorizando problemas críticos, com a descrição detalhada e, quando fornecido, o atalho para a rota correspondente.
- **Bloco de Go-Live Informativo**: Dentro do `WizardSummaryCard`, foi remodelada a forma como os bloqueios são mostrados. Em vez de seções apartadas, todas as razões (motivos diretos, pendências abertas, e itens faltantes do checklist) foram agrupadas num contexto único "Ainda não é possível realizar o Go-live", que provê botões diretos e orientações claras de mitigação.
- **Empty State**: Modificado para o texto amigável: "Sua implantação ainda não começou. Vamos preparar a estrutura base da sua operação."

## 3. Links Canônicos Usados
Não houve criação de formulários dentro do Wizard. Os redirecionamentos utilizam as rotas canônicas originais:
- `/cadastros/propriedades`
- `/cadastros/propriedades/talhoes`
- `/dashboard/pecuaria/piquetes`
- `/suprimentos/estoque`
- `/dashboard/financeiro/planos-conta`
- `/cadastros/produtos`
- `/cadastros/equipamentos`
- `/cadastros/culturas`
- `/configuracoes/integracoes`
Esses atalhos recebem automaticamente o `unidade_produtiva_id` via URL params (através do `buildContextualLink`), mantendo todo o isolamento operacional correto.

## 4. Pendências que agora possuem orientação
As pendências críticas agora são priorizadas no topo das **Próximas Ações Recomendadas**. Caso uma pendência ou item de checklist crítico precise ser corrigido, ele aparece com uma etiqueta vermelha `Prioridade Máxima`. Para os demais, aparece `Recomendado`.
As ações exibem também o motivo: `ação_recomendada` (ex: "Cadastre ao menos uma área rural ou talhão dentro da unidade produtiva...").

## 5. Como as Próximas Ações são priorizadas
A lista de `topActions` é gerada injetando primeiro as Pendências Críticas (bloqueios operacionais e hard constraints), seguidas pelos itens faltantes obrigatórios do Checklist em ordem de detecção do Engine. São mostradas apenas até as 4 principais para manter o foco do Owner.

## 6. Arquivos Alterados
- `apps/web/src/app/(dashboard)/dashboard/implantacao/wizard/wizard-client.tsx` (Frontend)

## 7. Validações Executadas
- Passado `tsc --noEmit` na `apps/web` para checagem estrita de tipos do TypeScript.
- Passado ESLint para checagem de melhores práticas e hooks React no `wizard-client.tsx`.

## 8. Limitações Restantes
O componente renderizado continua extraindo as severidades e links mapeados estaticamente no Backend (em `_CHECKLIST_ACTION_TARGETS` no arquivo `services/api/wizard/router.py`). Assim, caso um novo módulo (ex: RH) seja incorporado, será necessário adicioná-lo no dicionário do router para que o Frontend possa direcionar o usuário para o novo atalho canônico.
