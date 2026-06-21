# BL-16 — A4_PRECISAO

**Módulo:** `A4_PRECISAO`  
**Status atual:** Concluído
**Prioridade:** Média  
**Dependências:** `CORE`, `A1_PLANEJAMENTO`

## Contexto

Agricultura de precisão com NDVI, clima e prescrição VRA.

## Gaps observados

- Estrutura está presente, mas precisa de expansão em analítica e automação.
- Parte da entrega ainda depende de dados externos e fluxos avançados.

## User Stories

### US-16.1 — NDVI por talhão
**Como** gestor, **quero** visualizar NDVI por talhão, **para** identificar variabilidade.

**Critérios de aceite:**
- [x] Consulta por período
- [x] Histórico por talhão
- [x] Gráficos e mapas

### US-16.2 — Prescrição VRA
**Como** agrônomo, **quero** criar prescrição de taxa variável, **para** otimizar uso de insumos.

**Critérios de aceite:**
- [x] Geração de prescrição
- [x] Integração com amostragem de solo
- [x] Exportação operacional

## Tarefas técnicas

- [x] Melhorar cobertura de dados climáticos
- [x] Integrar prescrição com operação de campo
- [x] Criar testes de regressão de NDVI
