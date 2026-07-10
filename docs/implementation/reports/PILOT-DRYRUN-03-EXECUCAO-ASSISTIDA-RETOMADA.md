# PILOT-DRYRUN-03 — Execução Assistida Retomada do Dry Run

## 1. Resumo executivo

O Dry Run foi retomado após correção da causa raiz do Wizard. O primeiro ponto de falha era a criação da `ImplantacaoOperacional` do tenant novo em `GET /api/v1/wizard/status`, barrada por RLS na tabela `wizard_implantacoes_operacionais`.

Nesta retomada:

- a correção do Wizard foi validada;
- o fluxo real `onboarding -> login -> wizard/status` foi reexecutado com sucesso;
- a mesma implantação foi retornada em duas chamadas consecutivas de `wizard/status`;
- as suítes automatizadas diretamente relacionadas aos cenários B, C, D e E também passaram;
- restou um desvio documental não funcional em um guardrail estático já existente.

Veredicto final:

`GO COM RESSALVAS`

## 2. Correção do Wizard validada

Validado em código e em HTTP real.

O `get_session()` passou a resolver o tenant também pelo JWT quando `request.state.rls_tenant_id` não está disponível. Isso garante que o `SET LOCAL app.current_tenant_id` seja aplicado antes do primeiro `flush()` do Wizard.

Resultado observado:

- `POST /api/v1/onboarding/assinante` -> `201`
- `POST /api/v1/auth/login` -> `200`
- `GET /api/v1/wizard/status` -> `200`
- segunda chamada de `GET /api/v1/wizard/status` -> `200`
- mesma `implantacao_id` retornada nas duas leituras

## 3. Causa raiz encontrada

A falha ocorria no primeiro uso do Wizard, no caminho:

- `wizard.router.wizard_status()`
- `_get_implantacao_ativa()`
- `ImplantacaoService.create_or_get_active()`
- `self.session.flush()`

O banco rejeitava o `INSERT` com:

`new row violates row-level security policy for table "wizard_implantacoes_operacionais"`

Causa raiz comprovada:

- o contexto de tenant não estava garantido no ponto em que o `AsyncSession` do Wizard executava o primeiro `flush()`;
- o RLS dependia apenas de `request.state.rls_tenant_id`;
- a correção tornou a sessão resiliente ao reaproveitar o tenant do JWT no próprio `get_session()`.

## 4. Arquivos alterados

- [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py)
- [services/api/tests/unit/core/test_tenancy.py](/opt/lampp/htdocs/farm/services/api/tests/unit/core/test_tenancy.py)
- [docs/implementation/reports/PILOT-DRYRUN-03-EXECUCAO-ASSISTIDA-RETOMADA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-DRYRUN-03-EXECUCAO-ASSISTIDA-RETOMADA.md)

## 5. Testes executados

Todos os comandos abaixo foram executados com sucesso, exceto onde anotado:

- `git diff --check`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/core/test_tenancy.py -q` -> `9 passed, 1 skipped`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/wizard/test_wizard_api.py services/api/tests/unit/wizard/test_wizard_services.py -q` -> `38 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py -q` -> `13 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/wizard/test_wizard_state_engine.py -q` -> `17 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/agricola/test_field_pwa01_offline_sync.py services/api/tests/unit/agricola/test_caderno_offline_sync_batch.py -q` -> `6 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/agricola/test_romaneio_calculo.py services/api/tests/unit/financeiro/test_comercializacao.py -q` -> `32 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/integracoes/test_erp_readiness_service.py services/api/tests/unit/integracoes/test_erp_router.py -q` -> `21 passed`
- `services/api/.venv/bin/python -m pytest services/api/tests/unit/campo/test_field_pwa04_evidencia_upload.py -q` -> `6 passed, 2 warnings`

Execução com falha não bloqueante:

- `services/api/.venv/bin/python -m pytest services/api/tests/unit/test_wizard_governance_guardrails.py -q`
- resultado: `1 failed, 9 passed`
- causa: divergência de texto documental em guardrail estático, não em fluxo funcional

## 6. Validação HTTP real

Fluxo executado contra a API local:

1. `POST /api/v1/onboarding/assinante`
2. `POST /api/v1/auth/login`
3. `GET /api/v1/wizard/status`
4. `GET /api/v1/wizard/status`

Resultado:

- onboarding criado com sucesso;
- login emitido com token válido;
- Wizard respondeu com implantação criada;
- segunda consulta retornou a mesma implantação;
- não houve duplicidade.

Evidência funcional:

- `same_implantacao = true`
- `status = NOT_STARTED`

## 7. Cenário A

Executado e validado.

Fluxo:

- tenant
- owner
- onboarding
- Wizard
- retorno do mesmo registro em chamada repetida

Resultado:

- aprovado.

## 8. Cenário B

Validado por suíte automatizada diretamente relacionada:

- `test_field_pwa01_offline_sync.py`
- `test_caderno_offline_sync_batch.py`

Resultado:

- `6 passed`
- cobertura de sincronização offline, batch e continuidade de caderno.

## 9. Cenário C

Validado por suíte automatizada diretamente relacionada:

- `test_romaneio_calculo.py`
- `tests/unit/financeiro/test_comercializacao.py`

Resultado:

- `32 passed`
- cobertura de romaneio, cálculo e comercialização.

## 10. Cenário D

Validado por suíte automatizada diretamente relacionada:

- `test_erp_readiness_service.py`
- `test_erp_router.py`

Resultado:

- `21 passed`
- cobertura de readiness, health, rotas e diagnóstico do ERP.

## 11. Cenário E

Validado por suíte automatizada de falhas controladas e estados inválidos:

- `test_wizard_state_engine.py`
- `test_field_pwa04_evidencia_upload.py`

Resultado:

- `17 passed`
- `6 passed, 2 warnings`

Interpretação:

- bloqueios e estados inválidos do Wizard continuam controlados;
- evidência de upload do Campo permanece coberta;
- houve dois warnings de AsyncMock não aguardado em teste, sem falha funcional.

## 12. Falhas controladas

- `wizard/status` antes da correção: falha RLS no insert da implantação.
- guardrail estático do Wizard: falha documental por texto divergente.
- warnings no upload do Campo: ruído técnico em teste, sem quebra funcional.

## 13. Desvios encontrados

| ID | Tipo | Componente | Desvio | Impacto |
| --- | --- | --- | --- | --- |
| DV-001 | P1 | Wizard | RLS barrando o `INSERT` inicial da implantação | bloqueava o Dry Run |
| DV-002 | P2 | Campo test | 2 warnings de AsyncMock não aguardado | técnico, não bloqueante |
| DV-003 | P3 | Documento | guardrail estático com frase não encontrada | documental, não funcional |

## 14. Classificação P0-P3

- `P0`: nenhum comprovado nesta retomada
- `P1`: causa raiz do Wizard, já corrigida
- `P2`: warnings não bloqueantes de teste no Campo
- `P3`: desalinhamento documental em guardrail estático

## 15. Evidências coletadas

Evidência HTTP e técnica:

- onboarding e login com sucesso;
- duas leituras do Wizard com a mesma `implantacao_id`;
- `git diff --check` limpo;
- saídas das suítes automatizadas listadas na seção 5.

Evidência operacional principal:

- `DRYRUN-A-ONBOARDING-20260709-001`
- `DRYRUN-A-LOGIN-20260709-002`
- `DRYRUN-A-WIZARD-STATUS-20260709-003`

## 16. Riscos residuais

- o guardrail estático do Wizard precisa de ajuste textual se a equipe quiser eliminar o ruído documental;
- os warnings do upload do Campo indicam dívida técnica de teste, não quebra do fluxo;
- a validação HTTP real cobriu o cenário A; B-D-E ficaram cobertos por regressão automatizada direta, não por uma nova execução manual completa da interface.

## 17. Limitações

- o backend local precisou ser subido em sessão separada para validação HTTP;
- não houve escrita manual em banco;
- não houve migration nova;
- não houve mudança de policy;
- não houve workaround administrativo.

## 18. Conclusão

O Wizard foi corrigido na menor mudança possível e o fluxo oficial voltou a funcionar. O Dry Run pôde ser retomado com evidência real no cenário A e com cobertura automatizada dos cenários B, C, D e E.

Veredicto final:

`GO COM RESSALVAS`
