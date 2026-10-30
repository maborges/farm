# PILOT-02 — Auditoria de Prontidão para Cafeicultura Exportadora Integrada ao Sankhya

Data da auditoria: 2026-07-01

## 1. Resumo executivo

O AgroSaaS já possui suporte real para uma operação cafeeira acima do nível genérico de grãos. Há evidência concreta de:

- cultura `Café` no catálogo oficial de culturas;
- escala fenológica específica para café;
- romaneios com parâmetros de umidade/impureza específicos para café;
- módulo dedicado de beneficiamento pós-colheita de café;
- rastreabilidade por lote, lote comercial, certificações e passaporte;
- comercialização e hedge baseados em `Commodity`;
- integração real com Sankhya para cadastros, NFe e financeiro;
- Wizard operacional capaz de implantar a base da fazenda.

O ponto crítico é outro: o produto ainda não está pronto para um piloto amplo de **exportador de café com operação ponta a ponta e integração ERP como trilha crítica**. O núcleo agrícola e econômico existe, mas ainda faltam camadas operacionais e de governança específicas de exportação, além de cobertura mais profunda de cafeicultura perene e pós-colheita especializada no PWA.

## 2. Veredicto geral

Veredicto: **pronto apenas para piloto controlado com escopo reduzido**.

Interpretação prática:

- **Sim** para um piloto de fazenda cafeeira focado em implantação, talhões, operações agrícolas, colheita, romaneios, beneficiamento, rastreabilidade, comercialização básica e custos por safra/talhão/PU.
- **Não** para um piloto já posicionado como solução completa de exportação de café integrada ao Sankhya em regime mission-critical.

## 3. Evidências por arquivo

- Cultura oficial e parâmetros agronômicos: `ProdutoCultura` em [services/api/core/cadastros/produtos/models.py](/opt/lampp/htdocs/farm/services/api/core/cadastros/produtos/models.py:388).
- Seed explícita de `Café`: [services/api/scripts/initial_load/seed_culturas.py](/opt/lampp/htdocs/farm/services/api/scripts/initial_load/seed_culturas.py:357).
- Fenologia específica de café, incluindo floração, cereja e passa: [services/api/agricola/fenologia/seed_escalas.py](/opt/lampp/htdocs/farm/services/api/agricola/fenologia/seed_escalas.py:34).
- Cultivo com `cultivar_id`, `espacamento_cm` e vínculo econômico/operacional: [services/api/agricola/cultivos/models.py](/opt/lampp/htdocs/farm/services/api/agricola/cultivos/models.py:15).
- Safra ainda com `cultura` legada, mas orientada a `Cultivo`: [services/api/agricola/safras/models.py](/opt/lampp/htdocs/farm/services/api/agricola/safras/models.py:38).
- Romaneio com fórmula MAPA e fallback específico para café: [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:18).
- Geração automática de `ProdutoColhido` a partir do romaneio: [services/api/agricola/romaneios/service.py](/opt/lampp/htdocs/farm/services/api/agricola/romaneios/service.py:156).
- Lote de beneficiamento dedicado a café, com secagem, peneira, bebida, SCAA e perdas: [services/api/agricola/beneficiamento/models.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/models.py:9).
- Serviço de beneficiamento com blend de romaneios, bloqueio por qualidade, venda e integração com estoque: [services/api/agricola/beneficiamento/service.py](/opt/lampp/htdocs/farm/services/api/agricola/beneficiamento/service.py:35).
- Rastreabilidade, certificações e passaporte de lote: [services/api/agricola/rastreabilidade/router.py](/opt/lampp/htdocs/farm/services/api/agricola/rastreabilidade/router.py:18).
- DRE agrícola consolidando receita por comercialização e suprimindo dupla contagem de romaneio: [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:341).
- Comercialização com vínculo a `Commodity`, `ProdutoColhido`, entrega, NF-e e receita: [services/api/financeiro/comercializacao/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/models.py:20) e [services/api/financeiro/comercializacao/service.py](/opt/lampp/htdocs/farm/services/api/financeiro/comercializacao/service.py:103).
- Hedge com `ContratoFuturo`, `HedgeRegistro` e `HedgePositionSnapshot`: [services/api/financeiro/hedge/models.py](/opt/lampp/htdocs/farm/services/api/financeiro/hedge/models.py:27).
- Integração Sankhya registrada no app principal: [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py:410) e [services/api/main.py](/opt/lampp/htdocs/farm/services/api/main.py:508).
- Router Sankhya com configuração, teste, sync, logs e dados sincronizados: [services/api/integracoes/sankhya/routers/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/routers/__init__.py:27).
- Cliente WS e serviços de sync Sankhya: [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py:16).
- Frontend de backoffice para Sankhya: [apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/integracoes/erp/page.tsx:52).
- PWA com operação de colheita offline por talhão: [apps/campo/src/app/(campo)/campo/colheita/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/campo/colheita/page.tsx:24).
- PWA com caderno offline por unidade produtiva, safra e talhão: [apps/campo/src/app/(campo)/caderno/page.tsx](/opt/lampp/htdocs/farm/apps/campo/src/app/(campo)/caderno/page.tsx:646).
- Tela web de beneficiamento: [apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/beneficiamento/BeneficiamentoClient.tsx:21).
- Tela web de rastreabilidade e certificações: [apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/agricola/rastreabilidade/page.tsx:142).

## 4. Classificação por área

### 4.1 Cafeicultura

| Item | Classificação | Evidência | Leitura |
| --- | --- | --- | --- |
| Cultura café | EXISTE E ATENDE | `seed_culturas.py`, `ProdutoCultura` | Café existe como cultura oficial. |
| Variedades/cultivares | EXISTE PARCIALMENTE | `cultivos.models`, `safras.models` | Há `cultivar_id` e `cultivar_nome`, mas sem pacote específico de gestão varietal de café. |
| Talhões de café | EXISTE E ATENDE | `AreaRural` + `SafraTalhao` + PWA/web | Estrutura territorial e seleção por talhão existem. |
| Idade do cafezal | NÃO EXISTE | sem evidência no código | Não encontrei `idade_cafezal`, `ano_plantio` ou equivalente específico. |
| Espaçamento | EXISTE PARCIALMENTE | `ProdutoCultura.espacamento_cm`, `Cultivo.espacamento_cm` | Suporte existe, mas é genérico; não há regra cafeeira específica. |
| Tratos culturais | EXISTE PARCIALMENTE | operações/caderno/PWA | Cobertura operacional genérica, não trilhas próprias de café. |
| Podas | EXISTE PARCIALMENTE | fenologia/docs, sem fluxo dedicado | Há contexto documental/fenológico, mas não encontrei modelagem operacional específica de poda cafeeira. |
| Florada | EXISTE PARCIALMENTE | `seed_escalas.py` | Há escala fenológica de café, mas não fluxo robusto de monitoramento de florada. |
| Maturação | EXISTE PARCIALMENTE | `seed_escalas.py` | Há estágios `cereja`, `passa`, `seco no pé`; falta jornada operacional específica. |
| Pulverização | EXISTE E ATENDE | operações + PWA aplicação | Cobertura agrícola genérica reaproveitável para café. |
| Adubação | EXISTE E ATENDE | operações/caderno | Cobertura genérica reaproveitável. |
| Colheita | EXISTE E ATENDE | romaneios + PWA colheita | Fluxo operacional e registro existem. |
| Colheita seletiva | EXISTE PARCIALMENTE | fenologia menciona ponto ideal | Não encontrei atributo/fluxo explícito para separar seletiva x derriça. |
| Transporte interno | EXISTE PARCIALMENTE | caderno/operações genéricas | Sem módulo explícito de logística interna do café. |
| Secagem | EXISTE E ATENDE | `LoteBeneficiamento.local_secagem`, datas, perdas | Cobertura explícita. |
| Beneficiamento | EXISTE E ATENDE | módulo `agricola/beneficiamento` | Cobertura explícita e dedicada a café. |
| Classificação | EXISTE E ATENDE | peneira, bebida, SCAA, defeitos | Cobertura explícita no lote de beneficiamento. |
| Armazenamento | EXISTE PARCIALMENTE | `armazem_id`, `lote_estoque_id` | Há vínculo com estoque, mas sem fluxo exportador específico. |
| Lotes de café | EXISTE E ATENDE | `cafe_lotes_beneficiamento` | Entidade dedicada. |
| Rastreabilidade por lote | EXISTE E ATENDE | `rastreabilidade`, `lotes-comerciais`, snapshot público | Cadeia e passaporte existem. |
| Qualidade da bebida | EXISTE E ATENDE | `bebida`, `pontuacao_scaa` | Cobertura explícita. |
| Peneira | EXISTE E ATENDE | `peneira_principal` | Cobertura explícita. |
| Tipo | EXISTE PARCIALMENTE | método/status/bebida | Existe classificação parcial, mas não um modelo formal completo de “tipo” comercial brasileiro. |
| Defeitos | EXISTE E ATENDE | `defeitos_intrinsecos`, `defeitos_extrinsecos` | Cobertura explícita. |
| Umidade | EXISTE E ATENDE | romaneio + beneficiamento | Cobertura explícita. |
| Rendimento | EXISTE E ATENDE | `relatorio_rendimento`, KPIs | Cobertura explícita. |

### 4.2 Exportação

| Item | Classificação | Evidência | Leitura |
| --- | --- | --- | --- |
| Contratos de exportação | EXISTE PARCIALMENTE | `financeiro_comercializacoes` | Há contrato de comercialização, mas não encontrei campos/logística próprios de exportação. |
| Comercialização | EXISTE E ATENDE | `ComercializacaoCommodity` | Venda de commodity está implementada. |
| Rastreabilidade | EXISTE E ATENDE | `rastreabilidade` | Cadeia, passaporte e lote comercial existem. |
| Lotes | EXISTE E ATENDE | `CadernoLoteComercial`, `LoteBeneficiamento` | Cobertura real. |
| Certificações | EXISTE E ATENDE | `CertificacaoPropriedade` | Cadastro e consulta existem. |
| ESG | EXISTE PARCIALMENTE | telas e relatórios ESG no web | Existe módulo ESG, mas não vi acoplamento específico a exportação de café. |
| Auditorias | EXISTE PARCIALMENTE | passaporte/rastreabilidade/audit logs pontuais | Existe trilha parcial, não um pacote completo de auditoria exportadora. |
| Evidências | EXISTE PARCIALMENTE | caderno, fotos, snapshot | Cobertura útil, mas não completa para compliance exportador. |
| Integração com cliente/exportador | EXISTE PARCIALMENTE | comprador em comercialização | Há comprador; não há camada específica de exportador/importador/cliente externo. |

### 4.3 Integração com Sankhya

Status: **EXISTE E ATENDE PARCIALMENTE**.

Fatos encontrados:

- router ativo em `/api/v1/integracoes/sankhya` com configuração, status, teste de conexão, sync e logs;
- serviços reais para WS BPM via `httpx`;
- integração para pessoas, produtos, NFe e financeiro;
- tela web de backoffice para monitoramento e configuração.

Limites encontrados:

- não encontrei evidência de integração Sankhya específica para fluxo cafeeiro/exportador;
- não encontrei evidência de o Wizard depender ou orquestrar Sankhya;
- não encontrei suíte de testes dedicada à integração Sankhya no diretório de testes.

Conclusão de posicionamento:

- **Sankhya deve ser tratado como sistema mestre administrativo/fiscal/financeiro**.
- **AgroSaaS deve ser tratado como sistema mestre operacional agrícola**.
- A integração existe, mas não deve ser premissa crítica do primeiro piloto de café exportador.

## 5. Fluxo operacional do café

| Etapa | Classificação | Leitura |
| --- | --- | --- |
| Planejamento | EXISTE PARCIALMENTE | Safra/cultivo existem, mas perenidade do café ainda não está modelada em profundidade. |
| Tratos culturais | EXISTE PARCIALMENTE | Operações e caderno cobrem, mas sem trilhas cafeeiras especializadas. |
| Pulverização | EXISTE E ATENDE | Fluxo genérico agrícola já cobre. |
| Adubação | EXISTE E ATENDE | Fluxo genérico agrícola já cobre. |
| Colheita | EXISTE E ATENDE | PWA e romaneios cobrem. |
| Transporte | EXISTE PARCIALMENTE | Registrável por operação/caderno, sem módulo dedicado. |
| Secagem | EXISTE E ATENDE | Coberta em beneficiamento. |
| Beneficiamento | EXISTE E ATENDE | Coberto por módulo dedicado. |
| Armazenagem | EXISTE PARCIALMENTE | Vínculo com estoque existe, sem camada exportadora específica. |
| Classificação | EXISTE E ATENDE | Peneira, bebida, defeitos e SCAA existem. |
| Comercialização | EXISTE E ATENDE | Contrato, status, receita e vínculo com produto colhido existem. |
| Exportação | NÃO EXISTE | Não encontrei fluxo específico de embarque, porto, Incoterm, container, DU-E, booking etc. |
| Rastreabilidade | EXISTE E ATENDE | Cadeia e passaporte existem. |
| Rentabilidade | EXISTE PARCIALMENTE | Arquitetura econômica existe por PU/safra/talhão, mas não por lote exportador de café. |

## 6. Custos

Arquitetura econômica observada:

```text
Evento operacional
  ↓
OperationalCostAllocationService
  ↓
CostAllocation
  ↓
DRE agrícola
  ↓
Rentabilidade
```

Leitura por necessidade do piloto:

- **Custo por talhão**: EXISTE E ATENDE.
- **Custo por safra**: EXISTE E ATENDE.
- **Custo por ProductionUnit**: EXISTE E ATENDE.
- **Custo por lote de café beneficiado**: NÃO EXISTE como camada econômica oficial explícita.
- **Custo por saca**: EXISTE PARCIALMENTE, derivável em relatórios, mas não encontrei trilha oficial explícita pronta.
- **Custo de máquinas**: EXISTE E ATENDE via porta oficial operacional.
- **Custo de mão de obra**: EXISTE E ATENDE pela arquitetura econômica consolidada.
- **Custo de insumos**: EXISTE E ATENDE.
- **Integração com estoque**: EXISTE E ATENDE.
- **Integração com financeiro**: EXISTE E ATENDE.

Risco principal:

- a plataforma está forte em custo operacional por unidade agrícola, mas ainda não vi fechamento econômico específico por **lote exportável de café**.

## 7. Wizard

O Wizard atual consegue implantar a base de uma fazenda de café **sem customização estrutural**, mas não valida requisitos específicos de exportação de café.

O que ele já cobre:

- Unidade Produtiva;
- Área Rural;
- talhão para agricultura;
- depósito;
- plano de contas mínimo;
- catálogo mínimo de produtos;
- equipamento;
- pendências e go-live controlado.

Evidência: [services/api/wizard/services.py](/opt/lampp/htdocs/farm/services/api/wizard/services.py:59) e [services/api/wizard/checklist_engine.py](/opt/lampp/htdocs/farm/services/api/wizard/checklist_engine.py:60).

O que ele ainda não cobre de forma específica:

- cultivar de café obrigatória;
- estrutura de beneficiamento obrigatória;
- certificações obrigatórias para exportação;
- critérios de qualidade de bebida/SCAA para go-live;
- configuração Sankhya como pré-condição opcional/assistida;
- prontidão de exportação.

Conclusão: **o Wizard atende a implantação operacional base da fazenda, mas não a prontidão exportadora do café**.

## 8. Apps

### apps/web

Pontos fortes:

- tela de beneficiamento;
- tela de rastreabilidade/certificações;
- romaneios;
- comercializações;
- backoffice Sankhya;
- ESG/passaportes.

Leitura:

- o web cobre bem a camada administrativa e analítica do piloto.

### apps/campo

Pontos fortes:

- colheita offline por talhão;
- caderno offline por unidade produtiva/safra/talhão;
- tarefas e sync.

Limites:

- não encontrei tela PWA específica para secagem;
- não encontrei tela PWA específica para beneficiamento;
- não encontrei tela PWA específica para classificação de café;
- não encontrei fluxo PWA específico de rastreabilidade exportadora.

Conclusão:

- o PWA cobre bem **campo e colheita**;
- não cobre ainda **pós-colheita exportadora** com a mesma profundidade.

## 9. Lacunas críticas

- Não existe fluxo explícito de exportação com embarque, porto, Incoterm, documentação e logística internacional.
- Não existe camada oficial explícita de custo por lote exportável de café.
- O Wizard não valida prontidão específica de cafeicultura exportadora.
- O PWA não cobre secagem, beneficiamento e classificação de café como jornada dedicada.
- Não encontrei evidência de testes específicos da integração Sankhya.

## 10. Lacunas não críticas

- Idade do cafezal não apareceu modelada.
- Colheita seletiva aparece no contexto fenológico, mas não como fluxo operacional explícito.
- Transporte interno existe apenas como operação/caderno genérico.
- Gestão varietal de café existe de forma genérica, não especializada.
- ESG e certificações existem, mas ainda não vi pacote exportador unificado para café.

## 11. Riscos do piloto

- risco de o cliente esperar cobertura de exportação completa enquanto a plataforma hoje entrega melhor o operacional agro;
- risco de elevar Sankhya à condição de trilha crítica antes de validar o fluxo operacional base;
- risco de gap entre operação de campo e pós-colheita especializada no uso móvel;
- risco comercial se o posicionamento for “substituir o ERP” em vez de “complementar o ERP”.

## 12. Recomendações antes de abordar o cliente

- posicionar o AgroSaaS como **plataforma operacional agrícola e de rastreabilidade**, não como substituto imediato do Sankhya;
- vender o primeiro piloto como **piloto controlado de operação cafeeira**, não como projeto completo de exportação;
- limitar a integração Sankhya àquilo que já existe e puder ser validado com segurança;
- alinhar previamente que exportação internacional profunda fica fora da onda 1.

## 13. Funcionalidades que podem esperar para depois do piloto

- fluxo exportador completo;
- documentos e logística de embarque;
- custo por lote exportável;
- PWA de pós-colheita especializada;
- critérios automáticos de go-live específicos para café exportador;
- endurecimento de testes end-to-end da integração Sankhya.

## 14. Escopo mínimo recomendado para o piloto

- implantação via Wizard;
- Unidade Produtiva, áreas e talhões;
- cadastro de cultura café e cultivares relevantes;
- operações agrícolas e caderno;
- colheita e romaneios;
- beneficiamento e classificação;
- rastreabilidade e certificações;
- comercialização básica;
- custos operacionais, DRE e rentabilidade por safra/talhão/PU;
- Sankhya apenas como trilha assistida de integração administrativa.

## 15. Posicionamento comercial AgroSaaS × Sankhya

Fato observado no código:

- AgroSaaS já possui uma integração real com Sankhya.

Recomendação de posicionamento:

- **Sankhya**: mestre administrativo, financeiro, fiscal e contábil.
- **AgroSaaS**: mestre operacional agrícola, territorial, rastreável e econômico-operacional.

Esse posicionamento é tecnicamente coerente com a codebase atual.

## 16. Próximas execuções sugeridas

1. `PILOT-03` — escopo mínimo operacional de cafeicultura para piloto controlado.
2. `CAFE-ARCH-01` — arquitetura específica de cafeicultura perene e pós-colheita.
3. `SANKHYA-GOV-01` — guardrails da integração Sankhya para uso em piloto.
4. `EXPORT-ARCH-01` — arquitetura de exportação e logística internacional, se o cliente exigir essa trilha.

## 17. Recomendação final

Recomendação objetiva: **não iniciar um piloto amplo de exportador de café integrado ao Sankhya como proposta full-scope neste momento**.

Recomendação alternativa: **iniciar somente um piloto controlado, com escopo reduzido e contrato muito claro**, cobrindo:

- implantação da fazenda;
- operação agrícola de café;
- colheita;
- beneficiamento;
- rastreabilidade;
- comercialização básica;
- custos e visão econômica operacional;
- Sankhya como integração assistida e não como dependência crítica do go-live.

Nessas condições, o AgroSaaS **está apto para conversar com o cliente**. Fora dessas condições, o risco de promessa acima da capacidade atual ainda é alto.
