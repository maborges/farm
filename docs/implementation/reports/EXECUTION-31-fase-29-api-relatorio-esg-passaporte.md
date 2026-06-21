# Relatório de Execução: EXECUTION-31 — FASE 29 API PÚBLICA PROTEGIDA RELATÓRIO ESG E PASSAPORTE

## Resumo
A Fase 29 estabeleceu os endpoints públicos protegidos para as entidades `RelatorioESG` e `PassaporteRastreabilidade`, previamente implementadas na camada de domínio (Fase 28).

O objetivo principal desta fase foi expor essas entidades na API de forma a preservar o isolamento rigoroso de Tenant (via `TenantViolationError` e proteção em nível de Service/Router), sem alterar o banco de dados via novas migrations (aproveitando a head `20260621_certificacao_esg_relatorio_passaporte`) e mitigando o risco de colisões de models legado (`enterprise.models.sprints_27_33.py`).

## Implementações Realizadas

### 1. Rotas da API (`services/api/certificacoes_esg/router.py`)
- Endpoints de `RelatorioESG`:
  - `POST /relatorios-esg`: Criação de novo relatório ESG.
  - `GET /relatorios-esg`: Listagem de relatórios ESG.
  - `PATCH /relatorios-esg/{id}/status`: Atualização do status de um relatório ESG.
  - `POST /relatorios-esg/{id}/indicadores`: Adição de um indicador a um relatório.
  - `POST /relatorios-esg/{id}/evidencias`: Adição de uma evidência a um relatório.
- Endpoints de `PassaporteRastreabilidade`:
  - `POST /passaportes`: Criação de novo passaporte de rastreabilidade.
  - `GET /passaportes`: Listagem de passaportes.
  - `PATCH /passaportes/{id}/status`: Atualização do status de um passaporte.
  - `POST /passaportes/{id}/eventos`: Adição de evento a um passaporte.
  - `POST /passaportes/{id}/evidencias`: Adição de evidência a um passaporte.

As rotas foram acopladas ao injetor de dependências base do Agrosaas (`get_tenant_id`, `get_user_id`, `get_session`), isolando estritamente os tenants. Nenhuma informação de `tenant_id` trafega via payload.

### 2. Tratamento de Colisão de Models Legacy
Ao incorporar as rotas, nos testes de integração observou-se uma colisão de tabela (`esg_relatorios`) devido à permanência desta tabela em `enterprise.models.sprints_27_33`. 
- **Solução implementada:** `extend_existing=True` foi injetado nas declarações em `certificacoes_esg/models.py`.
- **Estratégia de Testes:** Os testes de integração foram refatorados para utilizar uma instância estéril do FastAPI em memória, não invocando `main.app`, o que evitou carregar a arvore inteira de models orfãos ou legacy não requeridos.

### 3. Testes de Integração
- Foram elaborados testes na suíte dedicada `services/api/tests/integration/certificacoes_esg/test_relatorio_passaporte_router_integration.py`
- Cobertura de cenários normais (retornando `201 Created` / `200 OK`).
- Validação ativa de restrição de payloads (`422 Unprocessable Entity` ao rejeitar `tenant_id` e erro de conversões de enum `TipoEventoPassaporte`).
- Teste específico garantindo o isolamento Multi-Tenant com `TenantViolationError` revertendo adequadamente em `403 Forbidden`.

### 4. Documentação de Arquitetura
- Atualizado `docs/architecture/agrosaas-routing-map.md` incorporando as rotas `/api/v1/certificacoes-esg/relatorios-esg` e `/api/v1/certificacoes-esg/passaportes`.

## Próximos Passos
O arcabouço lógico e de roteamento da base de ESG e Rastreabilidade se encontra estabilizado. A próxima evolução recairá em consumir esses endpoints no Front-End (`apps/web` App Router). Nenhuma deleção legacy foi feita em models `enterprise` por ser considerada fora de escopo e insegura na base atual.

## Status: FINALIZADO
Testes rodando: 11 passed (100%).
