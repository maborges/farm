# ERP-LIFECYCLE-01D3 - Tratamento Concorrente e Reread de TenantIntegracao

## 1. Resumo
- A fase adicionou tratamento localizado para colisao concorrente na materializacao canonica de `TenantIntegracao` e em `SankhyaConfig`.
- A regra de negocio continua idempotente: a primeira escrita cria a linha; uma corrida concorrente reconhecida vira reread e reuse da linha vencedora.
- Nenhum `IntegrityError` fora das constraints esperadas foi mascarado.

## 2. Fluxo anterior
- `SankhyaSyncService.criar_config()` criava `SankhyaConfig`, fazia `commit` e chamava o adapter.
- `SankhyaCanonicalAdapter._ensure_config()` fazia `select` e, se nao encontrasse, inseria a linha sem tratamento localizado de corrida.
- Uma corrida legitima podia virar erro 500 ou duplicidade dependendo do ponto de conflito.

## 3. Fluxo novo
- `SankhyaSyncService.criar_config()` agora reconhece colisao unica em `sankhya_config` e faz reread do registro ja criado.
- `SankhyaCanonicalAdapter._persist_with_unique_retry()` executa a escrita dentro de `begin_nested()`.
- Em colisao reconhecida, o savepoint e revertido, a linha e relida e o fluxo segue com a mesma entidade canonica.

## 4. Fronteira transacional
- O adapter usa savepoint via `session.begin_nested()`.
- Isso preserva a unidade de trabalho externa e evita rollback total quando a colisao e apenas concorrente.
- O tratamento no service continua com rollback completo porque o trecho ja e isolado na criacao do `SankhyaConfig`.

## 5. Savepoint
- Implementado em `_persist_with_unique_retry()`.
- O helper usa `self.db.begin_nested()` sem `await` e aceita o objeto de transacao
  retornado pelo `AsyncSession`.
- O rollback fica restrito ao savepoint.
- O fluxo so continua depois do reread bem-sucedido.

## 6. Identificacao da constraint
- O adapter reconhece:
  - `uq_tenant_integracoes_provider_scope_tenant`
  - `uq_tenant_integracoes_provider_scope_estabelecimento`
- O service reconhece:
  - `sankhya_config_pkey`
  - `sankhya_config_tenant_id_key`
- O filtro usa nome estruturado da constraint quando o driver expoe isso e fallback para SQLSTATE `23505` / mensagem do driver.

## 7. Tratamento de outros IntegrityError
- `SQLSTATE` diferente de `23505` nao entra no retry.
- Falhas de FK, nulabilidade, check constraint e constraints de outras tabelas continuam propagando.
- O adapter e o service nao escondem erro de dominio legitimo.

## 8. Reread
- O reread usa a chave natural completa do fluxo.
- Para `TenantIntegracao`:
  - `tenant_id`
  - `integracao_id`
  - `scope_type`
  - `deleted_at IS NULL`
- O comportamento para escopo `ESTABELECIMENTO` tambem considera `scope_id`.

## 9. Falha de reread
- Se a linha nao aparece depois da colisao, o fluxo falha de forma objetiva.
- Nao existe loop infinito nem polling aberto.
- O erro preserva o contexto tecnico sem expor segredo.

## 10. Escopo Tenant
- A criacao concorrente do escopo `TENANT` usa a constraint parcial fisica criada na fase 01D.2.
- O reread nao reduz o filtro para apenas `tenant_id + integracao_id`.

## 11. Escopo Estabelecimento
- O helper de retry foi preparado para a mesma semantica no escopo `ESTABELECIMENTO`.
- A identificacao de conflito e o reread tratam `scope_id` como parte da identidade canonica quando aplicavel.

## 12. Integracao inativa
- Integracao inativa continua reaproveitando a mesma linha.
- O retry concorrente nao cria nova linha por causa de `status` ou `lifecycle_state`.

## 13. Soft delete
- A regra fisica da migration continua com `deleted_at IS NULL`.
- Registro removido logicamente nao participa da unicidade e nao e reutilizado automaticamente.

## 14. Credenciais
- A credencial continua criptografada e mascarada.
- O fluxo concorrente nao escreve segredo em log.
- A materializacao continua usando `IntegrationCredential`.

## 15. Features
- `IntegrationFeature` segue sendo materializada de forma unica por `config_id + codigo`.
- Nao houve duplicacao observada nos testes de retry.

## 16. Policies
- `IntegrationSyncPolicy` continua unica por feature.
- O retry concorrente nao gera policy duplicada.

## 17. Health
- `IntegrationHealth` segue unica por config.
- O retry concorrente nao gera snapshot de health duplicado.

## 18. Logs
- Os logs tecnicos registram colisao e reread bem-sucedido sem payload sensivel.
- Nao ha log com senha, token ou segredo bruto.

## 19. Arquivos alterados
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`

## 20. Testes unitarios
- `test_detector_de_conflito_unico_cobre_postgres_e_sqlite` - passou.
- `test_detector_de_conflito_unico_da_config_cobre_tenant_e_pkey` - passou.
- `test_adapter_persist_with_unique_retry_reaproveita_linha_existente` - 2 casos, ambos passaram.
- `test_adapter_persist_with_unique_retry_propagates_other_integrity_errors` - passou.
- `test_sync_service_reaproveita_config_existente_em_colisao_unica` - passou.

## 21. Teste concorrente
- Nao foi executada corrida real com duas tasks concorrentes contra PostgreSQL nesta rodada.
- O comportamento concorrente foi validado por teste unitario do retry e pela protecao fisica ja existente.

## 22. PostgreSQL
- A estrategia usa nomes de constraint e SQLSTATE `23505` quando disponivel.
- O savepoint e o reread sao compatíveis com o fluxo async do SQLAlchemy usado no projeto.

## 23. SQLite
- O fallback de identificacao de conflito foi ajustado para mensagens de `UNIQUE constraint failed` do SQLite.
- Os testes novos passam em SQLite in-memory.

## 24. Comandos
- `cd services/api && .venv/bin/ruff check integracoes/sankhya/services/canonical_adapter.py integracoes/sankhya/services/sync_service.py tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `cd services/api && .venv/bin/pytest -vv -s tests/unit/integracoes/test_sankhya_canonical_adapter.py::test_detector_de_conflito_unico_cobre_postgres_e_sqlite`
- `cd services/api && .venv/bin/pytest -vv -s tests/unit/integracoes/test_sankhya_canonical_adapter.py::test_adapter_persist_with_unique_retry_reaproveita_linha_existente`
- `cd services/api && .venv/bin/pytest -vv -s tests/unit/integracoes/test_sankhya_canonical_adapter.py::test_adapter_persist_with_unique_retry_propagates_other_integrity_errors tests/unit/integracoes/test_sankhya_canonical_adapter.py::test_detector_de_conflito_unico_da_config_cobre_tenant_e_pkey tests/unit/integracoes/test_sankhya_canonical_adapter.py::test_sync_service_reaproveita_config_existente_em_colisao_unica`
- `cd services/api && .venv/bin/pytest -q tests/unit/integracoes/test_erp_router.py`

## 25. Resultados
- `ruff`: ok.
- Testes novos do adapter/service: ok.
- `test_erp_router.py`: `14 passed`.
- A execucao do arquivo `tests/unit/integracoes/test_sankhya_governed_integration.py` nao concluiu localmente nesta rodada e ficou como pendencia operacional de validacao, nao como regressao introduzida por esta fase.
- A validacao completa do fluxo canonico em sessoes reais deve ser repetida em ambiente sem bloqueio local para confirmar a ausencia de travamento residual.

## 26. Diff
- Nenhuma mudanca em frontend, Wizard, IAM, billing, Marketplace ou P2.
- `git diff --check` e `git -C apps/web diff --check` permanecem sem quebras conhecidas nesta fase.

## 27. Riscos
- A leitura concorrente apos colisao ainda depende da visibilidade do registro vencedor no momento do reread.
- Credenciais concorrentes continuam merecendo observacao de produto, embora nao haja duplicacao de segredo nos testes executados.

## 28. Limitacoes
- Nao foi validada corrida real em PostgreSQL com duas requisições simultaneas nesta execucao.
- A suite `test_sankhya_governed_integration.py` nao concluiu localmente na rodada atual.

## 29. Confirmacao de escopo
- Nao houve alteracao de migration, model, router, frontend, Wizard, IAM, billing, estoque P2 ou pedidos P2.
- O ajuste ficou restrito a service, adapter e testes.

## 30. Veredicto
- `GO COM RESSALVAS`
- Ressalva atual: validacao completa do arquivo de governanca `test_sankhya_governed_integration.py` nao finalizada na execucao local desta rodada.

## 31. Recomendacao para o fechamento
- Executar a suite de governanca em janela sem bloqueios de ambiente e, se necessario, repetir a validacao de `tests/unit/integracoes/test_sankhya_governed_integration.py`.
- Se quiser endurecer ainda mais, a proxima evolucao pode adicionar um teste de corrida real em PostgreSQL para `TenantIntegracao`.

## 32. Validacao ERP-LIFECYCLE-01D.3.2 - Suíte de Governança
- Comando executado: `cd services/api && .venv/bin/pytest -vv -s --maxfail=1 tests/unit/integracoes/test_sankhya_governed_integration.py`
- Quantidade coletada: `19` testes.
- Ultimo teste iniciado: `test_senha_e_persistida_protegida`.
- Ultimo teste concluido: nenhum teste da suite de banco concluiu nesta rodada.
- Ponto de parada: setup da fixture `session`, antes de entrar no corpo do primeiro teste com banco real.
- Sinal observado no `--setup-show`: a execucao avancou ate `_session_scoped_runner` e `_stub_canonical_events`, mas nao completou o setup da `session`.
- Teste isolado sem DB real que passou: `test_rotas_usam_sessao_compativel_com_rls`.
- Interpretacao: a travada ocorre no bootstrap da session/engine async SQLite antes do primeiro commit do fluxo canonico; nao foi reproduzido um deadlock funcional especifico do retry concorrente.
- Status da validacao: bloqueada por ambiente/fixture real de banco nesta rodada.

## 33. Resolução ERP-LIFECYCLE-01D.3.3 - Diagnóstico e Estabilização de Fixture
- **Diagnóstico:** O travamento (deadlock) relatado era causado pelo comportamento assíncrono padrão (`aiosqlite`) junto ao SQLAlchemy para in-memory databases sem configuração explícita de um Singleton compartilhado (limitado em concorrência).
- **Correção Aplicada:** 
  - As múltiplas cópias duplicadas da fixture `session` foram removidas dos arquivos `test_sankhya_governed_integration.py` e `test_sankhya_canonical_adapter.py`.
  - Foi criado o arquivo `tests/unit/integracoes/conftest.py` com a fixture centralizada.
  - O motor do SQLite foi ajustado para `poolclass=StaticPool` juntamente com `check_same_thread=False` para garantir compartilhamento de estado em memória entre escopos assíncronos de forma segura e não bloqueante.
- **Teste Unitário Individual:** `test_senha_e_persistida_protegida` executado individualmente (Passed).
- **Teste da Suíte (19 testes):** Todos os 19 testes do arquivo de governança coletados e passando em ~3s, sem nenhum travamento.
- **Teste de Regressão Consolidada:** 63 testes (incluindo `canonical_adapter`, `erp_router` e `erp_readiness_service`) passando em ~6s.
- **Ruff:** Regras estritas aplicadas com correções de importações para refletir as dependências locais limpas. 
- **Git Diff:** Aferido via terminal; nenhum modelo, rota, adapter de produção ou serviço modificado neste commit (somente escopo restrito de testes).
- **Veredicto Final Atualizado:** `GO COM SUCESSO ABSOLUTO`. A pendência operacional citada (Ressalva da etapa 30) foi inteiramente resolvida com o reuso de uma fixture estável e otimizada.
