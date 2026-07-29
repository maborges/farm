# OPS-INTELLIGENCE-15 — Consolidação e retirada controlada de legado

## Veredicto

**GO COM RESSALVAS.** A auditoria não encontrou componente comprovadamente morto para remoção segura. O núcleo oficial permanece único em `services/api/recommendations/`; nenhuma tabela, scheduler, subscriber, fila ou fluxo de notificação paralelo foi criado ou removido.

## Inventário

| Componente | Localização | Tipo | Consumidores | Substituto oficial | Estado | Ação recomendada |
| --- | --- | --- | --- | --- | --- | --- |
| Motor global | `services/api/recommendations/` | núcleo canônico | API, Web, Campo, scheduler, subscriber | — | ATIVO OFICIAL | preservar |
| Serviço climático | `agricola/climatico/recommendation_service.py` | contrato climático por operação | rota `/climatico/recomendacoes/{unidade_produtiva_id}`, dashboard Web climático, testes | `ClimaRecommendationProvider` para o read model global | COMPATIBILIDADE NECESSÁRIA | depreciação controlada; não remover |
| Rota climática | `agricola/climatico/router.py` | API pública legada | `apps/web/.../recomendacoes-operacionais.tsx` | `/recommendations` | COMPATIBILIDADE NECESSÁRIA | migrar somente com contrato de paridade aprovado |
| Projeção climática Campo | `campo/service.py::_build_recomendacoes_climaticas` | adapter offline de leitura | sync/pull e Dexie `recomendacoes_climaticas` | `recommendation_results` | COMPATIBILIDADE NECESSÁRIA | manter; já deriva exclusivamente do read model oficial |
| Recomendações agrícolas v1 | `agricola/recomendacoes/` | análise assistida por safra | rota `/agricola/recomendacoes/v1`, dashboard agrícola, testes | não há substituto equivalente comprovado | PROVIDER-SPECIFIC LEGÍTIMO | manter fora do escopo; não confundir com lifecycle global |
| Recomendações financeiras, hedge, solo e IA | domínios correspondentes | respostas analíticas/especializadas | rotas e telas dos próprios domínios | não há substituto equivalente comprovado | PROVIDER-SPECIFIC LEGÍTIMO | manter; avaliar migração em programa próprio, se necessário |

## Causa da não remoção do `ClimaRecommendationService`

O serviço é instanciado pela rota climática ativa e o Web a consulta diretamente. Ele não persiste, não notifica e não agenda trabalho: lê `RegistroClima` e `OperationalAlert` e devolve quatro respostas transitórias por operação.

O `ClimaRecommendationProvider` é o produtor oficial de `RecommendationCandidate` para o motor global, com persistência, dedupe, lifecycle e notificação posterior pelo fluxo canônico. Contudo, suas regras e contrato não são equivalentes ao legado: ele produz regras globais como `CLIMA_JANELA_PULVERIZACAO_DESFAVORAVEL` e `CLIMA_RISCO_OPERACAO_AGRICOLA`, enquanto o legado sempre estrutura `PULVERIZACAO`, `COLHEITA`, `ADUBACAO` e `GERAL`. Portanto, removê-lo quebraria contrato e alteraria comportamento funcional.

Foi adicionada documentação de depreciação controlada no próprio serviço. Nenhuma nova chamada deve ser criada. A remoção depende de: (1) migração do dashboard Web ao read model oficial; (2) decisão explícita sobre a paridade por operação; (3) atualização/remoção da projeção offline somente se o novo contrato a cobrir; e (4) busca sem consumidores de produção, Web, Campo e testes válidos.

## Evidências de arquitetura

- O registry oficial registra `ClimaRecommendationProvider`; o provider retorna somente `RecommendationCandidate`.
- O Campo consulta `RecommendationResult` no sync/pull e constrói a compatibilidade climática a partir de linhas com `provider_name == "clima"`; não instancia o serviço legado.
- Não foi encontrada persistência de recomendações fora de `recommendation_results` para o fluxo climático, nem chamada direta de `NotificationDispatcher` nos domínios auditados.
- Não foi encontrado scheduler local que gere recomendações; o scheduler ERP encontrado apenas trata integração ERP e não é produtor de recomendações.
- O subscriber global permanece único no `EventSubscriberRegistry`; a ativação atual de `campo.sync.falha` usa o engine e lifecycle oficiais.

## Impacto

- **APIs:** nenhuma rota removida; o endpoint climático continua ativo e explicitamente temporário.
- **Web:** continua preservado, pois ainda usa o contrato climático legado.
- **Campo:** preservado; consome o read model global e sua projeção offline não chama o legado.
- **Dados:** nenhuma migration, tabela ou dado histórico foi alterado.
- **Notificações:** nenhuma chamada direta duplicada foi encontrada ou introduzida.

## Arquivos alterados

- `services/api/agricola/climatico/recommendation_service.py`: documentação de depreciação controlada, sem mudança de regra ou contrato.
- `services/api/tests/unit/recommendations/test_recommendations_metrics.py`: a fixture de integração passou a criar o vínculo `TenantUsuario` owner do usuário autenticado. Isso corrige a preparação de RBAC exigida pelo router já governado; não altera produção nem o fluxo climático.
- `docs/architecture/OPS-INTELLIGENCE-ARCH-01.md`: estado da retirada controlada atualizado.
- Este relatório.

## Validação

Resultados aprovados:

- `test_recommendation_service.py` e `test_sync_pull_recommendations.py`: **6 passed**;
- provider climático global filtrado por `-k clima`: **1 passed, 12 deselected**;
- `tests/unit/recommendations -q`: **50 passed, 33 deselected**;
- integração de recommendations, executada por arquivo para respeitar o limite do executor: métricas **6 passed**, providers **7 passed**, lifecycle **6 passed** e router/query **13 passed** — **32 passed** no total.
- `py_compile` dos dois arquivos Python alterados: aprovado.

`ruff check` foi executado nos arquivos Python alterados e apontou 69 violações já existentes (formatação, importação e linhas longas) fora das linhas introduzidas nesta etapa; nenhuma foi ocultada ou corrigida por refatoração ampla. `git diff --check` foi executado ao término.

## Limitações e recomendação

A consolidação não pode encerrar com remoção física do serviço climático enquanto o Web mantiver o endpoint e enquanto não houver paridade funcional aprovada. A arquitetura global, o scheduler, o Event/Outbox, RBAC, RLS e o lifecycle permanecem preservados. Recomenda-se encerrar o OPS-INTELLIGENCE-15 como **GO COM RESSALVAS**, registrando uma futura migração contratual do dashboard climático antes de nova tentativa de retirada.
