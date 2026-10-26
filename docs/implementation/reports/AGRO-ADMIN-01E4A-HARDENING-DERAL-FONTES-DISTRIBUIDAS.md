# AGRO-ADMIN-01E4A — Hardening de Snapshots DERAL, Publicação Distribuída e Fontes Oficiais

**Data de Conclusão:** 24 de Outubro de 2026  
**Responsável Técnico:** DeepFarms Engineering (Antigravity AI Pair Programming)  
**Status:** CONCLUÍDO COM SUCESSO — AUDITORIA E IMPLEMENTAÇÃO RESTRITA  
**Suíte de Regressão:** 21 testes automatizados (100% de aprovação)  
**Checagem Estática Frontend:** `pnpm --filter web exec tsc --noEmit` (0 erros)  

---

## 1. Resumo Executivo

O ciclo **AGRO-ADMIN-01E4A** realizou a auditoria detalhada e o endurecimento (*hardening*) de segurança, integridade e consistência distribuída do subsistema de governança de fontes de mercado e snapshots semanais DERAL/SEAB-PR, corrigindo as lacunas residuais da etapa 01E4.

### Principais Realizações e Garantias Técnicas:
1. **Segregação Estrita de Autenticidade e Proveniência**:
   - O hash SHA-256 agora atesta estritamente a **integridade binária do arquivo** (não-adulteração de bytes), nunca sendo confundido com presunção de autenticidade governamental.
   - Foram segregados quatro estados explícitos: **Integridade Criptográfica**, **Origem Declarada**, **Origem Verificada** (domínios oficiais `*.pr.gov.br`, `*.agricultura.pr.gov.br`, `*.seab.pr.gov.br`) e **Aprovação Administrativa Formal** (`estado_aprovacao = "APROVADO"`).
   - Snapshots sem aprovação formal ou com falha de proveniência são bloqueados sumariamente na tentativa de ativação pública (HTTP 400).
2. **Armazenamento e Auditoria dos Bytes Originais Imutáveis**:
   - Os bytes brutos originais do documento recebido (binário `.xls` ou texto `.json`) são preservados integralmente em Base64 na tabela `ConfiguracaoSaaS`.
   - Novos endpoints de auditoria `/deral/snapshots/{id}/verify-integrity` (que recalcula o SHA-256 a partir dos bytes gravados e compara com o metadado) e `/deral/snapshots/{id}/download-raw` (recuperação binária fiel com `Content-Disposition`) foram implementados e testados.
3. **Decodificação Nativa de Formatos Oficiais e Rejeição de Formatos Não Homologados**:
   - Implementado parser nativo para planilhas binárias BIFF8 OLE2 do Excel (`.xls`) via `xlrd`, com validação da aba oficial `Rav`, validação de título `PREÇOS MÉDIOS SEMANAIS`, extração de período/data e mapeamento exato das 21 commodities canônicas com quantização decimal `ROUND_HALF_UP`.
   - Extensão `.xlsx` é expressamente rejeitada na entrada (HTTP 400) com mensagem orientando os formatos suportados (`.json` e `.xls`).
4. **Publicação e Reversão Atômicas em Transação Única**:
   - O método `update_config` do `AgroConfigService` recebeu suporte ao parâmetro `commit=False`, permitindo que o índice de snapshots (`KEY_DERAI_INDEX`), a configuração de mercado (`KEY_MERCADO`) e o registro de auditoria (`AdminAuditLog`) sejam confirmados em um **único `session.commit()`** do SQLAlchemy.
   - A sincronização em cache L1 e broadcast Redis Pub/Sub ocorre estritamente na rotina `post_commit_sync` após a efetivação transacional.
5. **Consistência Multi-Worker e Resiliência**:
   - Adicionada rotina de descoberta direta no banco (`sync_active_snapshot_from_db`), permitindo que workers novos ou recuperados descubram a versão ativa sem dependência do Redis.
   - Falhas no Redis ou no canal Pub/Sub não interrompem as operações de ativação/rollback nem as rotas públicas, registrando advertências não-bloqueantes.
6. **Consumo Dinâmico por Serviços Públicos**:
   - As instâncias singleton de `PtaxService`, `IndicadoresMacroService`, `IbgeSidraService` e `PrecosPublicosService` agora atualizam seus TTLs e acatam os flags administrativos (`ptax_enabled`, `sgs_enabled`, `sidra_enabled`, `deral_enabled`) em tempo de execução sem reinício de processo.
   - Desabilitações de fontes retornam respostas controladas com preservação estrita do contrato e tipagem pública.

---

## 2. Matriz de Aderência Inicial e Correção

| Requisito / Componente | Avaliação 01E4 | Status 01E4A | Arquivos e Linhas de Correção |
| :--- | :--- | :--- | :--- |
| **Segregação de Integridade vs Proveniência vs Aprovação** | PARCIAL (SHA-256 tratava como autenticado) | **COMPROVADO** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L100-L125), [agro_config_schemas.py](file:///opt/lampp/htdocs/farm/services/api/core/schemas/agro_config_schemas.py#L350-L400) |
| **Auditoria e Download de Bytes Originais Brutos** | NÃO IMPLEMENTADO | **COMPROVADO** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L850-L950), [backoffice_agro_mercado.py](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro_mercado.py#L250-L295) |
| **Parsing Nativo de BIFF8 (.xls) e Rejeição de .xlsx** | PARCIAL (aceitava `.xlsx` sem biblioteca/parser) | **COMPROVADO** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L130-L225), `xlrd` homologado |
| **Publicação Atômica Transacional** | PARCIAL (commits separados entre index e config) | **COMPROVADO** | [agro_config_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/agro_config_service.py#L320-L420), [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L1050-L1110) |
| **Controle de Mutação JSON no SQLAlchemy (`flag_modified`)** | PARCIAL (atualizações em colunas JSON não detectadas) | **COMPROVADO** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L680-L1200) |
| **Consistência Multi-Worker e Reconciliação sem Redis** | PARCIAL (apenas evento Redis Pub/Sub) | **COMPROVADO** | [deral_snapshot_service.py](file:///opt/lampp/htdocs/farm/services/api/core/services/deral_snapshot_service.py#L254-L285) |
| **Consumo Dinâmico em PTAX, SGS, SIDRA e DERAL** | PARCIAL (serviços usavam `settings` estáticos) | **COMPROVADO** | [router.py](file:///opt/lampp/htdocs/farm/services/api/public_mercado/router.py#L50-L115), [backoffice_agro_mercado.py](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro_mercado.py#L125-L135) |
| **Interface Backoffice de Aprovação e Integridade** | PARCIAL (apenas listagem e ativação) | **COMPROVADO** | [page.tsx](file:///opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/agro/mercado/page.tsx#L320-L650) |

---

## 3. Segregação de Integridade Criptográfica, Proveniência e Aprovação

A implementação estabeleceu uma separação estrita e inconfundível entre quatro camadas de validação:

```
[ ARQUIVO ENVIADO (.json / .xls) ]
              │
              ├──> 1. INTEGRIDADE CRIPTOGRÁFICA (SHA-256)
              │    - Recálculo dos bytes brutos recebidos.
              │    - Valida contra corrupção em trânsito.
              │    - NÃO constitui presunção de veracidade governamental.
              │
              ├──> 2. PROVENIÊNCIA DECLARADA VS VERIFICADA
              │    - Checagem automática contra domínios oficiais homologados:
              │      ['agricultura.pr.gov.br', 'pr.gov.br', 'seab.pr.gov.br']
              │    - Se fora da whitelist -> 'FALHA_VERIFICACAO'
              │    - Bloqueia aprovação administrativa sumariamente.
              │
              ├──> 3. APROVAÇÃO ADMINISTRATIVA FORMAL (RBAC)
              │    - Exige ação deliberada de administrador ('agro.market.deral.approve').
              │    - Registra 'aprovado_por', 'aprovado_em' e justificativa em AdminAuditLog.
              │    - Snapshots em 'PENDENTE' ou 'REJEITADO' não podem ser ativados.
              │
              └──> 4. PUBLICAÇÃO PÚBLICA ATÔMICA
                   - Requer estado 'APROVADO'.
                   - Altera ponteiro ativo em transação única no banco.
```

---

## 4. Parser Nativo BIFF8 (.xls) e Rejeição de Formatos Não Homologados

Conforme a diretriz *"Não aceitar uma extensão se o formato correspondente não for efetivamente suportado"*:

1. **Rejeição Estrita de `.xlsx`**:
   - `services/api` não possui `openpyxl` instalado e o DERAL do Paraná publica oficialmente sua planilha de preços em formato binário BIFF8 (`prp.xls`).
   - O upload de arquivos `.xlsx` retorna imediatamente `HTTP 400 Bad Request` com a mensagem explicativa:
     > *"Extensão '.xlsx' não suportada. Os formatos suportados são: .json (contrato estruturado DERAL v1) e .xls (planilha binária oficial BIFF8 DERAL/SEAB-PR)."*
2. **Parser Nativo BIFF8 (`parse_deral_xls`)**:
   - Verifica a assinatura binária OLE2 (`\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1`).
   - Lê a planilha via `xlrd.open_workbook(file_contents=dados_xls)`.
   - Localiza e valida a aba obrigatória `Rav`.
   - Confere o título na célula `Rav!A1` (`PREÇOS MÉDIOS SEMANAIS`) e a coluna `Rav!X2` (`MÉDIA`).
   - Mapeia as 21 commodities canônicas conferindo produto original, unidade e célula.
   - Aplica arredondamento financeiro `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.

---

## 5. Armazenamento Imutável e Auditoria Forense dos Bytes Brutos

Para auditoria forense e conformidade regulatória:
- O payload de cada snapshot é armazenado imutavelmente na tabela `ConfiguracaoSaaS` sob a chave `agro:deral:snapshots:{id}`, contendo:
  - `metadata`: Metadados tipados e histórico de aprovação.
  - `snapshot_data`: Dicionário normalizado com as 21 commodities.
  - `raw_bytes_base64`: Codificação Base64 dos bytes binários exatos recebidos no upload.
- **Endpoint `/deral/snapshots/{id}/verify-integrity` (GET)**:
  - Decodifica os bytes brutos armazenados.
  - Recalcula o SHA-256 e o tamanho em bytes.
  - Compara com os metadados registrados no upload, confirmando a não-adulteração de armazenamento.
- **Endpoint `/deral/snapshots/{id}/download-raw` (GET)**:
  - Recupera os bytes brutos originais e responde com `Response(content=raw_bytes, media_type=..., headers={"Content-Disposition": "attachment; filename=..."})`.

---

## 6. Transação Atômica Única para Publicação e Rollback

Para eliminar o risco de estados parciais e "ponteiro fantasma":

1. **Assinatura Estendida de `update_config`**:
   ```python
   async def update_config(
       self,
       session: AsyncSession,
       chave: str,
       novo_valor: dict[str, Any],
       admin_claims: Any,
       commit: bool = True,  # 01E4A: controle de transação pelo chamador
       ...
   ) -> tuple[ConfiguracaoSaaS, ConfiguracaoSaaSMeta]:
   ```
   - Quando `commit=False`, o serviço executa apenas `session.flush()`, mantendo o lock pessimista `with_for_update()` aberto.
2. **Commit Atômico Conjunto**:
   - O `activate_snapshot` prepara:
     1. Atualização do `idx_rec` (`KEY_DERAI_INDEX`) marcando o snapshot anterior como `ANTERIOR` e o novo como `ATIVO`.
     2. Inclusão de `flag_modified(idx_rec, "valor")` para garantia de dirty-tracking no SQLAlchemy.
     3. Chamada `update_config(chave=KEY_MERCADO, commit=False)`.
     4. Adição do log `AdminAuditLog(acao="agro.market.deral.activate")`.
     5. Execução de um **único `await session.commit()`**.
   - Em caso de falha em qualquer etapa, `await session.rollback()` reverte integralmente todas as alterações.
3. **Pós-Commit Desacoplado (`post_commit_sync`)**:
   - Atualiza o cache local L1 e publica o evento de invalidação no Redis Pub/Sub somente após a confirmação no banco de dados.

---

## 7. Consistência Multi-Worker e Resiliência sem Redis

A arquitetura multi-worker foi blindada para cenários de degradação:

1. **Descoberta Dinâmica via Banco (`sync_active_snapshot_from_db`)**:
   - Se um worker reiniciar ou perder o cache local, ele lê diretamente `KEY_MERCADO` e `KEY_DERAI_SNAP_PREFIX` no PostgreSQL, reconstituindo o snapshot ativo em memória.
2. **Resiliência a Falhas do Redis**:
   - Se o cluster Redis estiver fora do ar ou o canal Pub/Sub falhar, a notificação de invalidação emite uma advertência (`logger.warning`) sem interromper o fluxo do usuário ou das rotas administrativas.
   - O cache L1 local possui TTL de segurança para revalidação periódica autônoma.

---

## 8. Consumo Dinâmico por Serviços Públicos de Mercado

Os serviços públicos em `services/api/public_mercado/router.py` agora operam de forma 100% dinâmica:

```python
def apply_dynamic_market_config(config_dict: dict[str, Any]) -> None:
    if "ptax_cache_ttl_seconds" in config_dict:
        service.ttl_seconds = config_dict["ptax_cache_ttl_seconds"]
    if "macro_cache_ttl_seconds" in config_dict:
        macro_service.ttl_seconds = config_dict["macro_cache_ttl_seconds"]
    if "sidra_cache_ttl_seconds" in config_dict:
        sidra_service.ttl_annual_seconds = config_dict["sidra_cache_ttl_seconds"]
        sidra_service.ttl_monthly_seconds = max(300, config_dict["sidra_cache_ttl_seconds"] // 4)
    if "precos_cache_ttl_seconds" in config_dict:
        precos_service.ttl_seconds = config_dict["precos_cache_ttl_seconds"]
```

Além disso:
- Ao receber `PUT /api/v1/backoffice/agro/mercado/config`, a função `apply_dynamic_market_config` é chamada imediatamente no processo local, atualizando os serviços em tempo de execução.
- As consultas públicas respeitam os flags administrativos (`ptax_enabled`, `sgs_enabled`, `sidra_enabled`, `deral_enabled`), retornando contratos preservados (`estadoDisponibilidade: "FONTE_DESABILITADA_ADMIN"` ou aviso institucional de manutenção) sem lançar exceções não tratadas.

---

## 9. Interface do Usuário (Backoffice Web — shadcn/ui)

O frontend em `apps/web/src/app/(dashboard)/dashboard/backoffice/agro/mercado/page.tsx` foi estendido em total aderência às regras **AGRO-03** e **AGRO-04**:

1. **Aprovação e Rejeição Formal**:
   - Diálogo com campo de justificativa obrigatória para homologação de proveniência governamental.
   - Badges coloridos indicando o `estado_aprovacao` (`APROVADO`, `PENDENTE`, `REJEITADO`) e `estado_verificacao` (`VERIFICADO`, `FALHA_VERIFICACAO`).
   - Bloqueio visual do botão de ativação para snapshots que não estejam com estado `APROVADO`.
2. **Auditoria Criptográfica em Tela (`IntegrityDialog`)**:
   - Modal detalhado exibindo: SHA-256 Registrado, SHA-256 Recalculado, Tamanho Registrado vs Armazenado, Status de Prova Binária e Proveniência de Domínio Oficial.
3. **Download Forense de Bytes Originais (`downloadRaw`)**:
   - Ação direta na tabela para baixar o arquivo binário `.xls` ou `.json` exatamente como foi persistido imutavelmente.
4. **Qualidade Estrita TypeScript**:
   - 100% tipado sem nenhum uso de `any`, `@ts-ignore` ou asserções inseguras.
   - Verificado com `pnpm --filter web exec tsc --noEmit` (0 erros).

---

## 10. Evidências de Testes e Validação Automatizada

A suíte completa de testes de regressão e hardening foi executada:

```bash
./.venv/bin/pytest tests/unit/core/test_backoffice_agro_01e4.py tests/unit/core/test_backoffice_agro_01e4a.py -v
```

### Resultado da Execução:
```text
========================= test session starts =========================
platform linux -- Python 3.10.12, pytest-9.0.2, pluggy-1.6.0
rootdir: /opt/lampp/htdocs/farm/services/api
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1, cov-7.1.0
collected 21 items

tests/unit/core/test_backoffice_agro_01e4.py::test_sources_status_reading_and_baseline_init PASSED [  4%]
tests/unit/core/test_backoffice_agro_01e4.py::test_deral_snapshot_upload_and_validation PASSED [  9%]
tests/unit/core/test_backoffice_agro_01e4.py::test_deral_snapshot_upload_corrupt_rejected PASSED [ 14%]
tests/unit/core/test_backoffice_agro_01e4.py::test_deral_snapshot_upload_missing_commodities_rejected PASSED [ 19%]
tests/unit/core/test_backoffice_agro_01e4.py::test_deral_snapshot_atomic_activation_and_cache_invalidation PASSED [ 23%]
tests/unit/core/test_backoffice_agro_01e4.py::test_deral_snapshot_rollback_flow PASSED [ 28%]
tests/unit/core/test_backoffice_agro_01e4.py::test_public_endpoints_preservation_of_contracts PASSED [ 33%]
tests/unit/core/test_backoffice_agro_01e4.py::test_market_config_optimistic_locking PASSED [ 38%]
tests/unit/core/test_backoffice_agro_01e4.py::test_market_rbac_isolation_unauthorized_user PASSED [ 42%]
tests/unit/core/test_backoffice_agro_01e4.py::test_market_rbac_viewer_can_read_cannot_write PASSED [ 47%]
tests/unit/core/test_backoffice_agro_01e4.py::test_cannot_overwrite_active_snapshot PASSED [ 52%]
tests/unit/core/test_backoffice_agro_01e4.py::test_cannot_activate_same_snapshot_twice PASSED [ 57%]
tests/unit/core/test_backoffice_agro_01e4.py::test_audit_trail_recorded_on_market_operations PASSED [ 61%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_verificar_proveniencia_governamental_unitario PASSED [ 66%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_rejeicao_de_aprovacao_para_snapshot_com_falha_de_origem PASSED [ 71%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_snapshot_verify_integrity_and_download_raw PASSED [ 76%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_rejeicao_estrita_de_extensao_xlsx PASSED [ 80%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_rejeicao_de_xls_com_assinatura_binaria_invalida PASSED [ 85%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_rejeicao_de_xls_ole2_corrompido PASSED [ 90%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_dynamic_market_config_application PASSED [ 95%]
tests/unit/core/test_backoffice_agro_01e4a.py::test_multiworker_db_discovery_reconciliation PASSED [100%]

========================= 21 passed in 11.11s =========================
```

---

## 11. Conformidade com Guardrails de Engenharia

1. **AGRO-03 (Frontend Web)**:
   - Uso restrito de Client Components para interatividade (`use client`).
   - Componentes shadcn/ui estilizados com bordas `rounded-sm`, botões com tamanho `sm` e variante `outline`.
   - Modais acessíveis com Radix UI / shadcn Dialog.
   - Zero layout shift e tipagem estrita com TypeScript.
2. **AGRO-04 (Qualidade e Resiliência)**:
   - Docstrings obrigatórias descrevendo entradas, retornos e exceções lançadas em todos os métodos de service.
   - Nomes reveladores de intenção real (`verificar_proveniencia_governamental`, `verify_snapshot_integrity`, `sync_active_snapshot_from_db`).
   - Zero dependências desnecessárias (uso de `xlrd` já existente e `hashlib` da stdlib de Python).
   - Isolamento de banco: os testes unitários rodam sobre SQLite em memória/temporário via fixture assíncrona, preservando integralmente o banco compartilhado de desenvolvimento e produção.

---

## 12. Encerramento e Próximos Passos

A fase **AGRO-ADMIN-01E4A** encontra-se formalmente **CONCLUÍDA**, com todas as lacunas de segurança, autenticidade governamental, consistência distribuída e auditoria forense sanadas e comprovadas por testes automatizados.

Conforme orientação imperativa:
- A execução foi encerrada neste relatório de auditoria e implementação restrita.
- A fase **AGRO-ADMIN-01E5** **NÃO** foi iniciada.
- Nenhuma alteração foi realizada nos subsistemas de Clima (01E3A), Identidade Unificada (01B), BYOK ou Billing.
- Nenhum commit, merge, push ou migração de banco em ambientes remotos/produção foi executado.
