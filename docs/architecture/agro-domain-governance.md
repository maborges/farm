# AgroSaaS — Governança Arquitetural de Domínio

## Objetivo

Congelar a governança arquitetural atual dos domínios de:

- catálogo de produtos
- estoque físico
- valuation operacional
- domínio operacional agrícola
- apropriação econômica

Este documento existe para evitar regressões conceituais e duplicidade de responsabilidades em novas features.

## Princípios de Governança

- cada entidade deve ter papel claro e não híbrido
- fonte de verdade deve ser explícita
- leitura gerencial e escrita operacional não devem ser confundidas
- compatibilidade legada pode existir, mas não redefine a fonte oficial
- novos fluxos devem reutilizar o domínio existente antes de criar outra entidade

---

## 1. Governança de Produto, Estoque e Valuation

### Produto

`Produto` é o **catálogo mestre**.

Representa:

- cadastro mestre do item
- identidade comercial e operacional do item
- nome, unidade, classificação, códigos e metadados

Não representa:

- saldo físico oficial
- valuation operacional oficial
- custo histórico real por movimentação

Leitura correta:

- catálogo
- formulários
- seleção de produto
- compatibilidade com telas antigas

### SaldoEstoque

`SaldoEstoque` é a **verdade física oficial** do saldo atual.

Representa:

- quantidade atual por produto e almoxarifado
- referência operacional de disponibilidade
- visão consolidada de saldo utilizável

É a fonte oficial para:

- consulta de saldo
- disponibilidade operacional
- alertas de reposição
- mínimo operacional

### LoteEstoque + EstoqueMovimento

`LoteEstoque` e `EstoqueMovimento` são a base do **valuation operacional**.

Representam:

- custo histórico por lote
- entradas e saídas rastreáveis
- ordem real de consumo e valuation
- trilha operacional e auditável

Regra oficial:

- valuation operacional deve nascer de `LoteEstoque` + `EstoqueMovimento`
- custo histórico não deve ser inferido do catálogo de produto

### Produto.preco_medio

`Produto.preco_medio` permanece como **snapshot/fallback compatível**.

Uso permitido:

- compatibilidade com fluxos antigos
- exibição resumida
- telas que ainda não consomem valuation completo

Uso proibido como regra oficial:

- valuation operacional
- custo real de baixa
- custo histórico por lote

### Produto.estoque_minimo

`Produto.estoque_minimo` permanece como **campo legado compatível**.

Pode existir para:

- compatibilidade de telas antigas
- fallback temporário em contextos não migrados

Não é o mínimo operacional oficial.

### SaldoEstoque.estoque_minimo

`SaldoEstoque.estoque_minimo` é o **mínimo operacional oficial**.

Representa:

- mínimo aplicável ao contexto físico/operacional
- gatilho de alerta e reposição
- referência correta para operação

Regra oficial:

- mínimo operacional deve ser lido de `SaldoEstoque.estoque_minimo`
- novos fluxos não devem usar `Produto.estoque_minimo` como fonte oficial

---

## 2. Governança do Domínio Operacional

### Tarefa

`Tarefa` é **planejamento e orquestração**.

Representa:

- intenção operacional
- ação planejada da safra
- coordenação por fase, prioridade, talhão e contexto

Não representa:

- execução real
- custo realizado
- medição operacional

### Operação

`Operação` é a **execução real**.

Representa:

- operação agrícola efetivamente executada
- plantio, adubação, pulverização, colheita e demais execuções
- origem do custo operacional realizado

É a entidade que:

- integra com estoque
- materializa execução
- participa da formação do custo operacional

### Apontamento

`Apontamento` é a **medição operacional**.

Representa:

- horas
- área trabalhada
- consumo
- uso observado de recurso/equipamento/pessoa

Não substitui:

- tarefa
- operação
- jornada

### Jornada

`Jornada` é o **contexto temporal e de equipamento**.

Representa:

- janela operacional de uso
- contexto de máquina/equipe
- container temporal para apontamentos

### Checklist

`Checklist` é **validação operacional**.

Representa:

- confirmação de pré-condições
- gate operacional ou de fase
- itens obrigatórios de verificação

Não substitui:

- tarefa
- operação
- ordem de serviço

### OS

`OS` é **ordem de serviço de manutenção**.

Representa:

- fluxo formal de manutenção
- execução de oficina/manutenção
- contexto próprio do módulo correspondente

Não deve ser confundida com:

- tarefa agrícola
- operação agrícola

### CostAllocation

`CostAllocation` é **apropriação econômica**.

Representa:

- projeção/apropriação econômica da operação
- distribuição de custo por unidade operacional
- camada gerencial/econômica sobre a execução

Não substitui:

- estoque
- valuation de lote
- operação executada

---

## 3. Matriz Oficial de Governança

| Entidade | Papel | Fonte de verdade | Pode escrever | Pode ler | Observações |
| --- | --- | --- | --- | --- | --- |
| `Produto` | Catálogo mestre | Cadastro de produto | Cadastros e fluxos administrativos | Estoque, compras, agrícola, frota, financeiro, UI | Não usar como fonte oficial de valuation ou saldo |
| `SaldoEstoque` | Saldo físico consolidado | Estoque operacional | Serviços de estoque e movimentos | Operação, compras, agrícola, dashboards, consultas | Verdade física oficial |
| `LoteEstoque` | Custo histórico por lote | Estoque operacional | Entradas, recebimentos, movimentos de lote | Estoque, valuation, auditoria | Base de custo histórico real |
| `EstoqueMovimento` | Ledger operacional de estoque | Estoque operacional | Fluxos que movimentam estoque | Estoque, auditoria, valuation, integrações | Trilho oficial de movimentação |
| `Produto.preco_medio` | Snapshot/fallback compatível | Derivado/compatível | Compatibilidade legada e processos explícitos de snapshot | UI legada, consultas resumidas | Não usar em valuation operacional novo |
| `Produto.estoque_minimo` | Compatibilidade legada | Campo legado | Cadastros legados | UI legada e compatibilidade | Não é o mínimo oficial |
| `SaldoEstoque.estoque_minimo` | Mínimo operacional oficial | Estoque operacional | Configuração operacional de estoque | Alertas, reposição, operação | Fonte oficial do mínimo |
| `Tarefa` | Planejamento/orquestração | Domínio operacional agrícola | Planejamento da safra | UI agrícola, relatórios de planejamento | Não gera custo real sozinha |
| `Operação` | Execução real | Domínio operacional agrícola | Fluxos de execução agrícola | Estoque, custos, caderno, relatórios | Origem do custo operacional realizado |
| `Apontamento` | Medição operacional | Domínio operacional/frota | Fluxos de apontamento | Operacional, custos, análises | Não é planejamento nem execução principal |
| `Jornada` | Contexto temporal/equipamento | Operacional/frota | Fluxos de abertura/fechamento de jornada | Apontamentos, operacional, análises | Container operacional |
| `Checklist` | Validação operacional | Domínio de governança operacional | Templates/checklists/safra | Safra, operação, governança | Gate, não execução |
| `OS` | Manutenção | Domínio de manutenção/oficina | Fluxos de manutenção | Frota/oficina/gestão | Não confundir com tarefa agrícola |
| `ProductionUnit` | Unidade operacional | Agricultura | Safra/produção | Custos, cenários, operações, relatórios | Base operacional da apropriação |
| `CostAllocation` | Apropriação econômica | Agricultura/custos | Serviços de alocação econômica | Relatórios, custo, BI agrícola | Não substitui valuation de estoque |

---

## 4. Regras para Novas Features

### Regra 1 — Produto não é fonte de custo operacional

Não usar `Produto` como origem de:

- custo real
- valuation
- custo histórico de consumo

Se o fluxo precisa custo operacional, ele deve partir de:

- `LoteEstoque`
- `EstoqueMovimento`
- ou serviço oficial de valuation já existente

### Regra 2 — Não escrever `Produto.preco_medio` em fluxos operacionais

Fluxos operacionais não devem atualizar `Produto.preco_medio` como se fosse valuation oficial.

Se houver atualização desse campo, ela deve ser tratada como:

- snapshot
- fallback
- compatibilidade

### Regra 3 — Não usar `Produto.estoque_minimo` como mínimo oficial

O mínimo operacional oficial é:

- `SaldoEstoque.estoque_minimo`

`Produto.estoque_minimo` só pode ser usado para compatibilidade explícita.

### Regra 4 — Não usar “Atividade” como conceito oficial

Não usar `Atividade` como conceito central novo sem:

- entidade própria
- papel claro
- fronteira explícita

Hoje, o domínio oficial é:

- `Tarefa` para planejamento
- `Operação` para execução

### Regra 5 — Não criar dashboard paralelo se já existir serviço agregador

Antes de criar novo dashboard, sempre verificar se já existe:

- serviço agregador
- resumo consolidado
- endpoint de leitura oficial

Objetivo:

- evitar múltiplas verdades
- evitar métricas divergentes
- evitar duplicação de lógica de agregação

### Regra 6 — Verificar domínio existente antes de criar nova entidade

Antes de propor nova entidade, validar se o papel já é coberto por:

- estoque
- operacional
- agrícola
- manutenção
- custos
- apropriação econômica

Nova entidade só deve nascer se houver:

- responsabilidade inédita
- fronteira de escrita própria
- justificativa de domínio clara

---

## 5. Regras de Decisão Arquitetural

Quando surgir dúvida sobre onde colocar uma nova responsabilidade:

1. identificar se é catálogo, saldo, valuation, execução, medição ou apropriação
2. localizar a entidade que já é fonte de verdade do domínio
3. evitar escrever em campo compatível como se ele fosse oficial
4. evitar criar leitura paralela se já houver agregação consolidada
5. preferir evolução incremental em cima do domínio existente

---

## 6. Estado Congelado Atual

Este é o estado oficial congelado para próximas evoluções:

- `Produto` = catálogo mestre
- `SaldoEstoque` = verdade física
- `LoteEstoque` + `EstoqueMovimento` = valuation operacional
- `ProductionUnit` + `CostAllocation` = apropriação econômica
- `Produto.preco_medio` = snapshot/fallback compatível
- `Produto.estoque_minimo` = legado compatível
- `SaldoEstoque.estoque_minimo` = mínimo operacional oficial
- `Tarefa` = planejamento/orquestração
- `Operação` = execução real
- `Apontamento` = medição operacional
- `Jornada` = contexto temporal/equipamento
- `Checklist` = validação operacional
- `OS` = manutenção

Qualquer evolução que contradiga essas definições deve ser tratada como decisão arquitetural explícita, não como ajuste incremental implícito.
