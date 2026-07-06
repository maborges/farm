# PILOT-ERP-02 - Roteiro Prático de Execução Assistida Café + Sankhya

Data: 2026-07-06

## 1. Objetivo

Este roteiro transforma a simulação do piloto café + Sankhya em uma sequência prática para execução assistida.

Base documental:

- [PILOT-ERP-01-SIMULACAO-CAFE-SANKHYA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/PILOT-ERP-01-SIMULACAO-CAFE-SANKHYA.md)

## 2. Regras de uso

- Não criar infraestrutura nova.
- Não implementar novos módulos.
- Não criar sync bidirecional.
- Não criar staging novo.
- Não propor arquitetura nova.
- Usar apenas fluxos já existentes.
- Separar claramente o que é obrigatório, opcional e pós-piloto.

## 3. Papéis e responsáveis

| Papel | Responsabilidade |
| --- | --- |
| Equipe AgroSaaS | Conduzir o roteiro, validar bloqueios, acionar integração e registrar evidências. |
| Administrador do cliente | Aprovar dados, validar cadastros e tomar decisões de go/no-go. |
| Usuários operacionais | Executar tarefas de campo, estoque, financeiro e comercialização. |
| Responsável Sankhya / TI | Apoiar teste de conexão, acesso e conferência de dados do ERP. |

## 4. Pré-requisitos

Obrigatórios:

- tenant ativo;
- usuário owner/admin autenticado;
- onboarding concluído;
- `UnidadeProdutiva` ativa;
- estrutura territorial mínima;
- acesso ao console Sankhya;
- credenciais Sankhya válidas;
- permissão de integração e logs;
- responsável do cliente disponível.

Opcionais:

- Campo PWA ativo no piloto;
- associação P1 para masters adicionais;
- comercialização em uso no cliente;
- contas bancárias e centro de resultado já cadastrados.

Pós-piloto:

- refinamento de masters P1/P2;
- ampliação de comercialização;
- evolução de tipo de operação;
- ajustes avançados de cadastros societários.

## 5. Sequência real de execução

### D-5 - Preparação administrativa

Responsáveis: Equipe AgroSaaS + administrador do cliente.

Passos:

1. Confirmar tenant correto.
2. Confirmar usuário owner/admin.
3. Revisar onboarding concluído.
4. Confirmar assinatura e acesso.
5. Verificar disponibilidade do responsável Sankhya.
6. Revisar documentos de escopo do piloto.

Validação:

- tenant ativo;
- acesso administrativo confirmado;
- agenda de execução alinhada.

### D-4 - Estrutura territorial

Responsáveis: Equipe AgroSaaS + administrador do cliente.

Passos:

1. Abrir o Wizard de implantação.
2. Validar `UnidadeProdutiva`.
3. Conferir propriedades e imóveis rurais.
4. Conferir talhões e áreas operacionais.
5. Validar depósito inicial quando houver estoque no escopo.

Validação:

- unidade produtiva ativa;
- fazenda mapeada;
- talhões existentes;
- depósito inicial conferido, se aplicável.

### D-3 - Configuração Sankhya

Responsáveis: Equipe AgroSaaS + responsável Sankhya / TI.

Telas / rotas:

- `/dashboard/settings/integracoes/erp`

Passos:

1. Abrir o console Sankhya.
2. Conferir configuração atual.
3. Validar URL, credenciais e ambiente.
4. Executar teste de conexão.
5. Conferir status, health, jobs e logs.

Validação:

- teste de conexão aprovado;
- ambiente correto;
- console sem erro crítico;
- health coerente.

Critério de no-go:

- falha de autenticação;
- ambiente errado;
- health degradado sem explicação;
- ausência de permissão.

### D-2 - Carga inicial controlada

Responsáveis: Equipe AgroSaaS.

Passos:

1. Executar importação inicial aprovada.
2. Conferir pessoas, produtos, NFe e financeiro.
3. Validar Associação Oficial P0.
4. Listar pendências `PENDING`.
5. Reconhecer quais vínculos precisam de reconciliação manual.

Validação:

- P0 conferido;
- pendências visíveis;
- nenhum vínculo duplicado silencioso;
- dados mínimos importados.

Obrigatório:

- pessoas;
- produtos;
- documentos fiscais relevantes;
- títulos financeiros relevantes.

Opcional:

- masters P1 já disponíveis;
- depósito/local de estoque;
- contas bancárias e carteira;
- centro de custo/resultado.

### D-1 - Reunião de go/no-go

Responsáveis: Equipe AgroSaaS + administrador do cliente.

Passos:

1. Revisar pendências `PENDING`.
2. Reconciliar o que estiver claro.
3. Registrar o que continuará pendente.
4. Conferir estoque inicial.
5. Conferir plano de contas e financeiro mínimo.
6. Validar safra de café e estrutura de talhões.
7. Decidir go/no-go.

Validação:

- bloqueios críticos resolvidos;
- premissas documentadas;
- plano do dia D aprovado.

### D0 - Go-live assistido

Responsáveis: Equipe AgroSaaS + administrador do cliente + usuários operacionais.

Telas / rotas usadas:

- onboarding e dashboard;
- console Sankhya;
- safra de café;
- estoque;
- financeiro;
- rastreabilidade;
- rentabilidade;
- Campo PWA, se aplicável.

Passos:

1. Confirmar estado pronto para operação.
2. Iniciar primeira rotina operacional.
3. Registrar operação agrícola ou entrada de campo.
4. Conferir efeito no estoque.
5. Conferir efeito financeiro, quando aplicável.
6. Conferir rastreabilidade.
7. Verificar alertas e recomendações.

Validação:

- primeira operação registrada;
- trilha de rastreabilidade consistente;
- console Sankhya monitorado;
- logs sem falha crítica.

### D+1 a D+3 - Estabilização inicial

Responsáveis: Equipe AgroSaaS.

Checklist diário:

- revisar jobs Sankhya;
- revisar logs;
- revisar health;
- revisar pendências PENDING;
- revisar estoque;
- revisar financeiro;
- revisar rastreabilidade;
- revisar alertas.

Passos:

1. Validar novos registros importados.
2. Reconciliar pendências novas.
3. Verificar se houve duplicidade.
4. Ajustar premissas operacionais, se necessário.

### D+4 a D+7 - Operação assistida

Responsáveis: Equipe AgroSaaS + usuários operacionais.

Checklist diário:

- sincronizações;
- health;
- pendências;
- estoque;
- compras;
- financeiro;
- comercialização;
- Campo PWA, se usado.

Passos:

1. Executar rotinas diárias normais.
2. Monitorar a primeira semana de uso real.
3. Registrar incidentes e correções.
4. Preparar consolidação de estabilização.

## 6. Sequência de cliques e ações

1. Entrar no sistema.
2. Selecionar o tenant.
3. Concluir onboarding, se necessário.
4. Abrir o Wizard.
5. Validar unidade produtiva.
6. Ir para Configurações > Integrações > ERP Sankhya.
7. Executar teste de conexão.
8. Rodar importação inicial.
9. Abrir a lista de pendências.
10. Filtrar por provider, entidade e ambiente.
11. Reconciliar manualmente o que tiver local definido.
12. Abrir safra de café.
13. Conferir estoque e financeiro.
14. Validar rastreabilidade e rentabilidade.
15. Ativar Campo PWA, se fizer parte do escopo.

## 7. Plano de contingência

| Situação | Ação |
| --- | --- |
| Falha de conexão Sankhya | Parar a importação e revisar credenciais, ambiente e gateway. |
| Pendência crítica sem vínculo claro | Deixar como `PENDING` e registrar justificativa. |
| Duplicidade identificada | Suspender a promoção do vínculo e abrir reconciliação manual. |
| Estoque inicial incoerente | Bloquear avanço operacional até corrigir. |
| Divergência financeira relevante | Validar com o cliente antes de continuar o go-live. |
| Campo PWA com falha de sync | Manter operação no backoffice e regularizar depois. |

## 8. Critérios de go/no-go

### Go

- tenant ativo;
- onboarding concluído;
- unidade produtiva válida;
- conexão Sankhya aprovada;
- importação inicial controlada;
- associação oficial P0 conferida;
- pendências críticas resolvidas;
- estoque e financeiro mínimos coerentes;
- responsável do cliente presente.

### No-go

- conexão falhou;
- ambiente errado;
- unidade produtiva ausente;
- pendências críticas sem solução;
- estoque inicial não validado;
- responsável indisponível;
- risco de duplicidade sem reconciliação.

## 9. Evidências que devem ser registradas

- captura do console Sankhya com teste de conexão;
- lista de pendências `PENDING`;
- registro das reconciliações manuais;
- evidência do go/no-go;
- evidência da primeira operação;
- evidência de estoque e financeiro, quando aplicável;
- evidência de rastreabilidade e rentabilidade;
- incidentes do período D0 a D+7.

## 10. Conclusão

O roteiro acima executa o piloto com o que já existe no AgroSaaS.

Ele não cria novo caminho, não adiciona infraestrutura e não amplia o escopo técnico. Apenas organiza a execução assistida em uma sequência operacional clara, separando o que é obrigatório, opcional e pós-piloto.

