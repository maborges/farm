# OPS-INTELLIGENCE-14 — RBAC do Lifecycle de Recomendações

Status: concluído — GO

## Auditoria e matriz final

O IAM reutilizado é composto por `Usuario`, `TenantUsuario`, `PerfilAcesso` e `FazendaUsuario`/`UnidadeProdutivaUsuario`, com permissões avaliadas por `TenantPermissions` e vigência por unidade. RLS continua responsável somente pelo isolamento de linhas.

| Ação real | Origem | Permissão | Escopo | Auditoria |
| --- | --- | --- | --- | --- |
| listar/detalhar/marcar vista | humana | `recommendations:view` | unidade vinculada; tenant-wide só owner/admin | lifecycle para `view` |
| aceitar | humana | `recommendations:accept` | unidade vinculada | lifecycle + actor |
| adiar | humana | `recommendations:postpone` | unidade vinculada | lifecycle + motivo opcional |
| executar | humana | `recommendations:execute` | unidade vinculada | lifecycle + nota opcional |
| dispensar | humana | `recommendations:dismiss` | unidade vinculada | lifecycle + motivo opcional |
| reabrir | humana | `recommendations:reopen` | unidade vinculada | lifecycle + actor |
| métricas/tenant-wide | humana | `recommendations:admin` | tenant | leitura protegida |
| criar, dedupe, expirar | sistema | caminho interno | tenant interno | lifecycle/audit existente |

`owner` mantém acesso integral pelo catálogo existente. `admin` recebe `recommendations:*`; `gerente` recebe todas as transições humanas; `agronomo` e `operador` recebem leitura, aceite e execução; `consultor`, `financeiro` e `auditor` recebem somente leitura. Perfis customizados usam o mesmo formato `granted` já existente.

## Implementação

`RecommendationAuthorizationService` consulta o vínculo ativo real do usuário e, quando a recomendação possui `unidade_produtiva_id`, exige `FazendaUsuario` vigente para essa unidade. O header de fazenda não determina autorização. Recomendações tenant-wide e métricas são conservadoramente restritos a owner/admin.

O router protege listagem, detalhe, métricas e todas as ações humanas antes da mutação. A listagem recebe filtro de escopo do backend; não há capability persistida nem decisão no frontend. Web permanece consumidor da API; Campo continua somente read-only/offline e não possui endpoint de lifecycle, portanto não contorna RBAC.

Scheduler, subscriber, engine, dedupe e expiração automática não usam o router e não exigem usuário humano.

## Arquivos alterados

- `services/api/recommendations/authorization.py`
- `services/api/recommendations/router.py`
- `services/api/recommendations/query_service.py`
- `services/api/core/constants.py`
- `services/api/tests/unit/recommendations/test_recommendations_query_router.py`
- `docs/implementation/reports/OPS-INTELLIGENCE-14-RBAC-LIFECYCLE.md`

## Testes

```text
pytest tests/unit/recommendations/test_recommendations_query_router.py -m integration -q
13 passed
```

Os cenários adicionais comprovam `403` para membro sem vínculo na unidade e para membro com somente leitura tentando aceitar. Não houve alteração de RLS, tabelas, migrations, scheduler, Event/Outbox ou providers.

## Limitações

O contrato atual possui apenas recorte tenant/unidade; não há vínculo canônico persistido para autorização por safra, tarefa, animal ou equipamento. Por segurança, o domínio não infere esses escopos. Motivo para dismiss/postpone e nota de execução permanecem opcionais, conforme schemas e lifecycle existentes.

## Veredicto

**GO.** Todas as ações humanas do router são autorizadas no backend com permissão e escopo reais; as transições automáticas permanecem independentes de identidade humana.
