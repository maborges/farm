# AgroSaaS - Ciclo Operacional Agrícola Oficial

## Objetivo

Formalizar o ciclo operacional agrícola já fechado no AgroSaaS, com fronteiras claras entre análise, planejamento, execução e custo.

Este documento consolida a semântica do fluxo oficial e evita que novas features criem um ciclo paralelo.

## Ciclo Oficial

```text
Plano sugerido
-> Aprovação humana
-> Tarefa
-> Operação
-> Execução
-> Consumo
-> Custo
-> Apropriação econômica
-> DRE
-> Analytics
-> Prioridades
-> Novo plano sugerido
```

## Fronteiras Oficiais

- `Plano sugerido` não é `tarefa`.
- `Tarefa` não é `operação`.
- `Operação` não é `custo`.
- `Custo` não é `DRE`.
- `Analytics` não é automação.

## Responsabilidades Por Camada

### Analítica

Camadas analíticas:

- DRE agrícola v1
- KPIs oficiais
- Rentabilidade
- Eficiência Operacional
- Benchmark
- Diagnóstico
- Recomendações
- Prioridades
- Inteligência Operacional Aplicada

Responsabilidade:

- observar;
- classificar;
- consolidar;
- sugerir.

Não executa:

- operação agrícola;
- custo;
- automação.

### Operacional

Camadas operacionais:

- Tarefa
- Operação
- Execução
- Apontamento
- Jornada
- Checklist

Responsabilidade:

- organizar o trabalho;
- registrar a execução;
- dar contexto temporal e operacional.

Não define por si só:

- custo oficial;
- DRE;
- apropriação econômica.

### Econômica

Camadas econômicas oficiais:

- CostAllocation
- EstoqueMovimento
- Despesa
- LancamentoFinanceiro

Responsabilidade:

- apropriar;
- registrar consumo;
- refletir obrigação;
- consolidar o resultado econômico.

Fonte oficial do custo agrícola:

- `CostAllocation`

Fonte oficial da DRE agrícola:

- `DRE agrícola v1`

## Estados Do Fluxo

Sem criar máquina de estados formal, o ciclo oficial pode ser lido como:

- sugerido;
- aprovado;
- tarefa criada;
- operação executada;
- custo apropriado;
- resultado consolidado;
- nova recomendação gerada.

## Regras Obrigatórias

- Aprovação humana é obrigatória para converter sugestão em tarefa real.
- Não existe automação autônoma neste ciclo.
- Não existe workflow engine paralelo.
- Não existe execução automática.
- A DRE agrícola v1 é o núcleo econômico oficial.
- `CostAllocation` é a apropriação econômica oficial.
- Prioridades orientam, mas não executam.

## Fluxo Fechado Oficial

O ciclo agora é fechado de forma rastreável:

1. o analytics produz diagnóstico, recomendações e prioridades;
2. a Inteligência Operacional Aplicada transforma isso em plano sugerido;
3. o plano só vira tarefa com aprovação humana explícita;
4. a tarefa é executada como operação real;
5. a operação gera consumo e evidência;
6. o consumo se traduz em custo e apropriação econômica;
7. a DRE consolida o resultado;
8. os analytics reaparecem com base nesse resultado;
9. novas prioridades surgem para o próximo ciclo.

## O Que Não Fazer

- não criar workflow paralelo;
- não duplicar tarefas;
- não automatizar execução;
- não recalcular analytics fora da cadeia oficial;
- não criar analytics paralelos;
- não transformar prioridades em ordem automática;
- não confundir sugestão com execução;
- não confundir operação com custo;
- não confundir custo com DRE.

## Documentos Relacionados

- [agro-domain-governance.md](/opt/lampp/htdocs/farm/docs/architecture/agro-domain-governance.md)
- [operational-workflow-governance.md](/opt/lampp/htdocs/farm/docs/architecture/operational-workflow-governance.md)
- [economic-source-precedence.md](/opt/lampp/htdocs/farm/docs/architecture/economic-source-precedence.md)
- [analytics-governance-decision.md](/opt/lampp/htdocs/farm/docs/architecture/analytics-governance-decision.md)
- [assisted-task-provenance-decision.md](/opt/lampp/htdocs/farm/docs/architecture/assisted-task-provenance-decision.md)

## Diretriz

Este documento não cria um novo modelo de operação. Ele apenas declara o ciclo oficial já consolidado:

- plano sugere;
- humano aprova;
- tarefa organiza;
- operação executa;
- custo nasce da execução;
- DRE consolida;
- analytics devolvem orientação para o próximo ciclo.
