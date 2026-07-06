# OPS-INTELLIGENCE-03 — Providers Iniciais do Recommendation Engine

## Escopo

Implementados os primeiros providers reais do `Recommendation Engine` global em `services/api/recommendations/providers/`, sem criar motor paralelo por domínio, sem alterar frontend, Campo PWA, notificações ou `Alert Engine`.

## Auditoria dos serviços reaproveitados

Foram auditados e reaproveitados como fonte de heurísticas e leitura:

- `services/api/agricola/climatico/recommendation_service.py`
- `services/api/agricola/recomendacoes/service.py`
- `services/api/agricola/inteligencia_operacional/service.py`
- `services/api/agricola/prioridades/service.py`
- `services/api/financeiro/services/lancamento_service.py`
- `services/api/financeiro/services/alerta_inteligente_service.py`
- `services/api/ia/dre_intelligence_service.py`

Também foram usados modelos e serviços read-only já existentes como fonte de dados:

- `services/api/agricola/climatico/models.py`
- `services/api/agricola/climatico/config.py`
- `services/api/agricola/custos/service.py`
- `services/api/agricola/operacoes/models.py`
- `services/api/agricola/caderno/models.py`
- `services/api/agricola/a1_planejamento/models.py`
- `services/api/agricola/safras/models.py`
- `services/api/financeiro/services/dashboard_service.py`
- `services/api/financeiro/models/despesa.py`
- `services/api/financeiro/models/receita.py`
- `services/api/financeiro/models/lancamento.py`

## Providers criados

- `ClimaRecommendationProvider`
- `AgriculturaRecommendationProvider`
- `FinanceiroRecommendationProvider`

Arquivos:

- `services/api/recommendations/providers/clima_provider.py`
- `services/api/recommendations/providers/agricultura_provider.py`
- `services/api/recommendations/providers/financeiro_provider.py`
- `services/api/recommendations/providers/__init__.py`

## Regras implementadas

### Clima

- janela desfavorável para pulverização
- risco climático para operação agrícola
- recomendação geral de revisão pela janela climática
- condição favorável quando não há restrição relevante

### Agricultura

- safra sem movimentação recente
- operação agrícola atrasada
- talhão sem atualização recente
- custo agrícola acima do previsto
- priorização operacional recomendada

### Financeiro

- fluxo de caixa crítico
- contas vencidas
- contas a vencer em janela curta
- concentração de despesa
- margem financeira apertada
- orçamento comprometido

## Regras adiadas

- provider de pecuária
- provider de estoque
- provider de frota
- provider de ESG
- provider do wizard
- integração com `NotificationDispatcher`
- integração com `Alert Engine`
- qualquer router/API pública de recomendação
- mutações operacionais automáticas

## Riscos de acoplamento evitados

- providers não importam frontend
- providers não importam Campo PWA
- providers não dependem de `Alert Engine`
- providers não dependem de `NotificationDispatcher`
- providers não promovem `ClimaRecommendationService` a núcleo global
- engine continua responsável por persistência, dedupe e lifecycle

## Validação executada

Comandos executados:

```bash
cd services/api
.venv/bin/python -m pytest tests/unit/recommendations -q
.venv/bin/alembic heads
git diff --check
```

Resultado observado:

- `tests/unit/recommendations`: `25 passed`
- `alembic heads`: `20260703_ops_intelligence_02_recommendations_foundation (head)`
- `git diff --check`: sem erros

## Observações técnicas

- O provider climático lê `RegistroClima` e thresholds oficiais diretamente.
- O provider agrícola usa sinais read-only de operação, caderno, safra e orçamento previsto.
- O provider financeiro combina `DashboardService`, `LancamentoService`, despesas/receitas e orçamento de safra como heurística de decisão.
- Todos os providers retornam apenas `RecommendationCandidate`.
- A persistência e o lifecycle permanecem centralizados no `RecommendationEngine` global.

## Veredicto da etapa

Os primeiros providers reais foram adicionados com sucesso e ficam prontos para reutilização pelo núcleo global, sem criar motores paralelos nem acoplamento lateral indevido.
