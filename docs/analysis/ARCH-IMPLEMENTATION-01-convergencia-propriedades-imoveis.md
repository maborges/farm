# ARCH-IMPLEMENTATION-01 — PLANO DE CONVERGÊNCIA PROPRIEDADES X IMÓVEIS RURAIS

## Base de análise

Referências obrigatórias consideradas:

- [AGRI-DOMAIN-001](../architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002](../architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)
- [Governança Arquitetural](../architecture/governance/agrosaas-architecture-governance.md)
- [Master Context](../architecture/agrosaas-master-context.md)
- [Domain Map](../architecture/agrosaas-domain-map.md)
- [Data Model](../architecture/agrosaas-data-model.md)
- [Routing Map](../architecture/agrosaas-routing-map.md)

Escopo técnico analisado no código-fonte:

- Models SQLAlchemy
- Migrations Alembic
- Schemas Pydantic
- Routers FastAPI
- Páginas Next.js
- Componentes relacionados
- Relatórios e módulos documentados

Conclusão executiva:

- O AgroSaaS já possui dois domínios ativos e parcialmente sobrepostos: `Propriedades` e `Imóveis Rurais`.
- O domínio `Propriedades` está correto como camada operacional, territorial e produtiva.
- O domínio `Imóveis Rurais` está correto como camada legal, documental, patrimonial e fiscal.
- A convergência ainda não está pronta para implementação porque existem duplicidades de fonte da verdade e ausência de entidade canônica de vínculo.

## 1. Inventário atual

### Inventário técnico

#### Domínio Propriedades

| Arquivo | Responsabilidade | Status |
|---|---|---|
| [services/api/core/cadastros/propriedades/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/models.py) | Modelo territorial principal (`cadastros_areas_rurais`) e entidades coligadas de matrículas, registros ambientais, infraestrutura, arquivos geo e valores patrimoniais | Parcialmente alinhado; com sobreposição fundiária e ambiental |
| [services/api/core/cadastros/propriedades/router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/router.py) | API de áreas rurais, árvore hierárquica, matrículas, registros ambientais e valores patrimoniais | Ativo; concentra responsabilidades além do puramente operacional |
| [services/api/core/cadastros/propriedades/schemas.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/schemas.py) | Contratos de entrada e saída do módulo territorial | Ativo |
| [services/api/core/cadastros/propriedades/service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/service.py) | Regras de negócio do módulo territorial | Ativo |
| [services/api/core/cadastros/propriedades/propriedade_router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/propriedade_router.py) | Rotas operacionais de propriedades | Ativo |
| [services/api/core/cadastros/propriedades/propriedade_hierarquia_router.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/propriedade_hierarquia_router.py) | Rotas da hierarquia territorial | Ativo |
| [services/api/core/cadastros/propriedades/propriedade_service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/propriedade_service.py) | Serviços de propriedades | Ativo |
| [services/api/core/cadastros/propriedades/hierarquia_service.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/propriedades/hierarquia_service.py) | Estrutura hierárquica e operações de árvore | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx) | Entrada do cadastro de propriedades | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx) | Editor territorial e geoespacial | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx) | Gestão de talhões | Ativo |
| [apps/web/src/app/(dashboard)/dashboard/settings/propriedades/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/propriedades/page.tsx) | Configurações de propriedades | Ativo |
| [apps/web/src/app/(dashboard)/dashboard/settings/propriedades/[id]/estrutura/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/settings/propriedades/[id]/estrutura/page.tsx) | Estrutura territorial de uma propriedade | Ativo |
| [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx) | Rastreabilidade operacional vinculada ao território | Dependente do domínio territorial |

#### Domínio Imóveis Rurais

| Arquivo | Responsabilidade | Status |
|---|---|---|
| [services/api/imoveis/models/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/models/imovel.py) | Modelo fundiário, documental, patrimonial e fiscal principal | Ativo |
| [services/api/imoveis/routers/imovel.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/imovel.py) | CRUD de imóveis rurais | Ativo |
| [services/api/imoveis/routers/arrendamento.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/arrendamento.py) | Contratos de arrendamento e parceria | Ativo |
| [services/api/imoveis/routers/avaliacao.py](/opt/lampp/htdocs/farm/services/api/imoveis/routers/avaliacao.py) | Avaliações patrimoniais | Ativo |
| [services/api/imoveis/services/imovel_service.py](/opt/lampp/htdocs/farm/services/api/imoveis/services/imovel_service.py) | Regras do imóvel rural, validações e consistência | Ativo |
| [services/api/imoveis/services/arrendamento_service.py](/opt/lampp/htdocs/farm/services/api/imoveis/services/arrendamento_service.py) | Gestão de contratos | Ativo |
| [services/api/imoveis/services/avaliacao_service.py](/opt/lampp/htdocs/farm/services/api/imoveis/services/avaliacao_service.py) | Avaliação patrimonial | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx) | Tela principal de imóveis rurais | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx) | UI de arrendamentos | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx) | Tela de avaliações | Ativo |
| [apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/AvaliacoesClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/AvaliacoesClient.tsx) | UI de avaliações | Ativo |

#### Documentação de contexto que reforça a sobreposição

| Arquivo | Responsabilidade | Status |
|---|---|---|
| [docs/contexts/imoveis/_overview.md](/opt/lampp/htdocs/farm/docs/contexts/imoveis/_overview.md) | Contexto do domínio Imóveis Rurais | Consistente com a separação legal/documental |
| [docs/contexts/imoveis/essencial/cadastro-imovel.md](/opt/lampp/htdocs/farm/docs/contexts/imoveis/essencial/cadastro-imovel.md) | Cadastro do imóvel | Consistente |
| [docs/contexts/imoveis/essencial/documentos-legais.md](/opt/lampp/htdocs/farm/docs/contexts/imoveis/essencial/documentos-legais.md) | Documentos legais e rastreio documental | Consistente |
| [docs/contexts/imoveis/profissional/arrendamentos.md](/opt/lampp/htdocs/farm/docs/contexts/imoveis/profissional/arrendamentos.md) | Arrendamentos e contratos | Consistente |
| [docs/contexts/step47-existing-modules-inventory-context.md](/opt/lampp/htdocs/farm/docs/contexts/step47-existing-modules-inventory-context.md) | Inventário de módulos existentes | Revela duplicidade de domínio |
| [docs/contexts/step48-cross-module-ownership-context.md](/opt/lampp/htdocs/farm/docs/contexts/step48-cross-module-ownership-context.md) | Ownership entre módulos | Reforça `cadastros_areas_rurais` como domínio espacial |

## 2. Gap analysis

### Comparação com AGRI-DOMAIN-001 e AGRI-DOMAIN-002

| Item | Situação atual | Divergência | Classificação |
|---|---|---|---|
| Hierarquia territorial operacional | Já existe em `cadastros_areas_rurais` com `GLEBA`, `TALHAO`, `PIQUETE`, `AREA_AMBIENTAL`, `INFRAESTRUTURA` | Em geral alinhado | MANTER |
| Geometria e desenho territorial | Já existe com GeoJSON, mapa e árvore | Alinhado com domínio operacional | MANTER |
| Talhões e subdivisões | Já existem e são usados no frontend | Alinhado | MANTER |
| Matriz fundiária/legal | Parcialmente presente em `MatriculaImovel` dentro do módulo de Propriedades | Viola a fronteira normativa | MIGRAR |
| CAR, CCIR, NIRF, ITR, SIGEF, cartório e matrícula oficial | Presentes em Imóveis Rurais e também duplicados em Propriedades | Duplica fonte da verdade | AJUSTAR |
| Contratos de arrendamento e parceria | Presentes no módulo Imóveis Rurais | Alinhado | MANTER |
| Avaliações patrimoniais | Presentes no módulo Imóveis Rurais | Alinhado | MANTER |
| Infraestrutura operacional | Presentes no módulo de Propriedades | Pode permanecer como ativo territorial | MANTER |
| Registro ambiental e patrimonial no cadastro territorial | Presente em Propriedades | Parte é compartilhável, mas a prova documental deve ser centralizada | AJUSTAR |
| Entidade canônica de vínculo entre Propriedade e Imóvel Rural | Não existe | Lacuna central do modelo | CRIAR |
| Cardinalidade N:N formalizada em persistência | Não existe no banco | Lacuna central | CRIAR |
| Regras de espelhamento e edição controlada | Não formalizadas no código | Lacuna de governança técnica | CRIAR |

### Síntese do gap

- O que está certo:
  - Propriedades já cumpre o papel operacional e territorial.
  - Imóveis Rurais já cumpre o papel fundiário, legal e documental.
- O que está errado:
  - Dados fundiários continuam alojados no domínio territorial.
  - Há duplicação de campos de matrícula, CAR, CCIR, NIRF, ITR e cartório.
- O que falta:
  - Entidade de ligação canônica.
  - Plano de migração de dados e leitura compatível.
  - Regras formais de source-of-truth e sincronização.

## 3. Fonte da verdade

### Mapeamento atual vs. desejado

| Campo | Onde está hoje | Onde deveria estar | Duplicidade | Conflito |
|---|---|---|---|---|
| Nome da propriedade | Propriedades | Propriedades | Não | Não |
| Código interno | Propriedades | Propriedades | Não | Não |
| Município | Propriedades e Imóveis Rurais | Imóveis Rurais como cadastro oficial; Propriedades pode espelhar para operação | Sim | Sim |
| Estado / UF | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| Coordenadas | Propriedades e Imóveis Rurais | Propriedades como operacional; Imóveis Rurais como referência documental quando aplicável | Sim | Parcial |
| Área total | Propriedades e Imóveis Rurais | Propriedades como operacional; Imóveis Rurais como área legal/fiscal quando necessário | Sim | Sim |
| Área agricultável | Propriedades | Propriedades | Não | Não |
| Área preservação / APP | Propriedades e Imóveis Rurais | Imóveis Rurais como prova legal; Propriedades como leitura operacional | Sim | Sim |
| Área Reserva Legal | Propriedades e Imóveis Rurais | Imóveis Rurais como prova legal; Propriedades como leitura operacional | Sim | Sim |
| CAR | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| CCIR | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| ITR | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| NIRF | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| SIGEF | Em contexto fundiário e documental | Imóveis Rurais | Parcial | Parcial |
| Matrículas | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| Cartórios | Propriedades e Imóveis Rurais | Imóveis Rurais | Sim | Sim |
| Titularidade | Não consolidada em Propriedades; suportada por Imóveis Rurais e contratos | Imóveis Rurais | Parcial | Sim |
| Contratos | Imóveis Rurais | Imóveis Rurais | Não | Não |
| Talhões | Propriedades | Propriedades | Não | Não |
| Glebas | Propriedades | Propriedades | Não | Não |
| Pastagens | Propriedades | Propriedades | Não | Não |
| Infraestrutura | Propriedades | Propriedades | Não | Não |
| Safras | Domínio Agrícola, referenciando Propriedades | Domínio Agrícola | Não | Não |
| Produção | Domínio Agrícola, referenciando Propriedades | Domínio Agrícola | Não | Não |

### Regra de verdade recomendada

- `Propriedades` é a fonte da verdade operacional, espacial e produtiva.
- `Imóveis Rurais` é a fonte da verdade legal, fundiária, documental e fiscal.
- `PropriedadeImovel` será a fonte da verdade do vínculo entre os dois domínios.
- Qualquer dado espelhado entre os dois lados deve ser somente leitura e derivado da origem oficial.

## 4. Entidade PropriedadeImovel

### Situação atual

| Item | Status |
|---|---|
| Existe atualmente | INEXISTENTE |
| Tabela canônica de vínculo | Não existe |
| Modelo explícito de relacionamento N:N | Não existe |
| Regras de vínculo histórico | Não formalizadas |

### Definição conceitual recomendada

`PropriedadeImovel` é a entidade canônica de vínculo entre a unidade operacional `Propriedade` e a unidade legal/documental `Imóvel Rural`.

Ela não representa operação, nem titularidade, nem matrícula isoladamente. Ela representa a associação auditável entre os dois domínios.

### Campos mínimos esperados em futura implementação

| Campo | Classificação | Observação |
|---|---|---|
| `tenant_id` | Obrigatório | Escopo multi-tenant |
| `propriedade_id` | Obrigatório | Chave da unidade operacional |
| `imovel_rural_id` | Obrigatório | Chave da unidade fundiária |
| `tipo_vinculo` | Obrigatório | Classificação do vínculo |
| `area_vinculada` | Obrigatório | Área associada ao vínculo |
| `percentual_vinculado` | Obrigatório | Percentual do imóvel ou da propriedade relacionado ao vínculo |
| `data_inicio` | Obrigatório | Vigência inicial |
| `data_fim` | Opcional | Fim da vigência |
| `ativo` | Obrigatório | Estado lógico do vínculo |
| `origem_documental` | Obrigatório | Documento ou conjunto de documentos que justificam o vínculo |
| `observacoes` | Opcional | Contexto complementar |
| `created_at` / `updated_at` | Obrigatório | Auditoria |

### O que a entidade não deve armazenar

- Não deve armazenar o cadastro completo da propriedade.
- Não deve armazenar o cadastro completo do imóvel rural.
- Não deve armazenar documentos legais integrais.
- Não deve armazenar geometria principal.
- Não deve substituir contratos, matrículas ou avaliações.

## 5. Impacto no banco

### Tabelas afetadas

| Tabela | Impacto | Ação | Complexidade |
|---|---|---|---|
| `cadastros_areas_rurais` | Alto | Manter a estrutura operacional, mas revisar campos de natureza fundiária/documental | Alta |
| `cadastros_areas_matriculas` | Alto | Migrar ou desnormalizar para fora dos dados de verdade fundiária | Alta |
| `cadastros_areas_registros_ambientais` | Médio | Revisar escopo para evitar duplicidade com Imóveis Rurais | Média |
| `cadastros_infraestruturas` | Baixo | Manter como operacional | Baixa |
| `cadastros_arquivos_geo` | Baixo | Manter como operacional/geoespacial | Baixa |
| `cadastros_areas_valores_patrimoniais` | Médio | Revisar se permanece como leitura territorial ou migra para domínio patrimonial | Média |
| `imoveis_rurais` | Médio | Preservar como fonte fundiária oficial e remover ambiguidade com Propriedades | Média |
| `imoveis_matriculas` | Médio | Consolidar como origem oficial de matrícula | Média |
| `imoveis_documentos` | Baixo | Manter como documental oficial | Baixa |
| `imoveis_arrendamentos` | Baixo | Manter | Baixa |
| `imoveis_avaliacoes` | Baixo | Manter | Baixa |
| `propriedade_imovel` | Alto | Criar nova tabela canônica de vínculo | Alta |

### Leitura técnica

- O impacto de banco é **alto** porque a convergência exige:
  - criação de entidade de ligação
  - remoção gradual de duplicidade
  - eventual migração de campos fundiários do domínio territorial
  - manutenção de compatibilidade retroativa

## 6. Impacto nas APIs

### Rotas e módulos impactados

| Endpoint / Módulo | Impacto | Ação |
|---|---|---|
| `/api/v1/cadastros/areas-rurais` | Alto | Ajustar contratos para remover dependência de dados fundiários como verdade primária |
| `/api/v1/cadastros/areas-rurais/{id}/matriculas` | Alto | Refatorar ou depreciar conforme migração |
| `/api/v1/cadastros/areas-rurais/{id}/registros-ambientais` | Médio | Revisar espelhamento documental |
| `/api/v1/imoveis` | Médio | Consolidar como fonte legal e documental oficial |
| `/api/v1/imoveis/{id}` | Médio | Fortalecer leitura canônica de matrícula, cartório e documentos |
| `/api/v1/imoveis/arrendamentos` | Baixo | Manter e integrar ao vínculo PropriedadeImovel |
| `/api/v1/imoveis/avaliacoes` | Baixo | Manter |
| Future `/api/v1/propriedade-imovel` | Alto | Criar para gerenciar o vínculo canônico |

### Efeito prático

- As APIs atuais precisam passar a expor a separação de responsabilidades.
- A leitura de um imóvel rural deve indicar suas propriedades vinculadas.
- A leitura de uma propriedade deve indicar os imóveis vinculados.
- A edição de vínculo deve ser centralizada em `PropriedadeImovel`.

## 7. Impacto no frontend

### Telas impactadas

| Tela | Impacto | Ação |
|---|---|---|
| Cadastro de Propriedades | Alto | Separar visualmente o que é operacional do que é fundiário |
| Editor territorial de Propriedades | Médio | Manter como fonte territorial, mas retirar campos legais duplicados |
| Talhões | Baixo | Manter |
| Cadastro de Imóveis Rurais | Alto | Consolidar origem legal, documental e fiscal |
| Arrendamentos | Baixo | Manter com vínculo claro ao imóvel e à propriedade |
| Avaliações | Baixo | Manter |
| Rastreabilidade | Médio | Passar a exibir cadeia `Produção -> Safra -> Propriedade -> PropriedadeImovel -> Imóvel Rural` |

### Leitura prática

- O frontend já está organizado em duas entradas distintas, o que é bom.
- O problema não é layout; é semântica de dados.
- A UI de Propriedades precisa deixar de sugerir que ela é a origem documental fundiária.

## 8. Impacto em ESG e Projeto Raízes

### Classificação de impacto

| Tema | Impacto da convergência | Justificativa |
|---|---|---|
| ESG | Melhora | Cadeia de evidência mais confiável entre operação e documentação |
| Certificações | Melhora | Auditoria passa a distinguir fonte operacional e legal |
| Carbono | Melhora | Melhor lastro territorial e fundiário para inventários e comprovações |
| Projeto Raízes | Melhora | Rastreabilidade de origem fica mais precisa |

### Risco atual

- Enquanto a duplicidade persistir, existe risco de:
  - divergência documental em auditoria
  - inconsistência entre mapa operacional e matrícula
  - ambiguidade em certificações e rastreabilidade
  - dificuldade para provar origem fundiária da produção

## 9. Roadmap técnico

### Fase 1 — Correções documentais

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Formalizar a convergência no plano técnico | Baixo | Baixa | Normas já aprovadas |

### Fase 2 — Data Model

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Definir `PropriedadeImovel` no modelo canônico e eliminar ambiguidade conceitual | Médio | Alta | ADR e governança |

### Fase 3 — Banco de Dados

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Criar a tabela de vínculo e preparar migração de campos duplicados | Alto | Alta | Data Model aprovado |

### Fase 4 — Backend

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Ajustar APIs e serviços para ler e escrever no domínio correto | Alto | Alta | Banco preparado |

### Fase 5 — Frontend

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Atualizar telas para separar claramente operação e fundiário | Médio | Média | Backend consolidado |

### Fase 6 — Rastreabilidade

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Garantir rastreio até imóvel rural por meio de PropriedadeImovel | Alto | Alta | Backend e dados migrados |

### Fase 7 — ESG e Projeto Raízes

| Objetivo | Risco | Complexidade | Dependências |
|---|---|---|---|
| Usar o vínculo canônico como lastro de auditoria, ESG e origem | Médio | Média | Rastreabilidade estável |

## 10. ADR final

### O domínio Territorial/Fundiário está pronto para implementação?

**Resposta: NÃO.**

### Justificativa

- A arquitetura conceitual está madura.
- O sistema atual ainda contém duplicidade de dados fundiários entre Propriedades e Imóveis Rurais.
- A entidade canônica `PropriedadeImovel` ainda não existe.
- Não há ainda sequência de migração e compatibilidade retroativa formalizada em ADR.
- Implementar sem essa etapa elevaria o risco de inconsistência cadastral, documental e de rastreabilidade.

### Próximo passo recomendado

Gerar uma ADR específica para a convergência:

- `docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md`

Essa ADR deve autorizar:

- a criação da entidade de vínculo
- a redefinição de source-of-truth
- a migração gradual dos dados fundiários
- a manutenção de compatibilidade de leitura durante a transição

## Respostas objetivas

1. O que já está correto?

- A separação conceitual entre domínio operacional e domínio legal já está bem desenhada.
- Propriedades já é adequado para território, talhões, glebas, pastagens e infraestrutura.
- Imóveis Rurais já é adequado para documentação, matrícula, arrendamento e avaliação.

2. O que precisa mudar?

- Remover a duplicidade de campos fundiários dentro de Propriedades.
- Tornar Imóveis Rurais a fonte oficial de CAR, CCIR, ITR, NIRF, matrícula e cartório.
- Introduzir `PropriedadeImovel` como vínculo canônico.

3. O que precisa ser criado?

- A entidade `PropriedadeImovel`.
- A estratégia de sincronização e leitura compatível.
- A ADR de convergência.

4. Qual o impacto no banco?

- Alto.
- Haverá nova tabela de vínculo, revisão de campos duplicados e potencial migração de dados históricos.

5. Qual o impacto nas APIs?

- Alto.
- Alguns contratos atuais precisarão deixar de tratar dados fundiários como verdade primária do domínio territorial.

6. Qual o impacto no frontend?

- Médio a alto.
- As telas existem, mas a semântica exibida ao usuário precisa separar operação de legalidade fundiária.

7. O domínio está pronto para implementação?

- **Não.**

8. Qual deve ser o roadmap técnico de execução?

- Primeiro, formalizar a ADR.
- Depois, atualizar o modelo de dados.
- Em seguida, executar a migração de banco.
- Depois, refatorar backend.
- Por fim, ajustar frontend, rastreabilidade e camadas de ESG/Projeto Raízes.

## Conclusão

O AgroSaaS deve convergir `Propriedades` e `Imóveis Rurais` sem criar um terceiro módulo. A implementação futura depende da criação da entidade canônica `PropriedadeImovel`, da eliminação de duplicidades fundiárias e da formalização de uma ADR de migração. Hoje, o sistema já possui boa base conceitual, mas ainda não está pronto para uma implementação definitiva sem risco de regressão arquitetural.
