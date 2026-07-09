# ERP-CONSOLIDATION-03 - Roadmap de Implementacao ERP

Data: 2026-07-09
Origem: consolidacao final da arquitetura ERP

## 1. Premissa

O epic ERP esta arquiteturalmente encerrado.

O roadmap abaixo parte do principio de que:

- nao e necessaria nova arquitetura para iniciar;
- o runtime atual deve ser reutilizado;
- toda implementacao deve obedecer `ERP-DOMAIN-01`, `ERP-GOV-02`, `ERP-CAPABILITY-01` e `ERP-PROVIDER-CONTRACT-02`.

## 2. P0 - Piloto restrito

Objetivo:

tornar o ERP utilizavel no piloto controlado com governanca minima, observabilidade e capabilities P0.

Itens minimos:

- consolidar provider atual no console ERP do tenant;
- enriquecer `provider_definition`, `feature_schema`, `sync_schema` e `health_schema` do provider atual;
- materializar capability minima do piloto restrito no provider atual:
  - pessoas
  - clientes
  - fornecedores
  - produtos
  - NFe
  - financeiro basico
- garantir policy minima por capability em `IntegrationSyncPolicy`;
- garantir health, jobs, logs e reconciliacao manual utilizaveis no console e no backoffice;
- evoluir `CHECK_INTEGRACAO_ERP` para consumir provider, health, capabilities P0 e policies minimas;
- remover dependencias funcionais remanescentes do link legado do wizard;
- fechar classificacao operacional de pronto para piloto restrito.

Saida esperada:

- tenant consegue configurar o ERP;
- runtime mostra health, features e policies minimas;
- wizard consegue dizer se o tenant esta apto ou nao ao piloto restrito.

## 3. P1 - Piloto ampliado

Objetivo:

ampliar o uso administrativo e financeiro do ERP alem do piloto minimo.

Escopo:

- depositos
- contas correntes
- centros de custo
- centros de resultado
- naturezas financeiras
- pagamentos
- recebimentos
- baixas

Itens:

- materializar capabilities P1 no provider atual;
- completar de-para e reconciliacao para entidades administrativas compartilhadas;
- consolidar retorno de evidencias financeiras ao AgroSaaS;
- permitir classificacao automatica de piloto ampliado baseada em capability matrix;
- ampliar observabilidade por capability administrativa.

Saida esperada:

- provider atual consegue suportar financeiro administrativo ampliado com governanca e rastreabilidade.

## 4. P2 - Estoque administrativo e pedidos

Objetivo:

expandir o provider para fluxos administrativos de estoque e pedidos.

Escopo:

- estoque contabil/administrativo
- pedidos
- movimentacoes administrativas
- transferencias administrativas

Itens:

- ativar capabilities hoje futuras ou parciais do provider atual;
- distinguir estoque operacional AgroSaaS de estoque administrativo ERP na implementacao;
- fechar policies e mapeamentos de depositos, produtos e estabelecimentos;
- consolidar reconciliacao de movimentos administrativos e pedidos.

Saida esperada:

- provider atual suporta camada administrativa de estoque e pedidos sem invadir ownership operacional do AgroSaaS.

## 5. P3 - Exportacao

Objetivo:

habilitar escopo exportador e cadeia fiscal/logistica ampliada.

Escopo:

- CT-e
- MDF-e
- documentos de exportacao
- logistica integrada
- evidencias fiscais completas

Itens:

- classificar e implementar capabilities exportadoras do provider atual;
- fechar retorno de evidencias documentais ao AgroSaaS;
- tratar restricoes provider-specific e dependencias logistico-fiscais;
- definir bloqueios de piloto exportador por capability ausente, parcial ou desconhecida.

Saida esperada:

- provider atual pode ser classificado com clareza como apto ou nao ao piloto exportador.

## 6. P4 - Novos providers

Objetivo:

abrir a arquitetura para novos ERPs sem redesign estrutural.

Escopo alvo:

- TOTVS
- SAP
- Omie
- Senior
- ERPs regionais

Itens:

- aplicar `ERP-PROVIDER-CONTRACT-02` aos novos providers;
- declarar capability matrix, sync schema e health schema canônicos;
- reutilizar runtime atual sem nova tabela;
- validar conformidade por checklist arquitetural;
- classificar suporte por piloto restrito, ampliado ou exportador.

Saida esperada:

- novos providers entram no dominio ERP como adapters aderentes, nao como excecoes arquiteturais.

## 7. Dependencias transversais do roadmap

Itens transversais a todas as fases:

- naming tecnico menos Sankhya-first no frontend, quando isso reduzir ambiguidade;
- consumo funcional de capability matrix no console ERP e no backoffice;
- consumo funcional do lifecycle, health e capabilities pelo wizard;
- cobertura de testes por capability critica;
- aderencia estrita aos guardrails de escopo, ownership, policy, health e mapeamento.

## 8. Ordem recomendada

Ordem de implementacao:

1. P0
2. P1
3. P2
4. P3
5. P4

Regra:

- nao iniciar P1, P2 ou P3 sem fechar o minimo operacional de P0;
- P4 deve reutilizar o que foi estabilizado em P0 a P3.
