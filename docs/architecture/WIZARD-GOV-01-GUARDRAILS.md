# WIZARD-GOV-01 — Guardrails Arquiteturais do Assistente de Implantação

## 1. Objetivo

Este documento define os guardrails oficiais do domínio Wizard no AgroSaaS.

Pergunta que este documento responde:

**Quais regras arquiteturais devem permanecer congeladas para impedir que a futura implementação do Wizard crie regressões de domínio, acoplamentos indevidos ou fluxos paralelos antes da v1.0?**

Resposta objetiva:

- o Wizard deve permanecer estritamente no domínio de implantação operacional da fazenda;
- seu agregado raiz continua sendo `ImplantacaoOperacional`;
- sua implementação futura deve respeitar estados, etapas, unicidade, checklist com evidência, go-live com `UnidadeProdutiva` e separação total de Auth, Billing, Tenant provisioning e Convites;
- qualquer desvio dessas regras passa a ser regressão arquitetural.

## 2. Escopo da governança

Este documento protege:

- domínio do Wizard;
- modelo canônico de implantação;
- estados;
- etapas;
- checklist;
- pendências e bloqueios;
- histórico;
- idempotência;
- go-live;
- retomada;
- integração com arquiteturas canônicas já aprovadas.

## 3. Guardrail 1 — Separação de domínios

O Wizard nunca poderá assumir responsabilidade por:

- `Usuario`;
- `Pessoa`;
- Auth;
- MFA;
- Login;
- Senha;
- OAuth;
- Billing;
- Assinatura;
- `Tenant`;
- `TenantUsuario`;
- Convites;
- gestão global de permissões.

Norma oficial:

- toda tentativa futura de deslocar essas responsabilidades para o Wizard deve ser tratada como regressão arquitetural.

## 4. Guardrail 2 — Agregado raiz

O agregado raiz oficial do domínio Wizard permanece:

- `ImplantacaoOperacional`

Nunca:

- `Tenant`;
- `Usuario`;
- `UnidadeProdutiva`;
- `Onboarding`.

Norma oficial:

- o agregado raiz do Wizard não pode ser alterado sem nova arquitetura oficial.

## 5. Guardrail 3 — Unicidade

Na versão 1.0 deve existir no máximo:

- `1 ImplantacaoOperacional ativa por Tenant`

Estados ativos:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PAUSED`
- `BLOCKED`
- `READY_FOR_GO_LIVE`
- `GO_LIVE`
- `STABILIZATION`

Estados finais:

- `COMPLETED`
- `CANCELLED`

Norma oficial:

- reinício, retomada ou reexecução do Wizard não podem criar implantação ativa paralela no mesmo tenant.

## 6. Guardrail 4 — Unidade produtiva

`READY_FOR_GO_LIVE` e `GO_LIVE` somente podem existir quando houver:

- `UnidadeProdutiva` válida;
- `UnidadeProdutiva` ativa.

Norma oficial:

- nunca permitir go-live sem `UnidadeProdutiva`.

## 7. Guardrail 5 — Equipe

Equipe continua sendo:

- opcional

Norma oficial:

- equipe incompleta não pode impedir go-live mínimo;
- a única identidade obrigatória para implantação mínima continua sendo `Owner/Admin`.

## 8. Guardrail 6 — BLOCKED

Deve permanecer formalizada a diferença entre:

- `PAUSED`
- `BLOCKED`

Semântica oficial:

- `PAUSED` = decisão operacional ou interrupção não estrutural;
- `BLOCKED` = impedimento estrutural ou requisito crítico ausente.

Norma oficial:

- enquanto `BLOCKED` existir, nunca permitir:
  - `READY_FOR_GO_LIVE`
  - `GO_LIVE`

## 9. Guardrail 7 — Checklist

Checklist obrigatório nunca poderá ser satisfeito apenas por marcação manual.

Sempre deverá existir:

- evidência

Exemplos de evidência:

- `UnidadeProdutiva` existente;
- `AreaRural` criada;
- `Talhão` criado;
- `Piquete` criado;
- `PlanoConta` existente;
- `Deposito` existente;
- `Produto` existente.

Norma oficial:

- confirmação manual complementa a verificação;
- nunca substitui ausência de requisito factual obrigatório.

## 10. Guardrail 8 — Evidência

O Wizard trabalha sobre:

- estado real do tenant

Nunca sobre:

- "usuário marcou como concluído"

Norma oficial:

- progresso e go-live devem ser derivados do estado verificável das entidades canônicas.

## 11. Guardrail 9 — Idempotência

Reexecutar o Wizard não pode:

- criar nova implantação;
- duplicar etapas;
- duplicar checklist;
- duplicar pendências;
- duplicar histórico estrutural.

Norma oficial:

- toda implementação futura deverá respeitar idempotência por estado.

## 12. Guardrail 10 — Histórico

`ImplantacaoHistorico` deve ser:

- append-only

Nunca:

- editar histórico;
- reescrever histórico;
- apagar transições críticas.

## 13. Guardrail 11 — Etapas

As etapas oficiais permanecem:

1. Diagnóstico
2. UnidadeProdutiva
3. Território
4. Atividades
5. Agricultura
6. Pecuária
7. Estoque
8. Financeiro
9. Máquinas
10. Equipe
11. Revisão
12. Go-live
13. Estabilização

Norma oficial:

- `Equipe` permanece opcional;
- novas etapas estruturais só podem surgir por nova arquitetura oficial;
- etapas condicionais devem continuar subordinadas ao mesmo tronco canônico.

## 14. Guardrail 12 — Estados

Estados oficiais:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PAUSED`
- `BLOCKED`
- `READY_FOR_GO_LIVE`
- `GO_LIVE`
- `STABILIZATION`
- `COMPLETED`
- `CANCELLED`

Norma oficial:

- novos estados só podem surgir mediante nova arquitetura oficial.

## 15. Guardrail 13 — Relação com Onboarding

Ordem oficial:

```text
Onboarding
  ↓
Provisionamento

Wizard
  ↓
Implantação operacional
```

Norma oficial:

- nunca inverter essa ordem;
- Wizard não substitui o onboarding técnico atual sem plano explícito de migração.

## 16. Guardrail 14 — Relação com Billing

`Billing` continua responsável por:

- plano;
- cobrança;
- assinatura;
- trial.

Norma oficial:

- Wizard nunca altera:
  - plano;
  - assinatura;
  - cobrança.

## 17. Guardrail 15 — Relação com Auth

O Wizard nunca:

- cria login;
- cria senha;
- redefine senha;
- altera MFA;
- altera OAuth;
- cria identidade.

## 18. Guardrail 16 — Relação com Tenant

O Wizard apenas utiliza `Tenant` existente.

Nunca:

- cria;
- duplica;
- migra.

## 19. Guardrail 17 — Relação com Convites

Convites permanecem domínio de:

- equipe

Norma oficial:

- Wizard nunca envia convites.

## 20. Guardrail 18 — Modelo canônico

As entidades oficiais do domínio Wizard permanecem:

- `ImplantacaoOperacional`
- `ImplantacaoEtapa`
- `ImplantacaoChecklistItem`
- `ImplantacaoPendencia`
- `ImplantacaoHistorico`

Norma oficial:

- não criar modelos paralelos para implantação.

## 21. Guardrail 19 — Compatibilidade operacional

Toda implantação manual deverá seguir exatamente:

- a mesma arquitetura do Wizard

Norma oficial:

- o Wizard é a expressão guiada da arquitetura oficial;
- não é um processo paralelo.

## 22. Guardrail 20 — Compatibilidade com arquiteturas canônicas

Toda implementação futura do Wizard deverá continuar compatível com:

- `PERSON-ARCH-01`
- `TERRITORY-ARCH-01`
- `PRODUCT-ARCH-01`
- `ECONOMIC-ARCH-01`
- `EVENTS-ARCH-01`
- `PILOT-ARCH-01`
- `WIZARD-ARCH-01`
- `WIZARD-DOMAIN-01`

## 23. Guardrails de implementação futura

Antes de qualquer model, migration, endpoint, service ou frontend do Wizard:

- validar que o agregado raiz continua sendo `ImplantacaoOperacional`;
- validar unicidade por tenant;
- validar que `BLOCKED` impede go-live;
- validar que checklist obrigatório exige evidência;
- validar que equipe continua opcional;
- validar que `UnidadeProdutiva` é obrigatória antes de `READY_FOR_GO_LIVE`;
- validar que o Wizard continua desacoplado de Auth, Billing, Tenant provisioning e Convites.

## 24. Decisão oficial

Conclusão normativa:

- o domínio do Wizard está arquiteturalmente fechado para implementação;
- qualquer implementação futura deve apenas materializar essa arquitetura, não reinventá-la;
- regressões de fronteira de domínio, estados, etapas, go-live, evidência e idempotência passam a ser proibidas.

## 25. Resposta final

Após este documento, o AgroSaaS passa a possuir guardrails explícitos para impedir que o futuro Wizard assuma responsabilidades indevidas, crie fluxos paralelos, ignore `UnidadeProdutiva`, trate equipe como pré-requisito obrigatório, contorne evidência factual ou rompa o modelo canônico `ImplantacaoOperacional` + etapas + checklist + pendências + histórico.
