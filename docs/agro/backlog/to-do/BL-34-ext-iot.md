# BL-34 — EXT_IOT

**Módulo:** `EXT_IOT`  
**Status atual:** Implementado  
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
- [ ] Conectores específicos
- [ ] Sincronização periódica
- [ ] Monitoramento de falhas

### US-34.2 — Alertas de telemetria
**Como** operador, **quero** ver alertas de telemetria, **para** agir rápido.

**Critérios de aceite:**
- [ ] Alertas em tempo real
- [ ] Histórico de eventos
- [ ] Integração com frota e campo

## Tarefas técnicas

- [ ] Revisar cobertura dos conectores
- [ ] Padronizar contratos de integração
- [ ] Melhorar observabilidade

