# PILOT-DRYRUN-02 — Execucao Assistida do Dry Run Ponta a Ponta

## 1. Resumo executivo

Execucao assistida iniciada em 2026-07-09, seguindo o runbook oficial [`docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`](/opt/lampp/htdocs/farm/docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md).

O Dry Run foi interrompido ainda no Cenário A, durante o fluxo oficial do Wizard, por falha funcional reproduzida no backend: tentativa de criar a implantacao operacional do tenant recem-criado violou a politica de RLS da tabela `wizard_implantacoes_operacionais`.

Nao houve correcao de codigo, nao houve manipulacao manual de banco e nao foi aplicado workaround fora dos fluxos oficiais.

Veredicto final desta execucao:

`DRY RUN INTERROMPIDO`

## 2. Ambiente utilizado

Data/hora de inicio: 2026-07-09 22:07:50 -03

Repositorio: `main` em `4236bc550c967a4caffa7a2fa48e75fe1b4806b4`

Estado inicial do workspace:

- ` m apps/web`
- ` M docs/pilot/RUNBOOK-01-EXECUCAO-D-5-A-D+7.md`
- `?? docs/implementation/reports/PILOT-DRYRUN-01-AUDITORIA-CONSOLIDACAO-RUNBOOK.md`

Operador tecnico: execucao assistida via Codex

Operador funcional: nao informado nesta sessao

Responsavel Campo PWA: nao informado nesta sessao

Responsavel ERP: nao informado nesta sessao

Backend validado:

- Python `3.10.12`
- import de `main` concluido com sucesso
- Alembic atual: `20260709_sankhya_legacy_gateway_login (head)`
- conexao com banco confirmada
- schema efetivo: `farms`

Frontend/Web validado:

- `http://127.0.0.1:3000/` respondeu `200`
- `http://127.0.0.1:3000/login` respondeu `200`

Campo PWA validado parcialmente:

- ambiente dev iniciou em `http://127.0.0.1:3002`
- rota principal respondeu com redirecionamento para `/home`
- runtime dev informou `PWA support is disabled`

Backend isolado para validacao tecnica:

- instancia local em `8003` respondeu `/docs` com `200`
- `/health` respondeu `200` com `{"status":"ok","database":"connected","version":"1.0.0-frota-ready"}`
- `RUN_EMBEDDED_JOBS=false` foi necessario para evitar erro de permissao de jobs embutidos neste ambiente

## 3. Commit e branch

- Branch: `main`
- Commit: `4236bc550c967a4caffa7a2fa48e75fe1b4806b4`

## 4. Participantes

- Execucao tecnica: Codex
- Aprovacao funcional: nao executada nesta sessao
- Operador Web: nao informado
- Operador Campo PWA: nao informado
- Suporte/Backoffice: nao informado
- Responsavel ERP: nao informado

## 5. Criterios de entrada

| Criterio | Resultado | Evidencia | Responsavel | Observacao |
| --- | --- | --- | --- | --- |
| Ambiente disponivel | Parcial | API local em `8003`, Web em `3000`, Campo em `3002` | Tecnico | API compartilhada em `8000` respondeu de forma intermitente entre comandos |
| Banco acessivel | OK | probe SQLAlchemy `DB_OK farms SCHEMA farms` | Tecnico | sem escrita manual |
| Migrations consistentes | OK | `alembic current` em `head` | Tecnico | sem upgrade/downgrade |
| API disponivel | OK | `/docs` e `/health` em instancia isolada | Tecnico | jobs embutidos desabilitados localmente |
| Web disponivel | OK | `curl -I /` e `/login` com `200` | Tecnico | sem login funcional via browser nesta sessao |
| Campo PWA disponivel | Parcial | app dev iniciou em `3002` | Tecnico | sem validacao offline real; modo dev desabilita suporte PWA |
| Tenant valido | OK | onboarding oficial `201` | Tecnico | tenant novo criado para Dry Run |
| Owner/Admin acessivel | OK | login e token emitidos | Tecnico | autenticacao oficial |
| Usuario operacional acessivel | Nao validado | sem credencial separada | - | nao alcancado |
| Massa minima definida | Parcial | tenant novo sem fazendas iniciais | Tecnico | sem completar estrutura por bloqueio no Wizard |
| ERP configurado ou dispensado | Nao validado | nao alcancado | - | execucao interrompida antes |
| Evidencias preparadas | OK | arquivos temporarios sanitizados em `/tmp` | Tecnico | sem segredos persistidos no relatorio |
| Responsaveis presentes | Parcial | apenas operador tecnico ativo | Tecnico | faltou operador funcional |
| Contingencia conhecida | OK | sem workaround fora do fluxo oficial | Tecnico | interrupcao registrada formalmente |

## 6. Massa de dados

Tenant de Dry Run criado pelo fluxo oficial de onboarding:

- email: `dryrun.20260709@example.com`
- username: `dryrun_20260709`
- plano: `Profissional`
- tenant_id observado no JWT: `94f5ca53-7b3e-49de-93af-d78a4488f30a`
- owner_usuario_id observado no JWT: `0a8dab7d-5af0-4240-af87-8a852a0c705d`

Snapshot inicial sanitizado:

- tenants totais observados no banco: `2220`
- fazendas iniciais do tenant novo: `0`
- unidades produtivas confirmadas para o tenant novo: nao comprovadas antes da interrupcao
- safra selecionada: nao aplicavel
- talhao selecionado: nao aplicavel
- deposito selecionado: nao aplicavel
- produtos/insumos do cenario: nao aplicavel
- jobs ERP pendentes: nao validado para o tenant novo
- eventos pendentes no Outbox: nao validado
- itens pendentes de sync Campo: nao validado

## 7. Estado inicial

Estado confirmado antes do Cenário A:

- repositório sem diff estrutural introduzido por esta execucao
- backend importavel e conectado ao banco
- onboarding oficial operacional
- login oficial operacional
- Wizard ainda nao exercitado para o tenant novo

## 8. Cenário A

Fluxo executado:

`tenant -> Owner -> onboarding -> tentativa de Wizard`

### Passos comprovados

| Passo | Interface ou endpoint | Resultado esperado | Resultado obtido | Evidencia | Status |
| --- | --- | --- | --- | --- | --- |
| Criacao de tenant/owner | `POST /api/v1/onboarding/assinante` | tenant e owner criados | `201 Created` | `/tmp/dryrun_onboarding.json` | Aprovado |
| Login do owner | `POST /api/v1/auth/login` | emissao de token | `200 OK` | `/tmp/dryrun_8003_login.json` e tokens temporarios | Aprovado |
| Inicio do Wizard via status | `GET /api/v1/wizard/status` | criar/retomar implantacao ativa | falha ao criar implantacao por RLS | `/tmp/wizard_error.log` | Falhou |

### Divergencia central

Ao consultar `wizard/status`, o backend tentou criar/retomar a implantacao ativa e falhou com:

`new row violates row-level security policy for table "wizard_implantacoes_operacionais"`

Evidencia tecnica:

- stack trace em `/tmp/wizard_error.log`
- origem principal:
  - `services/api/wizard/router.py:406`
  - `services/api/wizard/router.py:157`
  - `services/api/wizard/services.py:783`

Efeito no Dry Run:

- impossibilita materializar a implantacao operacional do tenant recem-criado
- impede seguir o fluxo oficial de Wizard
- bloqueia criacao guiada de unidade produtiva, prontidao e `READY_FOR_GO_LIVE`

### Falha controlada do Wizard

A falha controlada prevista do Wizard nao chegou a ser executada, porque o proprio fluxo base falhou antes da implantacao existir.

Classificacao:

- severidade: `P1`
- tipo: `defeito funcional`
- decisao operacional: interrupcao do Dry Run por ausencia de workaround oficial e pela necessidade de alteracao funcional para prosseguir

## 9. Cenário B

Nao executado.

Motivo:

- o runbook exige progressao pelo Cenário A
- sem implantacao operacional valida e sem estrutura minima oficial, nao houve base segura para operacao agricola, Campo PWA, consumo real, estoque e custos

## 10. Cenário C

Nao executado.

Motivo:

- dependente de estrutura produtiva e operacional nao concluida no Cenário A

## 11. Cenário D

Nao executado para o tenant de Dry Run.

Motivo:

- o tenant novo nao chegou ao ponto de configuracao operacional via Wizard
- readiness, health, timeline e diagnostico ERP do tenant novo nao foram validados

Observacao:

- a superficie ERP continua fora de suspeita nesta execucao, porque o bloqueio ocorreu antes de sua utilizacao funcional no tenant novo

## 12. Cenário E

Executado parcialmente apenas na dimensao de ambiente:

- indisponibilidade de jobs embutidos em ambiente local por `Operation not permitted`
- confirmacao de que `RUN_EMBEDDED_JOBS=false` preserva a inicializacao da API para validacao tecnica

Falhas controladas previstas de Campo, estoque, ERP, engines e Wizard nao foram executadas integralmente, porque o Dry Run foi interrompido antes.

## 13. Falhas controladas

| Falha | Como foi provocada | Resultado esperado | Resultado obtido | Recuperacao | Evidencia | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Wizard em tenant novo | chamada oficial a `GET /api/v1/wizard/status` apos onboarding | criar ou retomar implantacao ativa | erro de RLS ao inserir em `wizard_implantacoes_operacionais` | sem workaround oficial nesta execucao | `/tmp/wizard_error.log` | Falhou |
| Jobs embutidos locais | inicializacao da API com jobs embutidos | API subir integralmente | erros `Operation not permitted` nos jobs embutidos | subir API local com `RUN_EMBEDDED_JOBS=false` | logs de inicializacao | Aprovado com ressalva |

## 14. Evidencias coletadas

Arquivos temporarios sanitizados relevantes:

- `/tmp/dryrun_onboarding.json`
- `/tmp/dryrun_8003_login.json`
- `/tmp/dryrun_8003_health.txt`
- `/tmp/dryrun_8004.log`
- `/tmp/wizard_error.log`

Identificadores de evidencia adotados nesta execucao:

- `DRYRUN-A-ONBOARDING-20260709-001`
- `DRYRUN-A-LOGIN-20260709-002`
- `DRYRUN-A-WIZARD-RLS-20260709-003`
- `DRYRUN-ENV-API-HEALTH-20260709-004`

## 15. Desvios

| ID | Cenario | Passo | Resultado esperado | Resultado obtido | Evidencia | Reproduzivel | Impacto | Workaround | Componente canonico | Classificacao | Decisao |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DV-001 | A | Wizard status apos onboarding | implantacao ativa criada/retomada | erro RLS em `wizard_implantacoes_operacionais` | `/tmp/wizard_error.log` | Sim | bloqueia fluxo oficial do piloto | nenhum aceitavel sem correcao funcional | Wizard oficial | `P1 / defeito funcional` | interromper execucao |
| DV-002 | Ambiente | API local com jobs embutidos | API subir com jobs internos | `Operation not permitted` em jobs embutidos | logs de inicializacao | Sim | reduz confiabilidade do ambiente local de validacao | iniciar API local com `RUN_EMBEDDED_JOBS=false` apenas para validacao tecnica | bootstrap da API | `P2 / problema de ambiente` | registrar ressalva |
| DV-003 | Campo | suporte PWA em dev | validar PWA offline real | runtime dev informa `PWA support is disabled` | log do app Campo | Sim | impede validar instalacao PWA real neste modo | usar ambiente apropriado de teste PWA em execucao futura | Campo PWA | `P2 / limitacao conhecida` | registrar ressalva |

## 16. Classificacao P0-P3

- `P0`: nenhum comprovado nesta execucao
- `P1`: falha funcional do Wizard para tenant novo (`DV-001`)
- `P2`: limitacoes de ambiente local para jobs embutidos e PWA dev (`DV-002`, `DV-003`)
- `P3`: nenhum registrado

## 17. Incidentes

Incidente principal:

- interrupcao do Dry Run no primeiro fluxo obrigatorio de implantacao oficial

Sem incidentes de:

- vazamento de credenciais
- manipulacao manual de banco
- corrupcao observada de dados
- acesso cross-tenant

## 18. Workarounds

Workarounds aceitos apenas para validacao tecnica:

- subir API local com `RUN_EMBEDDED_JOBS=false`

Workarounds rejeitados:

- criacao manual de implantacao no banco
- ajuste direto de RLS
- marcacao manual de etapas/checklist
- pular o Wizard para continuar cenarios B-E

## 19. Limitacoes

- nao houve operador funcional humano nesta sessao
- nao houve execucao browser-driven completa do Web e do Campo
- nao houve validacao offline real do Campo em build PWA apropriada
- a API compartilhada em `8000` apresentou acessibilidade intermitente entre comandos desta sandbox
- cenarios B, C, D e E permaneceram pendentes por bloqueio no Cenário A

## 20. Estado final

Estado ao encerrar:

- tenant de Dry Run criado
- owner autenticavel
- Dry Run interrompido antes da implantacao operacional
- nenhuma correcao aplicada
- nenhum dado ajustado manualmente

## 21. Dados criados

Confirmados:

- tenant novo de Dry Run
- usuario owner associado ao tenant
- assinatura/plano vinculados pelo onboarding oficial

Nao confirmados:

- unidade produtiva
- safra
- talhao
- registros operacionais
- jobs ERP do tenant novo

## 22. Dados alterados

Alteracoes operacionais confirmadas nesta execucao:

- criacao de tenant e owner pelo fluxo oficial de onboarding

Sem alteracoes confirmadas em:

- estoque
- custos
- financeiro
- comercializacao
- ERP runtime do tenant novo

## 23. Pendencias

- auditar e corrigir a falha de RLS/fluxo do Wizard para tenant novo
- reexecutar o Dry Run a partir do Cenário A apos correcao validada
- validar o Campo PWA em ambiente apto a teste offline real
- repetir criterios de entrada com operador funcional e massa minima controlada

## 24. Recomendacao

Proxima etapa recomendada: abrir execucao de auditoria/correcao focada no Wizard oficial, com:

1. auditoria de reutilizacao do fluxo `wizard/router.py` e `wizard/services.py`
2. auditoria arquitetural das politicas de tenant/RLS aplicadas a `wizard_implantacoes_operacionais`
3. reproducao minima usando onboarding oficial seguido de `GET /api/v1/wizard/status`
4. verificacao de testes existentes em `services/api/tests/unit/wizard/test_wizard_api.py`
5. definicao de teste de regressao cobrindo tenant recem-criado sob RLS real

Nao iniciar cenarios B-E antes dessa correcao.

## 25. Veredicto

`DRY RUN INTERROMPIDO`

Fundamentacao:

- o fluxo oficial de onboarding funcionou
- o owner do tenant novo autenticou com sucesso
- o primeiro passo obrigatorio do Wizard falhou por defeito funcional reproduzivel
- prosseguir exigiria contornar o fluxo oficial ou alterar dados/codigo durante a propria execucao, o que e proibido nesta etapa

## Comandos executados

Principais comandos desta execucao:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check

cd services/api
.venv/bin/python -V
timeout 20s .venv/bin/python -c "import main; print('IMPORT_OK')"
timeout 20s .venv/bin/alembic current

curl -I http://127.0.0.1:3000/
curl -I http://127.0.0.1:3000/login
curl -I http://127.0.0.1:3002/
curl -I http://127.0.0.1:8000/docs

POST /api/v1/onboarding/assinante
POST /api/v1/auth/login
GET /api/v1/wizard/status
```

## Alteracoes documentais realizadas

Nenhuma alteracao no runbook oficial foi necessaria durante esta execucao.

Documento criado:

- [`docs/implementation/reports/PILOT-DRYRUN-02-EXECUCAO-ASSISTIDA.md`](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-DRYRUN-02-EXECUCAO-ASSISTIDA.md)
