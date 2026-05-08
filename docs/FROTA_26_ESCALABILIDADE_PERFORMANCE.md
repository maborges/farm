# Frota-26: Escalabilidade e Performance do Módulo Frota

## 1. Resumo da Refatoração
Para suportar o crescimento do AgroSaaS com múltiplos clientes e grandes volumes de dados operacionais, o módulo Frota passou por uma refatoração estrutural focada em **SQL-First Aggregation**.

### Problemas Identificados (Gargalos):
*   **Processamento em Memória:** O Dashboard e Relatórios de Custos carregavam milhares de objetos SQLAlchemy em memória Python para realizar somas e filtros, causando picos de CPU e RAM.
*   **Falta de Índices Compostos:** Consultas multi-tenant (`tenant_id`) filtradas por data e equipamento não utilizavam índices otimizados, resultando em *Full Table Scans*.
*   **Inconsistência de Tenant:** Algumas tabelas auxiliares (`planos_manutencao`, `registros_manutencao`) não possuíam `tenant_id` nativo no banco, dificultando o isolamento.

## 2. Implementações Técnicas

### 2.1 Otimização de Queries (SQL Aggregation)
*   **Somas e Contagens:** Migramos cálculos de custo (Combustível, Peças, Mão de Obra) para o PostgreSQL utilizando `func.sum()` e `func.count()`.
*   **Filtro de Data em SQL:** O filtro de período (ex: últimos 30 dias) agora acontece no banco de dados (`WHERE data >= :corte`), reduzindo drasticamente o tráfego de dados.
*   **Window Functions:** Implementamos `ROW_NUMBER() OVER(PARTITION BY equipamento_id ORDER BY data DESC)` para obter o "último abastecimento" de toda a frota em uma única chamada eficiente.

### 2.2 Estrutura de Dados e Índices
Adicionamos os seguintes índices compostos para acelerar o Dashboard Executivo:
*   `ix_frota_abast_tenant_equip_data`: Otimiza histórico de consumo.
*   `ix_frota_os_tenant_equip_status`: Acelera contagem de ordens abertas e alertas.
*   `ix_frota_reg_manut_tenant_equip_data`: Otimiza histórico de manutenção avulsa.
*   `ix_frota_jornadas_tenant_equip_data`: Acelera relatórios de uso e eficiência.

### 2.3 Isolamento Multi-tenant
*   Adicionada coluna `tenant_id` em `frota_planos_manutencao` e `frota_registros_manutencao`.
*   Garantido que 100% das queries de agregação incluam o filtro por `tenant_id`.

## 3. Resultados Esperados
*   **Performance:** Redução de >80% no tempo de resposta do Dashboard para frotas com mais de 100 equipamentos.
*   **Memória:** Consumo de RAM constante no Backend, independente do volume de dados do cliente.
*   **Escalabilidade:** Capacidade de suportar 10x mais tenants simultâneos sem upgrade de infraestrutura.

## 4. Próximos Passos (P1/P2)
*   **Paginação (P1):** Implementar `limit/offset` em listagens de histórico de manutenção (AG Grid).
*   **Caching (P2):** Adicionar cache (Redis) para o resumo financeiro do Dashboard (TTL 5 min).
*   **Limpeza (P2):** Política de retenção de dados para telemetria de landing page.
