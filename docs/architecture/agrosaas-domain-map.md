# AgroSaaS - Mapa Oficial de Domínios

## Objetivo

Consolidar os bounded contexts oficiais do AgroSaaS e explicitar ownership, fronteiras e dependências permitidas.

Este documento evita sobreposição entre domínio operacional, econômico, analítico, assistido e governança.

## Domínios Oficiais

### 0. Domínio Territorial

Responsável por:

- Propriedades
- Glebas
- Talhões
- Pastagens
- Estradas
- Infraestrutura
- Áreas Operacionais
- Safras
- Produção
- Manejo
- Custos Operacionais
- Indicadores Produtivos

Ownership oficial:

- `Propriedades` é a fonte da verdade do território operacional.
- `AGRI-DOMAIN-001` define a fronteira com o domínio fundiário.

Pode fazer:

- representar a operação rural;
- consolidar a leitura territorial;
- alimentar rastreabilidade operacional.

Não deve fazer:

- assumir titularidade legal;
- duplicar CAR, CCIR, ITR, NIRF ou matrícula;
- substituir o domínio fundiário.

### 0.1 Domínio Fundiário

Responsável por:

- Proprietários
- Condôminos
- Representantes Legais
- Procuradores
- Matrículas
- Cartórios
- CAR
- CCIR
- ITR
- NIRF
- SIGEF
- Contratos
- Avaliações
- Documentação Fundiária

Ownership oficial:

- `Imóveis Rurais` é a fonte da verdade da titularidade e comprovação legal do território.
- `AGRI-DOMAIN-001` é a norma oficial de referência.

Pode fazer:

- representar a titularidade;
- representar o registro;
- representar a prova documental;
- alimentar certificações e rastreabilidade fundiária.

Não deve fazer:

- substituir a operação;
- duplicar talhões, glebas, safras ou produção;
- impor workflow operacional.

### 1. Domínio Econômico

Responsável por:

- Receita
- Despesa
- CostAllocation
- Apropriação econômica
- Reconciliação econômica
- DRE agrícola v1
- KPIs financeiros

Ownership oficial:

- `CostAllocation` é a apropriação econômica oficial.
- `DRE agrícola v1` é o núcleo econômico oficial.
- `economic-source-precedence.md` define a precedência de fontes econômicas.

Pode fazer:

- consolidar custo;
- refletir obrigação e realização;
- reconciliar origem econômica com reflexo financeiro;
- alimentar a DRE oficial.

Não deve fazer:

- automatizar operação;
- criar tarefa;
- criar analytics paralelos;
- gerar workflow.

### 2. Domínio Operacional

Responsável por:

- Safra
- Tarefa
- Operação
- Execução
- Consumo
- Estoque
- Frota
- Compras

Ownership oficial:

- `Tarefa` é planejamento e orquestração.
- `Operação` é execução real.
- `Execução` é evidência da execução.
- `EstoqueMovimento` registra trilha física e valuation operacional.
- `agricultural-operational-cycle.md` formaliza o ciclo oficial.

Pode fazer:

- planejar;
- coordenar;
- executar;
- registrar consumo;
- produzir evidência operacional.

Não deve fazer:

- recalcular DRE;
- criar analytics;
- automatizar aprovação;
- transformar prioridade em ordem automática.

### 3. Domínio Analítico

Responsável por:

- Rentabilidade
- Eficiência
- Benchmark
- Diagnóstico
- métricas derivadas

Ownership oficial:

- a DRE é a fonte upstream do domínio analítico;
- `analytics-governance-decision.md` define a estratégia de memoização e o monitoramento do fan-out;
- `analytics_taxonomy.py` concentra a taxonomia oficial.

Pode fazer:

- classificar;
- comparar;
- derivar;
- consolidar informação gerencial.

Não deve fazer:

- executar operação;
- criar tarefa;
- impor automação;
- substituir o domínio econômico.

### 4. Domínio Assistido

Responsável por:

- Recomendações
- Prioridades
- Inteligência Operacional Aplicada
- Planos sugeridos

Ownership oficial:

- `Prioridades` e `Diagnóstico` alimentam os planos;
- `Inteligência Operacional Aplicada` deriva planos sugeridos sem recalcular a cadeia oficial;
- `assisted-task-provenance-decision.md` registra a fronteira entre plano sugerido e tarefa real.

Pode fazer:

- sugerir;
- organizar;
- priorizar;
- permitir conversão assistida com aprovação humana.

Não deve fazer:

- executar operação;
- gerar custo;
- automatizar conversão;
- virar workflow engine.

### 5. Domínio de Governança

Responsável por:

- Taxonomia oficial
- Auditoria
- Guardrails
- Enforcement
- Aprovação humana
- TenantAuditLog

Ownership oficial:

- a taxonomia oficial vive em `analytics_taxonomy.py`;
- `TenantAuditLog` é o trilho transversal de auditoria;
- a governança operacional e econômica reutiliza guardrails já existentes;
- `agro-domain-governance.md` e `operational-workflow-governance.md` formalizam as fronteiras de domínio e fluxo.

Pode fazer:

- impor limites;
- registrar eventos;
- normalizar semântica;
- proteger contra duplicidade e drift.

Não deve fazer:

- virar regra de negócio espalhada;
- substituir domínio operacional ou econômico;
- executar automação;
- criar novos ciclos paralelos.

## Dependências Permitidas

```text
Territorial -> Fundiário (via vínculo oficial)
Operacional -> Econômico
Econômico -> Analítico
Analítico -> Assistido
Governança -> transversal
```

## Dependências Proibidas

- Assistido não executa operação.
- Analítico não cria tarefa.
- Econômico não gera automação.
- Governança não vira lógica de negócio espalhada.
- Operacional não recalcula DRE.
- Tarefa não substitui operação.
- Operação não substitui custo.
- Territorial não substitui Fundiário.
- Fundiário não substitui Territorial.

## Ownership Por Conceito

- `Safra`: domínio operacional.
- `Propriedade`: domínio territorial.
- `Imóvel Rural`: domínio fundiário.
- `Tarefa`: planejamento operacional.
- `Operação`: execução operacional.
- `CostAllocation`: apropriação econômica.
- `DRE agrícola v1`: consolidação econômica oficial.
- `Rentabilidade`, `Eficiência`, `Benchmark`: derivações analíticas.
- `Diagnóstico`, `Recomendações`, `Prioridades`: inteligência assistida derivada.
- `TenantAuditLog`: governança transversal.
- `Taxonomia oficial`: governança transversal de linguagem.

## Anti-Patterns Oficiais

Não:

- criar analytics paralelos;
- recalcular DRE fora do domínio econômico;
- criar workflow engine escondido;
- transformar prioridades em execução;
- duplicar cálculo econômico;
- criar automação autônoma;
- espalhar taxonomia fora do registry;
- misturar operação e analytics;
- misturar custo com tarefa;
- misturar sugestão com execução.

## Documentos Relacionados

- [agricultural-operational-cycle.md](/opt/lampp/htdocs/farm/docs/architecture/agricultural-operational-cycle.md)
- [agro-domain-governance.md](/opt/lampp/htdocs/farm/docs/architecture/agro-domain-governance.md)
- [operational-workflow-governance.md](/opt/lampp/htdocs/farm/docs/architecture/operational-workflow-governance.md)
- [economic-source-precedence.md](/opt/lampp/htdocs/farm/docs/architecture/economic-source-precedence.md)
- [analytics-governance-decision.md](/opt/lampp/htdocs/farm/docs/architecture/analytics-governance-decision.md)
- [assisted-task-provenance-decision.md](/opt/lampp/htdocs/farm/docs/architecture/assisted-task-provenance-decision.md)

## Diretriz

O AgroSaaS deve continuar operando com domínios oficiais claros, sem overlap funcional e sem recomposição indevida de responsabilidades.

Se uma feature precisar atravessar domínios, ela deve depender na ordem correta e respeitar o ownership de cada camada.
