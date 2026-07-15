# Relatório Final: ERP-CORE-REPAIR-01B

**Fase:** ERP-CORE-REPAIR-01B — Consolidação da Resolução Canônica do Provider ERP e Desativação Controlada do Fallback Sankhya Legado

## 1. Objetivo Concluído
O fluxo da API ERP foi totalmente padronizado em cima da estrutura canônica, o que significa que as requisições de serviço agora seguem rigorosamente o caminho: `Tenant -> TenantIntegracao -> MarketplaceIntegracao -> provider_slug -> Provider Runtime Registry`.
A resolução explícita do fallback legado (`legacy_provider_resolution.py`) e sua inferência acoplada foram permanentemente removidas.

## 2. Ações Executadas
* **Limpeza de Tenant Divergente:**
  * O estado de `tenant-1` que representava `BOTH_DIVERGENT` decorrente de dados dummy/teste, e que impedia o avanço por falha em constraints de credencial e domain event (outbox), foi propriamente purgado. Com isso, `reconcile_legacy_sankhya_integration.py` atestou **0 bloqueados** (100% `BOTH_CONSISTENT`).
* **Desacoplamento do Router ERP:**
  * Removida importação e invocação de `resolve_legacy_sankhya_provider` e a constante `_LEGACY_SANKHYA_SOURCE` de `services/api/integracoes/erp/router.py`.
  * Remoção do wrapper `_apply_legacy_provider_hint` garantindo que o status canônico e nulo venham de forma orgânica.
* **Remoção de Arquivos Mortos:**
  * O script temporário de reconciliação out-of-band `legacy_provider_resolution.py` foi **deletado**.
* **Adaptação e Estabilização dos Testes Unitários:**
  * Em `test_erp_provider_governance.py`: removida a exclusão de `legacy_provider_resolution.py` das listas de permissão.
  * Em `test_erp_provider_contract.py`: removidos os remendos (monkeypatch) em volta da API descontinuada.
  * Em `test_erp_router.py`: removidos mocks da API de fallback.
  * Em `test_erp_bootstrap_tardio.py`: excluído teste antiquado que atestava comportamento de fallback em cenários desconfigurados (não se aplica mais).

## 3. Estado Final e Governança
* O router agora rejeita acesso ERP para tenants sem a devida `TenantIntegracao`, retornando o payload `NOT_CONFIGURED`, o que forçará o Frontend a apresentar o Wizard se tentar operar sem configuração (comportamento desejado e validado).
* Os testes de validação de dependência e arquitetura (`test_erp_provider_governance.py`) estão passando com assertividade total de ausência do termo "Sankhya" dentro de pacotes de core e router.
* A migração para `ERP-CORE-REPAIR-01C` pode prosseguir, focando possivelmente na limpeza final de modelos no banco ou depreciação de outras tabelas se especificado.

*Autor:* Antigravity Agent
*Data:* 2026-07-15
