# AGRI-DOMAIN-001 - Impact Report

Data: 2026-06-20

## Objetivo

Registrar a incorporação da norma AGRI-DOMAIN-001 ao ecossistema documental do AgroSaaS.

## Documentos Alterados

- [agrosaas-master-context.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-master-context.md)
- [agrosaas-ai-rules.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)

## Divergências Encontradas

### 1. Master Context

- Não havia seção formal de domínio territorial e fundiário.
- A norma AGRI-DOMAIN-001 ainda não era citada como referência obrigatória.

### 2. AI Rules

- Não existia regra explícita exigindo consulta à norma antes de alterações envolvendo propriedades, imóveis rurais, rastreabilidade, ESG ou certificações.

### 3. Data Model

- O documento citava `Propriedades / Áreas Rurais`, mas não formalizava a cardinalidade `N:N`.
- A entidade oficial `PropriedadeImovel` não estava explicitada.
- O ownership territorial/fundiário não estava separado em blocos normativos.

### 4. Domain Map

- Não existiam domínios explícitos chamados `Territorial` e `Fundiário`.
- A relação entre os dois domínios não estava formalizada como dependência oficial.

### 5. Routing Map

- As rotas de `Propriedades` e `Imóveis Rurais` apareciam separadas na prática, mas sem leitura normativa consolidada.
- Não havia camada documental indicando que essas rotas fazem parte do domínio territorial/fundiário.

## Correções Realizadas

### Master Context

- Inserida seção `Domínio Territorial e Fundiário`.
- Adicionada referência obrigatória à norma AGRI-DOMAIN-001.

### AI Rules

- Adicionada regra obrigatória para consulta da norma antes de qualquer alteração ligada a propriedades, imóveis rurais, rastreabilidade, ESG ou certificações.

### Data Model

- Adicionada a entidade `Imóveis Rurais` como núcleo jurídico/patrimonial/documental/fiscal.
- Formalizada a cardinalidade oficial `N:N` entre `Propriedade` e `Imóvel Rural`.
- Formalizada a entidade oficial `PropriedadeImovel`.
- Declarado o ownership por domínio.

### Domain Map

- Adicionados os domínios `Territorial` e `Fundiário`.
- Registrada a dependência entre território e fundiário via vínculo oficial.
- Explicitadas as restrições de não sobreposição.

### Routing Map

- Criada a leitura normativa da superfície `Territorial & Fundiário`.
- Identificadas as rotas impactadas:
  - `/api/v1/cadastros/areas-rurais`
  - `/api/v1/imoveis`
  - `/api/v1/imoveis/arrendamentos`
  - `/api/v1/imoveis/avaliacoes`
- Atualizada a matriz de cobertura para reconhecer o conjunto territorial/fundiário.

## Riscos Identificados

### 1. Drift entre documento e implementação

A documentação passou a reconhecer formalmente a norma, mas a implementação de código ainda segue o estado atual do repositório. Isso cria risco de divergência futura se novos desenvolvimentos ignorarem a fronteira definida.

### 2. Duplicidade operacional vs. fundiária

Há risco de campos como área, município, UF e coordenadas continuarem sendo tratados de forma ambígua em telas ou integrações se a regra documental não for seguida.

### 3. Rastreabilidade incompleta

A cadeia de custódia depende da utilização consistente da entidade de vínculo `PropriedadeImovel`. Sem isso, dashboards e relatórios podem perder precisão.

### 4. ESG e certificações

Se ESG, certificações e carbono forem tratados como módulos isolados sem consultar a norma, a governança documental pode voltar a criar fontes concorrentes.

## Próximos Passos

1. Manter AGRI-DOMAIN-001 como referência obrigatória em revisão arquitetural.
2. Exigir consulta à norma em qualquer alteração de:
   - propriedades;
   - imóveis rurais;
   - rastreabilidade;
   - ESG;
   - certificações;
   - Projeto Raízes.
3. Usar `AGRI-DOMAIN-001` como base para revisão de requisitos de dados e contratos de API quando houver evolução de implementação.
4. Monitorar documentação e código para evitar regressão semântica entre domínio territorial e fundiário.

## Status Final

AGRI-DOMAIN-001 incorporada como norma oficial do AgroSaaS para o domínio territorial e fundiário.

