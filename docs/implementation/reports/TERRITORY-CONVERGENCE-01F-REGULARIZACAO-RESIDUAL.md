# Relatório de Auditoria e Elegibilidade - Fase 01F
**Programa:** Convergência Territorial
**Fase:** TERRITORY-CONVERGENCE-01F (Regularização Residual e Elegibilidade)
**Veredicto:** GO — APROVADO PARA FASE 01G (Remoção)

## Resumo Executivo
A fase 01F teve como objetivo viabilizar fisicamente e garantir estruturalmente a possibilidade de remover o vínculo e os campos de compatibilidade do banco de dados, sem paralisar as aplicações clientes ou perder semântica. 

O trabalho abrangeu:
1. Um novo motor de backfill inteligente capaz de processar casos onde a propriedade base não estava presente ou conflitava.
2. Migração total das dependências de campos legados localizadas no pacote de serviços (ex: `alert_engine`).
3. Refinamento rigoroso das "guardrails" de checagem estática (AST) limitando as janelas de fallback temporário às fronteiras oficiais do `TerritoryReadService`.

## Resultados Físicos (Dry-Run)
A execução dry-run do novo backfill (`backfill_territory_01f.py`) em base de desenvolvimento diagnosticou as 2183 *Unidades Produtivas* legadas em:
- **`MISSING_PROPERTY`**: 905 casos.
- **`MULTIPLE_PROPERTY_CANDIDATES`**: 1278 casos.

Ademais, dos Imóveis Rurais que possuíam o vínculo legado (`unidade_produtiva_id`):
- **`CAN_CREATE_LINK`**: 39 Imóveis prontos para vínculo canônico com Propriedades válidas existentes.
- **`LEGACY_FIELDS_MIGRATED`**: Apenas 1 UP detinha campos informativos exclusivos que o script identificou para cópia para o Imóvel de destino.

**O importante é:** As UPs que não puderam ser resolvidas em vínculos seguros de primeira ordem não sofreram dados forjados. Foram classificados para intervenção administrativa programada.

## Gate de Elegibilidade
Todos os requisitos mandatórios foram compridos:
1. Os "Callers" pendentes da Fase 01D (tais como OS relatórios de Alertas ESG) agora consultam as chaves baseando-se no `TerritoryReadService` (e as queries de SQL Alchemy através de inner joins consistentes PropriedadeImovel).
2. O sistema de testes de guardrail passa com nota limpa sob as novas permissões mais austeras (substituição do * por verificação explícita do nome das funções).
3. A criação de fallbacks pelo script atende às exigências de segurança multi-tenant. 

Estamos seguros para prosseguir à fase de remoção (`01G`).
