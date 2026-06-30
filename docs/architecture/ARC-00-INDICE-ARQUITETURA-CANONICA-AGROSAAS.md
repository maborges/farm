# ARC-00 — Índice da Arquitetura Canônica do AgroSaaS

## Objetivo

Este documento consolida oficialmente a arquitetura de referência do AgroSaaS.

A partir desta data, qualquer novo desenvolvimento deve seguir os documentos arquiteturais oficiais antes da implementação.

Os documentos de `docs/architecture/` deixam de ser apenas auditorias e passam a representar a **Arquitetura Oficial (Reference Architecture)** da plataforma.

## Princípios gerais

Todo novo desenvolvimento deve priorizar:

- reutilização de componentes existentes;
- evolução incremental;
- compatibilidade controlada com legado;
- desacoplamento entre domínios;
- arquitetura orientada a eventos;
- multi-tenant;
- rastreabilidade;
- idempotência;
- isolamento entre módulos.

É proibido criar novos modelos, cadastros, fluxos ou serviços paralelos quando já existir uma entidade canônica documentada.

## Domínios arquiteturais oficiais

### PERSON-ARCH-01

Documento oficial: [PERSON-ARCH-01-DOMINIO-PESSOAS.md](/opt/lampp/htdocs/farm/docs/architecture/PERSON-ARCH-01-DOMINIO-PESSOAS.md)

Define:

- Pessoa
- Usuário
- Colaborador RH
- Fornecedor
- Cliente
- Lead
- Papéis
- Relacionamentos

Fonte canônica:

```text
Pessoa
```

Compatibilidade:

- `Usuario` sem `Pessoa`
- `ColaboradorRH` sem `Pessoa`
- fornecedor textual
- cliente textual
- `LeadCRM`

### ECONOMIC-ARCH-01

Documento oficial: [ECONOMIC-ARCH-01-DOMINIO-ECONOMICO.md](/opt/lampp/htdocs/farm/docs/architecture/ECONOMIC-ARCH-01-DOMINIO-ECONOMICO.md)

Define:

- Receita
- Despesa
- CostAllocation
- OperationalCostAllocationService
- DRE
- Rentabilidade
- Fluxo de Caixa

Arquitetura oficial:

```text
Evento Operacional
  ↓
OperationalCostAllocationService
  ↓
CostAllocation
  ↓
DRE
  ↓
Rentabilidade
```

Fluxo financeiro:

```text
Receita
  ↓
Financeiro
  ↓
Fluxo de Caixa
  ↓
DRE
```

Compatibilidade:

- DRE legada
- `custo_total`
- lançamentos financeiros antigos

### TERRITORY-ARCH-01

Documento oficial: [TERRITORY-ARCH-01-DOMINIO-TERRITORIAL.md](/opt/lampp/htdocs/farm/docs/architecture/TERRITORY-ARCH-01-DOMINIO-TERRITORIAL.md)

Define:

```text
Tenant
  ↓
UnidadeProdutiva
  ↓
AreaRural
```

Arquitetura fundiária:

```text
Propriedade
  ↕
PropriedadeImovel
  ↕
ImovelRural
```

Arquitetura agrícola:

```text
AreaRural
  ↓
Talhão
  ↓
Safra
  ↓
Cultivo
  ↓
ProductionUnit
```

Arquitetura pecuária:

```text
AreaRural
  ↓
Piquete
  ↓
LoteAnimal
  ↓
Animal
```

Compatibilidade:

- `pec_piquetes`
- linguagem `fazenda`
- campos fundiários em `UnidadeProdutiva`

### PRODUCT-ARCH-01

Documento oficial: [PRODUCT-ARCH-01-DOMINIO-PRODUTOS-CULTURAS-COMMODITIES.md](/opt/lampp/htdocs/farm/docs/architecture/PRODUCT-ARCH-01-DOMINIO-PRODUTOS-CULTURAS-COMMODITIES.md)

Arquitetura oficial:

```text
Produto
  ├── ProdutoAgricola
  ├── ProdutoEstoque
  └── ProdutoEPI
```

Agronomia:

```text
ProdutoCultura
  ↓
Cultivo
  ↓
Safra
```

Mercado:

```text
Commodity
  ↓
Comercialização
  ↓
Hedge
```

Produção:

```text
ProdutoColhido
  ↓
Comercialização
```

Compatibilidade:

- cultura legada
- commodity textual
- produto colhido legado

### EVENTS-ARCH-01

Documento oficial: [EVENTS-ARCH-01-EVENT-DRIVEN-OUTBOX-ALERTS-NOTIFICATIONS.md](/opt/lampp/htdocs/farm/docs/architecture/EVENTS-ARCH-01-EVENT-DRIVEN-OUTBOX-ALERTS-NOTIFICATIONS.md)

Arquitetura oficial:

```text
Domain Service
  ↓
Outbox
  ↓
Relay
  ↓
EventPublisher
  ↓
Subscribers
```

Alertas:

```text
Subscriber
  ↓
Alert Engine
```

Notificações:

```text
Notification Dispatcher
  ↓
Policy
  ↓
Adapter
```

Compatibilidade:

- fallback in-memory
- `NotificationEventSubscriber` opcional
- `LOG`
- `NOOP`

## Guardrails oficiais

Cada domínio com governança implementada possui documento complementar de proteção arquitetural.

Documentos atuais:

- [ECONOMIC-GOV-01-GUARDRAILS-DOMINIO-ECONOMICO.md](/opt/lampp/htdocs/farm/docs/implementation/reports/ECONOMIC-GOV-01-GUARDRAILS-DOMINIO-ECONOMICO.md)
- [TERRITORY-GOV-01-GUARDRAILS-DOMINIO-TERRITORIAL.md](/opt/lampp/htdocs/farm/docs/implementation/reports/TERRITORY-GOV-01-GUARDRAILS-DOMINIO-TERRITORIAL.md)
- [PRODUCT-GOV-01-GUARDRAILS-PRODUTOS-CULTURAS-COMMODITIES.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PRODUCT-GOV-01-GUARDRAILS-PRODUTOS-CULTURAS-COMMODITIES.md)

Observação:

- `PERSON-ARCH-01` e `EVENTS-ARCH-01` ainda não possuem documento `GOV-01` correspondente entre os arquivos oficiais atuais.

Todo novo fluxo deve respeitar os guardrails existentes.

## Compatibilidade com legado

A estratégia oficial da versão 1.0 é:

**Compatibilidade sem expansão.**

Isso significa:

- o legado continua funcionando;
- novos desenvolvimentos não devem ampliar estruturas legadas;
- toda nova funcionalidade deve utilizar a entidade canônica correspondente;
- remoções estruturais ficam para a versão 1.1 ou posterior.

## Regras obrigatórias para novos desenvolvimentos

Antes de criar qualquer entidade, verificar:

- já existe um documento `ARCH` correspondente;
- já existe entidade canônica;
- existe resolver oficial;
- existe guardrail;
- existe compatibilidade prevista.

Caso exista, reutilizar.

É proibido criar:

- novos cadastros paralelos;
- novos modelos equivalentes;
- novos motores econômicos;
- novos fan-outs de eventos;
- novas árvores territoriais;
- novos catálogos de cultura;
- novos modelos de pessoa;
- novas entidades de produto sem justificativa arquitetural.

## Processo oficial de evolução

Toda alteração estrutural deverá seguir obrigatoriamente:

```text
1. Auditoria
  ↓
2. Documento ARCH
  ↓
3. Aprovação Arquitetural
  ↓
4. Guardrails
  ↓
5. Implementação
  ↓
6. Testes
  ↓
7. Documentação
  ↓
8. Liberação
```

Não será permitido implementar mudanças estruturais diretamente.

## Arquiteturas pendentes

Antes da versão 1.0 recomenda-se concluir:

- `WIZARD-ARCH-01` — Assistente de Implantação
- `SECURITY-ARCH-01` — Segurança, RBAC, RLS e Auditoria
- `API-ARCH-01` — Convenções de APIs, contratos e versionamento
- `PWA-ARCH-01` — Arquitetura Offline, Sync e Resolução de Conflitos
- `REPORT-ARCH-01` — Relatórios, BI e Analytics
- `AI-ARCH-01` — IA, Recomendações e Motores Inteligentes

Esses domínios complementam a arquitetura global da plataforma.

## Critérios para liberação da versão 1.0

A arquitetura será considerada congelada quando:

- todos os domínios críticos possuírem documento `ARCH` aprovado;
- todos os domínios críticos possuírem guardrails aplicáveis;
- novos desenvolvimentos seguirem obrigatoriamente os documentos arquiteturais;
- as compatibilidades legadas estiverem claramente documentadas;
- não existirem novos modelos paralelos sendo introduzidos.

## Governança arquitetural

A partir deste documento:

- a pasta `docs/architecture/` torna-se a referência oficial da arquitetura do AgroSaaS;
- qualquer proposta de mudança estrutural deve começar por uma auditoria arquitetural;
- implementações que contrariem os documentos `ARCH` deverão ser revisadas antes de integração.

## Resposta final

Após a conclusão dos documentos `PERSON-ARCH-01`, `ECONOMIC-ARCH-01`, `TERRITORY-ARCH-01`, `PRODUCT-ARCH-01` e `EVENTS-ARCH-01`, o AgroSaaS passa a possuir uma Arquitetura Canônica formalizada para seus principais domínios de negócio.

Esses documentos estabelecem as entidades canônicas, as responsabilidades de cada domínio, as estratégias de compatibilidade com o legado, os guardrails de governança e o processo oficial para evolução da plataforma, reduzindo significativamente o risco de regressões arquiteturais antes da versão 1.0.
