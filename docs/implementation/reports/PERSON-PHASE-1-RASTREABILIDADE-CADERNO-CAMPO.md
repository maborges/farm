# PERSON-PHASE-1 — Rastreabilidade do Executor no Caderno de Campo

## Objetivo Concluído
Concluída a implementação da Fase 1 do plano do domínio Pessoa: a introdução estruturada do conceito de "Executor Físico" (`executado_por_pessoa_id`) no agregado `CadernoCampoEntrada`, desacoplando quem *registra* a atividade de quem *executa*.

## Escopo Realizado

### 1. Modelagem & Banco de Dados (API)
- Adicionada a coluna `executado_por_pessoa_id` em `CadernoCampoEntrada`.
- Criada foreign key opcional (`nullable=True`) referenciando `cadastros_pessoas(id)` com `ON DELETE SET NULL`. Essa abordagem atende regras de LGPD: se a pessoa for excluída, mantemos o apontamento no Caderno de Campo sem corromper o histórico (apenas perde-se a referência direta de quem executou).
- Migration limpa do Alembic `f1dfe22c7fa5_add_executado_por_pessoa_id_to_caderno.py` gerada com sucesso e garantida sem dependências cruzadas indevidas.

### 2. Schemas & Transporte (API)
- Modelos Pydantic (`EntradaCreate`, `EntradaUpdate`, `EntradaResponse`) atualizados com o novo campo (`executado_por_pessoa_id: UUID | None`).
- Sincronização e integração com PWA atualizados: campo passado via `payload_operacional` em endpoints legados/complementares onde aplicável.

### 3. Regras de Negócio e Services (API)
- Modificado o `CadernoCampoService`:
  - Adicionada **Validação Tenant-Scoped**: ao receber um `executado_por_pessoa_id`, a API valida se a `Pessoa` referenciada de fato pertence ao mesmo `tenant_id` da operação/caderno, bloqueando Insecure Direct Object References (IDOR) e injeções cross-tenant (lançando `ValueError` se não existir ou for de outro tenant).
  - Lógica persistida no banco durante criação via sistema e também na rotina `sincronizar_eventos_offline` originada pelo PWA.
- Atualizado o fallback de ambiente de testes em `conftest.py` para injetar o campo nas sessões isoladas para garantir testes idempotentes.

### 4. Banco de Dados Local (PWA)
- Atualizado o `apps/campo/src/lib/db.ts` (Dexie.js).
- Adicionado campo `executado_por_pessoa_id` para:
  - `CampoEventoOffline`
  - `CampoEventoOficial`
  - `CadernoDraft`
- A versão do Dexie foi incrementada de `12` para `13`.

### 5. Qualidade e Testes (QA)
- Suite de testes (21 testes unitários) em `agricola/caderno` (como status, contratos, sincronia offline e retificação) rodou com sucesso (`100% passed`), garantindo que o novo campo não quebra integrações existentes.

## Conclusões Arquiteturais
Esta fase consolida a separação de responsabilidades (IAM vs Operacional) estabelecida na **Fase 0**. O sistema agora possui suporte backend e dados locais no PWA prontos para a adoção desta rastreabilidade em produção, servindo como pré-requisito para as telas de alocação onde o usuário irá apontar quem realmente efetuou a calibração, aplicação ou colheita no campo.
