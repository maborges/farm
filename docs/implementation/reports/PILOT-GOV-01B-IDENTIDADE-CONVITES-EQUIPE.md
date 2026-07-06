# PILOT-GOV-01B — Identidade Global, Convites, Acesso a Tenants e Governança da Equipe

## 1. Arquitetura oficial documentada

Conclusão objetiva: a implementação atual confirma a arquitetura de identidade global do AgroSaaS.

O desenho oficial encontrado na codebase é:

```text
Pessoa (domínio oficial futuro)
        │
Usuario
        │
        ├───────────────┐
        │               │
TenantUsuario      TenantUsuario
Tenant A           Tenant B
        │               │
UnidadeProdutivaUsuario
```

Leitura arquitetural:

- `Usuario` pertence à plataforma;
- `Tenant` representa o ambiente/conta operacional;
- o vínculo de acesso ao ambiente existe por `TenantUsuario`;
- o escopo operacional por fazenda/unidade produtiva existe por `UnidadeProdutivaUsuario`;
- o Owner é um caso especial de `TenantUsuario` com `is_owner=True`;
- convites concedem acesso ao tenant e, opcionalmente, às unidades produtivas, mas não criam identidade paralela.

## 2. Cenário A — Novo usuário assinante

Fluxo auditado:

```text
Usuário novo
  ↓
Assinatura
  ↓
Tenant
  ↓
TenantUsuario (Owner)
  ↓
Onboarding
  ↓
Primeira UnidadeProdutiva
  ↓
Operação
```

Evidências:

- `/onboarding/assinante`;
- `OnboardingService.register_new_tenant(...)`;
- criação de `Usuario`;
- criação de `Tenant`;
- criação de `TenantUsuario` com `is_owner=True`;
- criação de `AssinaturaTenant`;
- frontend redireciona para `/onboarding/configurar`.

Conclusão:

- o cenário A está alinhado com a arquitetura oficial;
- o onboarding atual não cria a `UnidadeProdutiva`, mas a operação não é liberada sem ela.

## 3. Cenário B — Usuário existente torna-se assinante

Fluxo auditado:

```text
Usuário existente
  ↓
Nova assinatura
  ↓
Novo Tenant
  ↓
TenantUsuario (Owner)
  ↓
Onboarding
  ↓
Primeira UnidadeProdutiva
```

Evidências:

- `/auth/create-subscription`;
- `AuthService.create_tenant_for_user(...)`;
- reaproveitamento de `claims["sub"]`;
- criação de novo `Tenant`;
- criação de `TenantUsuario` com `is_owner=True`;
- novo token no contexto do tenant recém-criado.

Conclusão:

- o usuário existente não é duplicado para virar assinante;
- o cenário B converge para a mesma espinha dorsal do cenário A.

## 4. Cenário C — Administrador convida usuário existente

Fluxo auditado:

```text
Administrador
  ↓
Convite
  ↓
Usuário existente faz login
  ↓
Aceita convite
  ↓
TenantUsuario
  ↓
Perfil
  ↓
UnidadesProdutivas
  ↓
Operação
```

Evidências:

- `/team/invite`;
- `/onboarding/convites/{token}`;
- `/onboarding/convites/aceitar`;
- `OnboardingService.aceitar_convite(...)`.

Comportamento encontrado:

- o convite é emitido por e-mail;
- se o usuário já existe, o fluxo orienta login e aceite;
- o aceite cria `TenantUsuario` se ainda não existir;
- o aceite cria `UnidadeProdutivaUsuario` para as unidades produtivas do convite, se houver;
- o sistema evita vínculo duplicado.

## 5. Cenário D — Administrador convida usuário inexistente

Fluxo auditado:

```text
Administrador
  ↓
Convite
  ↓
Cadastro
  ↓
Usuario
  ↓
Aceitação
  ↓
TenantUsuario
  ↓
Perfil
  ↓
UnidadesProdutivas
```

Evidências:

- `/onboarding/convites/registrar`;
- `OnboardingService.registrar_via_convite(...)`;
- `OnboardingService.aceitar_convite(...)`;
- frontend `/convite/aceitar`.

Comportamento encontrado:

- o e-mail do convite é a âncora da identidade;
- se o e-mail já existir, o cadastro por convite é bloqueado;
- nesse caso o usuário deve fazer login e aceitar;
- se o e-mail não existir, o sistema cria `Usuario` e depois realiza o aceite do convite.

Conclusão:

- o fluxo D respeita identidade global única;
- convites não justificam criar usuários duplicados.

## 6. Cenário E — Administrador cria usuário diretamente

Resultado da auditoria:

- não foi encontrado fluxo operacional oficial de `POST /team/users` ou criação direta de usuário pelo administrador do tenant;
- a gestão da equipe auditada é orientada a convite;
- o que existe é:
  - listar equipe;
  - convidar;
  - alterar perfil;
  - configurar fazendas;
  - remover vínculo;
  - listar/reenviar/cancelar convites.

Conclusão:

- o cenário E não existe como fluxo oficial atual;
- a entrada de equipe no tenant é oficialmente baseada em convite e vínculo posterior.

## 7. Implantação da equipe

### Pergunta 1

Durante a implantação inicial é obrigatório cadastrar todos os usuários da fazenda?

Resposta: **não**.

Evidência:

- `onboarding/status` calcula `etapa3_equipe`, mas `completo` depende de `etapa1` e `etapa2`;
- isto é, tenant ativo + pelo menos uma `UnidadeProdutiva` ativa;
- a equipe completa não é pré-requisito do gate de implantação.

### Pergunta 2

Quais usuários são obrigatórios para o Go-live?

Obrigatório:

- `Administrador / Owner`

Podem ser cadastrados posteriormente:

- operadores;
- técnicos;
- agrônomos;
- veterinários;
- almoxarifes;
- mecânicos;
- financeiro;
- compradores;
- gerentes;
- supervisor de campo;
- motoristas.

### Pergunta 3

É possível operar inicialmente apenas com o Owner?

Resposta: **sim**.

Arquiteturalmente, este é o cenário mínimo oficial.

### Pergunta 4

A entrada gradual da equipe faz parte da arquitetura oficial?

Resposta: **sim**.

O modelo atual já suporta:

- criação posterior por convite;
- vinculação progressiva a tenant;
- escopo progressivo por unidade produtiva;
- perfis e permissões por etapa de maturidade operacional.

## 8. Separação oficial de responsabilidades

- `Auth` continua responsável por identidade.
- `Billing` continua responsável por assinatura e direito de uso.
- `Onboarding` continua responsável pelo provisionamento inicial e status mínimo.
- `Wizard` futuro deve cuidar apenas da implantação operacional.

Consequência:

- o futuro wizard não deve criar identidades;
- o futuro wizard não deve duplicar usuários;
- o futuro wizard deve assumir que tenant, assinatura e owner já existem.

## 9. Guardrails adicionados

Foi criado o teste estático:

- `services/api/tests/unit/test_pilot_identity_team_governance_guardrails.py`

Regras protegidas:

- `Usuario` permanece identidade global;
- acesso ao tenant permanece exclusivo por `TenantUsuario`;
- escopo operacional permanece em `UnidadeProdutivaUsuario`;
- convites e assinaturas não devem duplicar `Usuario`;
- implantação inicial não depende da equipe completa;
- gestão da equipe permanece orientada a convite, não a criação direta de identidade pelo wizard.

## 10. O que fica proibido

- criar `Usuario` duplicado;
- criar `TenantUsuario` sem `Usuario`;
- criar acesso direto ao tenant sem `TenantUsuario`;
- tratar equipe completa como pré-requisito para Go-live;
- obrigar o cadastro de todos os colaboradores durante a implantação;
- acoplar wizard ao domínio de autenticação;
- usar o wizard futuro para criar identidades da plataforma.

## 11. Recomendações para `WIZARD-ARCH-01`

- assumir que a identidade já existe;
- assumir que o tenant já existe;
- assumir que a assinatura já existe;
- assumir que o owner já existe;
- conduzir apenas a implantação operacional da fazenda;
- tratar a equipe como trilha paralela e progressiva, não como bloqueio estrutural do go-live.

## 12. Validações

- `pytest` dos testes criados
  - `services/api/.venv/bin/pytest services/api/tests/unit/test_pilot_identity_team_governance_guardrails.py -q`
  - resultado: `6 passed`
- `ruff check` no escopo alterado
  - `services/api/.venv/bin/ruff check services/api/tests/unit/test_pilot_identity_team_governance_guardrails.py`
  - resultado: `All checks passed!`
- `git diff --check`
  - resultado: sem erros
