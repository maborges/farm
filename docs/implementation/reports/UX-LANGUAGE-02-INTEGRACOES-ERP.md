# UX-LANGUAGE-02 — Integrações ERP

## Objetivo

Padronizar a linguagem do fluxo de integração ERP para um vocabulário mais operacional, reduzindo dependência de termos de arquitetura e infraestrutura.

## Termos encontrados e decisão

| Termo encontrado | Decisão | Nova forma principal | Justificativa |
| --- | --- | --- | --- |
| Provider | Traduzir | ERP conectado / ERP atual | Fala do sistema que o usuário conhece |
| Capability | Simplificar | Função disponível | Explica utilidade, não estrutura |
| Capability Matrix | Simplificar | Funções disponíveis | Evita jargão de arquitetura |
| Health | Traduzir | Situação da integração | Mais claro para operação |
| Policy | Traduzir | Regra de atualização | Explica finalidade prática |
| Sync | Traduzir | Atualização de dados | Linguagem mais natural ao usuário |
| Runtime canônico | Contextualizar | Fluxo principal da integração | Mantém sentido sem expor arquitetura |
| Readiness | Simplificar | Situação para o piloto | Mostra objetivo de negócio |
| Payload | Traduzir | Dados recebidos | Linguagem mais acessível |
| Reconciliation | Contextualizar | Confirmação de vínculo | Aproxima do problema real do usuário |
| Feature | Contextualizar | Área da integração / função | Menos técnico em telas |

## Mensagens antes/depois

| Antes | Depois |
| --- | --- |
| `Provider ERP configurado, mas health pendente.` | `O ERP já foi configurado, mas ainda falta validar a comunicação.` |
| `Capabilities P0 incompletas` | `Algumas funções obrigatórias para o piloto inicial ainda não estão disponíveis nesta integração.` |
| `Policies de sincronização mínimas pendentes` | `Ainda faltam regras obrigatórias para atualização dos dados.` |
| `Health crítico` | `A comunicação com o ERP apresentou falha crítica.` |
| `Capability` | `Função` |
| `Health atual` | `Situação atual` |
| `Logs enriquecidos` | `Histórico complementar` |

## Locais alterados

### Frontend

* `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
* `apps/web/src/components/integracoes/sankhya-console.tsx`
* `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`

### Backend

* `services/api/wizard/router.py`
* `services/api/integracoes/erp_readiness_service.py`
* `services/api/integracoes/sankhya/services/sync_service.py`

### Documentação

* `docs/architecture/GLOSSARIO-OFICIAL-PLATAFORMA.md`

## Impacto na UX

1. O console ERP passa a explicar a situação da integração em linguagem operacional.
2. O Wizard orienta ação prática em vez de exigir entendimento de `provider`, `health`, `capability` e `policy`.
3. O backoffice continua útil para suporte, mas com vocabulário menos técnico.
4. As respostas do backend chegam ao frontend com mensagens mais acionáveis.

## Observações

1. Nomes técnicos internos foram preservados em código, contratos e modelos.
2. Identificadores técnicos ainda aparecem quando úteis para suporte, mas com contexto textual ao redor.
3. O arquivo de glossário não existia no repositório e foi criado no caminho solicitado para formalizar a padronização.

## Validações executadas

* `npm run typecheck`
* `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_erp_readiness_service.py services/api/tests/unit/wizard/test_wizard_checklist_engine.py -q`
* `git diff --check`
