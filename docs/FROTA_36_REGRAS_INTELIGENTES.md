# FROTA-36: Regras Inteligentes e Automação Controlada

## Status: Concluído ✅

### 1. Visão Geral
Implementamos o motor de "Regras Inteligentes" para o módulo Frota. Este sistema permite que o gestor configure automações que reagem a desvios operacionais e financeiros detectados pela inteligência do sistema, reduzindo o tempo de resposta sem abrir mão do controle gerencial.

### 2. Conceitos Chave

#### A. Regras Inteligentes
Configurações parametrizáveis por Tenant que definem:
- **Ativação**: Se a automação está ligada ou desligada.
- **Threshold (Limite)**: Qual a tolerância para o desvio (ex: 30% acima da média).
- **Modo de Execução**: 
  - **Assistida**: O sistema sugere a ação (Magic Action) e aguarda confirmação.
  - **Automática**: O sistema executa a ação e notifica o gestor.
- **Notificação**: Envio de alertas quando uma regra é disparada.

#### B. Logs de Automação (Auditoria)
Toda ação executada pelo motor de automação é registrada com:
- Data e hora.
- Regra disparada.
- Equipamento afetado.
- Status (EXECUTADA, PENDENTE_CONFIRMACAO, FALHA).
- Detalhes do motivo da ação.

### 3. Automações Disponíveis (v1)

1. **OS Automática: Preventiva Vencida**
   - **Gatilho**: Plano de manutenção atinge data ou horímetro de vencimento.
   - **Ação**: Geração automática (ou sugestão) de Ordem de Serviço Preventiva.

2. **Alerta: Custo Operacional Elevado**
   - **Gatilho**: Custo total do equipamento no período supera a média em X%.
   - **Ação**: Notificação crítica ao gestor e sugestão de abertura de OS Corretiva para revisão.

### 4. Endpoints Gerenciais
- `GET /frota/inteligencia/regras`: Lista configurações atuais.
- `PATCH /frota/inteligencia/regras/{id}`: Ajusta limites e ativação.
- `GET /frota/inteligencia/automacoes/logs`: Histórico de auditoria.

### 5. Benefícios
- **Redução de MTTR (Mean Time To Repair)**: Problemas técnicos são encaminhados para a oficina instantaneamente.
- **Consistência Operacional**: Garante que manutenções preventivas não sejam esquecidas por falha humana.
- **Controle Total**: O gestor decide quais regras rodam "no piloto automático" e quais exigem aprovação manual.
