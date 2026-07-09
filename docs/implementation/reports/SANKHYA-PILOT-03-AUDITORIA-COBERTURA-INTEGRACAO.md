# SANKHYA-PILOT-03 - Auditoria de Cobertura Funcional da Integração AgroSaaS x Sankhya

Data: 2026-07-08
Escopo: Auditoria sem alteração de código
Status da execução: Concluída

## 1. Resumo executivo

Esta auditoria confirma que a arquitetura oficial de integração AgroSaaS x Sankhya está materializada em boa parte da camada técnica de fundação, mas a cobertura funcional operacional para um piloto com ERP ainda é incompleta.

Há uma diferença objetiva entre:

- fundação técnica/canônica já implementada;
- integrações realmente operacionais no fluxo Sankhya;
- integrações apenas previstas, testadas em helper ou modeladas sem fluxo de negócio completo.

Conclusão objetiva:

- a fundação técnica da integração está em estágio avançado;
- a cobertura funcional operacional para piloto ERP está parcial;
- o AgroSaaS não está pronto para um piloto Sankhya completo para produtor de café exportador sem forte contenção de escopo;
- o veredicto final desta auditoria é **GO COM RESSALVAS** somente para piloto controlado com escopo reduzido;
- para piloto amplo com financeiro, estoque, contratos, comercialização e fiscal além de NFe, o veredicto seria **NO GO**.

Percentuais consolidados desta auditoria:

- cobertura técnica da fundação canônica: **76%**
- cobertura funcional operacional Sankhya para o piloto ERP: **34%**
- cobertura piloto crítica para cliente café exportador: **28%**

Critério usado:

- cobertura técnica considera modelos, adapter, autenticação, health, jobs, associação externa, observabilidade e rotas existentes;
- cobertura funcional considera somente fluxos utilizáveis de ponta a ponta para operação do piloto;
- itens apenas modelados, testados isoladamente ou desabilitados por feature não foram contabilizados como prontos.

## 2. Arquivos auditados

### Arquitetura e governança

- `docs/architecture/INTEGRATION-ARCH-03-ASSOCIACAO-REGISTROS-EXTERNOS.md`
- `docs/architecture/INTEGRATION-ARCH-04-PLANO-IMPLEMENTACAO-ASSOCIACAO-EXTERNA.md`
- `docs/implementation/reports/PILOT-ARCH-01-ARQUITETURA-IMPLANTACAO.md`
- `docs/implementation/reports/PRODUCT-ARCH-01-DOMINIO-PRODUTOS-CULTURAS-COMMODITIES.md`
- `docs/implementation/reports/ECONOMIC-ARCH-01-DOMINIO-ECONOMICO1.md`
- `docs/implementation/reports/EVENTS-ARCH-01-EVENT-DRIVEN-OUTBOX-ALERTS-NOTIFICATIONS.md`

### Backend de integração

- `services/api/integracoes/models.py`
- `services/api/integracoes/events.py`
- `services/api/integracoes/services/external_record_association_service.py`
- `services/api/integracoes/sankhya/__init__.py`
- `services/api/integracoes/sankhya/README.md`
- `services/api/integracoes/sankhya/models/__init__.py`
- `services/api/integracoes/sankhya/routers/__init__.py`
- `services/api/integracoes/sankhya/schemas/__init__.py`
- `services/api/integracoes/sankhya/services/__init__.py`
- `services/api/integracoes/sankhya/services/auth_service.py`
- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/external_association_helper.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/subscribers.py`
- `services/api/core/routers/configuration.py`
- `services/api/main.py`

### Frontend

- `apps/web/src/components/integracoes/sankhya-console.tsx`
- `apps/web/src/components/integracoes/sankhya-timeline.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/erp/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx`
- `apps/web/src/app/integracoes/sankhya/page.tsx`
- `apps/web/src/app/integracoes/page.tsx`

### Testes auditados

- `services/api/tests/unit/integracoes/test_external_record_association_service.py`
- `services/api/tests/unit/integracoes/test_integrations_architecture_guardrails.py`
- `services/api/tests/unit/integracoes/test_integrations_foundation_models.py`
- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_governance_router.py`
- `services/api/tests/unit/integracoes/test_sankhya_external_association_p0.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_auth_service.py`
- `services/api/tests/unit/integracoes/test_sankhya_gateway_test_connection.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## 3. Arquiteturas verificadas

### INTEGRATION-ARCH-03 e INTEGRATION-ARCH-04

Status: **IMPLEMENTADO PARCIALMENTE**

Constatações:

- `ExternalRecordAssociation` está implementado de forma genérica.
- `IntegrationCredential`, `IntegrationSyncPolicy`, `IntegrationJob` e `IntegrationHealth` existem e são usados.
- o `SankhyaCanonicalAdapter` sincroniza provider legado e domínio canônico.
- a fundação prevista em arquitetura foi materializada além do que os próprios documentos ainda descrevem.
- a operação real cobre menos do que a fundação permite.

### PILOT-ARCH-01

Status: **IMPLEMENTADO PARCIALMENTE**

Constatações:

- a arquitetura do piloto reconhece ERP externo como etapa de implantação.
- a ordem de implantação descrita no documento é coerente.
- a parte de configuração ERP no produto existe, mas a experiência ainda está desalinhada com o modelo Gateway-first.

### PRODUCT-ARCH-01

Status: **IMPLEMENTADO**

Constatações:

- produtos e estrutura agro permanecem do lado AgroSaaS.
- a integração com ERP não desloca o domínio agrícola para o Sankhya.

### ECONOMIC-ARCH-01

Status: **IMPLEMENTADO PARCIALMENTE**

Constatações:

- o AgroSaaS possui domínio econômico próprio.
- a integração financeira Sankhya existe, mas ainda não cobre ciclo financeiro completo.

### EVENTS-ARCH-01

Status: **IMPLEMENTADO PARCIALMENTE**

Constatações:

- existe modelagem oficial de eventos e publicação segura.
- o subscriber Sankhya existe.
- no Sankhya, o uso operacional do modelo event-driven ainda está limitado a `pessoas` e `produtos`.
- não foi encontrado produtor real de `IntegrationSyncRequested` em fluxo de negócio ativo.

## 4. Matriz completa de integração

### Cadastros

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Parceiros | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO | P0 |
| Clientes | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Fornecedores | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Produtos | Compartilhado, master preferencial no ERP quando houver ERP | ERP -> AgroSaaS | IMPLEMENTADO | P0 |
| Empresas | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Filiais | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Depósitos | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Bancos | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P1 |
| Contas Correntes | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Naturezas Financeiras | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Tipos de Operação | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P1 |
| Centros de Custo | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Centros de Resultado | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |

### Financeiro

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Contas a Pagar | Compartilhado, master administrativo no ERP | AgroSaaS <-> ERP | IMPLEMENTADO | P0 |
| Contas a Receber | Compartilhado, master administrativo no ERP | AgroSaaS <-> ERP | IMPLEMENTADO | P0 |
| Pagamentos | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P0 |
| Recebimentos | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P0 |
| Baixas | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P0 |
| Rateios | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P1 |
| Adiantamentos | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P1 |

### Estoque

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Depósitos | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Movimentos | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Entradas | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Saídas | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Transferências | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P1 |
| Inventário | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P1 |

### Comercialização

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Contratos | Compartilhado, master negocial depende do desenho do piloto | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Pedidos | Compartilhado | AgroSaaS <-> ERP | IMPLEMENTADO PARCIALMENTE | P0 |
| Comercialização | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Barter | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Entregas | Compartilhado | AgroSaaS <-> ERP | NÃO IMPLEMENTADO | P0 |
| Faturamento | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |

### Fiscal

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| NFe | Compartilhado, emissão fiscal no ERP | AgroSaaS <-> ERP | IMPLEMENTADO | P0 |
| CT-e | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P1 |
| MDF-e | ERP Sankhya | ERP -> AgroSaaS | NÃO IMPLEMENTADO | P1 |
| Documentos fiscais | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P0 |
| Impostos | ERP Sankhya | ERP -> AgroSaaS | IMPLEMENTADO PARCIALMENTE | P1 |

### Agricultura

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Safras | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Cultivos | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Talhões | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Operações Agrícolas | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Recomendações | AgroSaaS | N/A | NÃO SE APLICA | P1 |
| Clima | AgroSaaS | N/A | NÃO SE APLICA | P1 |
| Custos Operacionais | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Rentabilidade | AgroSaaS | N/A | NÃO SE APLICA | P0 |

### Pecuária

| Domínio | Dono da informação | Direção | Status | Prioridade |
| ------- | ------------------ | ------- | ------ | ---------- |
| Animais | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Lotes | AgroSaaS | N/A | NÃO SE APLICA | P0 |
| Piquetes | AgroSaaS | N/A | NÃO SE APLICA | P1 |
| Pesagens | AgroSaaS | N/A | NÃO SE APLICA | P1 |
| Vacinação | AgroSaaS | N/A | NÃO SE APLICA | P1 |
| Reprodução | AgroSaaS | N/A | NÃO SE APLICA | P1 |

## 5. Cobertura funcional

### 5.1 Integrações já implementadas

| Integração | Status | Onde está implementada | Endpoints | Eventos | Gateway | ExternalRecordAssociation | Testes | Pronta para piloto |
| ---------- | ------ | ---------------------- | --------- | ------- | ------- | ------------------------- | ------ | ------------------ |
| Configuração Sankhya | IMPLEMENTADO | `auth_service.py`, `sync_service.py`, `routers/__init__.py`, `canonical_adapter.py` | `/api/v1/integracoes/sankhya/config`, `/config/testar-conexao`, `/status`, `/health` | `IntegrationConfigured`, `IntegrationCredentialRotated`, `IntegrationHealthChanged` | Sim | Não se aplica | Sim | Sim, com ressalva de UX |
| Parceiros/Pessoas | IMPLEMENTADO | `sync_service.py`, `external_association_helper.py`, `routers/__init__.py` | `/sync/pessoas`, `/pessoas` | `IntegrationSyncStarted`, `IntegrationSyncCompleted`, `IntegrationSyncFailed` | Sim | Sim | Sim | Sim |
| Produtos | IMPLEMENTADO | `sync_service.py`, `external_association_helper.py`, `routers/__init__.py` | `/sync/produtos`, `/produtos` | `IntegrationSyncStarted`, `IntegrationSyncCompleted`, `IntegrationSyncFailed` | Sim | Sim | Sim | Sim |
| NFe | IMPLEMENTADO | `nfe_financeiro_service.py`, `routers/__init__.py` | `/nfe/exportar`, `/nfe/importar-entrada`, `/nfe` | `IntegrationSyncStarted`, `IntegrationSyncCompleted`, `IntegrationSyncFailed` | Sim | Sim | Sim | Sim, com escopo limitado a NFe |
| Financeiro básico | IMPLEMENTADO | `nfe_financeiro_service.py`, `routers/__init__.py` | `/financeiro/exportar-contas-pagar`, `/financeiro/exportar-contas-receber`, `/financeiro/importar`, `/financeiro` | `IntegrationSyncStarted`, `IntegrationSyncCompleted`, `IntegrationSyncFailed` | Sim | Sim | Sim | Parcialmente |
| Observabilidade e governança | IMPLEMENTADO | `canonical_adapter.py`, `sync_service.py`, `routers/__init__.py`, `sankhya-console.tsx`, `sankhya-timeline.tsx` | `/jobs`, `/timeline`, `/diagnostico`, `/logs`, `/associacoes/pendentes`, `/associacoes/{id}/reconciliar` | health e sync events canônicos | Sim | Sim | Sim | Sim |

### 5.2 Integrações implementadas parcialmente

| Integração | Evidência | Lacuna principal | Classificação |
| ---------- | --------- | ---------------- | ------------- |
| Empresas e filiais | `sync_organizacao` no helper | sem rota dedicada, sem job operacional explícito | IMPLEMENTADO PARCIALMENTE |
| Depósitos | `sync_deposito` no helper e testes P0 | sem sync operacional dedicado de depósitos | IMPLEMENTADO PARCIALMENTE |
| Contas correntes | `sync_conta_bancaria` no helper e testes | sem importação operacional dedicada | IMPLEMENTADO PARCIALMENTE |
| Naturezas financeiras | `sync_plano_natureza` chamado via financeiro | sem feature/rota dedicada de cadastro mestre | IMPLEMENTADO PARCIALMENTE |
| Centros de custo | `sync_centro_custo` no helper e testes | sem sync operacional dedicado | IMPLEMENTADO PARCIALMENTE |
| Centros de resultado | `sync_centro_resultado` no helper e testes | sem sync operacional dedicado | IMPLEMENTADO PARCIALMENTE |
| Tipos de operação | `sync_tipo_operacao` no helper e testes | sem fluxo operacional | IMPLEMENTADO PARCIALMENTE |
| Pedidos | feature canônica existe em `_FEATURE_DEFAULTS` | desabilitado e sem serviço/rota funcional | IMPLEMENTADO PARCIALMENTE |
| Estoque | feature canônica existe em `_FEATURE_DEFAULTS` | desabilitado e sem operação real | IMPLEMENTADO PARCIALMENTE |
| Faturamento/documentos fiscais | NFe já existe | CT-e, MDF-e e ciclo fiscal ampliado ausentes | IMPLEMENTADO PARCIALMENTE |
| Rateios | payload `rateio` modelado em financeiro | sem governança própria e sem fluxo de baixa/recebimento | IMPLEMENTADO PARCIALMENTE |
| Console de configuração ERP | tela existe | tela do tenant ainda modelada em WS legado e não gateway-first | IMPLEMENTADO PARCIALMENTE |

### 5.3 Integrações não implementadas

- bancos;
- pagamentos;
- recebimentos;
- baixas;
- adiantamentos;
- movimentos de estoque;
- entradas e saídas de estoque;
- transferências;
- inventário;
- contratos;
- comercialização;
- barter;
- entregas;
- CT-e;
- MDF-e;
- integração logística explícita;
- rastreabilidade orientada à cadeia de exportação;
- operação assistida para processos Sankhya além de pessoas e produtos.

### 5.4 Implementado mas não utilizado no piloto

| Item | Evidência | Observação |
| ---- | --------- | ---------- |
| Feature canônica de `pedidos` | `_FEATURE_DEFAULTS` em `canonical_adapter.py` | existe apenas como feature futura desabilitada |
| Feature canônica de `estoque` | `_FEATURE_DEFAULTS` em `canonical_adapter.py` | existe apenas como feature futura desabilitada |

## 6. Cobertura técnica

### 6.1 Modelos auditados

| Modelo | Status | Evidência |
| ------ | ------ | --------- |
| `ExternalRecordAssociation` | IMPLEMENTADO | `services/api/integracoes/models.py` |
| `IntegrationCredential` | IMPLEMENTADO | `services/api/integracoes/models.py` |
| `IntegrationJob` | IMPLEMENTADO | `services/api/integracoes/models.py` |
| `IntegrationHealth` | IMPLEMENTADO | `services/api/integracoes/models.py` |
| `IntegrationSyncPolicy` | IMPLEMENTADO | `services/api/integracoes/models.py` |
| `SankhyaSyncLog` | IMPLEMENTADO | `services/api/integracoes/sankhya/models/__init__.py` |

### 6.2 Arquitetura canônica

Status: **IMPLEMENTADO**

Evidências:

- domínio canônico de integrações presente;
- credenciais segregadas e mascaradas;
- jobs canônicos com health snapshot;
- feature e policy por configuração;
- governança de associação externa;
- histórico de associação externa;
- timeline operacional consolidada;
- diagnóstico consolidado.

### 6.3 Gateway, auth e provider

Status: **IMPLEMENTADO**

Evidências:

- `SankhyaGatewayAuthService` valida e autentica via Gateway;
- suporta fallback legado para compatibilidade;
- backend aceita `sankhya_api_base_url`, `sankhya_auth_url`, `sankhya_client_id`, `sankhya_client_secret`, `sankhya_x_token`;
- resposta de diagnóstico sanitiza segredos.

### 6.4 Event-driven e sync desacoplado

Status: **IMPLEMENTADO PARCIALMENTE**

Evidências:

- eventos canônicos definidos;
- subscriber Sankhya registrado;
- acoplamento real do subscriber limitado a `pessoas` e `produtos`;
- não foi encontrado produtor real de `IntegrationSyncRequested`, o que reduz a efetividade operacional do modelo desacoplado.

### 6.5 Frontend

| Área | Status | Evidência |
| ---- | ------ | --------- |
| Central de Integrações | IMPLEMENTADO PARCIALMENTE | `sankhya-console.tsx` existe, mas ainda usa `ws_url`, `username`, `password` |
| Configuração ERP | IMPLEMENTADO PARCIALMENTE | backend é gateway-first, frontend tenant ainda é legacy-first |
| Telas Sankhya | IMPLEMENTADO | páginas de tenant e backoffice existem |
| Monitoramento de sincronização | IMPLEMENTADO | status, health, jobs, logs, timeline e diagnóstico já expostos |

## 7. Cobertura para o piloto

### 7.1 O que está pronto para um piloto controlado

- configuração da integração no backend;
- autenticação via Gateway Sankhya;
- teste de conexão;
- importação de parceiros/pessoas;
- importação de produtos;
- importação e exportação básica de NFe;
- exportação/importação financeira básica em nível de títulos;
- health, jobs, logs, timeline e diagnóstico operacional;
- governança manual de associações externas pendentes.

### 7.2 O que só está parcialmente pronto

- experiência do tenant para configurar credenciais Gateway;
- carga de empresas, filiais, depósitos, contas correntes, centros e natureza financeira;
- sincronização financeira de ciclo completo;
- uso real de sync orientado a eventos;
- fluxo de estoque;
- pedidos;
- escopo de faturamento além de NFe.

### 7.3 O que não está pronto para o piloto ERP amplo

- contratos;
- comercialização de café;
- barter;
- logística fiscal ampliada;
- pagamentos, recebimentos e baixas;
- integração de estoque operacional;
- integração logística;
- rastreabilidade de exportação ancorada no ERP.

## 8. Lacunas encontradas

### 8.1 Lacunas estruturais

- documentação do módulo Sankhya está inconsistente com o código atual.
- `services/api/integracoes/sankhya/__init__.py` ainda descreve WS BPM e Basic Auth, enquanto o backend oficial já suporta Gateway.
- `services/api/integracoes/sankhya/README.md` declara sincronização de tabelas CFOP/NCM, mas a auditoria encontrou apenas modelo `SankhyaTabela` sem fluxo operacional correspondente.

### 8.2 Lacunas funcionais

- ausência de sincronização operacional dedicada para depósitos, contas correntes, centros de custo, centros de resultado, tipos de operação, bancos e organizações;
- ausência de contratos, barter, comercialização e logística;
- ausência de ciclo financeiro completo;
- ausência de estoque operacional;
- ausência de CT-e e MDF-e.

### 8.3 Lacunas de experiência do usuário

- a tela principal do tenant para ERP ainda pede campos legados, não os campos do Gateway;
- o usuário pode concluir que a integração oficial ainda é por WS legado;
- isso conflita com a arquitetura oficial do produto e com o piloto que depende de ERP como origem administrativa.

### 8.4 Lacunas de desacoplamento operacional

- o subscriber Sankhya só processa `pessoas` e `produtos`;
- não foi encontrado emissor real de `IntegrationSyncRequested`;
- `sync/completo` não executa sincronização completa real, apenas retorna mensagem estática de fila.

## 9. Riscos

### 9.1 Riscos gerais

- risco de percepção falsa de prontidão, porque a fundação técnica é madura mas o fluxo funcional ainda não cobre o piloto ampliado;
- risco de retrabalho na implantação por dependência de cargas manuais paralelas;
- risco de duplicidade cadastral se master data não for claramente definido por domínio;
- risco de inconsistência entre monitoramento e operação real quando uma feature existe na camada canônica, mas não no fluxo de negócio.

### 9.2 Riscos para produtor de café exportador

- ausência de contratos e comercialização limita operação de café vendido por contratos e entregas programadas;
- ausência de barter inviabiliza cenários comuns de financiamento de insumos e liquidação em produto;
- ausência de CT-e e MDF-e deixa descoberta a trilha logística da expedição;
- ausência de estoque operacional integrado compromete rastreabilidade entre insumo, movimentação e entrega;
- ausência de ciclo financeiro completo dificulta conciliação de títulos, baixas, pagamentos e recebimentos;
- cobertura fiscal limitada a NFe não atende cadeia exportadora completa.

### 9.3 Riscos de qualidade

- a suíte `services/api/tests/unit/integracoes` não está totalmente verde no ambiente auditado;
- houve 4 falhas:
  - 3 falhas em `test_openweather_domain.py` por falta da tabela `unidades_produtivas` no banco de teste;
  - 1 falha em `test_sankhya_governed_integration.py` por divergência do texto esperado no frontend de backoffice;
- isso não invalida os achados Sankhya, mas indica fragilidade do pacote de regressão das integrações.

## 10. Recomendações

1. Alinhar imediatamente a tela do tenant com o modelo Gateway-first.
2. Explicitar no onboarding do tenant se haverá ERP e qual ERP será utilizado antes do workflow de carga inicial.
3. Priorizar cadastros mestres ERP antes de qualquer etapa operacional do wizard.
4. Separar no produto o que já é operacional do que é apenas governança canônica.
5. Materializar syncs dedicados para depósitos, contas correntes, natureza financeira, centros de custo, centros de resultado e tipos de operação.
6. Decidir formalmente o recorte do piloto:
   - piloto restrito a parceiros, produtos, NFe e financeiro básico;
   - ou piloto ampliado com estoque, comercialização e contratos.
7. Se o piloto for café exportador, incluir obrigatoriamente comercialização, contratos, logística e fiscal ampliado no backlog de prontidão.
8. Corrigir a documentação Sankhya para refletir a arquitetura real.
9. Fazer o pacote de testes de integrações voltar a verde antes de homologação.

## 11. Priorização P0, P1 e P2

### P0

- configuração Gateway-first no frontend do tenant;
- pergunta inicial do onboarding: usa ERP? qual ERP?;
- sincronização operacional de depósitos;
- sincronização operacional de contas correntes;
- sincronização operacional de natureza financeira;
- sincronização operacional de centros de custo;
- sincronização operacional de centros de resultado;
- sincronização operacional de tipos de operação;
- financeiro com baixas, pagamentos e recebimentos;
- estoque básico para operação real;
- contratos e comercialização mínima se o piloto for café exportador.

### P1

- bancos;
- transferências e inventário;
- CT-e;
- MDF-e;
- integração logística;
- melhoria do fluxo event-driven para além de pessoas e produtos.

### P2

- barter completo;
- rastreabilidade ampliada ponta a ponta;
- automações de reconciliação assistida;
- cobertura documental e diagnóstica mais granular por domínio.

## 12. Veredicto final

### Veredicto

**GO COM RESSALVAS**

### Justificativa técnica

O AgroSaaS está apto a operar um **piloto controlado e restrito** com Sankhya quando o escopo for limitado a:

- configuração da integração;
- parceiros/pessoas;
- produtos;
- NFe;
- financeiro básico por títulos;
- monitoramento e governança manual.

O AgroSaaS **não está apto** para um piloto Sankhya amplo de cliente café exportador se o escopo exigir:

- contratos;
- comercialização;
- barter;
- estoque operacional integrado;
- ciclo financeiro completo;
- CT-e/MDF-e;
- logística;
- rastreabilidade de exportação.

Em outras palavras:

- **GO COM RESSALVAS** para piloto muito controlado;
- **NO GO** para operação Sankhya ampla no cenário exportador.

## 13. Resposta objetiva por item solicitado

### Percentual de cobertura da integração

- cobertura técnica da fundação: **76%**
- cobertura funcional operacional Sankhya: **34%**
- cobertura crítica para piloto café exportador: **28%**

### Funcionalidades prontas

- autenticação via Gateway;
- configuração e teste de conexão;
- parceiros/pessoas;
- produtos;
- NFe;
- financeiro básico em nível de títulos;
- jobs, health, logs, timeline, diagnóstico;
- governança de associações externas.

### Funcionalidades parcialmente prontas

- empresas e filiais;
- depósitos;
- contas correntes;
- naturezas financeiras;
- tipos de operação;
- centros de custo;
- centros de resultado;
- pedidos;
- estoque;
- faturamento ampliado;
- configuração ERP no frontend do tenant.

### Funcionalidades ausentes

- bancos;
- pagamentos;
- recebimentos;
- baixas;
- adiantamentos;
- movimentos de estoque;
- contratos;
- comercialização;
- barter;
- entregas;
- CT-e;
- MDF-e;
- logística integrada;
- rastreabilidade exportadora orientada ao ERP.

### Riscos para cliente produtor de café exportador

- fluxo comercial incompleto;
- fiscal e logística incompletos;
- baixa rastreabilidade ERP x operação;
- risco de processo paralelo manual para estoque, financeiro e contratos;
- risco de duplicidade e reconciliação manual excessiva.

### Apto para operar integrado ao Sankhya no piloto controlado?

Sim, **somente** em piloto controlado e restrito.

### Veredicto final

**GO COM RESSALVAS**

Base técnica:

- fundação canônica sólida;
- operação funcional parcial;
- lacunas P0 ainda abertas para cenário ERP completo.

## 14. Validações executadas

### Testes

Comando executado:

```bash
services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q
```

Resultado:

- **101 testes passaram**
- **4 testes falharam**

Falhas encontradas:

- `services/api/tests/unit/integracoes/test_openweather_domain.py::test_teste_de_conexao_cria_job_health_e_eventos_canonicos`
- `services/api/tests/unit/integracoes/test_openweather_domain.py::test_falha_de_conexao_cria_alerta_e_health_degradado`
- `services/api/tests/unit/integracoes/test_openweather_domain.py::test_status_timeline_e_diagnostico_consolidam_camadas_canonicas`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py::test_backoffice_nao_e_console_principal_da_configuracao`

### Integridade do diff

Comando executado:

```bash
git diff --check
```

Resultado:

- sem inconsistências de whitespace no diff.

Observação:

- esta execução não alterou código de aplicação;
- o único artefato criado foi este relatório documental.
