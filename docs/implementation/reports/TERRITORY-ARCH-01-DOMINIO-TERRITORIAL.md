# TERRITORY-ARCH-01 — Relatório curto

## Resultado

A auditoria encontrou uma arquitetura territorial canônica já desenhada, mas ainda com sobreposições relevantes.

Classificação: **Modelo C**.

## Conclusões centrais

- `UnidadeProdutiva` foi confirmada como unidade operacional mínima.
- `Propriedade` foi confirmada como camada patrimonial/organizacional.
- `ImovelRural` foi confirmado como camada legal/fundiária/documental.
- `PropriedadeImovel` foi confirmada como ponte N:N canônica.
- `AreaRural` foi confirmada como árvore espacial canônica.
- `Talhão` foi confirmado como tipo de `AreaRural`.
- `Piquete` foi confirmado como tipo de `AreaRural`, mas ainda coexistindo com legado `pec_piquetes`.
- `ProductionUnit` foi confirmada como unidade agrícola operacional/econômica da safra.

## Principais sobreposições

- `UnidadeProdutiva` ainda carrega campos fundiários legados.
- `Piquete` existe ao mesmo tempo como `AreaRural.tipo = PIQUETE` e como `pec_piquetes`.
- `AreaOperacional` é tipo de `AreaRural`, mas aparece em alguns pontos como conceito de tela/alias.
- `Infraestrutura` aparece tanto como parte da árvore `AreaRural` quanto como subrecurso próprio.

## Arquitetura oficial proposta

- Territorial/operacional:
  - `Tenant → UnidadeProdutiva → AreaRural`
- Fundiária/patrimonial:
  - `Propriedade ↔ PropriedadeImovel ↔ ImovelRural`
  - `Propriedade ↔ ExploracaoRural ↔ UnidadeProdutiva`
- Agrícola:
  - `Safra → Cultivo → CultivoArea → ProductionUnit`
- Pecuária:
  - `UnidadeProdutiva → AreaRural.PIQUETE → LoteAnimal`

## Separação v1.0 / v1.1

### v1.0

- Fixar `AreaRural` como única árvore nova de áreas.
- Fixar `PropriedadeImovel` como vínculo obrigatório entre `Propriedade` e `ImovelRural`.
- Fixar `ProductionUnit` como unidade agrícola oficial.
- Fixar `AreaRural.PIQUETE` como referência pecuária oficial para novos fluxos.

### v1.1

- Resolver `pec_piquetes`.
- Remover dependência de campos fundiários legados em `UnidadeProdutiva`.
- Limpar aliases e nomenclatura histórica `fazenda`.

## Validação

- `git diff --check`
  - Resultado: sem erros.

## Confirmações

- Nenhum código operacional foi alterado.
- Nenhuma migration foi criada.
- Apenas documentação foi criada nesta execução.
