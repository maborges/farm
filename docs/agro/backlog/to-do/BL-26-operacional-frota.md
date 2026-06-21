# BL-26 — O1_FROTA

**Módulo:** `O1_FROTA`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `O2_ESTOQUE`

## Contexto

Frota, manutenção, abastecimento e custos de máquinas.

## Gaps observados

- O módulo é consistente, mas ainda há espaço para consolidação de benchmark e automação.

## User Stories

### US-26.1 — Manutenção de frota
**Como** gestor, **quero** criar planos e ordens de serviço, **para** manter máquinas operacionais.

**Critérios de aceite:**
- [x] Plano de manutenção
- [x] OS e itens de OS
- [x] Fechamento com custos

### US-26.2 — Uso e abastecimento
**Como** gestor, **quero** registrar abastecimentos e uso, **para** medir consumo real.

**Critérios de aceite:**
- [x] Controle de abastecimento
- [x] Apontamento de uso
- [x] Custo por hora/km

## Tarefas técnicas

- [x] Ampliar cobertura de indicadores
- [x] Revisar relatórios de custo consolidado
- [x] Garantir integração estável com estoque
