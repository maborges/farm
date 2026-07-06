# LAUNCH-R2 - Auditoria dos Custos de Maquinas e Equipamentos

## 1. Objetivo

Auditar se os custos operacionais de maquinas e equipamentos chegam automaticamente ao custo da operacao, ao financeiro, ao centro de custos, a rentabilidade e aos indicadores.

## 2. Conclusao executiva

O fluxo existe de forma **parcial**.

Ha evidencia clara de:

- cadastro e telemetria operacional de frota;
- abastecimentos com custo;
- OS de manutencao com custos de pecas e mao de obra;
- dashboard de custos, consumo e inteligencia;
- DRE agricola consumindo `CostAllocation` e `Despesa`.

Mas o encadeamento **nao e totalmente automatico**. A apropriacao economica da maquina para safra / talhao / rentabilidade depende, em partes relevantes, de:

- apontamento operacional com `custo_total` informado manualmente;
- fechamento de OS;
- abastecimento externo;
- ou custos ja consolidados em dashboards analiticos.

Nao encontrei um evento oficial unico que transforme toda operacao mecanizada em custo economico persistido e consumido pela DRE sem intervencao operacional adicional.

Classificacao final do fluxo: **🟡 Parcial**

## 3. Evidencias encontradas

### 3.1. Abastecimento

- O servico de abastecimento grava o registro e herda safra / talhao da jornada ativa em [services/api/operacional/services/abastecimento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/abastecimento_service.py:20).
- Para abastecimento **interno**, o impacto e a baixa de estoque em combustivel via `EstoqueService.registrar_saida_insumo_por_nome(...)` em [services/api/operacional/services/abastecimento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/abastecimento_service.py:66).
- Para abastecimento **externo**, o servico cria `Despesa` com origem `ABASTECIMENTO` e status `PAGO` em [services/api/operacional/services/abastecimento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/abastecimento_service.py:86).
- Lacuna: no caminho interno, nao ha geracao direta de `Despesa` ou `CostAllocation`; o custo fica no estoque / dashboard analitico.

### 3.2. Apontamento operacional

- O servico de apontamento atualiza horimetro/km e registra `CostAllocation` somente se `custo_total` ja vier preenchido em [services/api/operacional/services/frota_apontamento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_apontamento_service.py:277).
- A apropriacao economica e explicitamente `source="MANUAL"` em [services/api/operacional/services/frota_apontamento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_apontamento_service.py:283).
- Isso confirma dependencia de intervencao manual para transformar apontamento em custo economico.

### 3.3. Ordem de Servico e manutencao

- O fechamento de OS gera `Despesa` automaticamente quando ha custo em [services/api/operacional/services/frota_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_service.py:398).
- Itens da OS baixam estoque e tambem geram `CostAllocation` com origem `ESTOQUE` em [services/api/operacional/services/frota_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_service.py:401).
- Isso fecha bem o ciclo de pecas / manutencao, mas nao cobre todas as demais leituras mecanizadas.

### 3.4. Consolidacao de custos da frota

- O agregado de frota soma combustivel, mao de obra, pecas e manutencao avulsa em [services/api/operacional/services/frota_custo_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_custo_service.py:45).
- A consolidacao por safra / UP / talhao / operacao e analitica e baseada em custos ja registrados em [services/api/operacional/services/frota_custo_consolidado_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_custo_consolidado_service.py:50).
- Isso produz visao de custo, mas nao prova sozinho apropriacao economica automatica para o DRE.

### 3.5. DRE agricola e rentabilidade

- A DRE agricola v1 consome `CostAllocation` como camada economica oficial em [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:520).
- Na consolidacao de despesas, a DRE exclui despesas que ja possuem appropriacao superior (`CostAllocation`) em [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:679).
- A DRE reconhece despesas de origem `ORDEM_SERVICO` e `ABASTECIMENTO`, mas apenas como despesa se nao estiverem ja representadas por `CostAllocation` em [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py:650).
- Conclusao: rentabilidade e DRE sao alimentadas por camadas economicas existentes, mas nao ha prova de que toda operacao mecanizada gere essas camadas automaticamente.

### 3.6. Infraestrutura financeira reutilizavel, porem nao integrada em toda a cadeia

- Existe um servico oficial para registrar custos / despesas operacionais em [services/api/financeiro/services/lancamento_operacional_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/lancamento_operacional_service.py:10).
- Esse servico contem helpers para uso de insumo, manutencao e abastecimento em [services/api/financeiro/services/lancamento_operacional_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/lancamento_operacional_service.py:15).
- Nao encontrei uso direto desse servico na cadeia mecanizada auditada. Isso indica capacidade existente, mas integracao incompleta.

## 4. Perguntas obrigatorias

1. O custo de combustivel entra automaticamente na operacao?

- **Parcialmente.**
- Abastecimento externo gera despesa financeira automaticamente.
- Abastecimento interno gera baixa de estoque, mas nao despesa financeira direta.

2. O custo das pecas entra automaticamente?

- **Sim, no fechamento da OS.**
- A baixa de item da OS gera `CostAllocation` e alimenta custo / DRE.

3. O custo da manutencao entra automaticamente?

- **Parcialmente.**
- O fechamento da OS cria `Despesa` de manutencao.
- Manutencao avulsa aparece nos agregados, mas nao vi uma unica trilha universal para toda manutencao mecanizada.

4. Existe custo por hora?

- **Sim, como analitica de frota.**
- O custo por hora e calculado nos dashboards de frota.

5. Existe custo por operacao?

- **Parcialmente.**
- Existe para OS e apontamentos com custo informado.
- Nao vi apropriacao automatica universal a partir da jornada mecanizada.

6. Existe apropriacao automatica na safra?

- **Parcialmente.**
- Existe quando a origem gera `CostAllocation` ou `Despesa` com contexto valido.

7. Existe apropriacao automatica no talhao?

- **Parcialmente.**
- Depende do contexto da origem (jornada / OS / abastecimento / apontamento) e da capacidade de mapear `production_unit`.

8. Existe apropriacao automatica na rentabilidade?

- **Parcialmente.**
- A rentabilidade consome DRE / custos, mas o fluxo de entrada nao esta integralmente automatico.

9. Existe rastreabilidade completa?

- **Parcialmente.**
- Ha rastreabilidade forte entre equipamento, jornada, OS, abastecimento, estoque e DRE.
- Faltam pontos oficiais unificados para todo custo mecanizado.

10. Existe intervencao manual?

- **Sim.**
- Principalmente no apontamento com `custo_total`.
- Tambem ha dependencia de classificacao operacional de abastecimento / OS para fechar a apropriacao economica.

## 5. Testes

### 5.1. Cobertura existente

- `services/api/tests/test_frota_custos_step03.py`
  - cobre disponibilidade, tempo parado, custo agregado por safra e indicadores da frota.
- `services/api/tests/test_frota_apontamentos_step08.py`
  - cobre apontamento operacional com `custo_total` manual e criacao de `CostAllocation`.
- `services/api/tests/test_frota_step09_executivo.py`
  - cobre dashboard executivo e combinacao de abastecimento / manutencao / apontamento.
- `services/api/tests/test_dre_operacional_step183.py`
  - cobre DRE operacional em nivel conceitual.

### 5.2. Lacunas de teste

- Nao encontrei teste que prove a cadeia completa:
  - jornada -> custo automatico -> `CostAllocation` / `Despesa` -> DRE -> rentabilidade.
- Nao encontrei teste focado em abastecimento interno com reflexo economico automatico.
- Nao encontrei teste end-to-end da experiencia de frota mecanizada ate a rentabilidade agricola.

## 6. Frontend

- Ha telas para frota, custos, consumo e inteligencia em:
  - [apps/web/src/app/(dashboard)/dashboard/operacional/frota/custos/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/frota/custos/page.tsx:1)
  - [apps/web/src/app/(dashboard)/dashboard/operacional/frota/inteligencia/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/frota/inteligencia/page.tsx:1)
  - [apps/web/src/app/(dashboard)/dashboard/operacional/frota/[equipamentoId]/EquipamentoDetalheClient.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/frota/[equipamentoId]/EquipamentoDetalheClient.tsx:363)
- O frontend exibe custo, consumo, manutencao e risco, mas isso e leitura analitica, nao prova de apropricao economica automatica no financeiro.

## 7. Resultado final

### Fluxo auditado

**Toda operacao mecanizada executada na fazenda gera automaticamente seus custos completos e atualiza corretamente a rentabilidade agricola, sem intervencao manual?**

- **Resposta: nao.**

### Classificacao

- **🟡 Parcial**

### Principais motivos

- Parte do custo nasce como analitica de frota, nao como lancamento economico persistente.
- O apontamento que gera `CostAllocation` exige `custo_total` informado manualmente.
- O abastecimento interno nao cria despesa financeira direta.
- O encadeamento ate DRE / rentabilidade existe, mas depende de origens especificas e nao cobre todo o fluxo mecanizado de forma oficial.

## 8. Arquivos consultados

- [services/api/operacional/services/abastecimento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/abastecimento_service.py)
- [services/api/operacional/services/frota_apontamento_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_apontamento_service.py)
- [services/api/operacional/services/frota_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_service.py)
- [services/api/operacional/services/frota_custo_consolidado_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_custo_consolidado_service.py)
- [services/api/operacional/services/frota_custo_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_custo_service.py)
- [services/api/agricola/dre/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dre/service.py)
- [services/api/financeiro/services/lancamento_operacional_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/lancamento_operacional_service.py)
- [services/api/tests/test_frota_custos_step03.py](/opt/lampp/htdocs/farm/services/api/tests/test_frota_custos_step03.py)
- [services/api/tests/test_frota_apontamentos_step08.py](/opt/lampp/htdocs/farm/services/api/tests/test_frota_apontamentos_step08.py)
- [services/api/tests/test_frota_step09_executivo.py](/opt/lampp/htdocs/farm/services/api/tests/test_frota_step09_executivo.py)
- [services/api/tests/test_dre_operacional_step183.py](/opt/lampp/htdocs/farm/services/api/tests/test_dre_operacional_step183.py)
- [apps/web/src/app/(dashboard)/dashboard/operacional/frota/custos/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/frota/custos/page.tsx)
- [apps/web/src/app/(dashboard)/dashboard/operacional/frota/inteligencia/page.tsx](/opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/operacional/frota/inteligencia/page.tsx)

