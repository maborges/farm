# ERP-P0-04 — Readiness Service ERP

## Resumo executivo

Esta execução consolidou a prontidão operacional de ERP em um único ponto de decisão no backend.

Antes, o `CHECK_INTEGRACAO_ERP` do Wizard concentrava a regra de prontidão. Agora essa regra foi extraída para `ErpReadinessService`, e o Wizard passou a consumir o resultado consolidado em vez de recalcular a lógica principal.

O resultado final mantém o runtime oficial como fonte operacional única para provider, health, capabilities, policies e reconciliação.

## Arquivos auditados

### Wizard e prontidão

- `services/api/wizard/checklist_engine.py`
- `services/api/wizard/router.py`
- `services/api/tests/unit/wizard/test_wizard_checklist_engine.py`
- `services/api/tests/unit/wizard/test_wizard_api.py`

### Integrações e Sankhya

- `services/api/integracoes/models.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

### Relatórios de referência

- `docs/implementation/reports/ERP-P0-02-CHECK-INTEGRACAO-ERP-CAPABILITIES.md`
- `docs/implementation/reports/ERP-P0-03-CONSOLE-ERP-PROVIDER-READINESS.md`

## Arquivos alterados

- `services/api/integracoes/erp_readiness_service.py`
- `services/api/wizard/checklist_engine.py`
- `services/api/tests/unit/integracoes/test_erp_readiness_service.py`
- `services/api/tests/unit/wizard/test_wizard_checklist_engine.py`

## Onde a regra estava antes

A regra de prontidão ERP estava concentrada no `ChecklistEngine`, especialmente no fluxo de `CHECK_INTEGRACAO_ERP`.

Esse fluxo carregava provider, health, features, policies, links pendentes e conflitos diretamente no engine do Wizard, o que criava duplicidade conceitual com a leitura de prontidão já disponível no runtime oficial do módulo de integrações.

## Como foi consolidada

Foi criado `ErpReadinessService`, responsável por:

- carregar o runtime oficial do ERP para o tenant;
- avaliar provider configurado;
- avaliar health;
- avaliar capabilities P0;
- avaliar policies mínimas;
- avaliar conflitos e reconciliação pendente;
- retornar um status único: `DISPENSADO`, `PENDENTE`, `ATENDIDO` ou `FALHOU`.

O `ChecklistEngine` agora apenas:

- chama o serviço;
- converte o resultado em `ChecklistEvaluation`;
- preserva o texto e o CTA oficial.

## Como o Wizard passou a consumir o serviço

O item `CHECK_INTEGRACAO_ERP` passou a usar `ErpReadinessService.avaliar_runtime(...)` como ponto central da decisão.

O engine não recalcula mais a regra principal. Ele apenas transforma o resultado consolidado no status de checklist esperado pelo Wizard.

## Duplicidades evitadas

- duplicidade de regra entre Wizard e serviço de prontidão;
- duplicidade de leitura de provider/health/capabilities/policies;
- duplicidade de cálculo de reconciliação pendente e conflito;
- duplicidade de contrato de prontidão entre Wizard e runtime de integrações;
- dependência do Wizard em classes do pacote `wizard` dentro do próprio serviço de prontidão, o que evitava um ciclo de importação.

## Confirmação da auditoria Gateway Sankhya

A revisão dos artefatos de Sankhya confirmou que o provider atual continua baseado em Gateway, com autenticação via `/authenticate` e credenciais mascaradas nos contratos e respostas de configuração.

A consolidação não alterou adapter, gateway, schemas ou runtime.

## Testes executados

### Suíte focada na consolidação

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_erp_readiness_service.py services/api/tests/unit/wizard/test_wizard_checklist_engine.py services/api/tests/unit/wizard/test_wizard_api.py -q
```

Resultado: `51 passed`

### Validação estrutural

```bash
git diff --check
```

Resultado: sem diferenças de formatação.

### Suíte ampla de integrações

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q
```

Resultado: 4 falhas fora do escopo desta execução:

- `test_sankhya_permanece_classificado_como_erp` esperou o texto `Integração Sankhya` na página de console;
- 3 falhas em `test_openweather_domain.py` relacionadas à ausência da tabela `unidades_produtivas` no cenário SQLite do teste.

Essas falhas não vieram do serviço de prontidão novo e não foram alteradas nesta execução.

## Lacunas remanescentes

- o Console ERP ainda pode consumir o runtime consolidado em uma etapa posterior, se desejado;
- a suíte ampla de integrações ainda possui falhas pré-existentes fora do escopo desta consolidação;
- o engine do Wizard ainda mantém funções auxiliares antigas de ERP em partes do arquivo, mas a regra principal já foi centralizada no serviço novo.

## Veredicto final

**CONSOLIDAÇÃO APLICADA COM SUCESSO.**

O backend passou a ter um ponto único de decisão para a prontidão ERP. O Wizard delega a regra principal ao serviço consolidado, sem nova tabela, migration, endpoint ou runtime paralelo.
