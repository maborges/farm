# Frota-31: Onboarding Otimizado e Importação de Dados

Este documento detalha as melhorias implementadas para reduzir a fricção no onboarding de novos clientes e acelerar a carga de dados históricos.

## 1. Simplificação do Cadastro de Maquinários
- **Campos Opcionais:** `unidade_produtiva_id` tornou-se opcional no cadastro inicial, permitindo que o cliente cadastre sua frota antes mesmo de configurar todas as fazendas.
- **Novos Tipos Suportados:** Adicionados tipos `CAMINHAO` e `PICKUP` com mapeamento automático para a categoria `VEICULO`.
- **Status "Parado":** Novo status `PARADO` que mapeia automaticamente para `INATIVO` no sistema, facilitando o entendimento do usuário.

## 2. Horímetro com Horas Fracionadas
- O sistema agora suporta explicitamente a entrada de horas fracionadas (ex: `1200.5`) em todos os campos de horímetro, tanto via API quanto via importação CSV.
- A validação aceita separadores decimais `.` e `,` para maior flexibilidade.

## 3. Importação em Massa via CSV
Implementados novos endpoints para carga de dados históricos:

### Abastecimentos
- **Endpoint:** `POST /api/v1/frota/importar/abastecimentos`
- **Template:** [frota_abastecimentos_template.csv](../docs/templates/frota_abastecimentos_template.csv)
- **Campos:** `equipamento_nome`, `data`, `horimetro`, `litros`, `preco_litro`

### Manutenções
- **Endpoint:** `POST /api/v1/frota/importar/manutencoes`
- **Template:** [frota_manutencoes_template.csv](../docs/templates/frota_manutencoes_template.csv)
- **Campos:** `equipamento_nome`, `data`, `tipo`, `descricao`, `custo_total`

## 4. Benefícios do Onboarding Otimizado
1.  **Redução de Tempo:** O cliente piloto pode carregar meses de histórico de abastecimento em segundos.
2.  **Menor Erro Manual:** A busca automática pelo nome do equipamento no CSV evita erros de UUID.
3.  **Adoção Imediata:** O dashboard já exibe métricas financeiras e de consumo logo após a importação, gerando valor imediato (Aha! Moment).

## 5. Próximos Passos
- Implementar interface visual (Frontend) para upload desses arquivos.
- Adicionar suporte a arquivos `.xlsx` (Excel) diretamente.
