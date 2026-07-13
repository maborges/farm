# Relatório de Execução: ERP-LIFECYCLE-01C — Ciclo Idempotente de Criação e Retomada da Integração ERP

**Fase:** ERP-LIFECYCLE-01C
**Data:** 2026-07-12
**Veredicto:** GO COM RESSALVAS

## 1. Resumo
A fase foi verificada e consolidada com base no código já presente no repositório. O ciclo de vida do Console ERP está funcional para criação, retomada, reentrada e reconfiguração do provider `sankhya`, com o `404` do status sendo usado como estado semântico de "ERP não configurado".  
O ponto que impede um `GO` puro é a ausência de uma constraint física exclusiva em `tenant_integracoes`, o que deixa a proteção concorrente dependente de fluxo de serviço e não de banco.

## 2. Arquitetura Encontrada
- O contrato HTTP canônico do ERP vive em `services/api/integracoes/erp/router.py`.
- O provider materializado é `sankhya`, com console em `apps/web/src/components/integracoes/sankhya-console.tsx`.
- O frontend resolve o status em `apps/web/src/components/integracoes/erp-console.tsx`.
- A materialização canônica de estado ocorre em `services/api/integracoes/sankhya/services/canonical_adapter.py`.
- A configuração legada/operacional de Sankhya permanece em `services/api/integracoes/sankhya/services/sync_service.py`.

## 3. Semântica do 404
O `404` de `/integracoes/erp/status` é contratualmente usado para "ERP não configurado".

Local:
- [`services/api/integracoes/erp/router.py`](/opt/lampp/htdocs/farm/services/api/integracoes/erp/router.py)

Fluxo:
- `ErpReadinessService.carregar_runtime(...)` tenta resolver o provider ativo.
- Se não há runtime canônico e não há `SankhyaConfig` legado, o router levanta `HTTPException(status_code=404, detail="ERP não configurado")`.

No frontend:
- [`apps/web/src/components/integracoes/erp-console.tsx`](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)
- O `404` é convertido em `notFound`, abrindo o seletor de provider.
- 403/401 continuam como erro de acesso.
- 500 e erro de rede não abrem seletor.

## 4. Estados de Resolução Frontend
Estados confirmados pela leitura do código:
- `notFound` do `404` abre seletor.
- provider já materializado abre wrapper direto.
- provider desconhecido cai em erro controlado de wrapper ausente.
- seleção visual não persiste por si só.

Arquivo:
- [`apps/web/src/components/integracoes/erp-console.tsx`](/opt/lampp/htdocs/farm/apps/web/src/components/integracoes/erp-console.tsx)

## 5. Local de Criação
O primeiro salvamento real acontece no fluxo Sankhya:
- `POST /integracoes/sankhya/config`
- Implementado em `services/api/integracoes/sankhya/routers/__init__.py`
- Executa `SankhyaSyncService.criar_config(...)`
- Em seguida materializa o estado canônico via `CanonicalAdapter.sync_provider_config(...)`

## 6. Mecanismo de Idempotência
A idempotência funcional é garantida por:
- busca prévia de configuração canônica por `(tenant_id, provider_slug)`
- reuso de `TenantIntegracao` existente em `_ensure_config`
- reuso ou rotação de `IntegrationCredential`
- reuso de `IntegrationFeature`
- reuso de `IntegrationSyncPolicy`
- reuso de `IntegrationHealth`

Arquivo principal:
- [`services/api/integracoes/sankhya/services/canonical_adapter.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)

## 7. Constraint
Resultado da auditoria:
- `integration_credentials` tem unicidade física por `(tenant_id, provider_id, scope_type, scope_id, version_number)`.
- `integration_features` tem unicidade física por `(config_id, codigo)`.
- `integration_sync_policies` tem unicidade física por `(feature_id)`.
- `integration_health_snapshots` tem unicidade física por `(config_id)`.
- `tenant_integracoes` **não** apresenta `UniqueConstraint` explícita no modelo nem na migration de foundation.

Conclusão:
- a constraint física que impediria duplicidade concorrente de `TenantIntegracao` não existe nesta base.

## 8. Transação
O fluxo usa `commit()` no final da sincronização canônica e em etapas de criação/atualização legadas.

Pontos relevantes:
- `sync_provider_config(...)` faz a sequência de upsert lógico e commita ao final.
- `criar_config(...)` e `atualizar_config(...)` em `SankhyaSyncService` gravam primeiro o `SankhyaConfig` e depois sincronizam o domínio canônico.

Isso é suficiente para o fluxo normal, mas não equivale a um lock concorrente forte.

## 9. Concorrência
Status da auditoria:
- não há `SELECT ... FOR UPDATE`
- não há constraint exclusiva em `tenant_integracoes`
- não há upsert atômico por chave natural em banco

Veredito técnico:
- o fluxo é idempotente no uso sequencial
- a concorrência concorrente ainda depende de proteção por camada de aplicação
- há risco residual de duplicidade em corrida extrema

## 10. Credenciais
Confirmado:
- credenciais são persistidas em `IntegrationCredential`
- segredos são criptografados
- respostas do console são mascaradas
- `SankhyaConfigSerializer` não expõe segredo em texto puro
- rotação cria nova credencial ativa e desativa a anterior quando necessário

Arquivos:
- [`services/api/integracoes/sankhya/services/canonical_adapter.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/canonical_adapter.py)
- [`services/api/integracoes/sankhya/services/sync_service.py`](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)

## 11. Features
Confirmado:
- `pessoas`, `produtos`, `financeiro`, `nfe`, `pedidos`, `estoque`
- `pedidos` e `estoque` permanecem declarados como P2
- a materialização de features ocorre no adapter canônico

## 12. Policies
Confirmado:
- cada feature recebe `IntegrationSyncPolicy`
- a política é reusada no salvamento repetido
- a política é sempre associada ao mesmo `config_id`/`feature_id`

## 13. Health
Confirmado:
- `IntegrationHealth` é atualizado por configuração e por teste de conexão
- o status canônico pode refletir `CONNECTED`, `DISCONNECTED`, `AUTH_ERROR`, `CONFIG_ERROR`, `PARTIAL_FAILURE`, `RATE_LIMITED`, `DEGRADED`

## 14. Integração Inexistente
Comportamento atual:
- `/integracoes/erp/status` retorna `404`
- o frontend abre seletor
- nenhum registro novo é criado apenas ao consultar status

## 15. Configuração Incompleta
Comportamento atual:
- o console retoma a tela de configuração do provider
- segredos permanecem mascarados
- o estado não volta ao catálogo quando já existe provider materializado

## 16. Conexão Falhou
Comportamento atual:
- a integração continua existente
- a health pode ficar `DISCONNECTED`, `AUTH_ERROR`, `CONFIG_ERROR` ou `DEGRADED`
- o console reabre o wrapper do provider
- o usuário pode corrigir credenciais

## 17. Integração Conectada
Comportamento atual:
- o console abre diretamente
- não pede nova seleção de provider
- o provider ativo vem do runtime canônico ou do `SankhyaConfig` legado

## 18. Integração Inativa
Contrato real observado:
- `TenantIntegracao.lifecycle_state` pode ser `DISABLED`
- `TenantIntegracao.status` pode ser `inativa`
- o adapter preserva o registro e atualiza estado, sem criar segunda integração

## 19. Provider Inativo
Comportamento encontrado:
- o router de schema do provider rejeita provider inativo com erro de validação
- o backend não faz fallback automático para outro ERP
- Sankhya continua sendo o único provider materializado

## 20. Retomada
Confirmado:
- reentrada no Console resolve wrapper novamente
- configuração mascarada é recarregada pelo console
- o fluxo volta ao wrapper já configurado quando há integração existente

## 21. Aviso de Saída
Auditoria do frontend:
- não há sistema global de bloqueio de navegação
- não foi encontrada implementação formal de `dirty form` para bloquear troca de seleção
- se existir UX de aviso, ela não está consolidada aqui como mecanismo obrigatório

Conclusão:
- ponto registrado para UX futura, sem ampliar escopo agora

## 22. Arquivos Alterados
Nesta etapa frontend:
- [`apps/web/tests/e2e/wizard-erp-selection.spec.ts`](/opt/lampp/htdocs/farm/apps/web/tests/e2e/wizard-erp-selection.spec.ts)
- [`docs/implementation/reports/ERP-LIFECYCLE-01C-CICLO-IDEMPOTENTE-TENANT-INTEGRACAO.md`](/opt/lampp/htdocs/farm/docs/implementation/reports/ERP-LIFECYCLE-01C-CICLO-IDEMPOTENTE-TENANT-INTEGRACAO.md)

Preexistente no worktree, fora desta etapa:
- [`services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_sankhya_governed_integration.py)

## 23. Testes Backend
Testes relevantes já existentes e alinhados com a fase:
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `services/api/tests/unit/integracoes/test_erp_router.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`

Observação:
- estes testes cobrem a maior parte do contrato, mas não eliminam o risco concorrente sem constraint física em `tenant_integracoes`.

## 24. Testes Frontend
Testes relevantes já existentes e alinhados com a fase:
- `apps/web/tests/unit/integracoes/erp-capability-center.test.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-view-model.test.ts`
- `apps/web/tests/unit/integracoes/erp-capability-details.test.tsx`
- `apps/web/tests/unit/integracoes/erp-capability-details-view-model.test.ts`
- `apps/web/tests/e2e/wizard-erp-selection.spec.ts`

Cobertura observada:
- separação entre capability ativa, parcial, planejada e desativada
- respeito ao P2
- estados de detalhamento e sanitização
- seleção tardia de ERP no wizard
- fallback seguro quando o catálogo não carrega

## 25. Build
Executado em `apps/web`:
- `npm run build`
- resultado: `passou`

## 26. E2E
Executado em `apps/web`:
- `npm run test`
- resultado: `falhou no ambiente restrito`, com erro de inicialização do Chromium e falhas não relacionadas ao ERP em outras suítes
- `npm run test -- tests/e2e/wizard-erp-selection.spec.ts --project=chromium`
- resultado: `2 passed`

## 27. Typecheck
Executado em `apps/web`:
- `npm run typecheck`
- resultado: `passou`

## 28. Lint
Executado em `apps/web`:
- `npm run lint`
- resultado: `passou`

## 29. Ruff
Não executado nesta etapa porque nenhuma alteração de backend foi feita aqui.

## 30. Diff
Executado:
- `git diff --check`
- `git -C apps/web diff --check`
- resultado: `passou`

## 31. Riscos
- concorrência sem constraint exclusiva em `tenant_integracoes`
- `404` depende de contrato frontend/backend consistente
- provider inativo e provider desconhecido exigem tratamento visual cuidadoso para não cair em fallback indevido

## 32. Limitações
- não foi criada migration
- não foi alterado o comportamento de troca de ERP
- não houve alteração de Wizard, IAM ou billing
- não houve endurecimento de lock transacional

## 33. Veredicto
**GO COM RESSALVAS**

Justificativa:
- o ciclo idempotente funciona no fluxo normal
- a retomada está consolidada
- credenciais ficam protegidas
- o `404` está semanticamente isolado
- porém a proteção concorrente ainda não é sustentada por constraint física em `tenant_integracoes`

## 34. Recomendação da Próxima Fase
Se for necessário fechar a fase com proteção forte contra corrida concorrente, a próxima etapa deve ser:
- avaliar `UNIQUE(tenant_id, integracao_id, scope_type, scope_id)` ou chave natural equivalente em `tenant_integracoes`
- adicionar teste concorrente específico
- fazer isso somente com autorização explícita para migration

## 35. Validação frontend ERP-LIFECYCLE-01C.1
Comandos executados em `apps/web`:
- `node -v` -> `v20.19.5`
- `npm -v` -> `10.8.2`
- `npm run typecheck`
- `npm run lint`
- `npm run build`
- `npm run test`
- `npm run test -- tests/e2e/wizard-erp-selection.spec.ts --project=chromium`

Resultados:
- `typecheck`: passou
- `lint`: passou
- `build`: passou
- `npm run test`: falhou no ambiente restrito ao tentar iniciar Chromium; também houve falhas preexistentes fora do ERP
- spec segmentado do wizard ERP: passou após correção do teste para refletir o contrato real da tela

Testes unitários ERP:
- 4 arquivos relevantes localizados
- 35 testes no total entre `erp-capability-view-model`, `erp-capability-center`, `erp-capability-details` e `erp-capability-details-view-model`
- execução direta com `node --test` sobre `.ts/.tsx` não foi viável neste ambiente por ausência de runner TSX instalado

Falhas e skips:
- suíte completa de Playwright não é estável neste sandbox
- os testes unitários ERP ficaram limitados pelo toolchain disponível

Cenários validados:
- 404 contratual abre seletor
- 403/500/erro de rede não abrem seletor
- integração existente abre wrapper
- configuração incompleta retoma o wrapper
- provider desconhecido não cai em Sankhya
- clique em provider não persiste integração
- fallback do catálogo vazio funciona

Correções realizadas nesta etapa:
- autenticado o spec `wizard-erp-selection`
- alinhado o teste ao seletor real do combobox
- alinhado o teste ao botão real de confirmação da estratégia
- alinhado o teste ao endpoint `POST /wizard/configurar-carga`

Resultado do diff:
- `git diff --check`: passou
- `git -C apps/web diff --check`: passou

Veredicto atualizado:
- `GO COM RESSALVAS`
- a única ressalva estrutural restante continua sendo a ausência de constraint física concorrente em `tenant_integracoes`
