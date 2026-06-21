# BL-33 — EXT_IA

**Módulo:** `EXT_IA`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`

## Contexto

IA Copilot, diagnóstico, recomendações e assistentes.

## Gaps observados

- O módulo existe, mas está disperso em vários routers e services.
- Precisa de governança clara de produto e limites.

## User Stories

### US-33.1 — Assistente IA
**Como** gestor, **quero** receber recomendações assistidas, **para** tomar decisões mais rápidas.

**Critérios de aceite:**
- [x] Respostas contextualizadas
- [x] Histórico de interações
- [x] Limites de uso por plano

### US-33.2 — Diagnóstico inteligente
**Como** agrônomo, **quero** usar IA para diagnóstico, **para** acelerar decisão de manejo.

**Critérios de aceite:**
- [x] Fluxos de diagnóstico
- [x] Integração com imagens
- [x] Auditoria de uso

## Tarefas técnicas

- [x] Consolidar rotas e naming
- [x] Amarrar limites de plano
- [x] Cobrir respostas com testes
