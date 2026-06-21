# EXECUTION-02 — Fase 1 Data Model Documental da Convergência Propriedades x Imóveis Rurais

Data de execução: 2026-06-21

## Escopo executado

Tickets cobertos em modo documental:

- TCK-008 — Desenhar a entidade `PropriedadeImovel`
- TCK-009 — Definir enum `tipo_vinculo` e regras de vigência
- TCK-010 — Definir constraints e índices do vínculo
- TCK-011 — Definir política de RLS para `PropriedadeImovel`
- TCK-012 — Atualizar documentação do Data Model

Este relatório não implementa código, migration, API ou frontend.

---

## 1. Entidade `PropriedadeImovel`

### Objetivo

`PropriedadeImovel` é a entidade canônica de vínculo entre `Propriedades` e `Imóveis Rurais`. Ela existe para registrar a relação auditável entre o domínio operacional e o domínio fundiário/legal.

### Ownership

- Ownership do vínculo: `PropriedadeImovel`
- Ownership operacional: `Propriedades`
- Ownership fundiário/documental: `Imóveis Rurais`

### Responsabilidades

- Representar sobreposição territorial e fundiária.
- Representar vínculo principal, secundário ou contratual.
- Preservar histórico de vigência.
- Sustentar rastreabilidade, ESG, certificações e Projeto Raízes.

### O que a entidade não pode armazenar

- Dados operacionais de safra ou produção.
- Cadastro completo de propriedade.
- Cadastro completo de imóvel rural.
- Documentos integrais.
- Titularidade completa.
- Dados fiscais completos.
- Regras operacionais rurais.
- Geometria principal.

### Campos obrigatórios

- `tenant_id`
- `propriedade_id`
- `imovel_rural_id`
- `tipo_vinculo`
- `ativo`
- `data_inicio`
- `origem_documental`
- `observacoes`
- `created_at`
- `updated_at`

### Campos opcionais

- `area_vinculada`
- `percentual_vinculado`
- `data_fim`
- `vinculo_principal`
- `origem_referencia`
- `status_documental`
- `created_by`
- `updated_by`

### Campos futuros

- `motivo_encerramento`
- `versao_normativa`
- `hash_documental`
- `origem_geoespacial`
- `score_confianca`

### Validação contra AGRI-DOMAIN-002

- A definição está alinhada com a norma.
- A entidade continua sendo exclusivamente relacional.
- A entidade não assume titularidade nem operação.
- O vínculo pode ser principal, secundário, contratual ou transitório.

---

## 2. Enum `tipo_vinculo`

### Enum oficial

```text
PROPRIEDADE_PRINCIPAL
PROPRIEDADE_SECUNDARIA
ARRENDAMENTO
PARCERIA_RURAL
COMODATO
USO_COMPARTILHADO
USO_TEMPORARIO
INTEGRACAO
OUTRO
```

### Diretrizes por valor

#### `PROPRIEDADE_PRINCIPAL`

- Define o vínculo fundiário principal da operação.
- Usar quando o imóvel for a base legal primária da propriedade operacional.
- Restrições:
  - no máximo um vínculo principal ativo por propriedade na mesma janela de vigência;
  - exige origem documental explícita.
- Vigência:
  - exige `data_inicio`;
  - `data_fim` opcional;
  - deve ser rastreável quando encerrado.

#### `PROPRIEDADE_SECUNDARIA`

- Define suporte fundiário ou complementar.
- Usar quando uma propriedade operar com mais de um imóvel de apoio.
- Restrições:
  - não substitui o vínculo principal;
  - não altera titularidade.
- Vigência:
  - segue as mesmas regras de vigência do vínculo principal.

#### `ARRENDAMENTO`

- Define vínculo contratual de arrendamento.
- Usar quando houver exploração mediante contrato de arrendamento.
- Restrições:
  - exige vigência;
  - exige origem documental;
  - pode ser parcial.
- Vigência:
  - temporalidade obrigatória;
  - encerramento deve permanecer histórico.

#### `PARCERIA_RURAL`

- Define vínculo contratual de parceria rural.
- Usar quando houver exploração compartilhada por contrato.
- Restrições:
  - exige vigência;
  - exige origem documental;
  - pode ser parcial.
- Vigência:
  - temporalidade obrigatória.

#### `COMODATO`

- Define cessão de uso sem transferência de titularidade.
- Usar quando houver uso gratuito formalizado.
- Restrições:
  - exige vigência;
  - exige origem documental.
- Vigência:
  - deve possuir período definido.

#### `USO_COMPARTILHADO`

- Define uso simultâneo por mais de uma operação ou unidade.
- Usar quando houver compartilhamento real de área.
- Restrições:
  - deve explicitar escopo;
  - deve informar área ou percentual quando aplicável.
- Vigência:
  - pode ser simultânea a outros vínculos, desde que documentada.

#### `USO_TEMPORARIO`

- Define ocupação ou uso transitório.
- Usar para janelas temporárias de apoio, execução ou transição.
- Restrições:
  - exige `data_inicio` e `data_fim`;
  - não altera titularidade.
- Vigência:
  - obrigatoriamente delimitada.

#### `INTEGRACAO`

- Define vínculo administrativo de integração, saneamento ou fusão documental.
- Usar em transições e consolidações.
- Restrições:
  - não cria efeito jurídico por si só;
  - deve ser acompanhado de origem documental.
- Vigência:
  - deve ser temporária ou transicional.

#### `OUTRO`

- Define vínculo não classificado.
- Usar apenas em casos excepcionais.
- Restrições:
  - uso excepcional;
  - precisa de justificativa em `observacoes`.
- Vigência:
  - segue as mesmas regras mínimas do vínculo escolhido.

---

## 3. Vigência e principalidade

### Regras documentais aprovadas

- `data_inicio` é obrigatória.
- `data_fim` é opcional.
- `ativo` é obrigatório.
- Vínculo encerrado não deve ser apagado.
- Um vínculo principal por propriedade e por vigência deve ser considerado a regra esperada.
- Sobreposição temporal:
  - permitida quando o tipo de vínculo suportar o cenário;
  - proibida quando gerar conflito de principalidade.
- Vínculo parcial:
  - é permitido quando área ou percentual forem explicitamente delimitados;
  - `area_vinculada` e `percentual_vinculado` devem ser coerentes quando ambos existirem.

### Critério documental de controle

- Principalidade é uma propriedade do vínculo, não do imóvel isolado.
- Histórico é obrigatório para auditoria.
- O vínculo não altera titularidade nem operação.

---

## 4. Constraints e índices propostos

### PK

- `pk_propriedade_imovel`

### FK

- `fk_propriedade_imovel_tenant_id`
- `fk_propriedade_imovel_propriedade_id`
- `fk_propriedade_imovel_imovel_rural_id`

### Unique constraints sugeridas

- `uq_propriedade_imovel_tenant_propriedade_imovel_vigencia`
- `uq_propriedade_imovel_principal_ativo`

### Check constraints sugeridas

- `ck_propriedade_imovel_datas_validas`
- `ck_propriedade_imovel_percentual_entre_0_e_100`
- `ck_propriedade_imovel_area_nao_negativa`
- `ck_propriedade_imovel_tipo_vinculo_valido`

### Índices sugeridos

- `ix_propriedade_imovel_tenant_id`
- `ix_propriedade_imovel_propriedade_id`
- `ix_propriedade_imovel_imovel_rural_id`
- `ix_propriedade_imovel_tipo_vinculo`
- `ix_propriedade_imovel_ativo`
- `ix_propriedade_imovel_data_inicio`
- `ix_propriedade_imovel_data_fim`
- `ix_propriedade_imovel_tenant_propriedade`
- `ix_propriedade_imovel_tenant_imovel`

### Leitura técnica

- Os nomes acima são apenas sugestões documentais para a futura migration.
- Eles ainda não existem no banco.
- A escolha final deve respeitar o padrão de nomenclatura já usado no schema.

---

## 5. RLS esperado para `propriedade_imovel`

### Resposta objetiva

- Deve ter `tenant_id` direto? **Sim**
- Deve ter `ENABLE ROW LEVEL SECURITY`? **Sim**
- Deve ter `CREATE POLICY`? **Sim**
- Deve usar `app.current_tenant_id`? **Sim**
- Deve ter `FORCE ROW LEVEL SECURITY`? **Sim, como endurecimento desejado**
- Deve cobrir `SELECT`? **Sim**
- Deve cobrir `INSERT`? **Sim**
- Deve cobrir `UPDATE`? **Sim**
- Deve cobrir `DELETE`? **Sim**

### Política esperada

- A futura tabela deve aceitar apenas linhas cujo `tenant_id` corresponda ao contexto ativo da sessão.
- Operações de leitura e escrita devem ser bloqueadas quando o contexto de tenant não coincidir.
- O modelo esperado é o mesmo padrão aplicado ao isolamento já usado pela aplicação.

### Observação

- Esta seção é especificação documental.
- Não contém SQL executável.
- A policy física deve ser criada apenas na fase de migration.

---

## 6. Atualização do Data Model

### Alteração realizada

- [docs/architecture/agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md) foi atualizado com:
  - cardinalidade N:N;
  - descrição da entidade `PropriedadeImovel`;
  - campos esperados;
  - constraints esperadas;
  - RLS esperado;
  - fonte da verdade;
  - regras estruturais.

### Resultado

- O Data Model agora reconhece explicitamente o vínculo canônico como entidade de primeira classe.
- A documentação está coerente com AGRI-DOMAIN-002 e com a ADR aprovada.

---

## 7. Bloqueios remanescentes

### Bloqueios ainda presentes

- Worktree ainda não está limpo.
- RLS físico no banco ainda não está formalizado.
- A modelagem documental existe, mas a implementação técnica ainda não começou.
- O risco de duplicidade fundiária ainda precisa ser controlado na execução.

### O que ainda impede a implementação técnica

- Falta de branch dedicada ou base limpa.
- Ausência de policy física PostgreSQL evidenciada nas migrations.
- Ausência de migration aprovada para `propriedade_imovel`.
- Necessidade de manter compatibilidade com o legado até a migração.

---

## 8. Respostas objetivas

1. Fase 1 documental foi concluída?

- **Sim.**

2. A entidade `PropriedadeImovel` ficou definida?

- **Sim.**

3. O enum `tipo_vinculo` ficou definido?

- **Sim.**

4. As constraints e índices ficaram especificados?

- **Sim.**

5. A política de RLS esperada ficou especificada?

- **Sim.**

6. O Data Model foi atualizado?

- **Sim.**

7. Pode avançar para Fase 2 — Migration Alembic?

- **Ainda não como execução técnica.**
- **Sim apenas como recomendação condicional, após resolução dos bloqueios restantes.**

8. Quais bloqueios ainda impedem implementação técnica?

- Worktree não limpo.
- RLS físico ainda não formalizado.
- Duplicidade fundiária ainda precisa ser controlada na transição.
- Migration de convergência ainda não existe.
- Compatibilidade com legado ainda depende de plano de execução.

---

## 9. Critério final

- A Fase 1 aprova apenas a modelagem documental.
- A Fase 2 só deve começar quando:
  - o worktree estiver limpo ou a branch dedicada estiver criada;
  - o RLS físico estiver formalizado;
  - as constraints estiverem aprovadas;
  - o risco de duplicidade estiver controlado.

