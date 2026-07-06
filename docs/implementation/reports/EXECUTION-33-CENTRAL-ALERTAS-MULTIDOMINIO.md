# EXECUTION-33 — Central de Alertas Operacionais Multi-Domínio

## Resumo executivo

O AgroSaaS já possui sinais de alerta distribuídos em quatro frentes: Financeiro, Agricultura, Pecuária e Operacional/Campo. Hoje esses sinais aparecem em contratos e services separados, com diferentes níveis de maturidade:

- Financeiro já tem alertas oficiais de vencimento, atraso e saldo negativo.
- Agricultura já emite alertas de checklist, safra parada, fenologia vencida e governança operacional.
- Pecuária já consolida manejo pendente, vacinação pendente, custo sanitário e indicadores de lote.
- Operacional/Campo já expõe atrasos, invalidações, erros de sync e disponibilidade/frota com risco.

A recomendação arquitetural é criar uma **Central de Alertas Operacionais Multi-Domínio híbrida**:

1. materializar alertas relevantes com status e histórico;
2. continuar permitindo leitura on-the-fly para dashboards e copiloto;
3. usar uma taxonomia única para severidade, domínio e status;
4. preservar rastreabilidade do `tenant_id` e da origem do sinal;
5. evitar que o Dashboard Geral ou o Copiloto recalcularem regras de cada domínio.

---

## 1. Inventário de alertas existentes

### 1.1 Financeiro

Fontes atuais:

- [services/api/financeiro/services/dashboard_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/dashboard_service.py)
- [services/api/financeiro/schemas/relatorio_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/relatorio_schema.py)
- [services/api/financeiro/services/alerta_inteligente_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/alerta_inteligente_service.py)
- [services/api/financeiro/services/resumo_diario_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/resumo_diario_service.py)
- [services/api/financeiro/routers/lancamentos.py](/opt/lampp/htdocs/farm/services/api/financeiro/routers/lancamentos.py)

Alertas e sinais já existentes:

- contas a pagar vencidas
- contas a receber vencidas
- despesas vencendo em 7 dias
- saldo do mês negativo
- alerta inteligente de baixa rentabilidade
- alerta inteligente de desvio de planejamento
- alerta inteligente de eficiência em risco
- alerta inteligente de estresse financeiro
- predição de risco financeiro
- resumo diário com top 3 alertas
- plano de ação financeiro por safra
- recomendações financeiras por safra

Observação:

- `DashboardService` já é o melhor contrato oficial de leitura geral.
- `AlertaInteligenteService` e `ResumoDiarioService` são úteis, mas ainda são safra-first e dependem de IA/estresse/planejamento.

### 1.2 Agricultura

Fontes atuais:

- [services/api/agricola/dashboard/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dashboard/service.py)
- [services/api/agricola/dashboard/router.py](/opt/lampp/htdocs/farm/services/api/agricola/dashboard/router.py)
- [services/api/agricola/alertas/service.py](/opt/lampp/htdocs/farm/services/api/agricola/alertas/service.py)
- [services/api/agricola/recomendacoes/service.py](/opt/lampp/htdocs/farm/services/api/agricola/recomendacoes/service.py)

Alertas e sinais já existentes:

- checklist obrigatório pendente
- safra parada na mesma fase
- safra em desenvolvimento sem registro fenológico recente
- inconsistências de governança operacional
- inconsistências de reconciliação econômica
- alertas NDE
- alertas de checklist no dashboard agrícola
- fenologia atual por safra
- recomendações operacionais e econômicas por safra

Observação:

- `DashboardAgricolaService` já consolida `alertas_checklist` e `alertas_nde`.
- `AlertasAgricolasService` já atua como motor de governança, mas ainda gera notificações focadas em safra.

### 1.3 Pecuária

Fontes atuais:

- [services/api/pecuaria/services/dashboard_resumo_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/dashboard_resumo_service.py)
- [services/api/pecuaria/services/lote_indicadores_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/lote_indicadores_service.py)
- [services/api/pecuaria/services/lote_resumo_sanitario_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/lote_resumo_sanitario_service.py)
- [services/api/pecuaria/routers/campo_sync.py](/opt/lampp/htdocs/farm/services/api/pecuaria/routers/campo_sync.py)
- [services/api/pecuaria/routers/dashboard.py](/opt/lampp/htdocs/farm/services/api/pecuaria/routers/dashboard.py)

Alertas e sinais já existentes:

- manejos pendentes
- vacinações pendentes
- custo sanitário acumulado
- última pesagem por lote
- GMD médio por lote
- sincronização de tarefas com `status_processamento`
- mensagens de erro por tarefa sincronizada
- tarefas pecuárias sem status de processamento
- tarefas pecuárias aguardando campo

Observação:

- `PecuariaDashboardResumoService` já agrega manejos, vacinações e custo sanitário no nível de fazenda/tenant.
- `LoteIndicadoresService` já fornece `ultima_pesagem` e `gmd_medio_kg_dia`, mas isso ainda é detalhe de lote.
- `campo_sync` já expõe erro de processamento e status por tarefa.

### 1.4 Operacional / Campo

Fontes atuais:

- [services/api/operacional/services/dashboard_resumo_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/dashboard_resumo_service.py)
- [services/api/operacional/services/frota_dashboard_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_dashboard_service.py)
- [services/api/operacional/services/frota_inteligencia_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/frota_inteligencia_service.py)
- [services/api/campo/service.py](/opt/lampp/htdocs/farm/services/api/campo/service.py)
- [services/api/campo/models.py](/opt/lampp/htdocs/farm/services/api/campo/models.py)
- [services/api/campo/router.py](/opt/lampp/htdocs/farm/services/api/campo/router.py)

Alertas e sinais já existentes:

- tarefas pendentes
- tarefas em execução
- tarefas atrasadas
- tarefas concluídas
- tarefas invalidadas
- tarefas com `status_execucao` inválido para cancelamento/fechamento
- dispositivos com `last_sync_at`
- dispositivos ativados/revogados
- equipamentos com manutenção vencida
- equipamentos com documento vencido
- equipamentos com custo acima da média
- equipamentos sem abastecimento recente
- equipamentos com checklist pendente ou não conforme
- equipamentos com risco de parada
- OS aberta há muito tempo

Observação:

- `DashboardResumoOperacionalService` já fornece o tronco transversal ideal para o dashboard geral.
- `campo.service.py` e `campo.models.py` mostram que já existe base para detectar sincronização, status e invalidação.
- `frota_dashboard_service` e `frota_inteligencia_service` ampliam o escopo operacional, mas são mais adequados como especialização de frota do que como núcleo do alerta oficial.

---

## 2. Modelo oficial proposto

### 2.1 Taxonomia recomendada

```ts
type AlertSeverity = "INFO" | "WARNING" | "DANGER" | "CRITICAL";

type AlertDomain = "FINANCEIRO" | "AGRICULTURA" | "PECUARIA" | "OPERACIONAL";

type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED" | "DISMISSED";
```

### 2.2 Nomeclatura

Recomendação:

- manter severidade e domínio em caixa alta;
- manter `status` em caixa alta;
- usar inglês para o código oficial;
- usar mensagens em português na UI.

Justificativa:

- o código-base já usa muitos estados de máquina em caixa alta (`PENDENTE`, `CONCLUIDA`, `INVALIDADA`, `CRITICO`, `ALERTA`);
- isso reduz variação e simplifica integrações multi-domínio;
- evita misturar termos de negócio com termos técnicos.

### 2.3 Contrato oficial

```ts
type OperationalAlert = {
  id: string;
  tenant_id: string;
  unidade_produtiva_id?: string;
  domain: AlertDomain;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message: string;
  source_type: string;
  source_id?: string;
  metric_name?: string;
  metric_value?: number;
  threshold?: number;
  detected_at: string;
  expires_at?: string;
  action_label?: string;
  action_url?: string;
};
```

### 2.4 O que deve ser obrigatório

- `id`
- `tenant_id`
- `domain`
- `severity`
- `status`
- `title`
- `message`
- `source_type`
- `detected_at`

Motivo:

- esses campos são o mínimo para exibir, agrupar, auditar e ordenar alertas.

### 2.5 O que deve ser opcional

- `unidade_produtiva_id`
- `source_id`
- `metric_name`
- `metric_value`
- `threshold`
- `expires_at`
- `action_label`
- `action_url`

Motivo:

- alguns alertas são agregados de tenant inteiro;
- outros apontam para um item específico;
- nem todo alerta tem threshold explícito;
- nem todo alerta precisa de CTA.

### 2.6 Como evitar duplicidade

Recomendação:

- adicionar uma chave interna determinística `dedupe_key` na camada de persistência;
- gerar a chave com base em:
  - `tenant_id`
  - `domain`
  - `source_type`
  - `source_id`
  - `metric_name`
  - janela temporal
  - `unidade_produtiva_id` quando aplicável

Exemplo de chave:

- `tenant_id + domain + source_type + source_id + metric_name + day_bucket`

Também recomendado:

- índice único parcial em `tenant_id + dedupe_key + status` ou `tenant_id + dedupe_key + detected_at_bucket`;
- expiração automática para alertas transitórios;
- atualização do mesmo alerta em vez de criar duplicatas idênticas.

### 2.7 Como rastrear origem

Recomendação:

- `source_type` identifica o módulo/origem;
- `source_id` identifica o objeto raiz do alerta;
- `metric_name` identifica o indicador que disparou;
- `metric_value` e `threshold` guardam o contexto numérico;
- opcionalmente manter `payload_snapshot` interno para auditoria.

### 2.8 Como permitir drill-down

Recomendação:

- `action_url` deve apontar para a tela de detalhe ou lista filtrada;
- `action_label` deve ser texto seguro, nunca execução automática;
- o backend pode expor `source_type` + `source_id` para o frontend montar a navegação;
- o Copiloto pode usar os campos acima para explicar o alerta e sugerir o próximo passo.

---

## 3. Estratégia de persistência recomendada

### Recomendação: híbrida

Motivo:

- o projeto já possui alertas on-the-fly úteis para dashboards e briefs;
- o caso de uso da central pede histórico, status e possibilidade de acknowledge/dismiss;
- materializar tudo simplifica auditoria e evita reprocessamento caro;
- gerar tudo on-the-fly impede histórico consistente e status humano.

### Modelo híbrido sugerido

1. fontes de domínio continuam gerando sinais determinísticos;
2. um agregador materializa apenas alertas relevantes em uma tabela central;
3. alertas resolvidos/dispensados permanecem históricos;
4. leituras do dashboard geral usam a tabela central, não os services profundos;
5. o copiloto pode consultar tanto a tabela central quanto os resumos agregados.

### Vantagens

- histórico
- acknowledge
- dismiss
- resolução
- auditoria
- deduplicação
- drill-down estável

### Desvantagens

- precisa motor de materialização
- precisa expiração
- exige política de recalculação

### Conclusão

`C` puro on-the-fly é insuficiente.
`A` puro materializado é rígido demais.
`B` híbrido é o melhor equilíbrio para o AgroSaaS.

---

## 4. Fontes MVP

### 4.1 MVP agora

#### Operacional

- tarefa atrasada
- erro de sync em tarefa pecuária
- tarefa inválida
- dispositivo sem sincronização recente

Base atual:

- [services/api/operacional/services/dashboard_resumo_service.py](/opt/lampp/htdocs/farm/services/api/operacional/services/dashboard_resumo_service.py)
- [services/api/pecuaria/routers/campo_sync.py](/opt/lampp/htdocs/farm/services/api/pecuaria/routers/campo_sync.py)
- [services/api/campo/service.py](/opt/lampp/htdocs/farm/services/api/campo/service.py)
- [services/api/campo/models.py](/opt/lampp/htdocs/farm/services/api/campo/models.py)

#### Pecuária

- lote sem pesagem recente
- vacinação pendente
- custo sanitário alto

Base atual:

- [services/api/pecuaria/services/dashboard_resumo_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/dashboard_resumo_service.py)
- [services/api/pecuaria/services/lote_indicadores_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/lote_indicadores_service.py)
- [services/api/pecuaria/services/lote_resumo_sanitario_service.py](/opt/lampp/htdocs/farm/services/api/pecuaria/services/lote_resumo_sanitario_service.py)

#### Agricultura

- checklist pendente
- safra parada
- NDE atingido
- fenologia vencida

Base atual:

- [services/api/agricola/dashboard/service.py](/opt/lampp/htdocs/farm/services/api/agricola/dashboard/service.py)
- [services/api/agricola/alertas/service.py](/opt/lampp/htdocs/farm/services/api/agricola/alertas/service.py)

#### Financeiro

- vencimento próximo
- saldo negativo
- contas vencidas

Base atual:

- [services/api/financeiro/services/dashboard_service.py](/opt/lampp/htdocs/farm/services/api/financeiro/services/dashboard_service.py)
- [services/api/financeiro/schemas/relatorio_schema.py](/opt/lampp/htdocs/farm/services/api/financeiro/schemas/relatorio_schema.py)

### 4.2 MVP depois

- GMD baixo
- equipamento com risco de parada
- equipamento com custo acima da média
- OS aberta há muito tempo
- alerta financeiro refinado por IA
- plano de ação financeiro de safra
- recomendações financeiras geradas por IA

Motivo:

- esses sinais são válidos, mas exigem calibragem adicional, thresholds mais estáveis ou reintroduzem safra/IA como centro da experiência.

### 4.3 Não recomendado agora

- execução automática de ações
- qualquer rota de aplicação de recomendação sem confirmação humana
- central baseada em IA generativa como fonte primária
- duplicar no dashboard geral o cálculo profundo do módulo agrícola ou pecuário

Motivo:

- o objetivo da central é consolidar atenção operacional, não automatizar decisões.

---

## 5. Integração com o Dashboard Geral

### O que o dashboard deve consumir

- top 3 alertas abertos
- agrupamento por domínio
- severidade máxima por domínio
- contagem por domínio
- alertas com `status = OPEN`

### O que o dashboard não deve fazer

- recalcular regras por domínio
- buscar múltiplos services profundos em cascata
- executar ações automáticas
- mostrar backlog inteiro de alertas

### Formato ideal de consumo

O Dashboard Geral deveria receber um payload agregado com:

- `alertas_top`
- `contagem_por_dominio`
- `severidade_maxima`
- `dominio_mais_critico`
- `ultimo_alerta_detectado`

### UX recomendada

- exibir o bloco de alertas abaixo do bloco Operacional ou ao lado do Copiloto;
- manter no máximo 3 alertas em destaque;
- usar o restante apenas como agregados e badges;
- se não houver alertas, mostrar estado vazio curto e neutro.

---

## 6. Integração com o Copiloto IA

### Regra de uso

- o Copiloto pode explicar alerta;
- o Copiloto pode sugerir ação;
- o Copiloto pode gerar rascunho;
- o Copiloto não pode executar sem confirmação humana.

### Exemplo de comportamento

- `Este lote está há 60 dias sem pesagem.`
- `Deseja gerar um rascunho de pesagem?`
- `Há 3 tarefas atrasadas no Campo.`
- `O saldo do mês está negativo.`

### Como o Copiloto deve consumir a central

- ler `title`, `message`, `severity`, `domain`, `source_type` e `metric_value`;
- usar `action_label` e `action_url` apenas como saída segura;
- não inferir ações destrutivas;
- não acionar automações diretamente;
- preferir explicação contextual ao invés de comando.

### Benefício

- o Copiloto passa a responder:
  - `O que merece atenção na fazenda?`
  - e não apenas `o que está acontecendo na safra?`

---

## 7. Riscos

- duplicação de sinal entre dashboards especializados e a central oficial
- alerta obsoleto se a expiração não for bem definida
- excesso de alertas de baixa relevância gerando ruído
- contrato muito amplo virando “catch-all”
- regressão para safra-first se os sinais financeiros/agrícolas de IA voltarem a dominar
- consulta múltipla sem cache causando custo desnecessário
- inconsistência entre leitura do dashboard e status humano de acknowledge/dismiss
- risco de misturar alertas de domínio com alertas de execução automática

Mitigações:

- dedupe_key determinística
- TTL / expires_at
- severidade bem calibrada
- origem rastreável
- status humano explícito
- revisão de thresholds por domínio
- cache curto na camada de leitura

---

## 8. Roadmap recomendado

### EXECUTION-33A — Contrato e backend de alertas MVP

Objetivo:

- criar o contrato oficial;
- persistir alertas relevantes;
- implementar deduplicação e status;
- expor leitura agregada por domínio.

### EXECUTION-33B — Dashboard Geral consumindo alertas

Objetivo:

- mostrar top 3 alertas;
- agrupar por domínio;
- exibir severidade máxima;
- manter o dashboard geral leve.

### EXECUTION-33C — Copiloto explicando alertas

Objetivo:

- fazer o Copiloto ler a central;
- explicar alertas;
- sugerir próximos passos;
- sem executar ações.

### EXECUTION-33D — Acknowledge/dismiss e histórico

Objetivo:

- permitir reconhecimento humano;
- encerrar alertas;
- manter histórico e auditoria;
- evitar reaparecimento desnecessário.

---

## 9. Recomendação final

A melhor modelagem para o AgroSaaS é:

1. **central oficial de alertas materializada** para os casos persistentes e acionáveis;
2. **sinais on-the-fly** apenas como fontes internas de cálculo;
3. **dashboards consumidores** com leitura agregada;
4. **Copiloto consultando a central**, não recalculando o mundo;
5. **status humano e rastreabilidade** como requisitos de primeira classe.

Isso preserva:

- multi-tenant
- RLS
- multi-domínio
- auditabilidade
- clareza de UX
- segurança operacional

E evita:

- reintroduzir safra-first como centro da experiência;
- espalhar alertas por módulos sem uma linguagem comum;
- transformar o dashboard em motor de execução automática.
