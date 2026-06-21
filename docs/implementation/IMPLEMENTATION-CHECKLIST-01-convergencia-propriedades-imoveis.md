# IMPLEMENTATION-CHECKLIST-01 — CONVERGÊNCIA PROPRIEDADES X IMÓVEIS RURAIS

## Base normativa

Checklist derivado de:

- [ADR-00XX - Convergência entre Propriedades e Imóveis Rurais](/opt/lampp/htdocs/farm/docs/architecture/adr/ADR-00XX-convergencia-propriedades-imoveis.md)
- [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md)
- [AGRI-DOMAIN-002](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-002-propriedade-imovel.md)
- [ARCH-IMPLEMENTATION-01](/opt/lampp/htdocs/farm/docs/analysis/ARCH-IMPLEMENTATION-01-convergencia-propriedades-imoveis.md)
- [AGROSAAS Data Model](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-data-model.md)
- [AGROSAAS Routing Map](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-routing-map.md)
- [AGROSAAS AI Rules](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-ai-rules.md)
- [AGROSAAS Engineering Playbook](/opt/lampp/htdocs/farm/docs/architecture/agrosaas-engineering-playbook.md)

## Objetivo

Transformar a decisão arquitetural aprovada em um roteiro técnico faseado para implementação segura da convergência entre:

- `Propriedades`
- `Imóveis Rurais`
- `PropriedadeImovel`

---

## Fase 0 — Preparação

### Checklist

- [ ] Validar branch de trabalho e garantir base limpa para a tarefa.
- [ ] Validar ambiente local e variáveis necessárias.
- [ ] Validar migrations existentes relacionadas a Propriedades e Imóveis Rurais.
- [ ] Validar suíte de testes atual para os módulos envolvidos.
- [ ] Validar schema `farms` e schemas correlatos do banco.
- [ ] Validar status de RLS nas tabelas envolvidas.
- [ ] Validar presença de `tenant_id` em todas as entidades impactadas.
- [ ] Validar rotas e telas atualmente existentes para evitar duplicidade de escopo.

### Bloqueios

- Falta de branch limpa.
- Inconsistência entre ambiente e documentação.
- Qualquer entidade crítica sem `tenant_id`.
- RLS desativado ou não verificável.

---

## Fase 1 — Data Model

### Checklist

- [ ] Modelar a entidade canônica `PropriedadeImovel`.
- [ ] Definir o enum oficial `tipo_vinculo`.
- [ ] Definir os atributos mínimos obrigatórios e opcionais.
- [ ] Definir constraints de integridade e cardinalidade.
- [ ] Definir índices para busca por `tenant_id`, `propriedade_id` e `imovel_rural_id`.
- [ ] Definir regras de vigência (`data_inicio`, `data_fim`, `ativo`).
- [ ] Definir regras de unicidade para vínculo principal e vínculos concorrentes.
- [ ] Definir `tenant_id` como campo obrigatório.
- [ ] Definir comportamento de RLS no novo modelo.
- [ ] Definir relacionamentos SQLAlchemy com `Propriedade` e `ImovelRural`.

### Bloqueios

- Modelo sem `tenant_id`.
- Falta de regras de vigência.
- Falta de definição do vínculo principal.
- Ausência de constraints que impeçam sobreposição inválida.

---

## Fase 2 — Migration Alembic

### Checklist

- [ ] Criar migration para `propriedade_imovel`.
- [ ] Criar a tabela com colunas e tipos corretos.
- [ ] Criar constraints de integridade referencial.
- [ ] Criar constraints de vigência e unicidade.
- [ ] Criar índices de consulta e auditoria.
- [ ] Aplicar políticas de RLS compatíveis com o restante do banco.
- [ ] Garantir rollback seguro com `downgrade`.
- [ ] Testar `upgrade` e `downgrade` em ambiente de validação.
- [ ] Validar compatibilidade com dados existentes de Propriedades e Imóveis Rurais.

### Bloqueios

- Migration sem rollback.
- Falta de constraint de integridade referencial.
- RLS não aplicado ao novo objeto.
- Incompatibilidade com chaves atuais.

---

## Fase 3 — Backend

### Checklist

- [ ] Criar model SQLAlchemy de `PropriedadeImovel`.
- [ ] Criar schemas Pydantic de request/response.
- [ ] Criar service dedicado com regras de negócio isoladas.
- [ ] Criar router FastAPI para gerenciamento do vínculo.
- [ ] Criar testes unitários do service.
- [ ] Criar testes de integração do router.
- [ ] Validar isolamento por tenant em todas as operações.
- [ ] Validar vínculo principal.
- [ ] Validar vigência ativa/inativa.
- [ ] Validar origem documental obrigatória.
- [ ] Validar leitura cruzada com `Propriedades` e `Imóveis Rurais`.
- [ ] Garantir que dados fundiários continuem sendo escritos apenas na origem oficial.

### Bloqueios

- Serviço sem isolamento por tenant.
- Router permitindo escrita fora da fonte oficial.
- Testes sem cobertura para vínculos inválidos.
- Origem documental opcional em casos obrigatórios.

---

## Fase 4 — Compatibilidade com Legado

### Checklist

- [ ] Manter leitura dos campos antigos enquanto a migração estiver em andamento.
- [ ] Bloquear escrita em campos fundiários duplicados quando a nova origem estiver ativa.
- [ ] Definir warnings claros para uso de campos legados.
- [ ] Definir política de depreciação dos campos duplicados.
- [ ] Mapear quais campos são migráveis, deriváveis ou apenas históricos.
- [ ] Preservar histórico completo de alterações.
- [ ] Garantir que o comportamento legado não quebre relatórios existentes durante a transição.

### Bloqueios

- Remoção imediata dos campos legados sem compatibilidade.
- Escrita simultânea em duas fontes oficiais.
- Perda de histórico.

---

## Fase 5 — Frontend

### Checklist

- [ ] Atualizar a tela de Propriedades para refletir apenas o domínio operacional.
- [ ] Atualizar a tela de Imóveis Rurais para refletir apenas o domínio fundiário/documental.
- [ ] Criar visualização de vínculos entre Propriedades e Imóveis Rurais.
- [ ] Criar formulário de vínculo `PropriedadeImovel`.
- [ ] Impedir edição de dados fora da fonte oficial.
- [ ] Exibir dados espelhados como somente leitura.
- [ ] Manter a UI premium com `shadcn/ui`, `Tailwind` e padrão visual existente.
- [ ] Revisar estados vazios, skeletons e carregamento das telas impactadas.

### Bloqueios

- UI permitindo edição em fonte derivada.
- Tela única misturando semântica operacional e fundiária sem distinção.
- Quebra do padrão visual do produto.

---

## Fase 6 — Rastreabilidade

### Checklist

- [ ] Atualizar a cadeia oficial para `Produção -> Safra -> Talhão -> Propriedade -> PropriedadeImovel -> Imóvel Rural`.
- [ ] Validar origem territorial da produção.
- [ ] Validar documentação fundiária do imóvel correspondente.
- [ ] Validar titularidade na camada fundiária.
- [ ] Validar histórico completo do vínculo.
- [ ] Garantir que rastreabilidade não termine em Propriedades sem chegar ao imóvel rural.

### Bloqueios

- Cadeia incompleta.
- Rastreamento sem vínculo canônico.
- Falta de prova documental para origem.

---

## Fase 7 — ESG / Certificações / Projeto Raízes

### Checklist

- [ ] Validar compatibilidade da nova modelagem com fluxos ESG.
- [ ] Validar suporte a certificações e auditorias externas.
- [ ] Validar suporte ao Projeto Raízes.
- [ ] Validar cadeia de custódia com lastro documental.
- [ ] Validar auditoria documental e temporal do vínculo.
- [ ] Garantir que a solução não crie fonte duplicada para evidência ambiental ou fundiária.

### Bloqueios

- Incompatibilidade com auditoria.
- Rastreabilidade sem lastro documental.
- Impossibilidade de provar origem para ESG ou Raízes.

---

## Fase 8 — Testes e Aceite

### Checklist

- [ ] Executar `pytest` no backend para os módulos alterados.
- [ ] Executar testes de RLS.
- [ ] Executar testes de isolamento por tenant.
- [ ] Executar testes de integração do novo vínculo.
- [ ] Executar testes frontend das telas impactadas.
- [ ] Executar testes de regressão para fluxos existentes.
- [ ] Executar testes de rastreabilidade fim a fim.
- [ ] Executar testes de migration `upgrade/downgrade`.
- [ ] Validar que não houve regressão na leitura de dados legados.

### Bloqueios

- Testes vermelhos em qualquer camada crítica.
- Falha em RLS ou tenant isolation.
- Falha de rastreabilidade.
- Falha na migração reversível.

---

## Ordem recomendada de execução

1. Fase 0 - Preparação.
2. Fase 1 - Data Model.
3. Fase 2 - Migration Alembic.
4. Fase 3 - Backend.
5. Fase 4 - Compatibilidade com Legado.
6. Fase 5 - Frontend.
7. Fase 6 - Rastreabilidade.
8. Fase 7 - ESG / Certificações / Projeto Raízes.
9. Fase 8 - Testes e Aceite.

---

## Tarefas bloqueantes

As tarefas abaixo precisam estar resolvidas antes de avançar:

- Definição formal do `PropriedadeImovel` no data model.
- Constraints e vigência formalizadas.
- Migration com rollback seguro.
- Garantia de RLS e isolamento por tenant.
- Definição da política de legado para campos fundiários duplicados.
- Atualização da rastreabilidade até o imóvel rural.

---

## Riscos a monitorar

- Duplicidade de fonte da verdade durante a transição.
- Quebra de compatibilidade em APIs já consumidas pelo frontend.
- Perda de histórico em dados migrados.
- Divergência entre leitura operacional e leitura fundiária.
- Regressão em rastreabilidade, ESG e certificações.
- Falhas de RLS ou isolamento por tenant.
- Impacto inesperado em relatórios e dashboards existentes.

---

## Critérios de aceite

A implementação pode ser considerada concluída quando todos os itens abaixo forem verdadeiros:

- `PropriedadeImovel` existe e é a entidade canônica do vínculo.
- Existe uma única fonte da verdade para cada campo crítico.
- A cardinalidade `N:N` está implementada e validada.
- RLS e tenant isolation estão preservados.
- O fluxo de rastreabilidade chega até o `Imóvel Rural`.
- ESG, Certificações e Projeto Raízes continuam suportados.
- Os testes de backend, frontend e migration estão em verde.
- Os dados legados foram preservados ou adequadamente deprecados sem quebra funcional.

---

## Resumo executivo

Este checklist deve ser usado como roteiro de execução para o agente Codex em tarefas futuras. A implementação só deve começar quando as fases estruturais de dados e migração estiverem aprovadas, pois elas são os pontos de maior risco e bloqueio.

