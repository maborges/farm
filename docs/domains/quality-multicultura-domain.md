# Domínio: Motor de Qualidade Multicultura

## 1. Visão Geral e Conceitos do Domínio

Para que o AgroSaaS consiga atender qualquer tipo de produtor ou originador (fazenda, algodoeira, cooperativa ou frigorífico), o controle de qualidade não pode ser "hardcoded" para uma cultura específica. O motor deve ser **dinâmico e genérico**.

### Glossário de Domínio

- **Protocolo de Qualidade (QualityProtocol):** É o "template" ou "tabela de regras" que define quais parâmetros serão medidos para um determinado produto. Exemplo: *Protocolo MAPA IN 11/2007 (Soja)* ou *Protocolo SCA (Café)*.
- **Critério (QualityCriterion):** É a variável individual a ser medida dentro de um protocolo, contendo regras de validação (ex: mínimo, máximo, unidade de medida). Exemplo: *Umidade (%)*, *Impurezas (%)*, *Pontuação SCA*.
- **Laudo (QualityReport):** É a instância de avaliação, o documento gerado em uma data específica por um classificador para um Lote ou Romaneio específico.
- **Resultado (QualityResult):** O valor aferido na vida real para um determinado critério dentro de um laudo. Exemplo: *15.2% de Umidade*.
- **Desconto/Prêmio (QualityAdjustment):** A consequência financeira ou física do resultado. Se a soja está com 15% de umidade (o padrão é 14%), o desconto aplica uma fórmula que subtrai o peso líquido a ser pago ao produtor. Se o café tira 85 pontos SCA, aplica-se um prêmio financeiro de +15% no valor da saca.

---

## 2. Modelagem de Entidades (Proposta de Schema)

```typescript
// Define o tipo de avaliação (numérico, booleano, enumerador)
enum CriterionType {
  NUMERIC,     // ex: 14.5 (%)
  ENUM,        // ex: "Bebida Dura", "Mole", "Rio"
  BOOLEAN      // ex: Aprovado / Reprovado
}

// O Template Padrão
interface QualityProtocol {
  id: string;
  name: string;                // "Soja - Padrão MAPA 14%"
  targetProduct: string;       // "SOJA_GRAO"
  active: boolean;
}

// A Regra de Medição
interface QualityCriterion {
  id: string;
  protocolId: string;
  name: string;                // "Umidade"
  type: CriterionType;
  unit?: string;               // "%"
  minAcceptable?: number;      // 0
  maxAcceptable?: number;      // 30
  standardValue?: number;      // 14.0 (a partir daqui gera desconto/prêmio)
}

// O Laudo Executado (Ligado a um Romaneio ou Lote)
interface QualityReport {
  id: string;
  protocolId: string;
  sourceEntity: 'ROMANEIO' | 'LOTE_BENEFICIADO' | 'LOTE_ESTOQUE';
  sourceEntityId: string;      // ID do Romaneio ou Lote
  evaluatorId: string;         // Quem fez o laudo
  evaluatedAt: Date;
  status: 'DRAFT' | 'APPROVED' | 'REJECTED';
}

// A Aferição
interface QualityResult {
  id: string;
  reportId: string;
  criterionId: string;
  valueNumeric?: number;       // 15.2
  valueString?: string;        // "Mole"
}

// A Consequência Econômica (Gatilho automático ou manual)
interface QualityAdjustment {
  id: string;
  reportId: string;
  type: 'DISCOUNT_WEIGHT' | 'DISCOUNT_FINANCIAL' | 'PREMIUM_FINANCIAL';
  value: number;               // -150 (kg a descontar) ou +500 (reais de prêmio)
  reason: string;              // "Excesso de umidade > 14%"
}
```

---

## 3. Integração com Domínios Existentes

O motor de qualidade atua como um *Middleware* ou *Hook* que intercepta a transição de entidades no AgroSaaS.

| Domínio Alvo | Como a Qualidade se Integra |
|---|---|
| **Romaneios (Entrada)** | Ao registrar a pesagem bruta/tara de um caminhão, o sistema exige/sugere um Laudo de Classificação. O peso líquido comercial a ser pago já considera os *Descontos de Peso* do `QualityAdjustment`. |
| **Beneficiamento** | O laudo de entrada determina o potencial do lote. O laudo de saída determina se o café bica corrida atingiu a peneira/SCA desejados, justificando a *quebra*. |
| **Lotes / Estoque** | O Lote (`estoque`) passa a ter a propriedade `qualityReportId`. Um lote de Milho com 16% de umidade não pode ser misturado (blend) com um lote de 12% sem recálculo ponderado. |
| **Comercialização Futura** | Os Contratos e Fixações travam um preço *Base* (ex: R$ 1.100 a saca para bebida Dura). Na entrega física (Romaneio), se o Laudo apontar bebida Riada, o `QualityAdjustment` aplica o deságio do contrato automaticamente. |

---

## 4. Exemplos Práticos por Cultura

O quão aderente é este modelo para diferentes cadeias?

### ☕ Café
- **Protocolo:** *Exportação NY 2 / SCA*
- **Critérios:** Umidade (Numérico), Peneira 16 acima (Numérico %), Defeitos Equivalentes (Numérico), Pontuação SCA (Numérico), Bebida (Enum: Estritamente Mole, Mole, Dura, Riada, Rio).
- **Ajuste:** Café > 84 pts SCA gera `PREMIUM_FINANCIAL` (ágio) de +15%. Bebida Riada gera `DISCOUNT_FINANCIAL` (deságio) de -20%.

### 🍫 Cacau
- **Protocolo:** *Tipo 1 - Padrão Amêndoa Fermentada*
- **Critérios:** Umidade (Num), Prova de Corte - Amêndoas Ardidas (Num %), Amêndoas Violetas (Num %).
- **Ajuste:** Amêndoas ardidas > 3% barram o recebimento (`REJECTED`) ou aplicam forte deságio.

### 🌿 Soja
- **Protocolo:** *Padrão MAPA IN 11/2007*
- **Critérios:** Umidade (Padrão 14%), Impurezas (Padrão 1%), Avariados (Padrão 8%), Esverdeados.
- **Ajuste:** Caminhão chegou com 16% de umidade. Gera `DISCOUNT_WEIGHT` (desconto de peso comercial e taxa de secagem) sobre o romaneio.

### 🌽 Milho
- **Protocolo:** *Padrão Grão*
- **Critérios:** Umidade (14%), Grãos Quebrados/Brotados (Padrão 3%), Grãos Ardidos (1%).
- **Ajuste:** Semelhante à soja, descontos progressivos em tabela geram quebra de peso comercial do romaneio.

### ☁️ Algodão
- **Protocolo:** *Classificação Visual / HVI (High Volume Instrument)*
- **Critérios:** Micronaire (espessura), Comprimento (mm), Resistência (gf/tex), Cor.
- **Ajuste:** Os fardos de algodão são precificados milimetricamente por esses índices na bolsa de NY.

### 🐄 Pecuária
- **Protocolo:** *Abate - Rendimento de Carcaça*
- **Critérios:** Peso Vivo (kg), Peso Carcaça Quente (kg), Rendimento (%), Acabamento de Gordura (Enum: Escasso, Mediano, Uniforme, Excessivo), pH da carne.
- **Ajuste:** Rendimento < 50% ou acabamento "Escasso" pode perder o prêmio de exportação (ex: Cota Hilton / China).
