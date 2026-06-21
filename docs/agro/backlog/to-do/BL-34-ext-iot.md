# BL-34 — EXT_IOT

**Módulo:** `EXT_IOT`  
**Status atual:** Concluído
**Prioridade:** Baixa  
**Dependências:** `CORE`, `A4_PRECISAO`, `O1_FROTA`

## Contexto

Integração com telemetria, máquinas e sensores.

## Gaps observados

- Há routers e integrações, mas a visão enterprise ainda pode ser ampliada.

## User Stories

### US-34.1 — Integrações de máquina
**Como** gestor, **quero** integrar máquinas e sensores, **para** automatizar coleta de dados.

**Critérios de aceite:**
- [x] Conectores específicos
- [x] Sincronização periódica
- [x] Monitoramento de falhas

### US-34.2 — Alertas de telemetria
**Como** operador, **quero** ver alertas de telemetria, **para** agir rápido.

**Critérios de aceite:**
- [x] Alertas em tempo real
- [x] Histórico de eventos
- [x] Integração com frota e campo

## Tarefas técnicas

- [x] Revisar cobertura dos conectores
- [x] Padronizar contratos de integração
- [x] Melhorar observabilidade
