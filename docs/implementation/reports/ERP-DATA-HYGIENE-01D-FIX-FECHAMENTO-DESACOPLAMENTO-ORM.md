# ERP-DATA-HYGIENE-01D-FIX — Fechamento Real do Desacoplamento ORM

## 1. Resumo Executivo

A contradição apontada em `ERP-DATA-HYGIENE-01E0` (import de `SankhyaConfig` em `nfe_financeiro_service.py`, mas guardrail passando) tinha **duas causas independentes**, ambas confirmadas por leitura direta do código:

1. O import de `SankhyaConfig` em `nfe_financeiro_service.py` existia, mas era **morto** — nenhum uso operacional do símbolo no corpo do arquivo além da linha de import. O fluxo real já usava exclusivamente `get_sankhya_connection_data`/`SankhyaConnectionData`, como o 01D pretendia.
2. O guardrail (`test_sankhya_architecture.py`) tinha uma **falha lógica de resolução de caminho**: `base_dir` resolvia para `/opt/lampp/htdocs/farm/services/services/api/integracoes/sankhya` (diretório inexistente, com "services" duplicado), então `file_path.exists()` era sempre `False` para os três arquivos protegidos e o `for` simplesmente pulava todas as verificações — o teste passava trivialmente, sem nunca inspecionar um único arquivo real.

Ambas as causas foram corrigidas com a menor alteração possível: removido o import morto; corrigido o cálculo de `base_dir`; e adicionada cobertura AST para import de módulo completo + acesso via atributo, com teste negativo comprovando que o guardrail agora falha diante de violação real.

## 2. Contradição Investigada

- Hipótese confirmada: **(5) o guardrail está inspecionando caminho incorreto** e **(6) o guardrail contém uma falha lógica** — ambas verdadeiras e relacionadas (o bug de caminho é a falha lógica).
- Hipóteses descartadas: o import não é apenas de tipagem nem protegido por `TYPE_CHECKING`; não há alias; o símbolo importado é de fato o ORM real (`integracoes.sankhya.models.SankhyaConfig`), não o schema homônimo; o arquivo não foi alterado entre o inventário e esta fase.

## 3. Import Real Encontrado

Antes da correção, em `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`:

```python
from integracoes.sankhya.models import (
    SankhyaConfig,
    SankhyaLancamentoFinanceiro,
    SankhyaNFe,
)
```

- Linha: 12-16 (símbolo na linha 13).
- Módulo de origem: `integracoes.sankhya.models` (ORM real, mesmo módulo onde `SankhyaConfig(Base)` é definida — não é o schema `SankhyaConfigCreate/Response`).
- Sem alias, sem `TYPE_CHECKING`, sem import local em função, sem acesso dinâmico.
- `grep -n "\bSankhyaConfig\b"` no arquivo inteiro retornou **apenas a linha do import** — confirmado como símbolo morto (não referenciado em nenhum outro ponto do arquivo).

## 4. Causa da Lacuna do Guardrail

```python
base_dir = Path(__file__).parent.parent.parent.parent.parent / "services" / "api" / "integracoes" / "sankhya"
```

`__file__` = `services/api/tests/unit/integracoes/test_sankhya_architecture.py`. Cinco `.parent` a partir daí chegam em `.../farm/services` (o diretório `services` do repo). Ao concatenar `"services" / "api" / ...` novamente, o resultado era `.../farm/services/services/api/integracoes/sankhya` — inexistente. Verificado com script Python isolado antes de qualquer alteração:

```
base_dir: /opt/lampp/htdocs/farm/services/services/api/integracoes/sankhya
exists: False
```

Como o loop principal fazia `if not file_path.exists(): continue`, nenhum dos três arquivos protegidos (`auth_service.py`, `nfe_financeiro_service.py`, `routers/*.py`) era efetivamente lido ou parseado — o teste "passava" por ausência de verificação, não por conformidade real.

## 5. Fluxo Anterior

```
nfe_financeiro_service.py
  → import SankhyaConfig (morto, nunca instanciado/consultado)
  → get_sankhya_connection_data(db, tenant_id)   [uso real]
  → SankhyaConnectionData
  → SankhyaWSClient
```

O fluxo funcional já estava correto; só o import residual e o guardrail quebrado davam a impressão de acoplamento.

## 6. Correção Implementada

### 6.1 `nfe_financeiro_service.py`
Removida a linha `SankhyaConfig,` do bloco de import (único símbolo eliminado; `SankhyaLancamentoFinanceiro` e `SankhyaNFe` preservados, pois são usados operacionalmente). Nenhuma outra linha do arquivo foi tocada.

### 6.2 `test_sankhya_architecture.py`
- Corrigido `base_dir` para `Path(__file__).resolve().parent.parent.parent.parent / "integracoes" / "sankhya"` (quatro `.parent` até `services/api`, sem duplicar `services/api` no append), com `assert base_dir.exists()` para que qualquer regressão futura de caminho quebre o teste de forma ruidosa em vez de silenciosa.
- Extraída a lógica de análise para `check_source_for_legacy_orm_import(content, file_label)`, reutilizável tanto pelo teste principal quanto pelos testes negativos.
- Mantida a detecção original de `ast.ImportFrom` com `module == "integracoes.sankhya.models"` e `alias.name == "SankhyaConfig"` (comparação exata — já protegia contra falso positivo em `SankhyaConfigCreate`/`Response`).
- Adicionada detecção de `import integracoes.sankhya.models [as alias]` seguido de uso via atributo (`alias.SankhyaConfig` ou `integracoes.sankhya.models.SankhyaConfig`), resolvendo o nome completo de `ast.Attribute`/`ast.Name` aninhados.
- `ast.walk` já percorre corpos de função, então imports locais dentro de função continuam cobertos automaticamente pela mesma lógica — não foi necessário tratamento especial.
- Adicionados dois testes: um teste negativo (`test_sankhya_architecture_guardrail_detects_prohibited_import`) que alimenta a função analisadora com três variações de violação sintética (import direto, import com alias, import de módulo completo + uso via atributo) e confirma que cada uma levanta `AssertionError`; e um teste de não-regressão (`test_sankhya_architecture_guardrail_allows_homonym_schema`) que confirma que `SankhyaConfigCreate`/`SankhyaConfigResponse` não disparam falso positivo.
- Nenhum arquivo de produção foi modificado para provar o teste negativo — as violações são strings de código-fonte sintéticas passadas diretamente para a função de análise.

## 7. Fluxo Final

```
nfe_financeiro_service.py
  → (sem import de SankhyaConfig)
  → get_sankhya_connection_data(db, tenant_id)
  → SankhyaConnectionData
  → SankhyaWSClient
```

Idêntico ao anterior, exceto pela remoção do import morto — nenhuma mudança de comportamento.

## 8. Arquivos Alterados

- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py` (−1 linha: import morto)
- `services/api/tests/unit/integracoes/test_sankhya_architecture.py` (correção de caminho + refatoração da lógica em função reutilizável + 2 testes novos)
- `docs/implementation/reports/ERP-DATA-HYGIENE-01D-FIX-FECHAMENTO-DESACOPLAMENTO-ORM.md` (este relatório, novo)

Nenhum outro arquivo foi tocado. `sync_service.py`, `canonical_adapter.py`, `legacy_reconciliation.py`, models, migrations, Core ERP, Router ERP, Readiness, Lifecycle, Console ERP, Provider Registry e bootstrap permanecem inalterados.

## 9. Comportamento Preservado

- Assinaturas públicas, rotas, payloads e retornos de `SankhyaNFeService`/financeiro: inalterados (nenhuma linha de lógica foi tocada, apenas o bloco de import).
- Autenticação, URLs, headers, timeout, paginação, filtros, tratamento de erros e mensagens: inalterados.
- Gravação dupla, fallback e precedência das fontes (config técnica/credenciais no legado, lifecycle/health/jobs/policies no canônico): inalterados — não fazem parte do escopo desta fase.
- Isolamento por tenant e transações: inalterados.

## 10. Teste Negativo do Guardrail

Executado dentro da própria suíte (não como manipulação de arquivo de produção):

```
test_sankhya_architecture_guardrail_detects_prohibited_import PASSED
test_sankhya_architecture_guardrail_allows_homonym_schema PASSED
```

Comprova três violações sintéticas (import direto, import com alias, import de módulo completo com uso via atributo) — todas corretamente detectadas — e confirma que os schemas homônimos `SankhyaConfigCreate`/`SankhyaConfigResponse` não geram falso positivo.

## 11. Testes Executados

```bash
cd services/api
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
```
→ `3 passed` (o teste principal agora de fato inspeciona os 3 arquivos reais + os 2 testes negativos/não-regressão).

```bash
.venv/bin/pytest tests/unit/integracoes/test_sankhya_gateway_auth_service.py tests/unit/integracoes/test_erp_provider_governance.py -v
```
→ `14 passed` — cobre `SankhyaGatewayAuthService`, cache de token, fluxo legado, e governança de imports do provider Sankhya no restante do domínio ERP.

```bash
.venv/bin/pytest tests/unit/integracoes -q
```
→ `4 failed, 128 passed, 103 errors` (antes desta fase: `4 failed, 126 passed, 103 errors` — os 2 testes a mais são os novos testes negativos do guardrail; nenhuma regressão introduzida).

## 12. Impacto das Fixtures SQLite

Confirmado que os 103 erros + 4 falhas remanescentes (incluindo `test_sankhya_canonical_adapter.py` e `test_sankhya_external_association_p0.py`, verificados novamente nesta fase) mantêm a mesma causa já documentada em `INTEGRATIONS-MODEL-FK-REPAIR-01`: `sqlalchemy.exc.NoReferencedTableError` por ausência de `farms.tenants` no `metadata.create_all()` de fixtures SQLite isoladas. Não corrigido nesta fase, conforme restrição explícita de escopo. Como evidência complementar, os testes de `auth_service` e de governança (14 testes, seção 11) não dependem dessa fixture e passam integralmente, corroborando que o desacoplamento funcional está correto independentemente do problema de fixture.

## 13. Buscas Finais

```bash
rg -n "SankhyaConfig" services/api/integracoes/sankhya/services/nfe_financeiro_service.py
```
→ nenhuma ocorrência.

```bash
rg -n "SankhyaConfig" services/api/integracoes/sankhya/services/auth_service.py
```
→ nenhuma ocorrência (auth service permanece desacoplado, confirmado também na fase 01E0).

## 14. Riscos Remanescentes

- Os 103 erros/4 falhas de fixture SQLite continuam bloqueando validação plena de `canonical_adapter.py`, `legacy_reconciliation.py` e do fluxo E2E de credenciais — devem ser tratados em uma fase própria antes de assumir qualquer fase 01G-01L como comprovadamente concluída.
- O guardrail agora cobre import direto e import de módulo completo, mas não cobre `importlib.import_module("integracoes.sankhya.models")` dinâmico nem `getattr(modulo, "SankhyaConfig")` — nenhuma ocorrência desse padrão foi encontrada no código atual, mas é uma lacuna teórica remanescente, de baixo risco dado o estilo de código observado no repositório.

## 15. Estado Final da Fase 01D

`nfe_financeiro_service.py` e `auth_service.py` estão comprovadamente desacoplados do ORM `SankhyaConfig`, com guardrail funcional e testado negativamente. A fase 01D está agora **concluída de fato**, corrigindo a divergência identificada em 01E0.

## 16. Recomendação da Próxima Execução

Conforme já antecipado em 01E0, não iniciar a antiga fase 01E diretamente. Abrir uma auditoria curta de **redefinição de sequência** (ex.: `ERP-DATA-HYGIENE-01E1-REDEFINICAO-SEQUENCIA`) para confirmar, agora com o guardrail e a suíte de arquitetura funcionando corretamente, quais fases 01G-01L (lifecycle, health, jobs, políticas) já estão de fato concluídas versus apenas aparentemente concluídas — evitando retrabalho. Essa auditoria deve preferencialmente rodar após uma correção pontual da fixture SQLite (`farms.tenants` ausente), para poder usar `canonical_adapter.py` e `legacy_reconciliation.py` como evidência executável, não apenas leitura estática.

## 17. Veredicto

`GO — ERP-DATA-HYGIENE-01D CONCLUÍDA`

Todos os 15 critérios de aceitação foram atendidos: a contradição foi explicada e corrigida em suas duas causas; `nfe_financeiro_service.py` não importa mais `SankhyaConfig`; NFe/financeiro usam exclusivamente `SankhyaConnectionData`/`get_sankhya_connection_data`; o guardrail cobre a forma de import que escapava e possui teste negativo comprovado; schemas homônimos não geram falso positivo; nenhuma fonte de verdade, gravação dupla, fallback ou precedência foi alterada; comportamento funcional preservado; testes direcionados passam (17 nos arquivos de arquitetura/auth/governança) e os bloqueios conhecidos de fixture estão isolados e documentados; `ruff` e `git diff --check` aprovados; nenhuma alteração ocorreu fora do escopo autorizado.
