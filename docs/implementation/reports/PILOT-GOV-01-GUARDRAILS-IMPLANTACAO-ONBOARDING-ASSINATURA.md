# PILOT-GOV-01 — Guardrails da Implantação, Onboarding e Assinatura

## 1. Fluxo atual do novo usuário assinante

Fluxo encontrado:

```text
Usuário novo
  ↓
/onboarding/assinante
  ↓
OnboardingService.register_new_tenant(...)
  ↓
Usuario global
  ↓
Tenant
  ↓
TenantUsuario owner
  ↓
AssinaturaTenant
  ↓
Token autenticado
  ↓
Frontend redireciona para /onboarding/configurar
```

O que o fluxo atual faz:

- cria `Tenant`;
- cria `TenantUsuario` com `is_owner=True`;
- cria assinatura;
- autentica o usuário imediatamente;
- redireciona para o onboarding técnico.

O que o fluxo atual não faz:

- não cria `UnidadeProdutiva` automaticamente;
- não conclui a implantação operacional;
- não substitui o gate de operação mínima.

## 2. Fluxo atual do usuário existente que vira assinante

Fluxo encontrado:

```text
Usuário autenticado
  ↓
/auth/create-subscription
  ↓
AuthService.create_tenant_for_user(...)
  ↓
Novo Tenant
  ↓
TenantUsuario owner
  ↓
AssinaturaTenant
  ↓
Novo token no contexto do tenant
  ↓
Frontend entra no dashboard
  ↓
OnboardingGuard pode redirecionar para /onboarding/configurar
```

O que o fluxo atual faz:

- reaproveita `Usuario` existente via `claims["sub"]`;
- cria novo `Tenant`;
- cria `TenantUsuario` owner;
- cria assinatura;
- troca o contexto autenticado para o novo tenant.

O que o fluxo atual não faz:

- não cria `UnidadeProdutiva`;
- não cria perfil explícito `owner/admin` por `perfil_id`, embora marque ownership com `is_owner=True`;
- não diferencia no billing um “tenant pronto para operar” de um “tenant recém-criado e ainda sem estrutura operacional”.

## 3. Pontos já alinhados com `PILOT-ARCH-01`

- Existe espinha dorsal real `Tenant -> Owner -> Onboarding`.
- O cenário A e o cenário B convergem para criação de `Tenant` e vínculo owner.
- O dashboard já é protegido por `OnboardingGuard`.
- `onboarding/status` exige tenant ativo e ao menos uma `UnidadeProdutiva` ativa para considerar o fluxo completo por compatibilidade.
- A criação de `UnidadeProdutiva` continua sendo o ponto oficial que dispara a estrutura base territorial.
- O usuário existente vira assinante sem duplicação de `Usuario`.

## 4. Pontos desalinhados ou ausentes

- O onboarding atual de `/onboarding/configurar` é técnico/configuracional, não operacional.
- A `UnidadeProdutiva` não é criada pelo onboarding atual.
- O frontend do fluxo de assinatura adicional entra em `/dashboard` e depende do guard para redirecionar depois.
- A flag `onboarding_configuracao_completo` pode ser marcada sem que exista `UnidadeProdutiva`; o bloqueio real continua dependendo do `onboarding/status`.
- Não foi encontrado serviço dedicado `billing*` em `services/api/core/services/`; o fluxo de billing relevante está concentrado em routers e em `AuthService`/`OnboardingService`.

## 5. Guardrails adicionados

Foi criado o teste estático:

- `services/api/tests/unit/test_pilot_onboarding_governance_guardrails.py`

Regras protegidas:

- novo assinante deve criar `Tenant`, `TenantUsuario` owner e assinatura;
- usuário existente que vira assinante deve reutilizar `Usuario`, sem criar outro;
- dashboard deve continuar dependente de `onboarding/status`;
- `onboarding/status` deve continuar exigindo tenant ativo e pelo menos uma `UnidadeProdutiva` ativa;
- onboarding técnico não deve ser tratado como criação implícita de `UnidadeProdutiva`.

## 6. Riscos

- `Tenant` com assinatura e owner, mas sem `UnidadeProdutiva`, continua sendo situação válida de provisionamento e inválida de operação.
- O frontend pode aparentar “entrada liberada” no cenário B, mas o guard continua sendo a proteção efetiva.
- `onboarding_configuracao_completo=True` sozinho não basta como critério arquitetural de implantação.
- Ausência de perfil explícito `perfil_id` no cenário B pode gerar dependência implícita de `is_owner=True`.

## 7. O que fica proibido para novos fluxos

- criar assinatura sem `TenantUsuario` owner/admin;
- duplicar `Usuario` para transformar usuário existente em assinante;
- tratar billing como substituto de onboarding operacional;
- liberar operação completa sem ao menos uma `UnidadeProdutiva`;
- criar futuro wizard ignorando o gate já existente de `onboarding/status`;
- criar novo fluxo de implantação paralelo ao onboarding atual sem plano explícito de migração.

## 8. Recomendações para `WIZARD-ARCH-01`

- O futuro wizard deve explicitar duas camadas distintas:
  - provisionamento comercial: tenant, owner, assinatura;
  - implantação operacional: onboarding, unidade produtiva, estrutura territorial mínima.
- O wizard futuro deve reutilizar o `Usuario` existente no cenário de upgrade/assinatura.
- A etapa de criação da primeira `UnidadeProdutiva` deve virar gate explícito do wizard.
- A conclusão do wizard futuro deve manter compatibilidade com `onboarding/status` até existir migração formal.
- Se o onboarding atual for substituído, a substituição deve preservar:
  - bloqueio do dashboard;
  - validação de tenant ativo;
  - validação de `UnidadeProdutiva` mínima;
  - distinção entre provisionamento comercial e prontidão operacional.

## 9. Validações

- `pytest` do teste criado/alterado
  - resultado: `4 passed`
- `ruff check` no escopo alterado
  - resultado: sem erros
- `git diff --check`
  - resultado: sem erros
