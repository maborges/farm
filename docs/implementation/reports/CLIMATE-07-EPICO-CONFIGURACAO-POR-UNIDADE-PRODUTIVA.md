# CLIMATE-07: Configuração de Dados Climáticos por Unidade Produtiva

**Tipo:** Épico de refatoração arquitetural  
**Status:** Em implementação  
**Domínio:** Agrícola / Integrações / Dados Climáticos  
**Prioridade:** Alta  
**Origem:** Auditoria de Dados Climáticos  

## 1. Resumo Executivo

Esta documentação formaliza o épico de refatoração da integração climática. A auditoria identificou que o provider OpenWeather é configurado no escopo do tenant, enquanto o dado climático consumido pelo dashboard pertence à unidade produtiva. O épico corrige essa divergência sem criar uma arquitetura paralela, preservando RLS, eventos, jobs, histórico e compatibilidade controlada.

## 2. Objetivo

Refatorar a integração climática para que sua configuração, execução, saúde operacional e sincronização sejam controladas por unidade produtiva, mantendo o isolamento por tenant e a persistência dos registros climáticos associada à unidade correta.

## 3. Estado Atual e Problema

O OpenWeather está configurado no escopo do tenant (`TENANT`), mas:

- os registros climáticos pertencem a uma unidade produtiva;
- a sincronização percorre todas as unidades ativas do tenant;
- não existe sincronização unitária;
- status, health e último sincronismo são agregados no tenant;
- a interface de configuração não permite selecionar a unidade;
- configurações unitárias existentes no modelo (`scope_type`/`scope_id`) não são utilizadas pelo provider climático.

## 4. Resultado Esperado

```text
Configuração  → Unidade produtiva
Sincronização → Unidade produtiva
Job/Health    → Unidade produtiva
Evento        → Unidade produtiva
Registro      → Unidade produtiva
Dashboard     → Unidade produtiva
```

A API key poderá permanecer como credencial compartilhada do tenant, referenciada pelas configurações unitárias, evitando duplicação de segredos criptografados. Essa decisão deve ser confirmada antes da implementação.

## 5. Escopo Funcional

### 5.1 Backend e modelo de dados

- Adotar `UNIDADE_PRODUTIVA` como escopo oficial da configuração climática.
- Persistir `unidade_produtiva_id` por meio de `scope_id` ou vínculo explícito equivalente.
- Garantir unicidade por tenant, provider, tipo de escopo e unidade.
- Validar que a unidade pertence ao tenant autenticado.
- Manter RLS em todas as configurações, credenciais, jobs, health e registros.
- Preservar histórico de versões e auditoria.

### 5.2 Migração

- Localizar configurações OpenWeather existentes no escopo `TENANT`.
- Criar configurações unitárias para as unidades produtivas ativas.
- Reutilizar a credencial compartilhada quando aplicável.
- Preservar configurações e histórico existentes.
- Marcar configurações tenant-only como legadas ou desativadas após a migração.
- Colocar unidades sem coordenadas em estado pendente, sem simular sincronização bem-sucedida.
- Tornar a migração segura para reexecução e rollback controlado.

### 5.3 API e sincronização

Criar contratos unitários para:

```text
GET  /api/v1/integracoes/openweather/config/{unidade_produtiva_id}
POST /api/v1/integracoes/openweather/config/{unidade_produtiva_id}
POST /api/v1/integracoes/openweather/testar-conexao/{unidade_produtiva_id}
POST /api/v1/integracoes/openweather/sync/current-weather/{unidade_produtiva_id}
GET  /api/v1/integracoes/openweather/status/{unidade_produtiva_id}
GET  /api/v1/integracoes/openweather/health/{unidade_produtiva_id}
```

Cada execução deverá:

- consultar somente a unidade solicitada;
- usar suas coordenadas;
- criar job com referência da unidade;
- publicar evento com `tenant_id` e `unidade_produtiva_id`;
- atualizar health e último sincronismo unitários;
- registrar falhas de conexão, credencial ou coordenada na unidade correta.

A rota tenant-wide atual poderá permanecer temporariamente como compatibilidade, delegando para execuções unitárias explícitas.

### 5.4 Frontend Web

- Adicionar contexto/seletor de unidade produtiva na tela OpenWeather.
- Exibir configuração, status, health e último sincronismo da unidade selecionada.
- Permitir testar e sincronizar uma unidade por vez.
- Informar claramente unidades sem coordenadas válidas.
- Alinhar a tela de configuração com o mesmo `activeFazendaId` usado no dashboard climático.
- Remover mensagens que indiquem uma configuração global quando o estado for unitário.

### 5.5 Observabilidade

- Identificar jobs, timeline, health, alertas e logs por unidade produtiva.
- Diferenciar falha parcial de falha total.
- Exibir quantidade de unidades processadas somente em operações agregadas.
- Impedir que o sucesso de uma unidade oculte falhas de outra.

## 6. Fora do Escopo

- Troca do provider OpenWeather.
- Implementação de previsão, histórico ou pluviometria além do contrato atual.
- Alteração do domínio territorial ou da entidade `UnidadeProdutiva`.
- Criação de uma segunda tabela paralela de configurações climáticas.
- Remoção imediata das rotas legadas antes da janela de compatibilidade.

## 7. Critérios de Aceite

- [ ] Duas unidades do mesmo tenant podem possuir configurações independentes.
- [ ] Uma unidade não acessa configuração, job, health ou registro de outra unidade de outro tenant.
- [ ] Sincronizar uma unidade não altera a configuração nem o status de outra.
- [ ] A sincronização usa exclusivamente as coordenadas da unidade selecionada.
- [ ] Unidade sem coordenadas aparece como pendente e gera diagnóstico acionável.
- [ ] Registros climáticos continuam idempotentes por unidade, data e fonte.
- [ ] Jobs, health, alertas e timeline identificam a unidade produtiva.
- [ ] A migração tenant → unidade preserva credenciais, histórico e rastreabilidade.
- [ ] A interface exibe dados da unidade selecionada, sem misturar tenants ou unidades.
- [ ] Testes automatizados cobrem RLS, migração, falhas parciais, ausência de coordenadas e reexecução.
- [ ] Documentação de modelo de dados e rotas está atualizada.

## 8. Fases de Execução

1. **Decisão de credencial e contrato unitário**
2. **Modelagem, constraints e migração de dados**
3. **Refatoração do adapter e service OpenWeather**
4. **Eventos, persistência, jobs, health e alertas unitários**
5. **Novas rotas e compatibilidade legada**
6. **Refatoração da tela de configuração e dashboard**
7. **Testes de integração, RLS e migração**
8. **Rollout gradual, observabilidade e retirada do fluxo legado**

## 9. Riscos e Decisões Pendentes

| Item | Risco/decisão |
|---|---|
| Credencial | Definir se a API key será compartilhada pelo tenant ou unitária. |
| Migração | Definir comportamento para tenants com várias unidades e um único `location_query`. |
| Coordenadas | Definir se coordenadas inválidas bloqueiam configuração ou apenas sincronização. |
| Compatibilidade | Definir prazo para remoção das rotas tenant-wide. |
| Agendamento | Definir se jobs automáticos serão unitários ou agregados com rastreabilidade unitária. |

## 10. Evidências e Referências

- `services/api/integracoes/openweather/services.py`
- `services/api/integracoes/openweather/routers.py`
- `services/api/integracoes/models.py`
- `services/api/agricola/climatico/models.py`
- `services/api/agricola/climatico/subscribers.py`
- `apps/web/src/components/integracoes/openweather-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/agricola/climatico/page.tsx`

## 11. Estado da Implementação

### Backend concluído nesta etapa

- Escopo `UNIDADE_PRODUTIVA` adicionado ao domínio de integrações.
- Configuração unitária OpenWeather implementada, mantendo a credencial compartilhada do tenant.
- Endpoints unitários de configuração, status, health, teste, sincronização, jobs, timeline e diagnóstico adicionados.
- Sincronização unitária passa somente as coordenadas da unidade selecionada ao provider.
- Migração criada para habilitar o escopo, materializar configurações por unidade e criar unicidade ativa por escopo.

### Frontend concluído nesta etapa

- Console OpenWeather passou a usar `activeFazendaId` como unidade ativa.
- Configuração, teste, sincronização, status, health, jobs, timeline e diagnóstico usam o contexto unitário.
- Ações ficam bloqueadas quando não há unidade produtiva ativa.

### Validação desta etapa

- Python: compilação sintática dos módulos alterados aprovada.
- TypeScript: sem erro identificado nos arquivos climáticos alterados; o projeto possui erros preexistentes em outros componentes.
- Testes OpenWeather: 7 aprovados e 1 falha preexistente relacionada à expectativa do menu lateral.
- Migração Alembic: criada, ainda requer execução em banco de homologação antes do rollout.

## 12. Veredicto do Épico

O épico é **necessário e aprovado para planejamento**. A configuração unitária deve ser implementada antes de ampliar o dashboard climático ou criar novos consumidores operacionais, pois o escopo atual mistura configuração global com dados unitários.

As mudanças de código foram iniciadas em ambiente de desenvolvimento. A migração ainda não foi executada em banco produtivo, e o rollout deverá aguardar validação em homologação, correção dos débitos de TypeScript preexistentes e confirmação da cadeia de migrations.
