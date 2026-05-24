# Nota Arquitetural: Origem Assistida em Tarefas

## Contexto

O Step 44 formalizou a governança de tarefas derivadas de planos assistidos sem criar migration.

O estado atual é:

- `PLANO_ASSISTIDO` fica registrado na `obs` da tarefa.
- `TenantAuditLog` registra `origem_operacional`, aprovação explícita, aprovador e data.
- A UI exibe o badge `Derivada de plano assistido`.
- Plano sugerido, tarefa real, operação e custo permanecem separados.

## Decisão

Não criar migration agora.

A origem assistida seguirá registrada em `obs` + auditoria até haver necessidade operacional real de estruturação em campos dedicados.

## Motivo

A solução atual já preserva:

- rastreabilidade operacional;
- confirmação humana explícita;
- separação entre sugestão, tarefa, operação e custo;
- ausência de automação;
- preservação de DRE, KPIs e analytics.

Criar migration neste momento aumentaria o custo de manutenção sem evidência suficiente de benefício prático.

## Riscos da Solução Atual

- `obs` depende de convenção textual e pode mudar de formato.
- consultas estruturadas por origem ficam mais frágeis.
- auditoria é excelente para rastreio, mas não substitui um modelo relacional dedicado.
- se a disciplina de escrita falhar, pode haver divergência entre `obs`, auditoria e UI.

## Benefícios Potenciais de Campos Estruturais no Futuro

- filtros e relatórios diretos por origem assistida;
- lineage mais forte por plano, origem analítica e aprovador;
- menor dependência de parsing textual;
- maior robustez para BI, exportação e governança operacional;
- melhor suporte a consultas de volume alto.

## Critérios Para Reavaliar Migration

Considerar migration futura apenas se houver um ou mais destes sinais:

- uso recorrente de filtros/relatórios por origem assistida;
- crescimento relevante do volume de tarefas derivadas;
- necessidade de consulta estrutural sem depender de `obs`;
- exigência de lineage formal por plano e aprovador;
- integração com BI, exportações ou governança externa;
- dor operacional real causada pela solução textual.

## O Que Não Fazer Agora

- Não criar migration.
- Não alterar o modelo de tarefa.
- Não alterar API.
- Não alterar UI para depender de novo schema.
- Não duplicar a entidade tarefa.
- Não mexer em DRE, KPIs ou analytics.
- Não automatizar conversão ou execução.

## Diretriz

A fronteira permanece:

1. plano sugerido: analítico e read-only;
2. aprovação humana: obrigatória;
3. tarefa: operacional;
4. operação: execução;
5. custo: nasce da execução/consumo.

Enquanto a solução atual atender rastreabilidade e governança, a postura correta é manter `obs` + auditoria e evitar migration prematura.
