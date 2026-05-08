# Módulo Frota — AgroSaaS

**Documentação Funcional e Comercial**  
Versão: 1.0 | Referência: Frota-01 a Frota-11.1 | Data: 2026-05-07

---

## 1. Visão Geral

O módulo **Frota** do AgroSaaS é o centro de controle da maquinaria agrícola. Ele centraliza o cadastro, o acompanhamento operacional e a análise de custos de todos os equipamentos da propriedade — tratores, colhedoras, pulverizadores, pivôs de irrigação, veículos e implementos.

Diferente de sistemas de frotas genéricos, o módulo foi desenhado para o contexto rural brasileiro: integra diretamente com safras, talhões e operações agrícolas, permitindo que o produtor e o gestor saibam exatamente quanto cada máquina custa por hora trabalhada, em qual área operou e se está em condições de ir ao campo.

O módulo é acessado em `/dashboard/operacional/frota` e está disponível em três níveis de plano, com funcionalidades progressivas conforme o contrato do tenant.

---

## 2. Problemas que o Módulo Resolve

| Problema do Produtor | Como o Módulo Resolve |
|---|---|
| "Não sei quanto gasto com cada máquina" | Custo por equipamento com detalhamento em combustível, manutenção e peças |
| "Minha máquina quebrou e eu não sabia que ia quebrar" | Planos de manutenção preventiva com alertas por km, horas ou dias |
| "Não sei se a máquina está disponível ou em conserto" | Painel de disponibilidade operacional em tempo real |
| "Não consigo rastrear quem usou a máquina e por quanto tempo" | Jornadas de uso com horímetro/km, operador e custo estimado |
| "Não sei quanto cada safra consumiu de máquina" | Integração Frota × Agricultura: custo por safra, talhão e tipo de operação |
| "Tenho várias máquinas mas não sei qual é o problema maior" | Score de risco e ranking por equipamento com recomendações automáticas |

---

## 3. Funcionalidades por Plano

### 3.1 BÁSICO

Foco em controle operacional fundamental. Indicado para produtores que precisam de organização básica sem investimento em análise avançada.

- **Cadastro de equipamentos**: registro de tratores, colhedoras, pulverizadores, pivôs, veículos, implementos e outros. Campos: nome, tipo, marca, modelo, ano, placa/chassi, número de série, patrimônio, combustível, potência (CV), capacidade do tanque, horímetro e km atuais, status (Ativo, Em manutenção, Inativo).
- **Dashboard essencial**: visão geral da frota com lista de equipamentos, status, custo total e alertas ativos.
- **Detalhe do equipamento**: ficha completa com indicadores, histórico de abastecimentos, ordens de serviço, manutenções e jornadas.
- **Ordens de Serviço (OS)**: abertura, acompanhamento e encerramento de OS com registro de custo de mão de obra e peças/insumos consumidos. Ao fechar a OS, o horímetro/km do equipamento é atualizado automaticamente.
- **Consulta de documentos**: visualização de documentos cadastrados com alertas de vencimento.
- **Proteção por tenant**: isolamento absoluto — equipamentos de um tenant são invisíveis a qualquer outro.

> Endpoints protegidos do plano PROFISSIONAL e ENTERPRISE retornam `402 Payment Required` com CTA de upgrade.

---

### 3.2 PROFISSIONAL

Adiciona controle de eficiência, planejamento de manutenção e gestão de disponibilidade. Indicado para fazendas com frota média (5–30 máquinas) e gestores de campo.

Inclui tudo do BÁSICO, mais:

- **Abastecimento com baixa de estoque**: registro de abastecimentos com litros, custo por litro, horímetro/km na data, local e observações. O sistema realiza baixa automática no módulo de Estoque (produto `DIESEL` ou equivalente).
- **Análise de consumo e eficiência**:
  - Consumo médio em L/h e km/L por equipamento
  - Custo por hora e custo por km
  - Alertas automáticos: consumo acima da média, custo acima da média, intervalo curto entre abastecimentos, leitura de horímetro menor que a anterior, equipamento sem abastecimento recente
  - Score de eficiência por equipamento com variação em relação à média da frota e ao histórico
  - Ranking dos equipamentos menos eficientes
- **Manutenção preventiva**:
  - Criação de planos por intervalo de km, horas ou dias (ex.: troca de óleo a cada 250 horas)
  - Alertas automáticos de manutenção próxima e vencida
  - Geração de OS preventiva a partir do plano — com validação para não duplicar OS já aberta
  - Status do plano: `OK`, `PROXIMA`, `VENCIDA`
- **Disponibilidade operacional**:
  - Painel com contagem em tempo real: Disponível, Em Uso, Em Manutenção, Bloqueado, Checklist Pendente, Não Conforme, Documento Vencido
  - Bloqueio/liberação manual de equipamento com motivo registrado
  - Impedimento automático de abertura de jornada para equipamento bloqueado (`422` com motivo do bloqueio)
  - Detalhamento por equipamento: OS abertas, não conformidades, documentos vencidos
- **Jornadas de uso**:
  - Abertura de jornada com horímetro/km inicial e operador responsável
  - Impedimento de duas jornadas simultâneas para o mesmo equipamento
  - Fechamento de jornada com horímetro/km final — atualiza automaticamente o cadastro do equipamento
  - Cálculo automático de horas trabalhadas, km rodados e custo estimado da jornada
- **Análise de custos**:
  - Custo total por equipamento: combustível + manutenção + peças/itens
  - Custo por hora e custo por km
  - Ranking dos equipamentos mais caros
  - Filtragem por período e por unidade produtiva
  - Detalhe de custo individual por equipamento com participação percentual na frota

---

### 3.3 ENTERPRISE

Adiciona inteligência operacional e integração total com o módulo Agrícola. Indicado para grandes fazendas, holdings agrícolas e gestores que necessitam de visibilidade estratégica.

Inclui tudo do PROFISSIONAL, mais:

- **Inteligência operacional (Score de Risco)**:
  - Cálculo automático de score de risco (0–100) por equipamento, baseado em múltiplos fatores ponderados:
    - Custo acima da média da frota
    - Consumo acima da média
    - Manutenção preventiva vencida ou próxima
    - Uso intensivo recente (horas/km)
    - OS aberta há muito tempo
    - Risco de parada (combinação de fatores críticos)
    - Documento vencido
    - Checklist não conforme
  - Nível de risco: `BAIXO`, `MÉDIO`, `ALTO`, `CRÍTICO`
  - Recomendações automáticas por equipamento (ex.: "Realizar manutenção preventiva", "Verificar consumo elevado")
  - Top 5 recomendações consolidadas para toda a frota
  - Ranking dos equipamentos menos eficientes e mais arriscados
- **Frota × Agricultura (integração)**:
  - Vinculação de jornadas a safras, talhões e tipo de operação agrícola
  - Custo estimado por safra: horas, km e custo total da frota empregada
  - Custo estimado por talhão: comparação de investimento de máquina por área
  - Custo estimado por tipo de operação: plantio, pulverização, colheita, etc.
  - Ranking de operação mais cara e talhão mais caro
  - Equipamento mais usado por safra
  - Suporte a hierarquia de área: Área Rural → Gleba → Talhão

---

## 4. Fluxos Principais

### 4.1 Cadastro de Equipamento

```
Usuário acessa /frota/equipamentos → clica em "Novo Equipamento"
→ Preenche: nome, tipo, marca, modelo, ano, combustível, potência, horímetro/km atual
→ Vincula à unidade produtiva
→ Sistema salva com status "ATIVO"
→ Equipamento aparece no dashboard e está disponível para OS, jornadas e planos
```

Tipos suportados: `TRATOR`, `COLHEDORA`, `PULVERIZADOR`, `CAMINHAO`, `UTILITARIO`, `IMPLEMENTO`, `PIVO_IRRIGACAO`, `VEICULO`, `OUTRO`.

Dados extras por tipo são armazenados em campo JSONB para especificações técnicas (ex.: tração 4×4, plataforma de corte, capacidade do tanque do pulverizador).

---

### 4.2 Abastecimento

```
Usuário acessa detalhe do equipamento → aba "Abastecimentos" → "Registrar"
→ Informa: data, litros, custo por litro, horímetro/km na data, local
→ Sistema realiza baixa automática no estoque (produto DIESEL/equivalente)
→ Custo do abastecimento entra no cálculo de custo total do equipamento
→ Sistema verifica anomalias: consumo fora da média, leitura menor que anterior
→ Alertas são gerados automaticamente no painel de consumo
```

**Pré-requisito:** produto de combustível cadastrado no módulo de Estoque (ex.: `DIESEL`).

---

### 4.3 Ordem de Serviço (OS) / Manutenção Corretiva

```
Usuário abre OS para equipamento → informa tipo, descrição, prioridade
→ Durante execução: adiciona itens (peças/insumos) com quantidade
→ Sistema busca preço médio do produto no catálogo e registra custo histórico
→ Ao fechar OS: informa custo de mão de obra, data de conclusão
→ Sistema atualiza horímetro/km do equipamento
→ Custo total da OS (peças + mão de obra) entra no custo do equipamento
```

Tipos de OS: corretiva, preventiva (gerada automaticamente por plano), checklist.  
Status: `ABERTA` → `EM_ANDAMENTO` → `CONCLUIDA`.

---

### 4.4 Manutenção Preventiva

```
Gestor cria plano preventivo para equipamento:
→ Define descrição (ex.: "Troca de óleo motor")
→ Define gatilho: intervalo em km E/OU horas E/OU dias
→ Sistema calcula próxima manutenção baseado no horímetro/km/data atual

Em operação:
→ A cada consulta, sistema verifica todos os planos ativos
→ Status do plano: OK (dentro do prazo) / PROXIMA (próxima do vencimento) / VENCIDA
→ Alerta aparece no dashboard e na inteligência operacional
→ Usuário clica "Gerar OS" no plano vencido/próximo
→ Sistema cria OS e bloqueia nova geração para o mesmo plano (sem duplicação)
```

---

### 4.5 Jornada de Uso

```
Operador (ou gestor) abre jornada:
→ Seleciona equipamento (bloqueado = impedido com 422)
→ Informa horímetro inicial e km inicial
→ Informa operador responsável

Ao final do turno, fecha a jornada:
→ Informa horímetro final e km final
→ Sistema calcula horas trabalhadas e km rodados
→ Horímetro e km do equipamento são atualizados automaticamente
→ Custo estimado da jornada é calculado com base no custo/hora ou custo/km do equipamento

[ENTERPRISE] Vinculação agrícola:
→ Usuário associa jornada a safra + talhão + tipo de operação
→ Custo da jornada entra no custo agrícola da safra/talhão
```

Regra: não é permitida mais de uma jornada aberta por equipamento ao mesmo tempo.

---

### 4.6 Custo por Máquina

```
Gestor acessa /frota/custos:
→ Seleciona período e (opcionalmente) unidade produtiva
→ Visualiza resumo da frota: custo total, combustível, manutenção, peças
→ Visualiza ranking dos equipamentos mais caros
→ Acessa detalhe de qualquer equipamento:
  - Breakdown: combustível / manutenção / peças
  - Custo por hora e custo por km
  - Participação percentual no custo total da frota
  - Histórico de eventos de custo
```

---

### 4.7 Integração com Agricultura

```
[ENTERPRISE] Gestor acessa /frota/agricultura:
→ Seleciona safra de referência
→ Visualiza:
  - Total de horas e km da frota na safra
  - Custo estimado total de máquinas na safra
  - Custo por talhão (qual área consumiu mais recurso de frota)
  - Custo por tipo de operação (plantio vs. pulverização vs. colheita)
  - Equipamento mais usado na safra
→ Acessa detalhe por talhão ou por operação para análise granular
```

Pré-requisito de hierarquia: Área Rural → Gleba → Talhão.

---

### 4.8 Inteligência Operacional

```
[ENTERPRISE] Sistema processa automaticamente todos os equipamentos:
→ Calcula score de risco (0–100) combinando 8+ fatores ponderados
→ Classifica equipamento: BAIXO / MÉDIO / ALTO / CRÍTICO
→ Gera recomendações específicas por equipamento
→ Consolida top 5 recomendações para toda a frota
→ Apresenta ranking dos menos eficientes e dos mais arriscados

Gestor acessa /frota/inteligencia:
→ Visualiza todos os equipamentos com score, nível e recomendações
→ Identifica os equipamentos que exigem ação imediata
→ Decide: gerar OS, agendar manutenção, bloquear equipamento
```

---

## 5. Indicadores Disponíveis

### Nível de Frota (Dashboard Geral)

| Indicador | Plano Mínimo |
|---|---|
| Total de equipamentos ativos | BÁSICO |
| Equipamentos em manutenção | BÁSICO |
| Equipamentos bloqueados | PROFISSIONAL |
| Custo total da frota no período | PROFISSIONAL |
| Equipamento mais caro | PROFISSIONAL |
| Custo médio por equipamento | PROFISSIONAL |
| Total de litros abastecidos | PROFISSIONAL |
| Custo total de combustível | PROFISSIONAL |
| Consumo médio L/h e km/L | PROFISSIONAL |
| Alertas de consumo ativos | PROFISSIONAL |
| Score de risco médio da frota | ENTERPRISE |
| Equipamentos críticos | ENTERPRISE |

### Nível de Equipamento (Detalhe)

| Indicador | Plano Mínimo |
|---|---|
| Horímetro atual | BÁSICO |
| Km atual | BÁSICO |
| OS abertas | BÁSICO |
| Último abastecimento | BÁSICO |
| Custo total (combustível + manutenção + peças) | PROFISSIONAL |
| Custo por hora | PROFISSIONAL |
| Custo por km | PROFISSIONAL |
| Status de disponibilidade operacional | PROFISSIONAL |
| Status de manutenção preventiva | PROFISSIONAL |
| Score de risco individual | ENTERPRISE |
| Nível de risco (BAIXO/MÉDIO/ALTO/CRÍTICO) | ENTERPRISE |
| Recomendações automáticas | ENTERPRISE |
| Custo por safra/talhão/operação | ENTERPRISE |

---

## 6. Benefícios para o Produtor e Gestor

**Controle financeiro real da frota**  
O módulo une combustível, peças e mão de obra em um único custo por equipamento, calculado automaticamente. O gestor para de estimar e começa a medir.

**Prevenção de paradas não planejadas**  
Os planos preventivos com alerta por horas, km e dias eliminam a manutenção reativa. A máquina não quebra na hora da colheita porque o sistema avisou antes.

**Visibilidade de quem usa o quê**  
As jornadas registram operador, tempo e área trabalhada. É possível saber quem operou qual máquina, por quanto tempo e qual foi o custo estimado daquela jornada.

**Integração com o ciclo agrícola**  
O custo de frota entra diretamente no custo da safra. O produtor vê quanto cada talhão custou em horas de máquina — informação essencial para o DRE operacional.

**Decisão baseada em dados, não em intuição**  
O score de risco e o ranking da inteligência operacional apontam exatamente quais máquinas precisam de atenção, sem que o gestor precise revisar cada equipamento manualmente.

---

## 7. Diferenciais Competitivos

1. **Integração nativa com Agricultura**: nenhum sistema de frota agrícola do mercado médio conecta jornadas de máquina diretamente a safras e talhões com custo por operação. No AgroSaaS, isso é nativo.

2. **Score de risco multi-fator**: o modelo de inteligência opera com 8+ fatores (custo, consumo, preventiva, uso intensivo, OS antiga, documento, checklist) em um único score ponderado — não é um alerta simples de prazo.

3. **Custo por hora e por km calculado automaticamente**: sem planilhas, sem cálculo manual. O sistema mantém os valores atualizados a cada abastecimento e encerramento de OS.

4. **Proteção por tenant e por plano**: multi-tenancy absoluto com feature gate por tier. O sistema nunca expõe dados de uma fazenda a outra, e o backend valida o plano em cada endpoint.

5. **Disponibilidade operacional com bloqueio ativo**: o gestor bloqueia um equipamento e qualquer tentativa de abertura de jornada é impedida automaticamente com motivo registrado.

6. **Preço histórico de peças na OS**: ao adicionar uma peça a uma OS, o sistema registra o preço médio do produto naquele momento — criando um histórico imutável de custo que não muda com variações futuras de preço.

---

## 8. Limitações Atuais e Backlog Futuro

### Limitações atuais (conhecidas após Frota-11.1)

| Limitação | Impacto | Observação |
|---|---|---|
| Abastecimento exige produto cadastrado no Estoque | Médio | Se o produto `DIESEL` não estiver no catálogo de estoque do tenant, o registro de abastecimento retorna 404 |
| Hierarquia agrícola obrigatória: Área Rural → Gleba → Talhão | Baixo | Não é possível vincular jornada direto à Área Rural sem passar por Gleba |
| Contrato HTTP de bloqueio usa 422 em vez de 400 | Baixo | Funcionalidade correta, mas diverge do padrão REST esperado para erros de regra de negócio |
| Score de risco sem histórico temporal | Médio | O score é calculado em tempo real sem comparação com períodos anteriores |
| Ausência de relatório exportável | Médio | Não há exportação de custos ou jornadas para PDF/Excel diretamente no módulo |
| Checklist de pré-uso não implementado como fluxo guiado | Alto | O status `CHECKLIST_PENDENTE` existe na disponibilidade, mas o fluxo de preenchimento do checklist ainda não está disponível no frontend |

### Backlog futuro (sugestões)

- **Checklist de pré-uso** guiado no frontend com modelo configurável por tipo de equipamento
- **Exportação de relatórios** de custo e jornadas para PDF/Excel
- **Gráfico de evolução do score de risco** por equipamento ao longo do tempo
- **Integração com financeiro**: custo de frota alimentando o DRE operacional da safra automaticamente
- **Gestão documental completa**: upload de CRLV, seguro, certificados com alertas de vencimento
- **Comparativo entre equipamentos** (benchmark interno de produtividade)
- **Alerta proativo por e-mail/notificação push** para preventivas vencidas e documentos a vencer
- **API de telemetria via GPS/telemática** para atualização automática de horímetro e km

---

## 9. Roteiro de Demonstração Comercial

### Público-alvo da demo: gestor de fazenda ou proprietário rural com 5+ máquinas

**Tempo estimado: 20–25 minutos**

---

**Bloco 1 — Dor (3 min)**  
Abrir com a pergunta: *"Você sabe quanto custa por hora operar seu trator hoje?"*  
Mostrar o problema: planilha genérica vs. dado em tempo real no AgroSaaS.

---

**Bloco 2 — Dashboard e visão geral (4 min)**  
- Abrir `/frota` com uma frota de demonstração (5–8 equipamentos)
- Mostrar o resumo: disponíveis, em manutenção, custo total do mês
- Destacar o equipamento com maior custo e o com alerta ativo
- Clicar no detalhe de um equipamento e mostrar a ficha completa

---

**Bloco 3 — Manutenção preventiva (4 min)**  
- Mostrar um plano preventivo próximo do vencimento (status `PROXIMA`)
- Gerar OS preventiva com um clique
- Demonstrar que o sistema impede duplicação se já existe OS aberta

---

**Bloco 4 — Jornada de uso (4 min)**  
- Abrir jornada para um trator (informar horímetro inicial + operador)
- Mostrar que equipamento bloqueado impede abertura de jornada
- Fechar a jornada, mostrar atualização automática do horímetro
- **[ENTERPRISE]** Vincular a safra + talhão + operação "Pulverização"

---

**Bloco 5 — Custos e inteligência (5 min)**  
- Mostrar tela de custos: ranking dos mais caros, custo por hora/km
- **[ENTERPRISE]** Abrir inteligência operacional: score de risco, recomendações
- Mostrar equipamento CRÍTICO com recomendação de preventiva
- **[ENTERPRISE]** Abrir Frota × Agricultura: custo por safra e por talhão

---

**Bloco 6 — Upgrade e fechamento (3 min)**  
- Fazer login com conta BÁSICO, tentar acessar "Consumo"
- Mostrar o `TierUpgradeCard` com CTA claro
- Comparar os planos na tela de assinatura
- Fechar com a pergunta: *"Qual é o custo de não saber isso hoje?"*

---

## 10. Status Atual do Módulo

**Versão:** Frota-11.1  
**Resultado da validação:** `APROVADO COM RESSALVAS`

### Funcionalidades validadas e em produção

| Funcionalidade | Status |
|---|---|
| Cadastro de equipamentos | ✅ Aprovado |
| Dashboard essencial (BÁSICO) | ✅ Aprovado |
| Detalhe do equipamento | ✅ Aprovado |
| Ordens de Serviço (abertura, itens, fechamento) | ✅ Aprovado |
| Manutenção preventiva (planos + geração de OS) | ✅ Aprovado |
| Disponibilidade operacional (bloqueio/liberação) | ✅ Aprovado |
| Jornadas de uso (abertura, fechamento, atualização de horímetro) | ✅ Aprovado |
| Análise de custos por equipamento | ✅ Aprovado |
| Análise de consumo e eficiência | ✅ Aprovado |
| Inteligência operacional (score de risco) | ✅ Aprovado |
| Frota × Agricultura (custo por safra/talhão/operação) | ✅ Aprovado |
| Proteção por plano (BÁSICO / PROFISSIONAL / ENTERPRISE) | ✅ Aprovado |
| Isolamento multi-tenant | ✅ Aprovado |
| CTA de upgrade para funcionalidades bloqueadas | ✅ Aprovado |

### Ressalvas abertas

| Item | Gravidade |
|---|---|
| Abastecimento falha se produto `DIESEL` não existe no Estoque do tenant | Alta (setup dependente) |
| Custo total pode estar subestimado em ambientes sem produto de estoque | Média |
| HTTP 422 em bloqueios (esperado: 400) | Baixa |
| Alembic com múltiplos heads pendentes de merge | Técnica |
| Checklist de pré-uso sem fluxo completo no frontend | Média |

### Próximo passo recomendado

Frota-12: documentação funcional e comercial (este documento) — ✅ concluído.  
Frota-13 (sugestão): resolver dependência de produto de estoque para abastecimento e implementar fluxo de checklist de pré-uso.

---

*Documento gerado com base no código implementado de Frota-01 a Frota-11.1. Não descreve funcionalidades planejadas como implementadas.*
