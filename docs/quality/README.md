# Épico QUALITY — Qualidade e Classificação Agro

## Objetivo

Criar um módulo comercial independente para registrar medições e laudos, determinar a qualidade de lotes agrícolas por protocolos versionados, aplicar consequências físicas/comerciais e publicar evidências auditáveis na rastreabilidade.

O módulo deve ser multicultura e não pode substituir nem duplicar as fontes oficiais de `Produto`, `Commodity`, `ProdutoColhido`, `RomaneioColheita`, `LoteBeneficiamento` ou `LoteEstoque`.

## Status

`PLANEJAMENTO / BRAINSTORM` — nenhuma migration, API ou alteração de runtime está autorizada por estes documentos.

## Documentos

| Documento | Finalidade |
|---|---|
| [01-visao-produto.md](./01-visao-produto.md) | Problema, proposta de valor, personas e escopo |
| [02-dependencias-e-pacotes.md](./02-dependencias-e-pacotes.md) | Pré-requisitos técnicos, funcionais e comercialização |
| [03-arquitetura-dominio.md](./03-arquitetura-dominio.md) | Limites, ownership, entidades e eventos |
| [04-motor-regras.md](./04-motor-regras.md) | Protocolos, critérios, cálculo e decisão |
| [05-integracoes-e-fluxos.md](./05-integracoes-e-fluxos.md) | Integrações com módulos existentes e fluxos ponta a ponta |
| [06-api-e-ux.md](./06-api-e-ux.md) | Superfície HTTP, telas e PWA |
| [07-seguranca-auditoria.md](./07-seguranca-auditoria.md) | Tenant, RLS, permissões e trilha de auditoria |
| [08-testes-e-aceite.md](./08-testes-e-aceite.md) | Estratégia de testes e Definition of Done |
| [09-roadmap-implementacao.md](./09-roadmap-implementacao.md) | Fases, entregas e critérios de liberação |
| [10-decisoes-em-aberto.md](./10-decisoes-em-aberto.md) | Perguntas que precisam de decisão de produto |

## Decisões-base

1. A primeira versão é explicável e baseada em regras; IA é evolução posterior.
2. O protocolo é específico por commodity, região, cliente e versão.
3. O resultado de qualidade é append-only após aprovação; correções geram nova versão.
4. Desconto físico não altera o ledger físico; gera valor comercial derivado e auditado.
5. O módulo é vendável separadamente, mas depende do Core e de cadastros oficiais.
6. O primeiro piloto recomendado é café ou uma commodity de grãos com protocolo conhecido.

## Fontes existentes a consolidar

- `docs/domains/quality-multicultura-domain.md`
- `docs/audits/BUSINESS-DOMAIN-03-quality.md`
- `docs/audits/BUSINESS-DOMAIN-05-commercial-quality.md`
- `docs/architecture/PRODUCT-ARCH-01-DOMINIO-PRODUTOS-CULTURAS-COMMODITIES.md`
- `services/api/operacional/models/qualidade.py`
- `services/api/agricola/colheita/models.py`
- `services/api/agricola/beneficiamento/models.py`
- `services/api/agricola/rastreabilidade/`
