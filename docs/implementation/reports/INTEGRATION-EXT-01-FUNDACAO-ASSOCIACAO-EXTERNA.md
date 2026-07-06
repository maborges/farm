# INTEGRATION-EXT-01 - Fundacao da Associacao Externa

Data: 2026-07-06

## Escopo implementado

Implementada a fundacao transversal da associacao oficial entre registros do AgroSaaS e registros de sistemas externos no dominio `integracoes`.

Itens entregues nesta fase:

- modelos `ExternalRecordAssociation` e `ExternalRecordAssociationHistory`;
- migration dedicada com tabelas, indices, constraints compostas, comentarios e RLS;
- schemas internos de criacao, atualizacao e reconciliacao;
- service transversal `ExternalRecordAssociationService`;
- testes unitarios da fundacao e da compatibilidade com o dominio atual.

## Reuso confirmado

- `MarketplaceIntegracao` para catalogo de providers;
- `TenantIntegracao` para configuracao real da integracao;
- `IntegrationFeature` para vinculo por dominio funcional;
- `IntegrationJob` para rastrear ultima execucao relacionada;
- padrao de migration com RLS e `tenant_id` do dominio `integracoes`.

## Nao alterado nesta fase

- adapters de providers;
- sync Sankhya;
- staging `sankhya_*`;
- endpoints publicos;
- autenticacao Gateway-first;
- jobs, health e logs existentes.

## Decisao desta entrega

O novo dominio esta pronto para ser consumido futuramente por Sankhya e por outros providers, sem acoplamento a ERP especifico.
