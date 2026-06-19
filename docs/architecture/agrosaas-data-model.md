# AGROSAAS DATA MODEL

Este documento mapeia o domínio de dados do sistema AgroSaaS/FarmOS com base na análise estrutural do código-fonte, servindo de fundação para o desenvolvimento e evolução da plataforma.

## ENTIDADES CRÍTICAS

As entidades listadas abaixo:
- Participam estritamente do **Row Level Security (RLS)**.
- **Não podem** sofrer alteração estrutural sem migração controlada via Alembic.
- Afetam múltiplos módulos simultaneamente (Cross-domain).

1. `Tenant` / `UnidadeProdutiva`: Raiz do isolamento de dados.
2. `SessaoAtiva`: Gerencia o heartbeat e controle de acesso em tempo real.
3. `Pessoas` (Clientes, Fornecedores, Funcionários): Entidade base compartilhada entre CRM, Financeiro e RH.
4. `Produtos` / `Commodities`: Base para Comercialização, Estoque e Planejamento Agrícola.
5. `Propriedades` / `Áreas Rurais`: Central para o módulo Agrícola, Pecuária, Ambiental e Rastreabilidade.

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
- **Responsabilidade**: Catálogo canônico de itens gerenciados, comprados ou vendidos.
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
