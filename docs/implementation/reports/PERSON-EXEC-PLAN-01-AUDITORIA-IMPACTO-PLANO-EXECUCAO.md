# PERSON-EXEC-PLAN-01 — Auditoria de Impacto e Plano de Execução do Domínio Pessoa

Este documento consolida a auditoria técnica de impacto das decisões arquiteturais sobre o domínio Pessoas (`PERSON-GOV-01A` e `01B`). Ele transforma a arquitetura ideal em um plano de execução pragmático e seguro para o AgroSaaS v1.0.

Nenhuma linha de código foi alterada na elaboração deste plano.

---

## 1. Contradições de Prioridade Resolvidas

### Integração IAM (`TenantUsuario.pessoa_id`)
- **Classificação Correta:** **Obrigatório antes da Release Candidate (Pós-Piloto)**.
- **Justificativa:** O piloto pode operar perfeitamente sem o vínculo duro no banco. Atualmente, `Usuario` autoriza o acesso e `Pessoa` governa a execução. Como o piloto terá escopo controlado, a falta de `TenantUsuario.pessoa_id` não impede nenhum fluxo de negócio. Classificá-lo como "Bloqueador" seria irrealista. 

### Executor da Operação (`executado_por_pessoa_id`)
- **Classificação Correta:** **Recomendado durante o piloto**.
- **Justificativa:** A auditoria em `OperacaoAgricola` (arquivo `agricola/operacoes/models.py`) revelou que já existe o campo `operador_id` mapeado para `cadastros_pessoas.id`. Ou seja, o executor *já está estruturado corretamente* nas Operações.
- No entanto, em `CadernoCampoEntrada` (`caderno/models.py`), existe apenas `usuario_id` (registrador). Embora as entradas do caderno possam ser manuais, para distinguir fisicamente o operador do registrador, a inclusão de `executado_por_pessoa_id` é válida. Como isso afeta o Campo PWA, deve ser incluído de forma não bloqueante.

---

## 2. Inventário Completo do Domínio Pessoa

**IAM (Autenticação/Acesso):**
- `Usuario` (`core/models/auth.py`)
- `TenantUsuario`
- `UnidadeProdutivaUsuario` (Aliased como `FazendaUsuario`)
- `ConviteAcesso`

**Core (Cadastros Mestres):**
- `Pessoa` (`core/cadastros/pessoas/models.py`)
- `PessoaPII` (Dados sensíveis)
- `PessoaDocumento`, `PessoaContato`, `PessoaEndereco`, `PessoaBancario`
- `TipoRelacionamento` (Catálogo de papéis)
- `PessoaRelacionamento` (A tabela pivô)

**RH (Módulo Operacional Especializado):**
- `ColaboradorRH` (`rh/models.py` - Wrappers legados, possui `pessoa_id` opcional)
- `LancamentoDiaria`, `Empreitada`
- `EPIEntrega` (Usa `colaborador_id` em vez de `pessoa_id`)

**Agrícola (Execução):**
- `OperacaoAgricola`, `OperacaoExecucao` (`operacoes/models.py` - Usam `operador_id` FK Pessoa)
- `CadernoCampoEntrada` (`caderno/models.py` - Usa `usuario_id`)

---

## 3. Auditoria de `PessoaRelacionamento` (Suporte de Banco)

Verificou-se diretamente no Schema SQL de `PessoaRelacionamento`:
- **Pessoa sem Unidade:** Suportado (`unidade_produtiva_id` é `nullable=True`).
- **Múltiplas unidades/Papéis:** Suportado (relacionamento N:N, chaves primárias via UUID isolado).
- **Vigências sucessivas/sobrepostas:** Suportado (`ativo_desde`, `ativo_ate`).
- **Gargalos potenciais:** O frontend e os repositórios (queries) não possuem bloqueios hard-coded no banco (ex: `UNIQUE (pessoa_id)`), permitindo livre uso.

**Veredicto:** Suportado integralmente no banco de dados. Atenção exclusiva aos repositórios e endpoints para que não apliquem limitadores lógicos (`.first()`) ao invés de listas.

---

## 4. Auditoria da Decisão `TenantUsuario.pessoa_id`

- **Análise Técnica:** O vínculo resolve o problema de isolamento. Como `TenantUsuario` possui `tenant_id` forte (Row Level Security nativo), atrelar `pessoa_id` ali é a arquitetura ideal para Multi-Tenancy.
- **Cardinalidade:** 0 ou 1 `Pessoa` por `TenantUsuario`. 
- **Integridade:** Não é aconselhável impor uma `UNIQUE(tenant_id, pessoa_id)` física que proíba a mesma pessoa de ter duas credenciais de acesso válidas se houver um caso de teste/suporte justificável, embora semanticamente indesejado. Uma FK `pessoa_id` em `TenantUsuario` com indexação resolve.
- **Conclusão:** Aprovar a elaboração do ADR, implementação programada para o fim do Piloto.

---

## 5. Rastreabilidade das Operações (Regra de Ouro)

Distinção clara entre:
- `executado_por_pessoa_id` (ID da entidade civil que suou a camisa).
- `registrado_por_usuario_id` (ID do login que apontou no software).

| Fluxo | Executor Atual | Registrador Atual | Necessita Mudança |
| :--- | :--- | :--- | :--- |
| **Operação Agrícola** | `operador_id` (Pessoa) | `created_by` (Implícito) / Contexto | NÃO (Aderente) |
| **Operação Execução** | `operador_id` (Pessoa) | Contexto de sessão | NÃO (Aderente) |
| **Caderno de Campo** | *Inexistente* (Null) | `usuario_id` | SIM (Add `executado_por`) |
| **EPI Entrega** | `colaborador_id` (RH) | Contexto de sessão | NÃO (Transição Legada) |

---

## 6. Compatibilidade com `ColaboradorRH`

A auditoria confirmou que `ColaboradorRH` atua de fato como um "wrapper" operacional de recursos humanos (com vínculos de departamento, salário hora, etc).
**Estratégia de Transição (Recomendada):**
- Manter registros existentes funcionando para Custos e Diárias.
- Para novos registros gerados após v1.0, o sistema deve gravar simultaneamente `Pessoa` e o wrapper `ColaboradorRH` com `pessoa_id` preenchido. Migração automática do legado não é escopo prioritário.

---

## 7. Campo PWA e Sincronização Offline

**Solução Elegível para Piloto:** *Sincronização Seletiva (Apenas Pessoas com papéis elegíveis nas UPs autorizadas).*
O payload offline não deve baixar o Tenant todo para evitar infração à LGPD e estouro de memória no IndexedDB (Dexie). O Sync Engine deve aplicar:
```sql
WHERE unidade_produtiva_id IN (unidades do usuario logado) 
  AND tipo_id IN ('OPERADOR', 'AGRONOMO')
```
Isso minimiza o pacote, melhora a segurança e preserva o comportamento sem rede.

---

## 8. Eventos de Domínio

Os eventos propostos estão de acordo com o `EVENTS-ARCH`.
- `PessoaRegistradaEvent` (Payload: `pessoa_id`, `tenant_id`). Sem PII.
- `PessoaAnonimizadaEvent` (Payload: `pessoa_id`, `tenant_id`). Usado para propagar o "Esquecimento".
- **Impacto no piloto:** Baixo. Serão implementados gradativamente conforme módulos de fora (ERP, CRM) passarem a escutá-los.

---

## 9. Impacto no Assistente de Implantação (Wizard)

A auditoria reitera que **o piloto não exige Pessoas cadastradas como requisito bloqueante de Go-Live**. 
O Wizard guiará o owner na parametrização da fazenda (Talhões, Safras). Se o owner não tiver equipe (ou se fará os apontamentos sozinho de sua própria execução), não existe gate paralisando-o. O checklist de Pessoas é estritamente **opcional** durante a implantação.

---

## 10. Plano de Execução em Fases

### Fase 0 — Correções Documentais e ADR (Imediato)
- **Objetivo:** Formalizar as decisões (como o `TenantUsuario.pessoa_id`) nos documentos arquiteturais.

### Fase 1 — Rastreabilidade Mínima (Durante o Piloto)
- **Objetivo:** Adicionar campo `executado_por_pessoa_id` no modelo `CadernoCampoEntrada`.
- **Justificativa:** Garantir a distinção entre digitador (registrador) e operador de campo no PWA.

### Fase 2 — Sincronização Seletiva PWA (Durante o Piloto)
- **Objetivo:** Ajustar o endpoint de Sync de Pessoas do PWA para filtrar apenas papéis relevantes e unidades permitidas.

### Fase 3 — Vínculo IAM Tenant-Scoped (Pós-Piloto / Release Candidate)
- **Objetivo:** Adicionar `pessoa_id` à tabela `TenantUsuario` e construir a tela que sugere o vínculo.
- **Risco:** Médio. Requer migration e alteração profunda nos serviços de Convite e Aceite de login.

### Fase 4 — Convergência de Wrappers (Pós-Release Candidate)
- **Objetivo:** Acionar os Resolvers para consolidar `ColaboradorRH` e `Fornecedor`. 

---

## 11. Veredicto Oficial de Prontidão

| Critério | Status | Classificação |
| :--- | :--- | :--- |
| **Suporte a múltiplos papéis e UPs** | Validado em DB | **GO** |
| **Pessoa sem UP / Tenant-wide** | Validado em DB | **GO** |
| **Pessoa sem Login (Operadores)** | Desacoplado | **GO** |
| **Usuário sem Pessoa (Admins/Backoffice)** | Desacoplado | **GO** |
| **Rastreabilidade (Execução vs Registro)**| Parcial (`Caderno`) | **GO COM RESSALVAS** |
| **Integração IAM Forte** | Não implantada | **GO COM RESSALVAS** |
| **Prontidão para o Piloto** | Não há bloqueios | **GO** |

**Conclusão Geral:**
Não existe nenhuma correção sistêmica bloqueadora para o início do Piloto. As restrições de rastreabilidade do Caderno (Fase 1 e 2) podem ser desenvolvidas simultaneamente ao rollout inicial. A arquitetura consolida as boas práticas de multi-tenancy e event-driven architecture do ecossistema AgroSaaS.

---

## 12. Adendo Documental (Fase 0)

Como resultado direto do marco **PERSON-PHASE-0**, foram validados os fluxos de código de Sincronização PWA (`apps/campo/src/lib/sync/pull.ts`), schema local de PWA (`db.ts`) e o mapeamento atual de `CadernoCampoEntrada`. 
Duas novas especificações normativas foram criadas e devem ser respeitadas pelas equipes de engenharia ao entrarem nas próximas fases:

1. **[ADR de Vínculo IAM Tenant-Scoped](file:///opt/lampp/htdocs/farm/docs/architecture/adr/ADR-IAM-TENANT-SCOPED-PESSOA.md):** Define a restrição de foreign key em `TenantUsuario` validada via RLS, sem constraints excessivamente duras, aprovando a Fase 3.
2. **[Contrato de Rastreabilidade e PWA](file:///opt/lampp/htdocs/farm/docs/implementation/reports/PERSON-PHASE-0-CONTRATO-RASTREABILIDADE-E-PWA.md):** Oficializa o uso do campo `executado_por_pessoa_id` de forma híbrida no Caderno e rege as regras de minimização do payload offline para os operadores de campo.

O piloto encontra-se em status **PRONTO PARA INÍCIO DE IMPLEMENTAÇÃO** (PRs). A primeira implementação tática a ser codificada (Fase 1) consistirá em atualizar as rotas e tabelas de Caderno de Campo para suportarem o novo campo de executor.
