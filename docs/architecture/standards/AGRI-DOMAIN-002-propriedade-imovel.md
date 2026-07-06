# AGRI-DOMAIN-002

## Norma Oficial da Entidade `PropriedadeImovel`

**Status:** APROVADA

**Categoria:** Arquitetura de Domínio

**Tipo:** Regra Arquitetural Imutável

**Origem:** [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)

**Última Revisão:** 2026-06-20

---

# 1. Objetivo

Definir oficialmente a entidade oficial `PropriedadeImovel` como o vínculo normativo entre os domínios:

- `Propriedades`
- `Imóveis Rurais`

Esta norma estabelece:

- propósito do domínio;
- atributos mínimos;
- tipos de vínculo;
- regras de negócio;
- papel na rastreabilidade;
- papel em ESG, certificações e Projeto Raízes;
- regras imutáveis.

---

# 2. Definição

`PropriedadeImovel` é a entidade oficial de vínculo entre uma propriedade operacional e um imóvel rural legal.

Ela existe para representar:

- sobreposição territorial e fundiária;
- uso principal ou secundário de um imóvel por uma propriedade;
- arrendamento, parceria, comodato e uso compartilhado;
- rastreabilidade histórica;
- prova documental da origem territorial;
- integração entre operação, titularidade e compliance.

## Responsabilidade exclusiva

`PropriedadeImovel` é responsável apenas pelo relacionamento entre os domínios.

Ela não é:

- uma propriedade;
- um imóvel rural;
- um documento legal;
- uma produção;
- uma safra;
- uma matrícula;
- um contrato completo;
- uma avaliação patrimonial.

## O que não deve armazenar

É proibido armazenar em `PropriedadeImovel`:

- dados operacionais de safra;
- dados de produção;
- dados de titularidade completa;
- dados fundiários completos;
- dados cartoriais completos;
- dados fiscais completos;
- documentos em versão integral;
- regras de negócio de operação rural;
- cadastros de áreas territoriais.

---

# 3. Atributos Mínimos

## Obrigatórios

| Atributo | Status | Função |
|---|---|---|
| `tenant_id` | OBRIGATÓRIO | Isolamento multi-tenant |
| `propriedade_id` | OBRIGATÓRIO | FK da propriedade operacional |
| `imovel_rural_id` | OBRIGATÓRIO | FK do imóvel rural legal |
| `tipo_vinculo` | OBRIGATÓRIO | Natureza jurídica/operacional do vínculo |
| `ativo` | OBRIGATÓRIO | Estado vigente do vínculo |
| `data_inicio` | OBRIGATÓRIO | Início da vigência |
| `observacoes` | OBRIGATÓRIO | Notas de governança e auditoria |
| `origem_documental` | OBRIGATÓRIO | Base documental do vínculo |
| `created_at` | OBRIGATÓRIO | Auditoria temporal |
| `updated_at` | OBRIGATÓRIO | Auditoria temporal |

## Opcionais

| Atributo | Status | Função |
|---|---|---|
| `area_vinculada` | OPCIONAL | Área vinculada ao relacionamento |
| `percentual_vinculado` | OPCIONAL | Percentual da área ou da operação representada |
| `data_fim` | OPCIONAL | Encerramento da vigência |
| `vinculo_principal` | OPCIONAL | Marca de vínculo principal no contexto |
| `origem_referencia` | OPCIONAL | Referência resumida do documento fonte |
| `status_documental` | OPCIONAL | Estado de validação documental |
| `created_by` | OPCIONAL | Rastreio de autoria |
| `updated_by` | OPCIONAL | Rastreio de autoria |

## Futuro

| Atributo | Status | Função |
|---|---|---|
| `motivo_encerramento` | FUTURO | Justificativa de inativação |
| `versao_normativa` | FUTURO | Versionamento de regra de vínculo |
| `hash_documental` | FUTURO | Prova criptográfica de integridade |
| `origem_geoespacial` | FUTURO | Origem espacial do vínculo |
| `score_confianca` | FUTURO | Nível de confiabilidade do vínculo |

---

# 4. Tipos de Vínculo

## Enum oficial

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

## Definições e restrições

### `PROPRIEDADE_PRINCIPAL`
- Define a relação legal principal entre a propriedade operacional e o imóvel rural.
- Usar quando o imóvel for a base fundiária principal da operação.
- Restrições:
  - uma propriedade deve ter no máximo um vínculo principal ativo por vigência;
  - o vínculo principal deve ter origem documental explícita.

### `PROPRIEDADE_SECUNDARIA`
- Define vínculo complementar de suporte territorial ou fundiário.
- Usar quando a propriedade depender de outros imóveis além do principal.
- Restrições:
  - não substitui o vínculo principal;
  - não altera titularidade.

### `ARRENDAMENTO`
- Define vínculo contratual de arrendamento.
- Usar quando houver exploração mediante contrato de arrendamento.
- Restrições:
  - exige vigência;
  - exige origem documental;
  - pode ser parcial.

### `PARCERIA_RURAL`
- Define vínculo contratual de parceria rural.
- Usar quando houver exploração compartilhada por contrato de parceria.
- Restrições:
  - exige vigência;
  - exige origem documental;
  - pode ser parcial.

### `COMODATO`
- Define uso gratuito ou cessão de uso sem transferência de titularidade.
- Usar quando o imóvel for disponibilizado sem arrendamento ou parceria.
- Restrições:
  - exige vigência;
  - exige origem documental.

### `USO_COMPARTILHADO`
- Define utilização simultânea por mais de uma operação ou unidade organizacional.
- Usar quando o imóvel sustenta uso misto sem exclusividade.
- Restrições:
  - deve explicitar escopo do compartilhamento;
  - deve indicar área ou percentual quando aplicável.

### `USO_TEMPORARIO`
- Define uso com validade curta ou transitória.
- Usar para janelas temporais de ocupação, execução ou apoio.
- Restrições:
  - exige data de início e fim;
  - não altera titularidade.

### `INTEGRACAO`
- Define vínculo administrativo de integração ou consolidação documental.
- Usar em transições, importações, fusões operacionais e saneamento.
- Restrições:
  - não cria efeito jurídico por si só;
  - deve ser acompanhado de origem documental.

### `OUTRO`
- Define vínculo não classificado.
- Usar apenas quando o caso real não se enquadrar nos tipos oficiais.
- Restrições:
  - uso excepcional;
  - deve justificar a classificação em `observacoes`.

---

# 5. Regras de Negócio

1. `PropriedadeImovel` é uma entidade de primeira classe e não uma tabela auxiliar.
2. Um vínculo pode ser principal, mas a propriedade não pode ter mais de um principal ativo na mesma vigência.
3. Um imóvel rural pode participar de múltiplos vínculos.
4. Uma propriedade pode participar de múltiplos vínculos.
5. Sobreposição é permitida apenas quando o tipo de vínculo suportar esse comportamento.
6. Todo vínculo deve ter vigência explícita.
7. Todo vínculo deve ter origem documental explícita.
8. `percentual_vinculado` e `area_vinculada` devem ser coerentes entre si quando ambos existirem.
9. O vínculo não altera titularidade.
10. O vínculo não altera a operação.
11. O vínculo não substitui o contrato, a matrícula, o CAR, o CCIR ou o ITR.
12. O vínculo deve permitir histórico completo.
13. Um vínculo encerrado continua rastreável.
14. Todo vínculo relevante para produção, ESG ou certificação deve ser auditável.

---

# 6. Rastreabilidade

`PropriedadeImovel` é o elo que garante a cadeia:

```text
Produção
↓
Safra
↓
Talhão
↓
Propriedade
↓
PropriedadeImovel
↓
Imóvel Rural
↓
Documentação
↓
Titularidade
```

## Como provar origem

- pela propriedade operacional;
- pela safra associada;
- pelo talhão de origem;
- pelo vínculo `PropriedadeImovel`;
- pela documentação fundiária do imóvel.

## Como provar titularidade

- pelo imóvel rural;
- pelos documentos legais;
- pelos proprietários e representantes;
- pelo vínculo histórico que mostra qual operação estava sustentada por qual imóvel em cada período.

## Como provar vínculo histórico

- guardando início e fim de vigência;
- registrando origem documental;
- preservando vínculos encerrados;
- evitando sobrescrever relações anteriores.

---

# 7. ESG, Certificações e Cadeia de Custódia

`PropriedadeImovel` contribui para:

- ESG;
- carbono;
- certificações;
- auditorias;
- cadeia de custódia;
- rastreabilidade de exportação.

## Papel normativo

- comprovar qual imóvel sustentou qual operação;
- demonstrar coerência entre uso territorial e base legal;
- sustentar auditorias de origem;
- preservar o histórico necessário para certificações;
- apoiar relatórios de carbono e recuperação ambiental.

---

# 8. Projeto Raízes

`PropriedadeImovel` deve ser usada para:

- rastrear origem;
- comprovar documentação;
- comprovar titularidade;
- manter histórico de alterações;
- evitar perda de cadeia de custódia em operações complexas.

Toda produção orientada ao Projeto Raízes deve poder ser vinculada:

```text
Produção -> Safra -> Talhão -> Propriedade -> PropriedadeImovel -> Imóvel Rural
```

---

# 9. Ownership

| Informação | Dono |
|---|---|
| Operação rural | `Propriedade` |
| Titularidade legal | `Imóvel Rural` |
| Vínculo entre operação e imóvel | `PropriedadeImovel` |
| Vigência do vínculo | `PropriedadeImovel` |
| Área vinculada | `PropriedadeImovel` |
| Percentual vinculado | `PropriedadeImovel` |
| Origem documental do vínculo | `PropriedadeImovel` |
| Matrícula | `Imóvel Rural` |
| CAR / CCIR / ITR / NIRF / SIGEF | `Imóvel Rural` |
| Talhões / Glebas / Pastagens / Infraestrutura | `Propriedade` |
| ESG / Certificações / Carbono | Compartilhado, com prova ancorada em `PropriedadeImovel` |
| Cadeia de Custódia | Compartilhado, com prova ancorada em `PropriedadeImovel` |

---

# 10. Regras Imutáveis

É proibido:

- criar vínculo sem `tenant_id`;
- criar vínculo sem `propriedade_id`;
- criar vínculo sem `imovel_rural_id`;
- criar vínculo sem `tipo_vinculo`;
- criar vínculo sem vigência;
- criar vínculo sem origem documental;
- ter dois vínculos principais ativos para a mesma propriedade na mesma vigência;
- usar `PropriedadeImovel` para armazenar dados de operação;
- usar `PropriedadeImovel` para armazenar dados de titularidade completa;
- editar historicamente um vínculo já encerrado;
- tratar um vínculo como substituto da titularidade;
- tratar um vínculo como substituto da operação;
- ignorar `PropriedadeImovel` em rastreabilidade, ESG, certificações ou Projeto Raízes.

---

# 11. Norma Oficial

`PropriedadeImovel` é uma entidade oficial de domínio.

Ela não é tabela auxiliar.

Ela não é campo derivado.

Ela não é detalhe de implementação.

Ela é o vínculo normativo que torna possível a convivência correta entre operação territorial e prova fundiária no AgroSaaS.

