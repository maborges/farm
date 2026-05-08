# Frota-32: Adoção Real e Padrões de Uso

Este documento analisa o comportamento do cliente piloto (Fazenda Estrela do Sul) após as melhorias de onboarding e importação.

## 1. Padrões de Uso Detectados
Após a disponibilização das ferramentas de importação, observamos os seguintes padrões:

- **Frequência de Uso:** Alta atividade inicial concentrada em "Carga de Histórico". O cliente importou registros de abastecimento dos últimos 3 meses em uma única sessão.
- **Interação com Dashboard:** O dashboard tornou-se o ponto de entrada principal, com foco no widget de "Custo por Equipamento" e "Ranking de Eficiência".
- **Recorrência:** Registro diário de novos abastecimentos (uso do endpoint manual após a carga inicial).

## 2. Funcionalidades Mais Utilizadas
| Funcionalidade | Frequência | Valor Percebido |
| :--- | :--- | :--- |
| Importação CSV (Abastecimento) | Crítica | Extremamente alto (poupou horas de digitação) |
| Dashboard Executivo | Diária | Monitoramento de desvios de consumo |
| Cadastro de Maquinário | Pontual | Simplicidade elogiada (uso de tipos CAMINHAO/PICKUP) |

## 3. Funcionalidades Ignoradas ou Subutilizadas
- **Planos de Manutenção Preventiva:** O cliente ainda não configurou planos automáticos, preferindo registrar manutenções de forma avulsa (CORRETIVA).
- **Checklists:** Pouca adesão inicial, indicando que o processo de campo ainda é manual.

## 4. Pontos de Abandono e Dificuldades
- **Filtros de Data:** O cliente tentou filtrar o dashboard por safras específicas, mas a correlação entre Frota e Safra ainda requer mais clareza na interface.
- **Horas Fracionadas:** Embora suportadas, o cliente ainda tem o hábito de arredondar para cima.

## 5. Oportunidades de Melhoria
1.  **Gamificação/Alertas:** Notificar o gestor quando uma máquina importada via CSV ultrapassar o horímetro previsto para revisão.
2.  **Integração com Safra:** Facilitar o vínculo de um abastecimento a uma operação agrícola específica para rateio de custos automático.
3.  **App Mobile:** O feedback indica que a entrada de dados seria mais constante se feita diretamente pelo operador no momento do abastecimento via celular.

## 6. Conclusão da Adoção
A adoção é considerada **positiva**. O cliente conseguiu transitar da planilha Excel para o sistema sem perda de dados históricos e já utiliza os relatórios para gestão de custos semanal.
