# PERSON-GOV-02 — Auditoria de Lotação, Alocação, Vínculo e Papel por Unidade Produtiva

Este documento apresenta a auditoria arquitetural detalhada sobre a representação de **Pessoas** e suas atuações em múltiplas **Unidades Produtivas** (UPs). O foco principal é assegurar que o AgroSaaS seja capaz de resolver o cenário comum de "lotação de origem" vs "alocação temporária operacional", sem fundir responsabilidades de RH, IAM e apontamentos agrícolas.

---

## 1. Glossário Consolidado e Semântica do Domínio

A análise das tabelas de `cadastros_pessoas` e `rh_colaboradores` confirmou as seguintes fronteiras semânticas:

| Conceito | Definição de Negócio | Entidade Atual | Source of Truth | Status |
|---|---|---|---|---|
| **Vínculo de Trabalho** | Contrato formal de RH/Financeiro (salário, encargos). | `ColaboradorRH` | RH / ERP | **GO** |
| **Unidade de Origem / Lotação** | UP raiz que administra o contrato e a folha do indivíduo. | `ColaboradorRH.unidade_produtiva_id` | RH / ERP | **GO** |
| **Alocação Temporária** | Permissão e registro para operar em UP diferente da origem. | `PessoaRelacionamento` | Agrícola / Campo | **GO** |
| **Papel Operacional** | A função técnica desempenhada pela pessoa em uma UP (ex: Motorista). | `PessoaRelacionamento.tipo_id` | Agrícola / Campo | **GO** |
| **Cargo** | A nomenclatura formal da folha de pagamento. | `ColaboradorRH.cargo` | RH / ERP | **GO** |
| **Autorização de Atuação** | Quem possui credenciais de acesso lógico/sistema na UP. | `UnidadeProdutivaUsuario` | IAM / Auth | **GO** |
| **Unidade de Execução** | Onde o evento (Caderno, Operação) realmente ocorreu. | `CadernoCampo.unidade_produtiva_id` | Apontamento | **GO** |
| **Unidade Pagadora** | De qual centro de custo ou UP o salário é processado. | Derivado do Vínculo de Trabalho | RH / Financeiro | **GO** |

---

## 2. Auditoria de `PessoaRelacionamento`

O modelo `PessoaRelacionamento` é um pivô poderoso que liga `Pessoa` a `TipoRelacionamento` (Papel), com uma `unidade_produtiva_id` e controle de vigência (`ativo_desde`, `ativo_ate`). 

**Veredito:** O modelo é totalmente capaz de distinguir:
- **"João é funcionário de UP1"**: Possui `ColaboradorRH(up=UP1)` e `PessoaRelacionamento(tipo=FUNCIONARIO, up=UP1)`.
- **"João está temporariamente alocado em UP2"**: Cria-se um `PessoaRelacionamento(tipo=OPERADOR, up=UP2, ativo_ate=DATA)`.

Não foi identificada inferência frágil nesta camada relacional de dados. O problema concentra-se nas camadas de *leitura* (UI e Serviços).

---

## 3. Papéis diferentes por Unidade Produtiva (Múltiplas Atuações)

**Problema Identificado**: O banco suporta (constraints ok), porém as queries e APIs expostas não exigem contexto da UP para filtrar e a UI expõe a pessoa globalmente.
- **Banco/Models**: **GO**.
- **APIs de Listagem (`/cadastros/pessoas`)**: **GO COM RESSALVAS**. Retorna uma matriz com todos os relacionamentos em todas as UPs. Não há um filtro de API maduro como `GET /pessoas?unidade_produtiva_id=UP2`.
- **Interface Web (`PessoaSelect`)**: **NO GO**. Atualmente o Seletor filtra apenas se a pessoa possui *qualquer* relacionamento ativo (`relacionamentos.length > 0`). Isso significa que João aparecerá no seletor de UP2 mesmo se ele só for alocado em UP1. 
- **Campo PWA (Fase 2)**: Pendente de sync. O design do schema deverá suportar catálogo por UP.

---

## 4. Resolver papel por contexto

Atualmente não há uma função central de *Resolver* de papel em `services.py`. Como as UPs podem sobrepor papéis, a assinatura conceitual correta para apropriação de custos seria:
```python
def resolver_papeis_operacionais(pessoa_id: UUID, unidade_produtiva_id: UUID, data_referencia: date) -> list[TipoRelacionamento]:
    # Buscar PessoaRelacionamento onde unidade_produtiva_id IN (UP_ALVO, NULL_TENANT_WIDE)
    # E ativo_desde <= data_referencia <= ativo_ate
```

---

## 5. Unidade Principal e Unidade de Origem

A unidade de origem está no lugar certo: `rh_colaboradores.unidade_produtiva_id`.
**Não presuma que a primeira Unidade vinculada na tabela PessoaRelacionamento é a principal.** 
O Core Pessoa não precisa e não deve possuir campo `unidade_principal_id`. Essa é uma métrica de Contrato/RH.

---

## 6. Alocação temporária e 7. Transferência Definitiva

- **Alocação temporária**: Resolvida sem criação de novas entidades. Cria-se um novo registro em `PessoaRelacionamento` com a `unidade_produtiva_id` de destino e a vigência (`ativo_ate`). O Vínculo de origem (`ColaboradorRH`) não sofre mutação.
- **Transferência Definitiva**: Realiza mutação no Vínculo do `ColaboradorRH.unidade_produtiva_id` e encerra-se a vigência (`ativo_ate`) do relacionamento na UP antiga, criando um relacionamento sem termo na nova UP. Preserva-se o histórico.

---

## 8. Relação com IAM e Autorização

**Auditoria:** Identidades operacionais e de acesso lógico estão estritamente separadas. 
- `UnidadeProdutivaUsuario` (Acesso lógico / IAM).
- `PessoaRelacionamento` (Acesso operacional ao campo).
- Uma Pessoa sem Usuário pode perfeitamente atuar como executor em UP2. A pessoa não conseguirá fazer login, mas o encarregado poderá lançar apontamentos para ela no Caderno de Campo. Nenhum provisionamento automático deve existir.
**Veredito:** **GO**.

---

## 9. Campo PWA e Catálogo Operacional (Fase 2)

Quando o catálogo do PWA for desenhado, o payload **deve** ser projetado no nível do relacionamento contextualizado por UP.
**Sugerido para Fase 2:**
```json
{
  "id": "pessoa-uuid",
  "nome": "João",
  "papeis_por_up": {
    "UP2-uuid": ["OPERADOR_MAQUINA"]
  }
}
```
Não propagar dados da UP1 se o dispositivo logado está restrito apenas à UP2. Evita vazamento de PII cruzado entre UPs.

---

## 10. Interface Web (`PessoaSelect`)

Conforme evidenciado, o Seletor recém-criado foi injetado sem a prop de contexto da `unidade_produtiva_id`.
**Correção Pós-Auditoria**: O `PessoaSelect` precisa receber `fazendaId` do formulário (ou sessão ativa) e filtrar a lista de pessoas para exibir apenas quem possui um Relacionamento válido para aquela `fazendaId`.

---

## 11. Custos e Apropriação

No cenário: *Salário administrado por UP1, Horas trabalhadas em UP2, Custo apropriado em UP2*.
A tabela `rh_lancamentos_diarias` resolve esse dilema com segurança, pois possui:
- `colaborador_id` (que remete ao RH em UP1).
- `unidade_produtiva_id` (onde o rateio será aplicado, no caso, UP2).
O risco de o custo ficar atrelado indevidamente à UP1 não se aplica ao Banco, mas dependerá da precisão da Engine de Rateio a ser implementada.

---

## 12. Fronteira ERP/RH

O AgroSaaS domina a *execução* e a *apropriação*. 
A Folha (ERP) não tem permissão para sobrescrever arbitrariamente os *papéis operacionais temporários* na tabela `PessoaRelacionamento` ao realizar sincronizações. O ERP deve ser mestre de `ColaboradorRH`.
**Veredito:** **GO**.

---

## 13. Conflitos e Precedência de Papel

Se João tem `MOTORISTA` e `OPERADOR_MAQUINA` ativos ao mesmo tempo na mesma UP, a API no momento devolverá ambos. Na hora de gerar o custo, a Engine de Apontamento teria que inferir pelo de maior valor ou pedir que o usuário especificasse qual papel João usou na tarefa. 
No Caderno de Campo (Fase 1), temos apenas `executado_por_pessoa_id`. Se a complexidade financeira exigir no futuro, poderemos ter que adicionar `executado_como_papel_id` no apontamento.

---

## 14. Veredictos Resumidos e Impacto no Dry Run

| Requisito / Componente | Veredito | Comentário |
|---|---|---|
| Múltiplos Papéis por Pessoa (Geral) | **GO** | BD estruturado para 1:N no `PessoaRelacionamento`. |
| Lotação Principal vs Origem | **GO** | Absorvido no model especializado `ColaboradorRH`. |
| Alocação Temporária vs Definitiva | **GO** | Histórico via vigência (`ativo_desde`, `ate`). |
| Isolamento IAM (Logins) | **GO** | Arquitetura estritamente separada. |
| Modelo de Custos Base (Diárias) | **GO** | Suporta separação Pagador vs Apropriação. |
| Resolução de Papéis Diferentes por Unidade | **GO COM RESSALVAS** | Banco suporta, mas Serviços não exigem/filtram contexto da UP na API atual. |
| PessoaSelect Web (Filtragem UP) | **NO GO** | Atual seletor exibe todos. Necessário ajustar para filtrar pela UP ativa. |
| Campo PWA Catálogo (Fase 2) | **NO GO** | Aguardando sync modelado corretamente. |
| Resolução de Precedência de Custos | **NO GO** | Caderno de Campo ainda não aponta *qual* papel executou se houver +1. |

**Impacto no Dry Run (PERSON-PILOT-01B):**
O Dry Run **PODE prosseguir** para validar os cenários de um operador padrão. O problema de listagem no `PessoaSelect` (vazamento visual de UP) é um débito de UX que não inviabiliza a validação da rastreabilidade do apontamento `executado_por_pessoa_id` ponta-a-ponta no pipeline. 

---

## 15. Plano de Evolução (Próximas Fases)

1. **Dry Run Operacional (PERSON-PILOT-01B)**: Executar fluxo feliz de rastreabilidade.
2. **Correção do PessoaSelect (PERSON-UX-01-HOTFIX)**: Evoluir API de pessoas e Seletor Web para aceitar/exigir a `unidade_produtiva_id` de contexto.
3. **Catálogo Seletivo Campo PWA (PERSON-PHASE-2)**: Criar schema Dexie sincronizando apenas pessoas válidas para a UP do dispositivo.
4. **Engine de Papéis vs Apropriação (PERSON-COSTS)**: Discutir e implementar a lógica de precedência se uma pessoa tiver mais de um papel ativo na mesma UP, exigindo, se necessário, apontar "Qual Papel" no Caderno de Campo (Fase 3).
