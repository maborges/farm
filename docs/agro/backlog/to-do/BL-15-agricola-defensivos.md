# BL-15 — A3_DEFENSIVOS

**Módulo:** `A3_DEFENSIVOS`  
**Status atual:** Implementado  
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
- [ ] Cadastro e consulta por safra
- [ ] Catálogo de pragas/doenças
- [ ] Diagnóstico assistido

### US-15.2 — Receituário
**Como** agrônomo, **quero** gerar receituários, **para** formalizar aplicação de defensivos.

**Critérios de aceite:**
- [ ] Emissão de receituário
- [ ] Vínculo com operação
- [ ] Auditoria de alterações

## Tarefas técnicas

- [ ] Adicionar testes de diagnóstico assistido
- [ ] Cobrir cenários de prescrição
- [ ] Melhorar integração com estoque

