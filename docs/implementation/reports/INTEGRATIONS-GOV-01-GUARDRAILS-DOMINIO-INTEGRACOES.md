# INTEGRATIONS-GOV-01 — Guardrails do Domínio de Integrações

Data da execução: 2026-07-01

## 1. Resumo executivo

Foram criados guardrails estáticos para proteger o domínio de Integrações definido em `INTEGRATIONS-ARCH-01` e `INTEGRATIONS-ARCH-02`.

Objetivo dos guardrails:

- impedir regressões arquiteturais;
- impedir acoplamento do domínio a um provider específico;
- preservar a separação entre `Connection` e `Credential`;
- preservar `ERP != UnidadeProdutiva`;
- capturar lacunas reais já conhecidas no Sankhya sem refatorar a produção nesta execução.

## 2. Guardrails criados

Os testes estáticos cobrem:

1. ERP não pode usar `UnidadeProdutiva` como escopo de configuração.
2. Escopos oficiais limitados a `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`.
3. `Connection` e `Credential` permanecem conceitos separados.
4. Campos sensíveis não podem ser tratados como `Connection`.
5. `Provider` não pode armazenar credenciais reais de cliente.
6. `ProviderDefinition` não pode armazenar credenciais reais de cliente.
7. Backoffice não pode ser console principal de configuração do cliente.
8. Permissões de tenant não devem depender de permissões backoffice.
9. Sankhya permanece classificado como `ERP`.
10. Sankhya não deve exigir `UnidadeProdutiva` como escopo.
11. Configuração de ERP aceita `TENANT` e fica preparada para `ESTABELECIMENTO`.
12. Credenciais exigem criptografia, masking e rotação por contrato oficial.
13. Rotas tenant-scoped devem usar mecanismo de sessão/RLS ou ficar marcadas como lacuna conhecida.
14. Logs e health devem possuir `tenant_id` ou escopo equivalente.
15. Sync/jobs devem registrar `tenant_id` ou escopo equivalente.

## 3. Lacunas encontradas

Lacunas atuais confirmadas:

- a integração Sankhya ainda persiste `password` diretamente, sem evidência de criptografia real na implementação produtiva atual;
- o módulo Sankhya ainda usa `get_db()` em vez de `get_session()` com contexto RLS, então o isolamento atual é principalmente lógico por filtro de `tenant_id`;
- a principal visibilidade da integração ainda aparece no backoffice;
- ainda não existe permissão tenant específica para integrações ERP;
- ainda não existe modelagem de produção por `ESTABELECIMENTO`.

Frases normativas consolidadas para as lacunas atuais:

- a configuração atual no Backoffice não está correta como ponto principal de governança;
- unidade produtiva: inexistente como escopo de ERP no Sankhya atual;
- credenciais devem exigir criptografia, masking e rotação por contrato oficial;
- rotas tenant-scoped atuais do Sankhya ainda usam `get_db()` em vez de `get_session()`;
- isso permanece como lacuna conhecida de RLS físico no módulo atual.

Declarações objetivas:

- a configuração atual no backoffice não está correta como ponto principal de governança.
- credenciais devem exigir criptografia, masking e rotação por contrato oficial.

## 4. Violações atuais conhecidas

Violações conhecidas documentadas, sem correção nesta execução:

- credencial do Sankhya ainda misturada na configuração concreta legada;
- password ainda gravado diretamente;
- backoffice ainda aparece como casa principal da integração para o usuário;
- RLS físico não está claramente ativado no módulo Sankhya.

## 5. Itens que devem falhar agora, se forem lacunas reais

Se alguém tentar afirmar que:

- Sankhya já está protegido por criptografia plena de credenciais;
- Sankhya já usa RLS físico explícito via sessão;
- backoffice é o lugar correto para o cliente configurar o ERP;
- ERP deve ser por `UnidadeProdutiva`;

isso deve ser tratado como regressão ou leitura incorreta da arquitetura atual.

## 6. Itens que devem passar

Devem continuar passando:

- ERP como integração administrativa do cliente;
- Sankhya classificado como `ERP`;
- escopo padrão por `TENANT`;
- preparação arquitetural para `ESTABELECIMENTO`;
- ausência de `UnidadeProdutiva` como escopo de ERP;
- logs e jobs carregando `tenant_id`.

## 7. Impacto sobre Sankhya

Impacto prático:

- Sankhya continua operacionalmente utilizável;
- as lacunas ficam explicitamente protegidas e visíveis;
- novas mudanças não podem ampliar o erro arquitetural;
- qualquer refatoração futura do Sankhya deve partir dos guardrails e não de implementação ad hoc.

## 8. Próxima execução recomendada

Próxima execução recomendada:

**SANKHYA-GOV-02** ou execução equivalente de correção arquitetural governada.

Foco sugerido:

- separar `Connection` e `Credential` no Sankhya;
- introduzir contrato seguro de credenciais;
- migrar a governança principal da UI para o console do tenant;
- substituir `get_db()` por mecanismo alinhado a `get_session()`/RLS;
- preparar a evolução por `ESTABELECIMENTO`.
