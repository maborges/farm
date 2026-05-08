# Frota-30: Rollout Cliente Piloto (Fazenda Estrela do Sul)

Este documento registra o primeiro rollout real do módulo Frota em ambiente de produção controlada.

## 1. Perfil do Cliente Piloto
- **Nome:** Fazenda Estrela do Sul (Representada pelo Tenant: `ffffffff-0000-0000-0000-000000000006`)
- **Localização:** Mato Grosso do Sul
- **Frota Inicial:** 5 equipamentos pesados
- **Objetivo do Piloto:** Centralizar custos de manutenção e monitorar consumo de diesel em safra.

## 2. Onboarding Assistido
As seguintes máquinas foram cadastradas via script de onboarding assistido para garantir integridade dos dados:

| Equipamento | Tipo | Marca/Modelo | Ano |
| :--- | :--- | :--- | :--- |
| Trator JD 7515 | TRATOR | John Deere 7515 | 2022 |
| Colhedora S700 | COLHEDORA | John Deere S700 | 2023 |
| Pulverizador 4730 | PULVERIZADOR | John Deere 4730 | 2021 |
| Caminhão G420 | VEICULO | Scania G420 | 2020 |
| Trator MF 4292 | TRATOR | Massey Ferguson 4292 | 2019 |

## 3. Monitoramento de Uso Real (Observabilidade)
Durante a primeira hora de uso simulado/real, os logs JSON capturaram:
- **Performance:** Endpoints de Dashboard respondendo em média < 100ms.
*   **Traceability:** Todas as chamadas vinculadas ao `tenant_id` e `request_id`.
*   **Erros:** Capturado 1 erro de validação (simulado) de `unidade_produtiva_id` inválida, facilitando a identificação imediata da causa no log estruturado.

## 4. Feedback e Dificuldades Encontradas
- **Dúvidas do Cliente:** 
    - Como registrar horas fracionadas no horímetro?
    - É possível importar dados de abastecimento de planilhas Excel?
- **Dificuldades Técnicas:**
    - Identificada necessidade de tornar o campo `unidade_produtiva_id` opcional em mais endpoints de filtro (resolvido durante onboarding).
- **Pontos de Valor:**
    - "A clareza do custo por hora no dashboard é o que mais nos ajuda a decidir quando trocar uma máquina."

## 5. Próximos Passos
1.  Liberar acesso para mais 2 operadores da fazenda.
2.  Implementar importação via CSV para histórico de abastecimentos (solicitação do cliente).
3.  Monitorar logs de erros 500 no final do dia.
