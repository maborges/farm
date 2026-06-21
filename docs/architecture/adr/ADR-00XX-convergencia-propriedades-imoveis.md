# ADR-00XX - Convergência entre Propriedades e Imóveis Rurais

Status: Aprovado
Data: 2026-06-21
Autores: AgroSaaS Architecture / Codex

## 1. Contexto

O AgroSaaS já possui dois domínios ativos e válidos:

- `Propriedades`, responsável pelo território operacional, territorial e produtivo;
- `Imóveis Rurais`, responsável pela titularidade, matrícula, cartório, CAR, CCIR, ITR, NIRF, SIGEF, contratos e avaliações.

A análise arquitetural consolidada em `AGRI-DOMAIN-001`, `AGRI-DOMAIN-002` e `ARCH-IMPLEMENTATION-01` identificou:

- sobreposição de responsabilidades;
- duplicidade de fonte da verdade para dados fundiários;
- ausência de entidade canônica de vínculo;
- necessidade de rastreabilidade completa até o imóvel legal;
- necessidade de suporte consistente para ESG, Certificações e Projeto Raízes.

Esta ADR formaliza a decisão arquitetural oficial para a convergência dos domínios sem criação de um terceiro domínio concorrente.

## 2. Problema

O estado atual apresenta três problemas centrais:

1. `Propriedades` ainda concentra alguns dados fundiários e documentais que pertencem ao domínio legal.
2. `Imóveis Rurais` já é a fonte oficial do lastro fundiário, mas não existe vínculo canônico obrigatório entre os domínios.
3. O sistema não possui uma forma única de representar, auditar e rastrear a relação entre operação territorial e propriedade legal.

Sem essa convergência, o AgroSaaS fica exposto a:

- inconsistência cadastral;
- divergência entre operação e matrícula;
- fragilidade documental para auditoria;
- ambiguidade para certificações;
- rastreabilidade incompleta para Projeto Raízes;
- duplicação de dados e regras.

## 3. Decisão

O AgroSaaS adota oficialmente a convergência entre `Propriedades` e `Imóveis Rurais` com as seguintes regras:

1. Não será criado um terceiro domínio para substituir os dois existentes.
2. `Propriedades` permanece como fonte da verdade do território operacional, incluindo glebas, talhões, pastagens, infraestrutura, produção, safra e operação.
3. `Imóveis Rurais` permanece como fonte da verdade da titularidade, matrícula, cartório, CAR, CCIR, ITR, NIRF, SIGEF, contratos e avaliações.
4. A cardinalidade oficial entre `Propriedade` e `Imóvel Rural` é `N:N`.
5. A entidade canônica obrigatória de vínculo é `PropriedadeImovel`.
6. Toda rastreabilidade relevante deve alcançar o `Imóvel Rural`.
7. Toda fonte da verdade deve ser única por dado.
8. Dados espelhados entre domínios serão apenas derivados e não editáveis fora da origem oficial.

## 4. Alternativas Consideradas

### Manter tudo em Propriedades

- Rejeitada.
- Viola a separação entre operação e titularidade.
- Reforça duplicidade de dados fundiários.
- Fragiliza auditoria, ESG e Projeto Raízes.

### Manter tudo em Imóveis Rurais

- Rejeitada.
- Descaracteriza o domínio operacional e territorial.
- Inviabiliza a modelagem natural de talhões, glebas, pastagens, infraestrutura e produção.
- Rompe o ciclo operacional do AgroSaaS.

### Criar terceiro domínio

- Rejeitada.
- Gera duplicação de bounded contexts.
- Aumenta custo de manutenção e de governança.
- Cria confusão sobre a fonte da verdade.

### Modelo N:N com `PropriedadeImovel`

- Aprovada.
- Preserva as fronteiras de domínio.
- Representa cenários reais de arrendamento, parceria, compartilhamento, multiuso e sobreposição territorial/fundiária.
- Suporta rastreabilidade, ESG, certificações e Projeto Raízes.

## 5. Consequências Positivas

- Uma única fonte da verdade para cada dado.
- Separação clara entre operação territorial e lastro fundiário.
- Representação adequada de cenários complexos do agronegócio.
- Rastreabilidade completa até o imóvel legal correspondente.
- Melhor suporte para auditoria, certificações e ESG.
- Base sólida para Projeto Raízes.
- Redução de ambiguidade arquitetural.

## 6. Consequências Negativas

- A convergência exige migração planejada.
- Haverá impacto em banco, APIs e frontend.
- Campos duplicados precisarão ser desnormalizados ou descontinuados.
- Pode existir compatibilidade retroativa temporária durante a transição.
- A implementação demanda governança rígida e monitoramento de regressões.

## 7. Impacto no Banco

- Criação da tabela `propriedade_imovel`.
- Revisão dos campos fundiários duplicados em `cadastros_areas_rurais`.
- Consolidação de `imoveis_rurais` como origem fundiária oficial.
- Potencial migração de dados históricos.
- Necessidade de constraints para garantir:
  - unicidade lógica do vínculo por contexto;
  - vigência coerente;
  - integridade referencial;
  - isolamento por tenant.

### Classificação do impacto

- Impacto geral: alto.
- Risco de migração: alto.
- Complexidade de integridade: alta.

## 8. Impacto nas APIs

- As APIs de `Propriedades` devem deixar de tratar dados fundiários como origem primária.
- As APIs de `Imóveis Rurais` devem ser a origem oficial de documentação fundiária.
- Uma nova API ou recurso canônico para `PropriedadeImovel` será necessária.
- Rotas legadas poderão permanecer por período de transição, mas apenas como compatibilidade.

### Classificação do impacto

- Impacto geral: alto.
- Risco de regressão contratual: alto.
- Necessidade de versionamento: média a alta.

## 9. Impacto no Frontend

- As telas já existentes podem ser reaproveitadas, mas com semântica corrigida.
- `Propriedades` deve exibir operação e território.
- `Imóveis Rurais` deve exibir documentação, titularidade e lastro legal.
- A interface de vínculo entre ambos precisará ser criada ou ampliada.
- A rastreabilidade visual deve atravessar `PropriedadeImovel` até o imóvel legal.

### Classificação do impacto

- Impacto geral: médio a alto.
- Risco de confusão de UX durante a transição: médio.

## 10. Impacto em ESG

A decisão melhora o suporte a ESG porque:

- separa evidência operacional de prova legal;
- fortalece cadeia de custódia;
- melhora auditoria de origem;
- reduz risco de inconsistência documental;
- facilita inventários e comprovações ambientais.

## 11. Impacto no Projeto Raízes

O Projeto Raízes passa a ter base arquitetural mais sólida porque:

- a produção pode ser rastreada até a safra, o talhão, a propriedade, o vínculo canônico e o imóvel legal;
- a origem fundiária fica explicitamente comprovável;
- a documentação passa a ser auditável por camada;
- a cadeia de custódia deixa de depender de campos duplicados ou implícitos.

## 12. Plano de Implementação

### Fase 1 - Preparação documental

- congelar a decisão arquitetural nesta ADR;
- referenciar esta ADR em documentos normativos e estratégicos;
- alinhar equipes e agentes de IA à nova fronteira de domínio.

### Fase 2 - Modelo de dados

- introduzir `PropriedadeImovel` como entidade canônica;
- definir constraints, cardinalidade e vigência;
- mapear campos a migrar, manter ou descontinuar.

### Fase 3 - Banco de dados

- criar a tabela de vínculo;
- preparar migração assistida dos dados duplicados;
- manter compatibilidade de leitura durante a transição.

### Fase 4 - Backend

- refatorar APIs para respeitar fontes oficiais;
- centralizar escrita de dados fundiários em `Imóveis Rurais`;
- centralizar escrita do vínculo em `PropriedadeImovel`.

### Fase 5 - Frontend

- separar claramente telas operacionais e fundiárias;
- expor o vínculo canônico nos fluxos relevantes;
- revisar rastreabilidade e visualizações de auditoria.

### Fase 6 - Rastreabilidade, ESG e Raízes

- integrar o vínculo canônico aos fluxos de origem;
- validar o encadeamento até o imóvel rural;
- reforçar relatórios, auditorias e certificações.

## 13. Critérios de Aceite

Esta ADR será considerada implementável quando:

- existir uma única fonte da verdade para cada dado;
- `PropriedadeImovel` existir como entidade obrigatória;
- a rastreabilidade alcançar o `Imóvel Rural`;
- a solução suportar ESG;
- a solução suportar Certificações;
- a solução suportar Projeto Raízes;
- não existir terceiro domínio concorrente;
- dados espelhados não puderem ser editados fora da origem.

## 14. Critérios de Rollback

A implementação deve ser revertida ou pausada se ocorrer qualquer um dos casos abaixo:

- perda de integridade referencial;
- divergência entre operação e lastro legal;
- quebra de rastreabilidade até o imóvel rural;
- inconsistência em relatórios de ESG ou certificação;
- falha de migração que gere perda de dados históricos;
- duplicidade de fonte da verdade reaparecendo em produção.

Rollback recomendado:

- manter leitura das estruturas antigas até estabilização;
- desativar escrita nas rotas novas que causem inconsistência;
- restaurar a origem oficial previamente validada;
- registrar o incidente em ADR complementar se a reversão alterar a fronteira.

## 15. Riscos

- Risco de duplicidade residual durante a migração.
- Risco de contratos de API não refletirem a nova fronteira.
- Risco de telas antigas continuarem sugerindo fonte incorreta.
- Risco de inconsistência histórica em dados já persistidos.
- Risco de relatórios de auditoria exibirem semântica ambígua.
- Risco de sobreposição indevida entre Propriedades e Imóveis Rurais se a migração for parcial.

## 16. Próximas Etapas

1. Publicar a decisão como norma de referência nos documentos dependentes.
2. Planejar e aprovar o modelo físico de `PropriedadeImovel`.
3. Definir sequência de migração e compatibilidade retroativa.
4. Atualizar contratos de API.
5. Ajustar frontend.
6. Validar rastreabilidade, ESG e Projeto Raízes em cenário real.

## Impacto em Normas

- AGRI-DOMAIN-001: sem impacto conceitual; esta ADR operacionaliza a norma.
- AGRI-DOMAIN-002: sem impacto conceitual; esta ADR reforça a entidade canônica já definida.
- Agrosaas Architecture Governance: sem impacto; a ADR segue o processo exigido.
- Data Model: impacto relevante, pois explicita a cardinalidade e o vínculo canônico.
- Domain Map: impacto relevante, pois formaliza a fronteira entre os dois domínios.

## Impacto em Domínios

- Territorial: mantém ownership operacional.
- Fundiário: mantém ownership legal e documental.
- Operacional: preserva execução, produção e safra.
- Ambiental: melhora lastro e comprovação.
- ESG: melhora auditoria e origem.
- Certificações: melhora conformidade.
- Projeto Raízes: melhora rastreabilidade de origem e cadeia de custódia.

## Impacto Técnico

- Banco: alta alteração estrutural.
- APIs: alto impacto de contratos e leitura.
- Frontend: impacto moderado, com ajustes semânticos.
- RLS: deve ser preservado.
- Relatórios: devem ser revalidados.
- Rastreabilidade: passa a ser endereçada por vínculo canônico obrigatório.

## Plano de Migração

1. Criar a estrutura de vínculo `PropriedadeImovel`.
2. Mapear dados duplicados e escolher a origem oficial por campo.
3. Migrar leituras e escritas para as fontes corretas.
4. Manter compatibilidade temporária com campos legados.
5. Encerrar gradualmente a escrita em estruturas duplicadas.
6. Validar histórico, rastreabilidade e relatórios.

## Aprovação

- Revisor de Arquitetura: AgroSaaS Architecture
- Owner de Domínio: Domínio Territorial/Fundiário
- Data: 2026-06-21

## Referencias

- [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)
- [ARCH-IMPLEMENTATION-01](/opt/lampp/htdocs/farm/docs/analysis/ARCH-IMPLEMENTATION-01-convergencia-propriedades-imoveis.md)
- [agrosaas-architecture-governance.md](/opt/lampp/htdocs/farm/docs/architecture/governance/agrosaas-architecture-governance.md)
- [agrosaas-data-model.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [agrosaas-domain-map.md](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-domain-map.md)

