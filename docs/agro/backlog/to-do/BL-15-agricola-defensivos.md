# BL-15 — A3_DEFENSIVOS

**Módulo:** `A3_DEFENSIVOS`  
**Status atual:** Concluído
**Prioridade:** Alta  
**Dependências:** `CORE`, `A2_CAMPO`

## Contexto

Monitoramento fitossanitário, diagnósticos e receituário.

## Gaps observados

- Diagnóstico existe, mas depende de continuidade de cobertura em catálogos e regras.
- Integração com IA diagnóstica deve ser testada com casos reais.

## User Stories

### US-15.1 — Monitorar pragas e doenças
**Como** agrônomo, **quero** registrar monitoramentos, **para** responder rapidamente a surtos.

**Critérios de aceite:**
- [x] Cadastro e consulta por safra
- [x] Catálogo de pragas/doenças
- [x] Diagnóstico assistido

### US-15.2 — Receituário
**Como** agrônomo, **quero** gerar receituários, **para** formalizar aplicação de defensivos.

**Critérios de aceite:**
- [x] Emissão de receituário
- [x] Vínculo com operação
- [x] Auditoria de alterações

## Tarefas técnicas

- [x] Adicionar testes de diagnóstico assistido
- [x] Cobrir cenários de prescrição
- [x] Melhorar integração com estoque
