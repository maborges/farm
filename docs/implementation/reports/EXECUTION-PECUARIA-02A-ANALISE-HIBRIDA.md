# EXECUTION-PECUARIA-02A — Modelo Híbrido de Rebanho
## Análise de Viabilidade Arquitetural

**Data:** 23/06/2026  
**Status:** ANÁLISE — READ-ONLY  
**Objetivo:** Validar a coexistência de Lotes Agregados (controlados apenas por quantidade) e Lotes Detalhados (controlados por animais individualizados).

---

## 1. Viabilidade

**É viável?**
**SIM, e altamente recomendado.** O AgroSaaS visa atender desde fazendas menores (que operam na "pedagogia da prancheta" e gerenciam cabeças por lote) até operações de alta precisão (que usam SISBOV, brincos eletrônicos e acompanhamento individual). Forçar todos os clientes a cadastrar 5.000 animais individualmente no "Dia 1" de uso geraria atrito impeditivo para adoção (onboarding killer). O modelo híbrido permite uma evolução gradual da maturidade de gestão do cliente.

---

## 2. Impactos Mapeados

### Impacto no model `LoteAnimal` (pec_lotes)
- **Atual:** Os campos `quantidade_cabecas` e `peso_medio_kg` são editados livremente via criação/edição ou inferidos por manejos coletivos.
- **Híbrido:** O comportamento dessas colunas precisará mudar dependendo da natureza do lote. Em um lote detalhado, essas colunas se tornam *readonly* e devem espelhar o estado agregado da tabela `pec_animais`.

### Impacto no model `Animal` (pec_animais)
- Sem impacto estrutural, mas o model adquire a restrição de negócio de **só poder ser associado a lotes configurados como "Detalhados"**.

### Impactos em Relatórios e Dashboards
- **Dashboards:** NENHUM impacto desde que a fonte da verdade para "total de cabeças" continue sendo `LoteAnimal.quantidade_cabecas` (seja ela digitada manualmente ou populada via triggers/listeners). A query de agregação não precisa fazer um `UNION` pesado com `pec_animais`.
- **Relatórios:** Será necessário exibir um indicativo visual (Ex: "Controle por Lote" vs "Controle Individual") para explicar por que não é possível detalhar os animais em lotes agregados.

### Impacto Financeiro e DRE Pecuária (Futuro)
- A apropriação de custos é facilitada. Um custo alocado a um Lote Agregado é dividido pela `quantidade_cabecas` digitada. Em um Lote Detalhado, o custo pode ser rateado exatamente pelos animais ativos no lote na data da despesa. O DRE Pecuária continuará tendo como dimensão principal o Lote (nível gerencial).

### Impactos no Cálculo de GMD e Lotação de Piquetes
- **GMD:** O Ganho Médio Diário só é possível com precisão matemática confiável em animais individuais. Lotes agregados terão apenas uma métrica de "Evolução de Peso do Lote", não um GMD clássico por indivíduo.
- **Lotação (UA/ha):** NENHUM impacto. A lotação continuará usando `LoteAnimal.quantidade_cabecas` multiplicada pelo fator de UA (0.5 a 1.2, dependendo da categoria).

### Impacto na Integração com Estoque
- NENHUM impacto grave. A vacinação de um lote de 100 cabeças baixará 100 doses do estoque, independentemente de essas cabeças estarem detalhadas no banco ou não. O handler consumirá `LoteAnimal.quantidade_cabecas`.

---

## 3. Qual a melhor modelagem?

A melhor modelagem é o isolamento estrito de modalidade por Lote.

**Regra de Ouro:** **Um Lote NUNCA deve ser misto.**
Ou o lote é 100% Agregado (onde `quantidade_cabecas` é input manual/calculado por eventos de lote e a tabela `pec_animais` para este lote está vazia).
Ou o lote é 100% Detalhado (onde `quantidade_cabecas` é estritamente a soma dos registros ativos em `pec_animais` vinculados a este lote).

Isso previne a anomalia arquitetural clássica onde "Lote A tem 100 cabeças cadastradas na capa, mas apenas 40 animais registrados no banco".

---

## 4. Deve existir um campo `tipo_controle`?

**SIM.** A introdução de um campo explícito elimina suposições (guessing) no código.

Recomendação de Migration no `LoteAnimal`:
```sql
ALTER TABLE pec_lotes ADD COLUMN tipo_controle VARCHAR(20) DEFAULT 'AGREGADO' NOT NULL;
-- Valores possíveis: 'AGREGADO', 'DETALHADO'
```

### Comportamento do Sistema via tipo_controle:

| Ação | Lote AGREGADO | Lote DETALHADO |
|------|--------------|----------------|
| Input Qtd. Cabeças | Editável pelo usuário / Eventos | Bloqueado (Readonly) |
| Criar `Animal` no lote | Bloqueado (Gera Exception) | Permitido |
| Evento Morte (Lote) | Deduz do campo quantidade | Exige selecionar qual animal morreu |
| GMD e Histórico | Por estimativa de lote | Individualizado preciso |

---

## 5. Como migrar sem quebrar dados existentes? e 6. Como garantir compatibilidade?

A estratégia de evolução não-destrutiva:

1. **Schema Additive:** A migration define `DEFAULT 'AGREGADO'`. Automaticamente, todos os milhares de lotes que já existem no banco dos clientes assumem a modalidade Agregada.
2. **Compatibilidade de API:** O endpoint atual de `POST /pecuaria/lotes/` assume `tipo_controle = "AGREGADO"` se o campo for omitido. Nenhuma integração ou app mobile do campo quebra.
3. **Novo Endpoint (Fase 2):** Criar a rota de transição: `POST /pecuaria/lotes/{id}/converter-detalhado`.
   - Essa função exigiria receber um payload com a lista de animais individuais (brincos).
   - O sistema criaria os registros em `pec_animais` e validaria se a quantidade bate com a `quantidade_cabecas` anterior.
   - Bateu? `tipo_controle` muda para `DETALHADO`.

## Conclusão e Parecer Arquitetural

A adoção do Modelo Híbrido não apenas é viável, como é a única arquitetura tolerante a diferentes graus de adoção de tecnologia no campo (low-tech vs high-tech).

Com a adição simples do campo `tipo_controle` no model `LoteAnimal`, o sistema fica blindado contra inconsistências, e a implantação da Tabela de Animais Individuais (EXECUTION-02) poderá prosseguir de forma segura e sem regressões para as operações que já utilizam a plataforma hoje.

**Status Final:** Arquitetura Validada. Caminho livre para a execução da implementação do CRUD do Animal.
