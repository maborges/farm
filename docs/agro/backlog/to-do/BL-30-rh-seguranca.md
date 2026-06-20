# BL-30 — RH2_SEGURANCA

**Módulo:** `RH2_SEGURANCA`  
**Status atual:** Implementado  
**Prioridade:** Média  
**Dependências:** `CORE`, `RH1_REMUNERACAO`

## Contexto

Segurança do trabalho, EPIs, EPCs, PPP, PCMSO e NR-31.

## Gaps observados

- Não há domínio operacional pronto.
- Não há rotas nem interface correspondente.

## User Stories

### US-30.1 — Controle de EPI
**Como** gestor, **quero** controlar entrega e validade de EPI, **para** cumprir segurança do trabalho.

**Critérios de aceite:**
- [x] Cadastro de EPI/EPC
- [x] Entrega por colaborador
- [x] Histórico de validade

### US-30.2 — Documentos de SST
**Como** gestor, **quero** registrar PPP e PCMSO, **para** manter compliance trabalhista.

**Critérios de aceite:**
- [x] Documentos por colaborador
- [x] Alertas de vencimento
- [x] Relatórios NR-31

## Tarefas técnicas

- [x] Criar domínio e entidades
- [x] Criar workflow de EPI
- [x] Criar telas e permissões
