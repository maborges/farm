# TICKETS-IMPLEMENTATION-01 — CONVERGÊNCIA PROPRIEDADES X IMÓVEIS RURAIS

## TCK-001 — Validar branch e base limpa

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Confirmar que a base local está consistente antes de qualquer trabalho de convergência.

Escopo:

* Verificar branch atual.
* Verificar status do repositório.
* Identificar mudanças locais não relacionadas.
* Confirmar que a árvore de trabalho está apta para análise.

Fora de escopo:

* Qualquer alteração em código, docs normativos ou banco.

Arquivos prováveis:

* N/A

Dependências:

* Nenhuma

Critérios de aceite:

* Branch e status do repositório documentados.
* Nenhuma mudança não relacionada interfere na execução futura.

Riscos:

* Base suja mascarar problemas reais.

Comando de validação sugerido:

* `git status --short`

---

## TCK-002 — Validar migrations existentes

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Inventariar as migrations que já tocam Propriedades e Imóveis Rurais.

Escopo:

* Listar migrations Alembic relevantes.
* Identificar alterações em tabelas relacionadas.
* Mapear possíveis conflitos antes de nova migration.

Fora de escopo:

* Criar, alterar ou aplicar migrations.

Arquivos prováveis:

* `services/api/alembic/versions/*`

Dependências:

* TCK-001

Critérios de aceite:

* Lista das migrations relacionadas está documentada.
* Migrações conflitantes são identificadas.

Riscos:

* Perder histórico de alterações estruturais já existentes.

Comando de validação sugerido:

* `find services/api/alembic/versions -maxdepth 1 -type f`

---

## TCK-003 — Validar RLS nas tabelas impactadas

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Confirmar se as tabelas críticas já operam sob RLS e quais políticas existem.

Escopo:

* Identificar tabelas de Propriedades.
* Identificar tabelas de Imóveis Rurais.
* Mapear indícios de RLS, constraints e políticas transversais.

Fora de escopo:

* Alterar políticas de RLS.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/models.py`
* `services/api/imoveis/models/imovel.py`
* `services/api/main.py`

Dependências:

* TCK-002

Critérios de aceite:

* Situação de RLS por tabela documentada.
* Lacunas de proteção identificadas.

Riscos:

* Supor RLS onde ele não existe.

Comando de validação sugerido:

* `rg -n "RLS|tenant_id|policy|row level" services/api`

---

## TCK-004 — Validar tenant_id nas entidades impactadas

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Confirmar que as entidades envolvidas possuem escopo por tenant.

Escopo:

* Mapear `tenant_id` em Propriedades.
* Mapear `tenant_id` em Imóveis Rurais.
* Identificar entidades auxiliares sem isolamento claro.

Fora de escopo:

* Corrigir os modelos.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/models.py`
* `services/api/imoveis/models/imovel.py`
* `services/api/core/*`

Dependências:

* TCK-003

Critérios de aceite:

* Mapa de presença de `tenant_id` concluído.
* Riscos de bypass por entidade documentados.

Riscos:

* Entidade crítica sem escopo tenant.

Comando de validação sugerido:

* `rg -n "tenant_id" services/api/core services/api/imoveis`

---

## TCK-005 — Levantar campos fundiários duplicados

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Identificar todos os campos fundiários que aparecem em mais de um domínio.

Escopo:

* Mapear CAR, CCIR, ITR, NIRF, SIGEF, matrícula, cartório e titulares.
* Identificar onde há leitura e escrita duplicadas.
* Classificar cada campo como oficial, derivado ou legado.

Fora de escopo:

* Remover ou mover campos.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/models.py`
* `services/api/imoveis/models/imovel.py`
* `docs/architecture/agrosaas-data-model.md`

Dependências:

* TCK-004

Critérios de aceite:

* Tabela de duplicidades concluída.
* Campo por campo com origem atual e origem oficial.

Riscos:

* Omissão de campo duplicado escondido em relacionamento indireto.

Comando de validação sugerido:

* `rg -n "CAR|CCIR|ITR|NIRF|SIGEF|matri|cartorio|titular" services/api`

---

## TCK-006 — Levantar rotas impactadas

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Mapear os endpoints que precisam respeitar a convergência.

Escopo:

* Levantar rotas de Propriedades.
* Levantar rotas de Imóveis Rurais.
* Identificar rotas legadas que expõem duplicidade.

Fora de escopo:

* Alterar rotas.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/router.py`
* `services/api/imoveis/routers/imovel.py`
* `services/api/imoveis/routers/arrendamento.py`
* `services/api/imoveis/routers/avaliacao.py`
* `docs/architecture/agrosaas-routing-map.md`

Dependências:

* TCK-005

Critérios de aceite:

* Matriz de rotas impactadas concluída.
* Dependências entre rotas documentadas.

Riscos:

* Omissão de rotas indiretas usadas pelo frontend.

Comando de validação sugerido:

* `rg -n "@router|APIRouter|include_router" services/api/core services/api/imoveis`

---

## TCK-007 — Levantar telas impactadas

Tipo:

* docs

Fase:

* Fase 0

Objetivo:

Mapear páginas e componentes que precisam respeitar a nova fronteira de domínio.

Escopo:

* Identificar telas de cadastro de Propriedades.
* Identificar telas de cadastro de Imóveis Rurais.
* Levantar pontos de rastreabilidade e formulários de vínculo.

Fora de escopo:

* Alterar frontend.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/cadastros/propriedades/*`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/*`
* `apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx`

Dependências:

* TCK-006

Critérios de aceite:

* Lista de telas e componentes impactados.
* Prioridade de refatoração documentada.

Riscos:

* UI duplicando semântica de cadastro.

Comando de validação sugerido:

* `rg -n "cadastros/propriedades|cadastros/imoveis|rastreabilidade" apps/web/src/app`

---

## TCK-008 — Desenhar a entidade PropriedadeImovel

Tipo:

* docs

Fase:

* Fase 1

Objetivo:

Definir o contrato conceitual da entidade canônica de vínculo.

Escopo:

* Consolidar propósito, ownership e campos mínimos.
* Revisar atributos obrigatórios, opcionais e futuros.
* Documentar o que a entidade não pode armazenar.

Fora de escopo:

* Implementar código ou migration.

Arquivos prováveis:

* `docs/architecture/agrosaas-data-model.md`
* `docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md`

Dependências:

* TCK-005

Critérios de aceite:

* Entidade descrita de forma inequívoca.
* Sem sobreposição com Propriedades ou Imóveis Rurais.

Riscos:

* Contrato conceitual amplo demais e difícil de implementar.

Comando de validação sugerido:

* `sed -n '1,240p' docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md`

---

## TCK-009 — Definir enum tipo_vinculo e regras de vigência

Tipo:

* docs

Fase:

* Fase 1

Objetivo:

Formalizar os tipos oficiais de vínculo e suas regras temporais.

Escopo:

* Definir enum canônico.
* Definir restrições de uso por tipo.
* Definir vigência, vínculo principal e vínculos secundários.

Fora de escopo:

* Persistir enum em banco.

Arquivos prováveis:

* `docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md`
* `docs/architecture/agrosaas-data-model.md`

Dependências:

* TCK-008

Critérios de aceite:

* Enum e regras de vigência sem ambiguidade.
* Regras de principalidade documentadas.

Riscos:

* Tipos de vínculo sobrepostos ou semanticamente vagos.

Comando de validação sugerido:

* `rg -n "tipo_vinculo|vigencia|principal" docs/architecture`

---

## TCK-010 — Definir constraints e índices do vínculo

Tipo:

* docs

Fase:

* Fase 1

Objetivo:

Definir o desenho lógico das constraints e dos índices da futura entidade.

Escopo:

* Definir unicidade lógica.
* Definir índices de consulta.
* Definir regras de integridade por tenant.

Fora de escopo:

* Criar constraints no banco.

Arquivos prováveis:

* `docs/architecture/agrosaas-data-model.md`
* `docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md`

Dependências:

* TCK-008

Critérios de aceite:

* Relação entre constraints e requisitos documentada.
* Índices sugeridos estão alinhados ao uso real.

Riscos:

* Constraint incompatível com o cenário N:N validado.

Comando de validação sugerido:

* `rg -n "constraint|index|tenant_id|N:N" docs/architecture`

---

## TCK-011 — Definir política de RLS para PropriedadeImovel

Tipo:

* docs

Fase:

* Fase 1

Objetivo:

Documentar como o vínculo será protegido por tenant e RLS.

Escopo:

* Definir isolamento esperado.
* Definir comportamento de leitura e escrita.
* Definir relação com tabelas pai.

Fora de escopo:

* Alterar políticas reais do banco.

Arquivos prováveis:

* `docs/architecture/agrosaas-data-model.md`
* `docs/architecture/agrosaas-ai-rules.md`

Dependências:

* TCK-010

Critérios de aceite:

* Política RLS documentada.
* Nenhuma leitura cross-tenant permitida.

Riscos:

* Bypass de tenant no vínculo.

Comando de validação sugerido:

* `rg -n "RLS|tenant isolation|tenant_id" docs/architecture`

---

## TCK-012 — Atualizar documentação do Data Model

Tipo:

* docs

Fase:

* Fase 1

Objetivo:

Atualizar o Data Model com a convergência aprovada.

Escopo:

* Registrar cardinalidade N:N.
* Registrar ownership dos domínios.
* Registrar a entidade `PropriedadeImovel`.

Fora de escopo:

* Alterar a implementação.

Arquivos prováveis:

* `docs/architecture/agrosaas-data-model.md`

Dependências:

* TCK-008
* TCK-009
* TCK-010
* TCK-011

Critérios de aceite:

* Documento atualizado e consistente com a ADR.

Riscos:

* Divergência entre documentação e plano de implementação.

Comando de validação sugerido:

* `sed -n '1,220p' docs/architecture/agrosaas-data-model.md`

---

## TCK-013 — Criar migration inicial do vínculo

Tipo:

* migration

Fase:

* Fase 2

Objetivo:

Preparar a migration inicial da entidade `PropriedadeImovel`.

Escopo:

* Estruturar a migration inicial.
* Definir nome e ordem da revisão.
* Planejar dependências com o schema atual.

Fora de escopo:

* Aplicar a migration em produção.

Arquivos prováveis:

* `services/api/alembic/versions/*`

Dependências:

* TCK-012

Critérios de aceite:

* Revisão definida.
* Estrutura da migration validada contra o modelo.

Riscos:

* Ordem incorreta de migração quebrar referências.

Comando de validação sugerido:

* `services/api/.venv/bin/alembic heads`

---

## TCK-014 — Criar tabela propriedade_imovel

Tipo:

* migration

Fase:

* Fase 2

Objetivo:

Estruturar a tabela física do vínculo canônico.

Escopo:

* Criar tabela.
* Definir colunas base.
* Garantir FK para Propriedades e Imóveis Rurais.

Fora de escopo:

* Inserir dados históricos.

Arquivos prováveis:

* `services/api/alembic/versions/*`

Dependências:

* TCK-013

Critérios de aceite:

* Tabela criada conforme o modelo.

Riscos:

* FK incompatível com dados legados.

Comando de validação sugerido:

* `services/api/.venv/bin/alembic upgrade head`

---

## TCK-015 — Criar constraints, índices e rollback

Tipo:

* migration

Fase:

* Fase 2

Objetivo:

Garantir integridade, performance e reversibilidade da migration.

Escopo:

* Criar constraints.
* Criar índices.
* Definir `downgrade`.
* Testar upgrade/downgrade.

Fora de escopo:

* Alterar semântica funcional.

Arquivos prováveis:

* `services/api/alembic/versions/*`

Dependências:

* TCK-014

Critérios de aceite:

* Upgrade e downgrade funcionam.
* Constraints e índices aplicados.

Riscos:

* Rollback inconsistente.

Comando de validação sugerido:

* `services/api/.venv/bin/alembic downgrade -1`

---

## TCK-016 — Criar model SQLAlchemy de PropriedadeImovel

Tipo:

* backend

Fase:

* Fase 3

Objetivo:

Criar a modelagem ORM da entidade de vínculo.

Escopo:

* Definir classe SQLAlchemy.
* Mapear campos obrigatórios.
* Mapear relacionamentos com Propriedades e Imóveis Rurais.

Fora de escopo:

* Criar rotas ou UI.

Arquivos prováveis:

* `services/api/.../models.py`
* `services/api/core/cadastros/propriedades/models.py`
* `services/api/imoveis/models/imovel.py`

Dependências:

* TCK-014

Critérios de aceite:

* Model pronta e coerente com a migration.

Riscos:

* Relacionamento ORM ambíguo.

Comando de validação sugerido:

* `rg -n "class .*PropriedadeImovel|relationship\\(" services/api`

---

## TCK-017 — Criar schemas Pydantic do vínculo

Tipo:

* backend

Fase:

* Fase 3

Objetivo:

Criar os contratos de entrada e saída para o vínculo canônico.

Escopo:

* Definir schema de criação.
* Definir schema de atualização.
* Definir schema de resposta.

Fora de escopo:

* Implementar persistência.

Arquivos prováveis:

* `services/api/.../schemas.py`
* `services/api/core/cadastros/propriedades/schemas.py`
* `services/api/imoveis/schemas.py`

Dependências:

* TCK-016

Critérios de aceite:

* Schemas coerentes com o model e com a ADR.

Riscos:

* Contrato permitir campos que não pertencem ao vínculo.

Comando de validação sugerido:

* `rg -n "BaseModel|Schema|Pydantic" services/api`

---

## TCK-018 — Criar service do vínculo

Tipo:

* backend

Fase:

* Fase 3

Objetivo:

Separar a regra de negócio do vínculo em um service isolado.

Escopo:

* Validar vínculo principal.
* Validar vigência.
* Validar origem documental.
* Garantir isolamento por tenant.

Fora de escopo:

* Criar frontend.

Arquivos prováveis:

* `services/api/.../service.py`
* `services/api/core/cadastros/propriedades/service.py`
* `services/api/imoveis/services/imovel_service.py`

Dependências:

* TCK-016
* TCK-017

Critérios de aceite:

* Service executa regras sem misturar domínio operacional e fundiário.

Riscos:

* Service ficar gordo ou acoplado a routers.

Comando de validação sugerido:

* `rg -n "def .*propriedade_imovel|class .*Service" services/api`

---

## TCK-019 — Criar router da entidade canônica

Tipo:

* backend

Fase:

* Fase 3

Objetivo:

Expor operações do vínculo por API de forma explícita.

Escopo:

* Criar router FastAPI.
* Expor endpoints mínimos necessários.
* Garantir tenant isolation no acesso.

Fora de escopo:

* Reescrever rotas legadas.

Arquivos prováveis:

* `services/api/.../router.py`
* `services/api/core/cadastros/propriedades/router.py`
* `services/api/imoveis/routers/imovel.py`

Dependências:

* TCK-018

Critérios de aceite:

* Router funcional e alinhado ao data model.

Riscos:

* Exposição de escrita em fonte errada.

Comando de validação sugerido:

* `rg -n "APIRouter|include_router" services/api`

---

## TCK-020 — Criar testes unitários do vínculo

Tipo:

* tests

Fase:

* Fase 3

Objetivo:

Cobrir as regras de negócio do service com testes unitários.

Escopo:

* Testar vínculo principal.
* Testar vigência.
* Testar origem documental.
* Testar isolamento por tenant.

Fora de escopo:

* Testar UI.

Arquivos prováveis:

* `tests/unit/*propriedade_imovel*`

Dependências:

* TCK-018

Critérios de aceite:

* Casos positivos e negativos cobertos.

Riscos:

* Testes não cobrirem conflito de vigência.

Comando de validação sugerido:

* `services/api/.venv/bin/pytest -q tests/unit`

---

## TCK-021 — Criar testes de integração backend

Tipo:

* tests

Fase:

* Fase 3

Objetivo:

Validar o fluxo completo da API do vínculo.

Escopo:

* Testar criação e leitura.
* Testar validação de tenant.
* Testar resposta de erro e semântica de vínculo principal.

Fora de escopo:

* Testes de migration.

Arquivos prováveis:

* `tests/integration/*propriedade_imovel*`

Dependências:

* TCK-019

Critérios de aceite:

* Fluxos principais cobertos por teste de integração.

Riscos:

* Integração falhar por dependência de fixtures frágeis.

Comando de validação sugerido:

* `services/api/.venv/bin/pytest -q tests/integration`

---

## TCK-022 — Mapear leitura de campos antigos

Tipo:

* refactor

Fase:

* Fase 4

Objetivo:

Documentar quais leituras antigas permanecem compatíveis na transição.

Escopo:

* Identificar consumidores de campos fundiários legados.
* Classificar leitura como oficial, derivada ou histórica.

Fora de escopo:

* Remover campos.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/models.py`
* `services/api/imoveis/models/imovel.py`
* `apps/web/src/app/(dashboard)/cadastros/propriedades/*`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/*`

Dependências:

* TCK-021

Critérios de aceite:

* Mapa de leitura legado documentado.

Riscos:

* Dependência escondida em relatório ou tela não mapeada.

Comando de validação sugerido:

* `rg -n "matricula|car_numero|ccir|nirf|sigef|itr" apps/web services/api`

---

## TCK-023 — Bloquear escrita duplicada nos campos fundiários

Tipo:

* refactor

Fase:

* Fase 4

Objetivo:

Impedir novas escritas em campos que deixaram de ser fonte oficial.

Escopo:

* Definir política de depreciação.
* Definir warnings para escrita legada.
* Garantir que a escrita vá para a fonte correta.

Fora de escopo:

* Redesenhar a UI completa.

Arquivos prováveis:

* `services/api/core/cadastros/propriedades/service.py`
* `services/api/imoveis/services/imovel_service.py`
* `services/api/core/cadastros/propriedades/router.py`

Dependências:

* TCK-022

Critérios de aceite:

* Escrita duplicada bloqueada onde aplicável.

Riscos:

* Impacto em fluxos antigos ainda em uso.

Comando de validação sugerido:

* `rg -n "create|update|upsert|matricula|car_numero|ccir|nirf" services/api/core/cadastros/propriedades services/api/imoveis`

---

## TCK-024 — Preservar histórico e depreciação

Tipo:

* refactor

Fase:

* Fase 4

Objetivo:

Garantir que a transição preserve histórico e a trilha de auditoria.

Escopo:

* Registrar política de depreciação.
* Garantir histórico de alterações.
* Documentar comportamento durante a transição.

Fora de escopo:

* Apagar dados legados.

Arquivos prováveis:

* `docs/analysis/ARCH-IMPLEMENTATION-01-convergencia-propriedades-imoveis.md`
* `docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md`

Dependências:

* TCK-023

Critérios de aceite:

* Histórico preservado.
* Depreciação documentada.

Riscos:

* Perda de evidência em auditoria.

Comando de validação sugerido:

* `rg -n "history|historico|deprecated|deprecia" docs/architecture docs/implementation`

---

## TCK-025 — Atualizar tela de Propriedades

Tipo:

* frontend

Fase:

* Fase 5

Objetivo:

Separar a tela de Propriedades da semântica fundiária/legal.

Escopo:

* Revisar a tela de cadastro de Propriedades.
* Reforçar o foco em território, talhões e operação.
* Remover ou marcar como derivado o que for fundiário.

Fora de escopo:

* Reescrever o backend.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/cadastros/propriedades/page.tsx`
* `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx`
* `apps/web/src/app/(dashboard)/cadastros/propriedades/talhoes/page.tsx`

Dependências:

* TCK-024

Critérios de aceite:

* Tela comunica domínio operacional sem ambiguidade.

Riscos:

* Mistura de dados operacionais e fundiários na mesma interface.

Comando de validação sugerido:

* `rg -n "propriedade|matricula|car|ccir|nirf" apps/web/src/app/(dashboard)/cadastros/propriedades`

---

## TCK-026 — Atualizar tela de Imóveis Rurais

Tipo:

* frontend

Fase:

* Fase 5

Objetivo:

Reforçar a tela de Imóveis Rurais como fonte oficial fundiária.

Escopo:

* Revisar listagem e detalhe.
* Evidenciar matrícula, cartório, CAR, CCIR, ITR e titularidade.
* Garantir leitura canônica de dados fundiários.

Fora de escopo:

* Alterar tela de Propriedades.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/ArrendamentosClient.tsx`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/avaliacoes/page.tsx`

Dependências:

* TCK-025

Critérios de aceite:

* Interface posiciona corretamente a origem fundiária.

Riscos:

* Exposição de campos derivados como editáveis.

Comando de validação sugerido:

* `rg -n "imovel|matricula|cartorio|car|ccir|itr|nirf" apps/web/src/app/(dashboard)/cadastros/imoveis`

---

## TCK-027 — Criar visualização de vínculos

Tipo:

* frontend

Fase:

* Fase 5

Objetivo:

Exibir a relação canônica entre Propriedades e Imóveis Rurais.

Escopo:

* Criar bloco visual para vínculos.
* Exibir vínculo principal e secundário.
* Exibir vigência e origem documental.

Fora de escopo:

* Implementar regras de negócio do vínculo no backend.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx`
* `apps/web/src/components/*`

Dependências:

* TCK-026

Critérios de aceite:

* Vínculos visíveis na interface com semântica correta.

Riscos:

* Visualização induzir edição fora da fonte oficial.

Comando de validação sugerido:

* `rg -n "link|vinculo|imovel" apps/web/src/app apps/web/src/components`

---

## TCK-028 — Criar formulário de vínculo

Tipo:

* frontend

Fase:

* Fase 5

Objetivo:

Criar a UI para cadastro e manutenção do vínculo canônico.

Escopo:

* Formulário de criação e edição de vínculo.
* Campos de vigência e origem documental.
* Validação de campos somente leitura.

Fora de escopo:

* Implementar lógica de persistência.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/page.tsx`
* `apps/web/src/app/(dashboard)/cadastros/imoveis/page.tsx`
* `apps/web/src/components/*`

Dependências:

* TCK-027

Critérios de aceite:

* Formulário funcional e sem conflito semântico.

Riscos:

* Campo editável em domínio derivado.

Comando de validação sugerido:

* `rg -n "form|FormField|react-hook-form|zod" apps/web/src/app apps/web/src/components`

---

## TCK-029 — Validar UI premium e somente leitura

Tipo:

* frontend

Fase:

* Fase 5

Objetivo:

Garantir que a experiência continue coerente com o design system do AgroSaaS.

Escopo:

* Validar skeletons.
* Validar estados vazios.
* Validar componentes `shadcn/ui`.
* Validar campos espelhados como somente leitura.

Fora de escopo:

* Rebranding da interface.

Arquivos prováveis:

* `apps/web/src/app/(dashboard)/**`
* `apps/web/src/components/**`

Dependências:

* TCK-028

Critérios de aceite:

* UI mantém padrão premium.

Riscos:

* Regredir UX na tentativa de separar domínios.

Comando de validação sugerido:

* `rg -n "Skeleton|loading|Empty|readonly|shadcn" apps/web/src/app apps/web/src/components`

---

## TCK-030 — Atualizar cadeia de rastreabilidade

Tipo:

* backend

Fase:

* Fase 6

Objetivo:

Garantir a cadeia oficial de rastreabilidade até o imóvel rural.

Escopo:

* Atualizar a cadeia `Produção -> Safra -> Talhão -> Propriedade -> PropriedadeImovel -> Imóvel Rural`.
* Validar origem territorial.
* Validar documentação fundiária.

Fora de escopo:

* Alterar o fluxo de produção em si.

Arquivos prováveis:

* `services/api/core/*`
* `services/api/imoveis/*`
* `apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx`

Dependências:

* TCK-019
* TCK-027

Critérios de aceite:

* Cadeia completa e navegável.

Riscos:

* Rastreabilidade interrompida em propriedades sem vínculo formalizado.

Comando de validação sugerido:

* `rg -n "rastreabil|safra|talhao|propriedade|imovel" services/api apps/web/src/app`

---

## TCK-031 — Validar origem territorial e documentação fundiária

Tipo:

* tests

Fase:

* Fase 6

Objetivo:

Testar a prova de origem e o lastro documental da rastreabilidade.

Escopo:

* Testar a origem territorial.
* Testar a documentação fundiária.
* Testar a titularidade e o histórico do vínculo.

Fora de escopo:

* Testes de UI.

Arquivos prováveis:

* `tests/unit/*`
* `tests/integration/*`

Dependências:

* TCK-030

Critérios de aceite:

* Fluxo de origem validado por teste.

Riscos:

* Falta de fixture representando caso real.

Comando de validação sugerido:

* `services/api/.venv/bin/pytest -q tests`

---

## TCK-032 — Validar compatibilidade ESG e certificações

Tipo:

* docs

Fase:

* Fase 7

Objetivo:

Garantir que a convergência não quebre requisitos de ESG e certificações.

Escopo:

* Mapear dependências de ESG.
* Mapear impactos em certificações.
* Registrar limites e pontos de validação.

Fora de escopo:

* Implementar regras ESG novas.

Arquivos prováveis:

* `docs/analysis/ARCH-IMPLEMENTATION-01-convergencia-propriedades-imoveis.md`
* `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md`

Dependências:

* TCK-031

Critérios de aceite:

* Compatibilidade ESG e certificações documentada.

Riscos:

* Evidência documental insuficiente para auditoria externa.

Comando de validação sugerido:

* `rg -n "ESG|certific|carbono|auditor" docs/architecture docs/analysis`

---

## TCK-033 — Validar Projeto Raízes e cadeia de custódia

Tipo:

* docs

Fase:

* Fase 7

Objetivo:

Garantir que a arquitetura suporta o Projeto Raízes e a cadeia de custódia.

Escopo:

* Validar origem da produção.
* Validar comprovação documental.
* Validar ligação com o imóvel rural.

Fora de escopo:

* Criar novos fluxos de negócio.

Arquivos prováveis:

* `docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md`
* `docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md`

Dependências:

* TCK-032

Critérios de aceite:

* Projeto Raízes suportado pela modelagem.

Riscos:

* Cadeia de custódia perder o elo legal.

Comando de validação sugerido:

* `rg -n "Raízes|custódia|origem|export" docs/architecture docs/analysis`

---

## TCK-034 — Executar testes backend de regressão

Tipo:

* tests

Fase:

* Fase 8

Objetivo:

Validar que a convergência não quebrou fluxos existentes no backend.

Escopo:

* Executar suíte relevante do backend.
* Cobrir regressões em Propriedades e Imóveis Rurais.
* Validar respostas esperadas.

Fora de escopo:

* Refatorar produção.

Arquivos prováveis:

* `tests/**`

Dependências:

* TCK-021
* TCK-030

Critérios de aceite:

* Suíte verde para módulos impactados.

Riscos:

* Teste legado ocultar regressão nova.

Comando de validação sugerido:

* `services/api/.venv/bin/pytest -q`

---

## TCK-035 — Executar testes RLS e tenant isolation

Tipo:

* tests

Fase:

* Fase 8

Objetivo:

Garantir que a nova estrutura respeita RLS e isolamento por tenant.

Escopo:

* Testar leitura cruzada.
* Testar escrita cruzada.
* Testar isolamento do vínculo.

Fora de escopo:

* Ajustar políticas na mesma tarefa.

Arquivos prováveis:

* `tests/**`

Dependências:

* TCK-034

Critérios de aceite:

* Nenhuma falha de isolamento.

Riscos:

* Bypass acidental por consulta indireta.

Comando de validação sugerido:

* `services/api/.venv/bin/pytest -q tests -k rls`

---

## TCK-036 — Executar testes frontend, migration e rastreabilidade fim a fim

Tipo:

* tests

Fase:

* Fase 8

Objetivo:

Validar a experiência completa após a convergência.

Escopo:

* Executar testes frontend.
* Executar testes de migration.
* Executar teste de rastreabilidade fim a fim.

Fora de escopo:

* Modificar o fluxo em produção.

Arquivos prováveis:

* `apps/web/**`
* `services/api/alembic/versions/*`
* `tests/e2e/*`

Dependências:

* TCK-035

Critérios de aceite:

* Fluxo ponta a ponta validado.

Riscos:

* Inconsistência entre front, back e banco.

Comando de validação sugerido:

* `pnpm test`

---

## Ordem sugerida de execução

1. TCK-001
2. TCK-002
3. TCK-003
4. TCK-004
5. TCK-005
6. TCK-006
7. TCK-007
8. TCK-008
9. TCK-009
10. TCK-010
11. TCK-011
12. TCK-012
13. TCK-013
14. TCK-014
15. TCK-015
16. TCK-016
17. TCK-017
18. TCK-018
19. TCK-019
20. TCK-020
21. TCK-021
22. TCK-022
23. TCK-023
24. TCK-024
25. TCK-025
26. TCK-026
27. TCK-027
28. TCK-028
29. TCK-029
30. TCK-030
31. TCK-031
32. TCK-032
33. TCK-033
34. TCK-034
35. TCK-035
36. TCK-036

## Tickets bloqueantes

- TCK-008, TCK-009, TCK-010, TCK-011, TCK-012.
- TCK-013, TCK-014, TCK-015.
- TCK-016, TCK-017, TCK-018, TCK-019.
- TCK-030 e TCK-031 para rastreabilidade fim a fim.
- TCK-035 e TCK-036 para aceite final.

## Tickets que podem rodar em paralelo

- TCK-002, TCK-003, TCK-004, TCK-005, TCK-006 e TCK-007 podem rodar em paralelo após TCK-001.
- TCK-025 e TCK-026 podem rodar em paralelo após a fase de legado.
- TCK-032 e TCK-033 podem rodar em paralelo após a fase de rastreabilidade.
- TCK-034 e TCK-035 podem rodar em paralelo com dependências respeitadas, desde que TCK-030 e TCK-031 estejam concluídos.

## Ticket inicial recomendado

- **TCK-001 — Validar branch e base limpa**

## Resumo executivo

Este pacote de tickets transforma a convergência arquitetural em execução atômica e controlável. A sequência prioriza diagnóstico, modelagem, migração, backend, legado, frontend, rastreabilidade, ESG e aceite final, com pontos claros de bloqueio e dependência.

