# AgroSaaS Architecture Governance

Data de referência: 2026-06-20

## Objetivo

Definir o processo oficial de governança arquitetural do AgroSaaS para criação, alteração, aprovação e proteção das normas de arquitetura.

Esta governança protege especialmente:
- [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)

## Princípios

1. Toda norma arquitetural deve ter dono, escopo e status.
2. Normas imutáveis não podem ser alteradas sem processo formal e explícito.
3. Alteração arquitetural sem ADR é inválida.
4. Documentação tem precedência sobre memória operacional.
5. Código deve seguir a documentação, não o inverso.
6. Nenhuma IA pode violar normas imutáveis.

## Classificação das Normas

### Nível 1 - Imutável

Exemplos:
- AGRI-DOMAIN-001
- AGRI-DOMAIN-002

Regras:
- não podem ser alteradas diretamente;
- só podem ser substituídas por nova versão formalizada via ADR e aprovação;
- qualquer mudança exige justificativa de alto impacto e registro explícito de compatibilidade;
- são autoridade máxima do domínio que cobrem.

### Nível 2 - Estratégica

Exemplos:
- Domain Map
- Data Model
- Master Context

Regras:
- podem evoluir com mais frequência;
- alterações devem respeitar as normas imutáveis;
- exigem análise de impacto entre domínios;
- podem ser atualizadas para refletir evolução do produto e do domínio.

### Nível 3 - Operacional

Exemplos:
- Routing Map
- Engineering Playbook
- AI Rules

Regras:
- devem seguir as camadas superiores;
- podem mudar para acomodar operação, desde que não violem normas imutáveis;
- alterações devem ser rastreáveis em ADR quando afetarem semântica de domínio.

## Processo Oficial de Alteração

### Fluxo

```text
Proposta
↓
Análise
↓
ADR
↓
Aprovação
↓
Atualização documental
↓
Implementação
```

### Descrição das etapas

#### 1. Proposta

- registrar a motivação;
- identificar o documento impactado;
- descrever escopo, risco e objetivo.

#### 2. Análise

- avaliar impacto arquitetural, de domínio e de roteamento;
- verificar compatibilidade com normas imutáveis;
- identificar dependências e regressões potenciais.

#### 3. ADR

- toda alteração relevante deve gerar um ADR;
- o ADR deve registrar contexto, decisão, alternativas e consequências.

#### 4. Aprovação

- normas imutáveis exigem aprovação explícita de arquitetura;
- documentos estratégicos podem ser aprovados com revisão arquitetural;
- documentos operacionais podem ser aprovados pelo maintainer responsável, desde que respeitem as camadas superiores.

#### 5. Atualização documental

- atualizar os documentos normativos correspondentes;
- manter links cruzados e datas de revisão;
- refletir a decisão nos documentos dependentes.

#### 6. Implementação

- somente após a documentação estar consistente;
- mudanças de código devem seguir a norma aprovada;
- testes devem ser alinhados ao novo comportamento.

## Quando uma norma pode ser alterada?

### Norma Imutável

Só pode ser alterada se:
- houver ADR aprovado;
- houver justificativa de arquitetura superior;
- houver compatibilidade ou plano explícito de migração;
- a alteração não criar ambiguidade de fonte da verdade;
- a alteração não violar rastreabilidade, ESG ou Projeto Raízes.

### Norma Estratégica

Pode ser alterada quando:
- houver evolução real do produto;
- a mudança não conflitar com normas imutáveis;
- houver impacto documentado;
- houver atualização do ADR.

### Norma Operacional

Pode ser alterada quando:
- houver necessidade de operação ou roteamento;
- o ajuste não afetar semântica de domínio;
- o impacto for documentado;
- a mudança respeitar as normas superiores.

## Regras de Aprovação

### Pode aprovar mudanças em Nível 1

- governança arquitetural formal;
- responsável de arquitetura;
- revisão explícita com ADR.

### Pode aprovar mudanças em Nível 2

- arquitetura;
- manutenção técnica com revisão de impacto.

### Pode aprovar mudanças em Nível 3

- manutenção técnica;
- ownership do módulo;
- revisão de compatibilidade.

## ADR - Architectural Decision Record

### Quando criar ADR

Criar ADR quando a mudança:
- alterar norma;
- alterar fronteira de domínio;
- alterar cardinalidade;
- alterar fonte da verdade;
- alterar roteamento estrutural;
- alterar regras de rastreabilidade;
- alterar ESG, certificações ou Projeto Raízes;
- introduzir exceção em norma imutável.

### Onde registrar

- Diretório oficial: `docs/architecture/adr/`
- Um ADR por decisão relevante.
- ADRs devem ser referenciados pelos documentos normativos afetados.

### Padrão mínimo

Um ADR deve conter:
- contexto;
- decisão;
- alternativas consideradas;
- consequências;
- risco;
- data;
- status;
- vínculo com normas afetadas.

## IA Governance

### Regras para Codex, Cursor, Claude Code e agentes futuros

1. Nenhuma IA pode violar AGRI-DOMAIN-001.
2. Nenhuma IA pode violar AGRI-DOMAIN-002.
3. Nenhuma IA pode propor mudança estrutural sem consultar o Domain Map, Data Model e normas aplicáveis.
4. Toda alteração envolvendo propriedades, imóveis rurais, rastreabilidade, ESG, certificações ou Projeto Raízes exige consulta às normas e, quando aplicável, ADR.
5. IAs não podem criar domínio concorrente ou fonte oficial duplicada.
6. IAs não podem tratar documento normativo como sugestão.
7. IAs devem explicitar quando uma decisão é derivada de norma e quando é inferência de contexto.

## Regras de Proteção

É proibido:
- editar AGRI-DOMAIN-001 ou AGRI-DOMAIN-002 sem o fluxo formal;
- introduzir exceções silenciosas;
- contornar ADR;
- aplicar mudança de código antes da documentação;
- produzir norma nova que duplique ou contradiga norma imutável;
- apagar histórico de decisão;
- substituir fonte da verdade por conveniência de implementação.

## Regra de Regressão

Toda alteração arquitetural deve preservar:
- fronteira de domínio;
- cardinalidade oficial;
- ownership;
- rastreabilidade;
- ESG;
- Projeto Raízes;
- consistência com RLS e tenant isolation.

## Status das Normas

- AGRI-DOMAIN-001: protegida, imutável, norma oficial do domínio territorial e fundiário.
- AGRI-DOMAIN-002: protegida, imutável, norma oficial da entidade `PropriedadeImovel`.

## Conclusão

A governança arquitetural do AgroSaaS opera em três camadas:

- `Nível 1`: normas imutáveis.
- `Nível 2`: documentos estratégicos.
- `Nível 3`: documentos operacionais.

Toda mudança relevante deve seguir ADR, revisão arquitetural e compatibilidade com as normas protegidas.

