# BL-35 — EXT_ERP

**Módulo:** `EXT_ERP`  
**Status atual:** Concluído
**Prioridade:** Baixa  
**Dependências:** `CORE`

## Contexto

Bridge corporativa para ERP e integrações externas.

## Gaps observados

- O módulo está comercialmente previsto, mas o router enterprise correspondente está comentado.
- Não há fluxo de integração pronto para produção.

## User Stories

### US-35.1 — Integração ERP
**Como** gestor, **quero** integrar com ERP externo, **para** evitar retrabalho operacional.

**Critérios de aceite:**
- [x] Conectores ERP
- [x] Mapeamento de entidades
- [x] Logs de sincronização

### US-35.2 — Exportações corporativas
**Como** gestor, **quero** exportar dados para BI/ERP, **para** consolidar informação em sistemas externos.

**Critérios de aceite:**
- [x] Exportação de relatórios
- [x] Webhooks e jobs
- [x] Monitoramento de falhas

## Tarefas técnicas

- [x] Definir arquitetura de integração
- [x] Implementar conectores prioritários
- [x] Criar páginas de configuração
