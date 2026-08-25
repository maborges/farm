# AGROSAAS DATA MODEL

Este documento mapeia o domínio de dados do sistema AgroSaaS/FarmOS com base na análise estrutural do código-fonte, servindo de fundação para o desenvolvimento e evolução da plataforma.

## ENTIDADES CRÍTICAS

As entidades listadas abaixo:
- Participam estritamente do **Row Level Security (RLS)**.

## Namespace da Plataforma Balança

O PostgreSQL possui o namespace `balanca`, criado para a extração gradual da
Plataforma Balança. As tabelas legadas do módulo permanecem temporariamente no
schema público por compatibilidade com o AgroSaaS. Toda nova entidade própria
da Plataforma Balança deve declarar explicitamente `schema="balanca"`, possuir
`tenant_id` e política RLS própria; nenhuma tabela nova deve depender de uma
FK direta para modelos de Compras, Agrícola, Pecuária ou Pessoas.
- **Não podem** sofrer alteração estrutural sem migração controlada via Alembic.
- Afetam múltiplos módulos simultaneamente (Cross-domain).

1. `Tenant` / `UnidadeProdutiva`: Raiz do isolamento de dados.
2. `SessaoAtiva`: Gerencia o heartbeat e controle de acesso em tempo real.
3. `Pessoas` (Clientes, Fornecedores, Funcionários): Entidade base compartilhada entre CRM, Financeiro e RH.
4. `Produtos` / `Commodities`: Base para Comercialização, Estoque e Planejamento Agrícola.
5. `Propriedades` / `Áreas Rurais`: Central para o módulo Agrícola, Pecuária, Ambiental e Rastreabilidade.
6. `Imóveis Rurais`: Base jurídica, patrimonial, documental e fiscal do território.

### Entidades climáticas

- `RegistroClima`: leitura observada por `tenant_id`, `unidade_produtiva_id`, data e fonte.
- `PrevisaoClima`: previsão diária por tenant e unidade produtiva; a combinação
  `(tenant_id, unidade_produtiva_id, data_previsao)` é única para garantir idempotência.
- Ambas possuem FK para `Tenant` e `UnidadeProdutiva` e são abastecidas pelos
  eventos de ingestão do provider climático.

---

## NORMA TERRITORIAL E FUNDIÁRIA

O modelo territorial e fundiário oficial do AgroSaaS é regido pela norma [AGRI-DOMAIN-001](/opt/lampp/htdocs/farm/docs/architecture/standards/AGRI-DOMAIN-001-territorial-fundiario.md).

### Cardinalidade oficial

- `Propriedade` ↔ `Imóvel Rural`: `N:N`
- A entidade oficial de vínculo é `PropriedadeImovel`
- `PropriedadeImovel` representa o relacionamento entre os domínios e não deve armazenar dados operacionais nem fundiários

### Ownership dos domínios

- `Propriedades`: domínio operacional, territorial e produtivo
- `Imóveis Rurais`: domínio jurídico, patrimonial, documental e fiscal
- `Compartilhado`: ESG, certificações, carbono, recuperação ambiental e licenciamento ambiental

### Entidade oficial de vínculo

- `PropriedadeImovel`: entidade de primeira classe responsável exclusivamente pelo vínculo entre `Propriedade` e `Imóvel Rural`
- Cardinalidade oficial: `Propriedade` ↔ `Imóvel Rural` = `N:N`
- `PropriedadeImovel` não é fonte de verdade para operação territorial nem para lastro fundiário
- A entidade existe para registrar sobreposição, principalidade, vigência, origem documental e rastreabilidade histórica

#### Campos mínimos esperados

- `tenant_id` como isolamento multi-tenant obrigatório
- `propriedade_id` como FK para `Propriedades`
- `imovel_rural_id` como FK para `Imóveis Rurais`
- `tipo_vinculo` como enum oficial
- `ativo` como indicador de vigência atual
- `data_inicio` como início obrigatório da vigência
- `data_fim` como fim opcional da vigência
- `origem_documental` como prova documental resumida do vínculo
- `area_vinculada` como escopo de área vinculada
- `percentual_vinculado` como representatividade percentual
- `observacoes` como contexto de governança
- `created_at` e `updated_at` como auditoria temporal

#### Campos futuros

- `vinculo_principal`
- `status_documental`
- `motivo_encerramento`
- `versao_normativa`
- `hash_documental`
- `origem_geoespacial`
- `score_confianca`

#### Regras estruturais esperadas

- Um vínculo principal ativo por propriedade e por janela de vigência
- Histórico preservado quando o vínculo for encerrado
- Sobreposição permitida somente quando o tipo de vínculo permitir
- `area_vinculada` e `percentual_vinculado` devem ser coerentes quando ambos existirem
- Dados espelhados não podem ser editados fora da origem oficial

#### Constraints e índices esperados

- PK em `id`
- FK em `tenant_id`
- FK em `propriedade_id`
- FK em `imovel_rural_id`
- Unique constraint para evitar vínculo principal ativo duplicado por propriedade e vigência
- Check constraints para coerência de vigência
- Index em `tenant_id`
- Index composto em `tenant_id + propriedade_id`
- Index composto em `tenant_id + imovel_rural_id`
- Index em `tipo_vinculo`
- Index em `ativo`
- Index em `data_inicio` e `data_fim` para buscas históricas

#### RLS esperado

- `tenant_id` deve existir diretamente na tabela
- A tabela futura deve ter `ENABLE ROW LEVEL SECURITY`
- A tabela futura deve ter `CREATE POLICY` para `SELECT`, `INSERT`, `UPDATE` e `DELETE`
- A política deve usar `app.current_tenant_id`
- `FORCE ROW LEVEL SECURITY` é esperado para endurecimento do isolamento

#### Fonte da verdade

- `Propriedades`: fonte da verdade do território operacional
- `Imóveis Rurais`: fonte da verdade fundiária, documental e fiscal
- `PropriedadeImovel`: fonte da verdade do vínculo entre os dois domínios

---

## DETALHAMENTO DE ENTIDADES (EXEMPLOS CORE)

*Nota: Os campos exatos que não puderam ser escaneados linha a linha estão marcados como NÃO IDENTIFICADO.*

### Entidade: SessaoAtiva
- **Nome**: SessaoAtiva
- **Módulo**: Core / Autenticação
- **Responsabilidade**: Controle do ciclo de vida das sessões logadas e heartbeat.
- **Ownership**: Infraestrutura Global
- **Possui tenant_id?**: Não (É vinculada ao Token Hash global, ou sim se atrelado a acesso restrito).
- **Status**: Implementado (Referência: `SessionHeartbeatMiddleware` no `main.py`).

**Campos principais:**
- `token_hash` (String, UK)
- `status` (String)
- `ultimo_heartbeat` (DateTime)
- `expira_em` (DateTime)

**Relacionamentos:**
- NÃO IDENTIFICADO (presumivelmente FK para `User` e/ou `Tenant`).

**Regras de negócio:**
- Renova a sessão por +30 minutos a cada requisição válida se o intervalo for superior a 5 minutos do último update (throttling).

**Endpoints relacionados:**
- Interceptação global em `/api/v1/*`

**Telas relacionadas:**
- Frontend Web: Middleware de autenticação e timeout.

---

### Entidade: Propriedade (Área Rural)
- **Nome**: Propriedade
- **Módulo**: Core Cadastros / Agrícola
- **Responsabilidade**: Representa o espaço físico gerido pelo inquilino.
- **Ownership**: Core
- **Possui tenant_id?**: Sim.
- **Status**: Implementado (Referência: Routers `core.cadastros.propriedades`).

**Campos principais:**
- `id` (UUID)
- `tenant_id` (UUID, RLS policy key)
- `nome` (String)
- Demais campos: NÃO IDENTIFICADO.

**Relacionamentos:**
- Pertence a um `Tenant`.
- Possui vários `Talhões` / `Áreas`.

**Regras de negócio:**
- O acesso a qualquer propriedade deve validar o `tenant_id` injetado na sessão.

**Endpoints relacionados:**
- GET/POST `/api/v1/propriedades_econ`
- GET/POST `/api/v1/areas_rurais`

**Telas relacionadas:**
- NÃO IDENTIFICADO especificamente, mas presumido no Setup e Configurações do Backoffice Web.

---

### Entidade: Produto / Commodity
- **Nome**: Produto
- **Módulo**: Core Cadastros / Financeiro / Estoque
- **Responsabilidade**: Catálogo oficial de itens gerenciados, comprados ou vendidos.
- **Ownership**: Módulo Estoque / Suprimentos
- **Possui tenant_id?**: Sim.
- **Status**: Implementado.

**Campos principais:**
- `id` (UUID)
- `tenant_id` (UUID)
- `tipo` (Insumo, Colheita, etc)
- Demais: NÃO IDENTIFICADO.

**Relacionamentos:**
- Classificações e Cotações.
- EstoqueMovimentos e Notas Fiscais.

**Regras de negócio:**
- Restrito ao RLS. Relaciona-se com Unidade de Medida (UOM).

**Endpoints relacionados:**
- `/api/v1/produtos`, `/api/v1/commodities`

**Telas relacionadas:**
- Cadastro de Produtos (Web).

---

## MAPA DE RELACIONAMENTOS (VISÃO MACRO DO DOMÍNIO)

Abaixo o organograma da arquitetura orientada a tenant no AgroSaaS:

```text
Global (Admin / Infrastructure)
├── Backoffice_Admins
├── Tenants
├── SessoesAtivas
└── Planos (Billing / Assinaturas)

Tenant (Contexto Isolado por RLS)
├── Acessos
│   ├── Usuários
│   ├── Perfis (RBAC)
│   └── Permissões
│
├── Core / Cadastros Base
│   ├── Pessoas (Clientes, Fornecedores, Funcionários)
│   ├── Equipamentos (Máquinas, Implementos)
│   ├── Produtos & Commodities
│   └── Propriedades (Áreas Rurais)
│
├── Agrícola
│   ├── Safras
│   │   ├── Cultivos
│   │   ├── Talhões
│   │   ├── Planejamentos
│   │   └── Operações
│   ├── NDVI / Climático (Previsões e Mapas)
│   ├── Romaneios
│   └── Amostragem Solo (Prescrições, Mapas de Fertilidade)
│
├── Operacional & Logística
│   ├── Estoque (Implantação, Movimentações)
│   ├── Frota (Abastecimento, Oficina, Checklists, Apontamentos)
│   └── Compras
│
├── Pecuária
│   ├── Lotes
│   └── Manejos
│
└── Financeiro & Comercial
    ├── Receitas
    ├── Despesas
    ├── Plano de Contas
    ├── Notas Fiscais
    ├── Conciliação Bancária
    ├── Contratos (Hedge)
    └── Comercialização
```

---
*Documento gerado como complemento de regras de AI. Para expansão, consulte os schemas SQLAlchemy da pasta `models/` em cada serviço.*
