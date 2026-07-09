# ERP-DOMAIN-01 - Decisões para Piloto ERP

Data: 2026-07-08
Escopo: arquitetura e governança
Status: concluído

## 1. Decisões tomadas

1. Foi criada a arquitetura oficial agnóstica a provider em [ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md](/opt/lampp/htdocs/farm/docs/architecture/ERP-DOMAIN-01-MATRIZ-PROPRIEDADE-DADOS.md).
2. O domínio ERP foi separado formalmente do adapter do provider.
3. O AgroSaaS foi reafirmado como master de operação agrícola, pecuária, território, custos operacionais e rastreabilidade operacional.
4. O ERP foi reafirmado como master de fiscal, contábil e financeiro administrativo.
5. Estoque operacional e estoque administrativo/contábil foram separados como fronteiras obrigatórias.
6. Financeiro operacional AgroSaaS e financeiro administrativo ERP foram separados como fronteiras obrigatórias.
7. Contratos agrícolas, comercialização, barter e rastreabilidade de exportação foram posicionados com master AgroSaaS, com reflexos administrativos para o ERP.
8. O escopo oficial do ERP foi fixado em `TENANT` ou `ESTABELECIMENTO`, nunca `UNIDADE_PRODUTIVA`.
9. Foi fixada a decisão v1.0 de suportar operação sem ERP, um ERP por tenant e evolução para ERP por estabelecimento.

## 2. Entidades críticas para piloto ERP

### P0 universais

- pessoas
- clientes
- fornecedores
- produtos de estoque
- empresas
- filiais
- estabelecimentos
- depósitos
- bancos
- contas correntes
- naturezas financeiras
- centros de custo
- centros de resultado
- contas a pagar
- contas a receber
- pagamentos
- recebimentos
- baixas
- NFe
- documentos fiscais
- `ExternalRecordAssociation`
- `IntegrationJob`
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- logs
- reconciliação manual

### P0 do lado AgroSaaS para convivência com ERP

- unidade produtiva
- propriedade
- área rural
- talhão
- safra
- operação agrícola
- aplicação de insumos
- colheita
- romaneio
- produto colhido
- `CostAllocation`
- DRE operacional
- rentabilidade operacional
- rastreabilidade operacional

## 3. Entidades críticas para piloto Sankhya

### Já cobertas ou parcialmente cobertas

- configuração do provider
- autenticação
- health
- jobs
- pessoas
- produtos
- NFe
- financeiro básico
- governança de associações externas

### Ainda críticas e abertas

- depósitos
- contas correntes
- naturezas financeiras
- centros de custo
- centros de resultado
- tipos de operação
- pagamentos
- recebimentos
- baixas
- estoque administrativo
- contratos
- comercialização
- barter
- CT-e
- MDF-e

## 4. Lacunas gerais de arquitetura ERP

- ausência histórica de uma matriz única de propriedade dos dados;
- falta de arbitragem formal para entidades compartilhadas;
- ausência de separação explícita entre estoque operacional e estoque contábil em integrações;
- ausência de separação explícita entre custo operacional e financeiro administrativo;
- necessidade de resolução oficial por `ESTABELECIMENTO`;
- necessidade de regra oficial de múltiplos ERPs por escopo;
- necessidade de contrato obrigatório para adapters.

## 5. Lacunas específicas do Sankhya

- adapter atual cobre só parte do domínio ERP;
- event-driven real ainda limitado;
- `sync/completo` não representa sync completo funcional;
- UX do tenant ainda não está plenamente alinhada ao modelo Gateway-first;
- cadastros mestres administrativos relevantes ainda não têm sync operacional dedicado;
- cobertura comercial, logística e fiscal ampliada ainda é insuficiente para exportação.

## 6. O que deve ser obrigatório para qualquer adapter ERP

- provider identificado
- escopo administrativo explícito
- autenticação segura
- teste de conexão
- health check
- diagnóstico
- logs
- jobs
- políticas de retry
- políticas de rate limit
- paginação
- payload normalizado
- declaração de entidades suportadas
- declaração de entidades não suportadas
- direção suportada por entidade
- campos obrigatórios por entidade
- estratégia de `external_id`
- estratégia de chave composta
- `ExternalRecordAssociation`
- reconciliação manual
- `IntegrationSyncPolicy`
- `IntegrationHealth`
- eventos de sync ou estratégia equivalente de desacoplamento

## 7. O que pode ser provider-specific

- protocolo técnico
- modelo de autenticação
- endpoints
- paginação específica
- eventos nativos do provider
- staging especializado
- objetos fiscais ou logísticos específicos
- suportes proprietários a barter
- exportação
- CT-e
- MDF-e
- limites de throughput
- formato de payload

## 8. Recomendação de escopo

### Piloto restrito

Recomendado quando houver necessidade de validar fundação e operação mínima.

Escopo:

- pessoas
- produtos
- NFe
- financeiro básico
- cadastros mestres administrativos mínimos
- observabilidade
- reconciliação manual

Classificação:

- **recomendado**

### Piloto ampliado

Recomendado apenas quando os P0 administrativos e a separação estoque/financeiro estiverem operacionais.

Escopo adicional:

- depósitos
- contas correntes
- centros
- naturezas
- pagamentos
- recebimentos
- baixas
- estoque administrativo
- pedidos
- contratos
- comercialização

Classificação:

- **recomendado com ressalvas**

### Piloto não recomendado

Não recomendado enquanto não houver cobertura adicional para cadeia exportadora.

Gatilhos:

- barter obrigatório
- comercialização de café exportador
- CT-e/MDF-e
- logística integrada
- documentos de exportação
- forte dependência do ERP para rastreabilidade final

Classificação:

- **não recomendado**

## 9. Regras práticas para o piloto ERP

1. O tenant deve declarar cedo se opera com ERP e qual ERP.
2. O provider deve ser resolvido por `TENANT` ou `ESTABELECIMENTO`.
3. Cadastros mestres administrativos devem ser carregados antes de go-live.
4. O AgroSaaS não deve ceder ao ERP a autoria da operação rural.
5. Toda entidade compartilhada precisa de política explícita de conflito.
6. Documento fiscal emitido no ERP deve voltar ao AgroSaaS como evidência.
7. Rastreabilidade de exportação não pode depender exclusivamente do ERP.

## 10. Próximas execuções sugeridas

1. `ERP-GOV-02` para definir guardrails obrigatórios de adapter ERP.
2. `ERP-SCOPE-03` para formalizar domínio `Estabelecimento` e resolução de provider por escopo.
3. `ERP-PILOT-04` para definir backlog P0 de piloto ampliado.
4. `SANKHYA-PILOT-04` para reclassificar o adapter Sankhya sob a nova matriz genérica.
5. `ERP-STOCK-01` para fechar a arquitetura de separação entre estoque operacional e estoque contábil.
6. `ERP-FIN-01` para fechar a arquitetura de convivência entre `CostAllocation` e títulos administrativos ERP.

## 11. Síntese final

Após esta execução:

- o AgroSaaS passa a ter uma matriz oficial de propriedade dos dados para qualquer ERP;
- Sankhya deixa de ser tratado como arquitetura e passa a ser tratado como adapter de referência;
- as decisões de piloto ERP ficam ancoradas em regras de domínio e não em limitações acidentais do primeiro provider;
- a próxima etapa correta é transformar esta arquitetura em guardrails de adapter e escopo, sem ainda alterar código nesta execução.
