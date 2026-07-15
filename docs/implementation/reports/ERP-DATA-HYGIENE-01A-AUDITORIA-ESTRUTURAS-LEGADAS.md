# Auditoria de Estruturas Legadas ERP - ERP-DATA-HYGIENE-01A

## 1. Resumo Executivo
A estrutura que gerou dúvida no relatório anterior foi a `tenant_integracoes`. Foi atestado inequivocamente que a tabela `tenant_integracoes` é a **CANÔNICA** que orquestra a relação multitenant multiprovider. 
A recomendação prévia de DROP foi um erro de nomenclatura do relatório.
A estrutura que é *realmente* candidata a saneamento futuro é a tabela específica do provider Sankhya, particularmente a `sankhya_config` e as tabelas auxiliares de staging (ex: `sankhya_pessoas`, `sankhya_nfe`), que mantêm redundâncias (cache local de dados ERP).
Não existe risco imediato, contanto que não se execute o DROP recomendado erroneamente.

## 2. Arquitetura física e lógica encontrada
O mapeamento aponta a seguinte organização física e lógica de dependências:
- **TenantIntegracao (`tenant_integracoes`)**: Canonical table de relacionamento de integração. O Router ERP e o Readiness dependem exclusivamente dela.
- **MarketplaceIntegracao (`marketplace_integracoes`)**: Canonical table de catálogo do provider.
- **IntegrationCredential (`integration_credentials`)**: Armazena as credenciais canonicamente.
- **SankhyaConfig (`sankhya_config`)**: Tabela técnica e legada que armazena informações provider-specific de conexão, credenciais e parâmetros.
- **SankhyaSyncLog (`sankhya_sync_logs`)**: Tabela de log das requisições do provider.
- **Staging tables (`sankhya_pessoas`, `sankhya_produtos`, `sankhya_nfe`, `sankhya_tabelas`)**: Tabelas provider-specific usadas para conciliar cache entre a base local e o ERP remoto.

## 3. Análise de `TenantIntegracao`
A `TenantIntegracao` (`tenant_integracoes`) desempenha papel central e absoluto na arquitetura multitenant:
1. **É a tabela física canônica?** SIM.
2. **Existe homônima ou anterior?** Não.
3. **Existe tabela duplicada com função semelhante?** Não.
4. **Existe uma tabela antiga que deveria ter sido citada no relatório?** SIM. A `sankhya_config` e correlatas.
5. **Remoção quebraria o fluxo oficial?** SIM, resultaria em colapso total do Gateway ERP (Readiness, Lifecycle e Router cairiam imediatamente).
6. **Outros módulos dependem?** Sim, todo o controle de Lifecycle (associações) e Sync dependem dessa canonicidade.

## 4. Estruturas Sankhya
- `SankhyaConfig`: PROVIDER-SPECIFIC ATIVA — MANTER. Ela ainda dita a realidade do sync local no `sankhya_runtime.py`, e seus dados estão sendo mapeados via fachada read-only pela classe `SankhyaCanonicalAdapter`.
- `SankhyaSyncLog`: PROVIDER-SPECIFIC ATIVA — MANTER. Mantém logs específicos cujos registros são transformados em `IntegrationJob` sob demanda.
- `sankhya_tabelas` e demais: PROVIDER-SPECIFIC ATIVA — MANTER. São usadas como camada de staging para as operações do provedor.

## 5. Origem da recomendação incorreta
O relatório ERP-CORE-REPAIR-01C mencionou o `DROP TABLE tenant_integracoes` devido a um erro de designação textual gerado durante a redação do artefato pela IA. A frase *"após a totalidade dos SankhyaConfigs transitarem para os records da TenantIntegracao"* evidencia claramente que a origem do DROP deveria ser o `sankhya_config`, pois ele é a tabela velha sendo substituída pelo receptor canônico (`TenantIntegracao`).

## 6. Matriz de classificação

| Estrutura | Tipo | Responsabilidade atual | Uso em runtime | Canônica | Provider-specific | Legada | Pode remover agora |
| --------- | ---- | ---------------------- | -------------- | -------- | ----------------- | ------ | ------------------ |
| `tenant_integracoes` | Tabela / Model | Vínculo Tenant -> Provider | Sim (Router, Readiness) | Sim | Não | Não | NÃO |
| `marketplace_integracoes`| Tabela / Model | Definição do Provider | Sim | Sim | Não | Não | NÃO |
| `integration_credentials`| Tabela / Model | Segredos Criptografados | Sim | Sim | Não | Não | NÃO |
| `sankhya_config` | Tabela / Model | Configurações Técnicas | Sim (SankhyaSync) | Não | Sim | Sim (Em Migração) | NÃO |
| `sankhya_sync_logs` | Tabela / Model | Logs e Jobs de Sync | Sim (SankhyaSync) | Não | Sim | Sim | NÃO |
| `sankhya_pessoas` (etc) | Tabela / Model | Staging/Cache de Sync | Sim (SankhyaSync) | Não | Sim | Sim | NÃO |
| `legacy_reconciliation.py` | Script (Helper) | Sync SankhyaConfig <-> TenantIntegracao | Sim (Background) | Não | Sim | Sim | NÃO |

## 7. Banco físico
- As tabelas existem ativamente na base (Alembic `fase3_sankhya.py`). 
- As restrições e relacionamentos mantêm consistência referencial (`config_id` apontando para `sankhya_config.id`).
- Todas as estruturas foram classificadas como operacionais (seja no framework canônico ou nas delegações provider-specific). Nenhuma deve sofrer purgação física neste instante.

## 8. Riscos
- **Remoção Indevida:** A remoção de `tenant_integracoes` implodiria a espinha dorsal de Gateway/Multiprovider.
- **Manutenção Eterna:** Manter o `sankhya_config` eternamente causará uma dupla fonte de verdade no banco, forçando o worker `legacy_reconciliation.py` a rodar perpetuamente e aumentando complexidade.

## 9. Plano de saneamento (Recomendação Futura)
- **ERP-DATA-HYGIENE-01B** — Alteração estrutural no `SankhyaSyncService` e services correlatos para passar a consumir nativamente `TenantIntegracao` e `IntegrationCredential`, abandonando a dependência de `SankhyaConfig`.
- **ERP-DATA-HYGIENE-01C** — Remoção do `legacy_reconciliation.py` (código morto).
- **ERP-DATA-HYGIENE-01D** — Migration de limpeza física (`DROP TABLE sankhya_config`).

*(Fases a serem orquestradas futuramente com autorização explícita)*.

## 10. Errata recomendada
Substituir a seção 7 ("Recomendações") do relatório `ERP-CORE-REPAIR-01C-AUDITORIA-FINAL-PLUGABILIDADE-MULTIPROVIDER.md` pelo seguinte:

> **Errata (Ações Adicionais):** A longo prazo, aconselha-se planejar a depreciação real (DROP TABLE) da tabela específica do provedor **`sankhya_config`** (e tabelas de staging vinculadas) e o descarte do helper `legacy_reconciliation.py`, após a totalidade dos dados operacionais e credenciais transitarem efetivamente para uso ativo via `TenantIntegracao` e `IntegrationCredential` no runtime Sankhya. Como se trata apenas de limpeza técnica (eliminação da dupla fonte de verdade), esta evolução isolada não afetará a arquitetura multitenant agnóstica já consolidada.

## 11. Veredicto
**GO COM RESSALVAS** 
A conclusão primária (*"A) tenant_integracoes é canônica e a recomendação de DROP foi incorreta"*) foi plenamente atestada. O sistema é estável, e a ressalva se dá apenas pela presença de dupla fonte de verdade (`SankhyaConfig`) que está tolerada, mas exige um roadmap seguro de higiene de dados nas próximas rodadas, sem risco iminente para o negócio atual. O ambiente está seguro para avanço e novas implementações.
