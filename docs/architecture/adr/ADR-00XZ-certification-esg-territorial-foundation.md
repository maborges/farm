# ADR-00XZ - Certificações, ESG e Projeto Raízes sobre a Fundação Territorial/Fundiária

Status: Proposto
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## Contexto

O AgroSaaS já consolidou a fronteira entre:

- `Propriedade`, como fonte oficial operacional, territorial e produtiva;
- `Imóvel Rural`, como fonte oficial jurídica, patrimonial, documental e fiscal;
- `PropriedadeImovel`, como vínculo canônico N:N entre os dois domínios.

Além disso, o produto já possui:

- rastreabilidade comercial e documental;
- passaporte e snapshot imutável;
- documentos ambientais e legais;
- relatórios ESG;
- treinamentos e EPIs;
- auditoria e trilhas de escrita.

A questão arquitetural desta ADR é decidir se Certificações, ESG e Projeto Raízes devem criar um novo domínio territorial paralelo ou consumir a fundação existente.

## Decisão

Adotar oficialmente que Certificações, ESG e Projeto Raízes:

1. consumem `Propriedade`, `Imóvel Rural` e `PropriedadeImovel` como fontes oficiais upstream;
2. não criam uma nova fonte oficial territorial ou fundiária;
3. não duplicam CAR, matrícula, CCIR, ITR, NIRF ou SIGEF;
4. escrevem apenas artefatos próprios do domínio de conformidade, como evidências, respostas, auditorias, não conformidades, pareceres e snapshots;
5. tratam Projeto Raízes como um caso de uso de prova documental e rastreabilidade, não como domínio paralelo.

## Alternativas Consideradas

- Criar um domínio territorial paralelo para certificação
- Duplicar dados fundiários dentro de Certificações/ESG
- Manter Certificações/ESG apenas como documento solto sem vínculo territorial
- Consumir as fontes oficiais existentes e escrever apenas o que é próprio do domínio

## Consequências

### Positivas

- elimina duplicidade de verdade territorial/fundiária;
- preserva a cardinalidade oficial;
- reduz risco de inconsistência regulatória;
- simplifica auditoria e governança;
- fortalece Projeto Raízes com prova documental única;
- permite evolução incremental sem migration estrutural imediata.

### Negativas

- o domínio de Certificações/ESG depende fortemente de leituras consistentes;
- a modelagem funcional precisa respeitar várias fronteiras de domínio;
- alguns casos de uso podem exigir novos agregados de leitura.

## Impacto em Normas

- AGRI-DOMAIN-001: sem impacto, com reforço de conformidade
- AGRI-DOMAIN-002: sem impacto, com reforço de rastreabilidade de vínculo
- AGROSAAS data model: sem impacto estrutural imediato

## Impacto em Domínios

- Territorial: leitura apenas
- Fundiário: leitura apenas
- Operacional: leitura apenas quando necessário para auditoria
- Ambiental: leitura e derivação de score/relatório
- ESG: escrita local de evidências e relatórios
- Certificações: escrita local de checklists, auditorias e snapshots
- Projeto Raízes: leitura da cadeia de custódia e prova documental

## Impacto Técnico

- Banco: nenhum novo modelo territorial necessário nesta fase
- APIs: consumo das rotas existentes, sem alteração de contrato público nesta ADR
- Frontend: nenhuma mudança mandatória nesta fase
- RLS: mantido integralmente
- Relatórios: consolidação em artefatos do domínio consumidor
- Rastreabilidade: preservada até o imóvel rural

## Plano de Migração

Não há migration estrutural obrigatória para esta decisão.

A implementação deve seguir a ordem:

1. consumir fontes oficiais existentes;
2. modelar apenas artefatos de domínio de certificação/ESG;
3. manter evidências e auditorias no domínio consumidor;
4. validar que nenhuma escrita territorial/fundiária surge em paralelo.

## Riscos

- criação acidental de duplicidade de CAR/documentos;
- tentação de transformar questionários em fonte oficial;
- expansão indevida de escopo para criar um "territorial de certificações";
- sobrecarga de consultas se os agregados de leitura não forem bem definidos.

## Aprovação

- Revisor de Arquitetura: pendente
- Owner de Domínio: pendente
- Data: 2026-06-21

## Referências

- [AGRI-DOMAIN-001-territorial-fundiario.md](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002-propriedade-imovel.md](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-routing-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
