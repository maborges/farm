# OPS-INTELLIGENCE-06 - Providers de Domínios Restantes

## Auditoria Inicial

| Domínio | Achado | Classificação | Base reutilizada |
| --- | --- | --- | --- |
| Pecuária | Há serviços executivos de lote, sanidade, dashboard e sync de campo para pecuária. | EXISTE PARCIALMENTE | `pecuaria/services/*`, `pecuaria/animal/models.py`, `campo.models.TarefaCampo` |
| Estoque | Há serviço operacional completo com saldos, lotes, reservas, requisições e ledger. | EXISTE PARCIALMENTE | `operacional/services/estoque_service.py`, `operacional/models/estoque.py` |
| Frota | Há dashboard, disponibilidade, manutenção preventiva e inteligência de frota. | EXISTE PARCIALMENTE | `operacional/services/frota_dashboard_service.py`, `operacional/services/frota_manutencao_preventiva_service.py` |
| ESG/Certificações | Há serviço de certificações, integridade, não conformidades, planos de ação e geração de alertas canônicos. | EXISTE E ATENDE | `certificacoes_esg/service.py`, `certificacoes_esg/models.py`, `alert_engine/generators/esg_certificacoes_generator.py` |
| Wizard/Onboarding | Há engine canônica de checklist e implantação operacional. | EXISTE E ATENDE | `wizard/checklist_engine.py`, `wizard/models.py`, `wizard/services.py` |
| Campo PWA | Há sync push/pull, dispositivos, tarefas offline e eventos de falha. | EXISTE PARCIALMENTE | `campo/service.py`, `campo/router.py`, `campo/models.py` |

## Providers Criados

- `PecuariaRecommendationProvider`
- `EstoqueRecommendationProvider`
- `FrotaRecommendationProvider`
- `ESGRecommendationProvider`
- `WizardRecommendationProvider`
- `CampoRecommendationProvider`

Registro explícito em `services/api/recommendations/providers/__init__.py` e reexportação em `services/api/recommendations/__init__.py`.

## Regras Implementadas

- Pecuária
  - lote sem pesagem recente
  - custo sanitário alto por cabeça
  - lote sem movimentação recente
  - lote sem piquete vinculado
  - vacinação atrasada
- Estoque
  - saldo abaixo do mínimo
  - reserva acima do disponível
  - consumo recente acima do saldo
  - lote de estoque vencendo
  - requisição pendente
- Frota
  - manutenção preventiva vencida
  - manutenção preventiva próxima
  - OS pendente
  - sem abastecimento recente
  - equipamento possivelmente ocioso
  - risco operacional consolidado
- ESG/Certificações
  - certificação vencida
  - certificação vencendo
  - checklist incompleto
  - não conformidade aberta
  - plano de ação atrasado
- Wizard
  - unidade produtiva ausente
  - onboarding incompleto
  - pendência crítica
  - go-live bloqueado por checklist
- Campo
  - sincronização desatualizada
  - tarefa de campo atrasada
  - falha de sync de pecuária
  - tombstones pendentes de sincronização

## Regras Adiadas

- Conflito pendente de Campo com estado persistido canônico
  - Motivo: o fluxo atual retorna `CONFLICT` para o cliente, mas não persiste um estado canônico próprio para consulta posterior sem criar nova estrutura paralela.

## Fontes Oficiais Reutilizadas

- `pecuaria.services.lote_indicadores_service.LoteIndicadoresService`
- `pecuaria.services.lote_resumo_sanitario_service.LoteResumoSanitarioService`
- `operacional.services.frota_dashboard_service.FrotaDashboardService`
- `operacional.services.estoque_service.EstoqueService`
- `certificacoes_esg.models`
- `wizard.models`
- `campo.models`
- `campo.service.SyncService` como referência de sinais, sem mutação

## Riscos de Acoplamento Evitados

- Nenhum provider chama `AlertEngine`.
- Nenhum provider chama `NotificationDispatcher`.
- Nenhum provider altera frontend ou Campo PWA.
- Nenhum provider executa mutações operacionais.
- Nenhum provider recalcula lifecycle, dedupe ou persistência.
- Os providers retornam somente `RecommendationCandidate`.

## Validação Executada

- `cd services/api && .venv/bin/python -m pytest tests/unit/recommendations -q`
  - Resultado: `49 passed`
- `cd services/api && .venv/bin/alembic heads`
  - Resultado: `20260703_ops_intelligence_02_recommendations_foundation (head)`
- `git diff --check`
  - Resultado: sem erros

