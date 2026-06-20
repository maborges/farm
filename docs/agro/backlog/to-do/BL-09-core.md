# BL-09 — CORE

**Módulo:** `CORE`  
**Status atual:** Implementado, com necessidade de estabilização  
**Prioridade:** Alta  
**Dependências:** nenhuma

## Objetivo

Consolidar o núcleo da plataforma em uma base única e confiável para:
- identidade e tenant
- multitenancy
- onboarding
- billing e limites
- RBAC e feature gates
- catálogo canônico de módulos e pacotes

## Contexto

O CORE já existe no código, mas ainda há pontos de divergência entre backend, frontend e documentação.
Este backlog serve para fechar lacunas de consistência e reduzir risco de regressão em módulos dependentes.

## Problemas observados

- Catálogo de módulos e pacotes aparece em mais de um lugar.
- Alguns nomes de módulo ainda divergem entre documentos e código.
- Fluxos de onboarding e billing ainda dependem de seeds e documentação para ficar previsíveis.
- Feature gates precisam de cobertura de teste mais forte.

## User Stories

### US-09.1 — Catálogo canônico de módulos
**Como** administrador da plataforma, **quero** uma fonte única para módulos e pacotes, **para** evitar divergências entre frontend e backend.

**Critérios de aceite:**
- [ ] Catálogo único versionado
- [ ] Validação automática de sincronismo entre backend e frontend
- [ ] Seeds idempotentes para módulos e pacotes
- [ ] Falha explícita quando houver divergência de chave ou código

### US-09.2 — Feature gates consistentes
**Como** sistema, **quero** aplicar gates iguais em toda a stack, **para** bloquear acesso inconsistente.

**Critérios de aceite:**
- [ ] `require_module()` padronizado em todos os routers
- [ ] Testes cobrindo acesso permitido e negado
- [ ] Mensagens de erro unificadas
- [ ] Tratamento consistente para módulos e tiers

### US-09.3 — Billing e onboarding previsíveis
**Como** gestor da assinatura, **quero** um fluxo previsível de criação e atualização de plano, **para** iniciar uso sem inconsistência operacional.

**Critérios de aceite:**
- [ ] Plano inicial criado com módulos esperados
- [ ] Onboarding não depende de ajuste manual
- [ ] Limites refletidos no backend e frontend

## Escopo Inicial

- Identidade do tenant
- Assinatura e plano
- Catálogo de módulos
- Gating por módulo
- Seeds e contratos de dados

## Tarefas Técnicas

### Backend
- [ ] Consolidar catálogo de módulos em uma fonte canônica
- [ ] Revisar divergências de nomenclatura entre módulos e pacotes
- [ ] Validar a correspondência entre `Modulos`, `ModuloMetadata` e pacotes
- [ ] Adicionar testes de contract para billing e onboarding
- [ ] Cobrir `require_module()` com cenários de erro e sucesso

### Frontend
- [ ] Garantir que o catálogo do frontend use os mesmos códigos do backend
- [ ] Revisar labels dos módulos em menus e telas administrativas
- [ ] Validar estados vazios e de bloqueio por módulo

### Qualidade
- [ ] Criar teste automatizado de sincronismo do catálogo
- [ ] Criar teste automatizado para plano inicial e módulos inclusos
- [ ] Criar teste automatizado para gates de acesso

## Critério de Pronto

- [ ] Catálogo único validado
- [ ] Gates cobertos por testes
- [ ] Seeds previsíveis
- [ ] Sem divergências entre documentação e código para o CORE
