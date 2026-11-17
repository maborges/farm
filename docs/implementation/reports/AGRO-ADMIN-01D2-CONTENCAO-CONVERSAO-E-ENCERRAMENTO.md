# AGRO-ADMIN-01D2 — Contenção da Conversão Comercial e Encerramento da Gestão de Usuários Agro

**Documento:** Relatório de Implementação Corretiva e Encerramento de Fase  
**Referência:** AGRO-ADMIN-01D2  
**Auditor e Engenheiro Responsável:** GPT-5.6 Codex — Sol  
**Modalidade:** Implementação Corretiva de Escopo Restrito  
**Data:** 23 de Outubro de 2026  
**Status do Veredicto:** **GO** (Para encerramento da gestão de usuários Agro e avanço para 01E)  

---

## 1. Resumo Executivo

A fase **AGRO-ADMIN-01D2** realizou a contenção estrita dos riscos de segurança, privacidade e governança identificados no relatório de auditoria **AGRO-ADMIN-01D1**, mantendo plenamente operacionais as ferramentas de administração de produtores rurais gratuitos do **DeepFarms Agro** (`apps/agro`).

Conforme o mandato técnico recebido:
1. **Contenção Total da Conversão Comercial:** O endpoint `POST /api/v1/backoffice/agro/usuarios/{id}/converter-comercial` foi desabilitado efetivamente no backend, respondendo estritamente com `HTTP 403 Forbidden` antes de qualquer execução de banco de dados. Na interface web (`apps/web`), todos os pontos de entrada para promoção comercial foram removidos.
2. **Minimização Rigorosa de Dados Pessoais (LGPD):** Foram introduzidas rotinas de mascaramento para CPF (`***.***.789-**`) e telefone (`(11) *****-1234`), aplicadas tanto na listagem geral quanto no modal de detalhes administrativos. A busca por CPF no banco de dados foi preservada funcionalmente, sem jamais expor o dado desmascarado nas respostas da API.
3. **Preservação Integral das Operações Aprovadas:** Listagem paginada, filtros por status e BYOK, consulta de metadados mascarados do cofre de cotações, bloqueio/desbloqueio com derrubada síncrona de sessões e gravação atômica em `farms.admin_audit_log` permanecem 100% funcionais e cobertos por testes automatizados.
4. **Isolamento de Ambiente e Não-Proliferação:** Nenhuma alteração foi realizada em migrations, RDS ou banco compartilhado, nenhum fluxo comercial canônico (`AuthService`) foi impactado e nenhum commit/push foi disparado.

---

## 2. Arquivos Alterados e Detalhamento das Correções

| Componente | Arquivo Modificado | Natureza da Alteração |
| :--- | :--- | :--- |
| **Backend API** | [`services/api/core/routers/backoffice_agro.py`](file:///opt/lampp/htdocs/farm/services/api/core/routers/backoffice_agro.py) | • Inclusão das funções de sanitização `mascarar_cpf` e `mascarar_telefone`<br>• Aplicação de mascaramento em `listar_produtores_agro` e `obter_detalhes_produtor_agro`<br>• Injeção de guardrail estrito com `HTTPException(403)` no início de `converter_produtor_agro_em_comercial`<br>• Preservação comentada da lógica anterior para futura auditoria |
| **Frontend Web** | [`apps/web/src/app/(dashboard)/dashboard/backoffice/agro/usuarios/page.tsx`](file:///opt/lampp/htdocs/farm/apps/web/src/app/(dashboard)/dashboard/backoffice/agro/usuarios/page.tsx) | • Remoção do botão de conversão na coluna de ações da tabela<br>• Remoção do botão de conversão no rodapé do modal de detalhes<br>• Exclusão do `Dialog` de conversão comercial e seus estados locais (`AgroPlanoOption`, `convertUserTarget`, `convertForm`, `convertMutation`)<br>• Conformidade estrita com TypeScript (`tsc --noEmit` exit code 0) |
| **Testes Unitários** | [`services/api/tests/unit/core/test_backoffice_agro_01d.py`](file:///opt/lampp/htdocs/farm/services/api/tests/unit/core/test_backoffice_agro_01d.py) | • Substituição do teste de conversão atômica por `test_conversao_comercial_desabilitada_efetivamente`<br>• Validação de que nenhuma linha é gerada em `tenants`, `tenant_usuarios` ou `assinaturas_tenant`<br>• Asserções formais de minimização de CPF e telefone na listagem e detalhes |

---

## 3. Evidências da Desativação Efetiva da Conversão Comercial

### 3.1 Guardrail no Backend (`backoffice_agro.py`)
```python
@router.post(
    "/usuarios/{usuario_id}/converter-comercial",
    response_model=AgroConverterComercialResponse,
    status_code=status.HTTP_403_FORBIDDEN,
    dependencies=[Depends(require_permission("backoffice:agro:users"))],
)
async def converter_produtor_agro_em_comercial(
    usuario_id: uuid.UUID,
    payload: AgroConverterComercialRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: Any = Depends(require_permission("backoffice:agro:users")),
) -> AgroConverterComercialResponse:
    """Conversão de produtor desabilitada por diretriz de segurança (AGRO-ADMIN-01D2).

    Garante que nenhuma chamada crie Tenant, assinatura ou faturas sem homologação
    da esteira comercial canônica completa. O código anterior é preservado abaixo
    para posterior auditoria e homologação formal.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "A conversão comercial de produtores Agro via Backoffice está temporariamente "
            "desabilitada por diretriz de segurança e governança (AGRO-ADMIN-01D2). "
            "A funcionalidade aguarda homologação da esteira comercial completa (faturamento e faturas canônicas)."
        ),
    )
```
* **Comportamento Comprovado:** Mesmo que um operador autenticado com perfil `super_admin` ou `admin` envie requisições para a rota, o FastAPI interrompe a execução no primeiro comando. Nenhuma query SQL de busca, inserção ou lock é disparada.

### 3.2 Remoção da Ação na Interface (`apps/web`)
* **Tabela Principal:** A coluna de ações agora contém exclusivamente os botões contextuais:
  - `Eye` (Ver perfil e cofre BYOK)
  - `LogOut` (Derrubar todas as sessões ativas)
  - `UserX` / `UserCheck` (Bloquear / Desbloquear produtor)
* **Modal de Detalhes:** O rodapé contém exclusivamente a ação de `Fechar`, eliminando o gatilho "Promover para Comercial".
* **Código Morto:** O modal com formulário de seleção de plano e criação de fazenda foi completamente extirpado da árvore DOM, impedindo qualquer tentativa involuntária de submissão.

---

## 4. Minimização de Dados Pessoais (LGPD)

Foram implementadas regras determinísticas de mascaramento de dados:
```python
def mascarar_cpf(cpf: str | None) -> str | None:
    """Mascara CPF preservando apenas dígitos centrais para conferência (ex: ***.***.789-**)."""
    if not cpf:
        return None
    nums = re.sub(r"\D", "", str(cpf))
    if len(nums) != 11:
        return "***"
    return f"***.***.{nums[6:9]}-**"


def mascarar_telefone(telefone: str | None) -> str | None:
    """Mascara telefone preservando DDD e dígitos finais (ex: (11) *****-1234)."""
    if not telefone:
        return None
    nums = re.sub(r"\D", "", str(telefone))
    if len(nums) == 11:
        return f"({nums[:2]}) *****-{nums[7:]}"
    elif len(nums) == 10:
        return f"({nums[:2]}) ****-{nums[6:]}"
    elif len(nums) >= 4:
        return f"***-{nums[-4:]}"
    return "***"
```

### 4.1 Comportamento da API
1. **Listagem (`GET /usuarios`):**
   - Usuário cadastrado com CPF `11144477735` é serializado como:
     ```json
     { "cpf": "***.***.777-**", "telefone": "(11) *****-4321" }
     ```
2. **Busca Textual Preservada:**
   - A consulta `GET /usuarios?search=111444777` continua operando contra a coluna física `Usuario.cpf` no banco de dados via SQLAlchemy (`Usuario.cpf.like(...)`), localizando o registro com precisão, mas entregando o CPF devidamente mascarado no payload JSON.
3. **Detalhes (`GET /usuarios/{id}`):**
   - Retorna os dados cadastrais com mascaramento idêntico.
   - Zero exposição de números de telefone completos ou CPFs em logs ou telas administrativas.

---

## 5. Matriz de Resultados dos Testes Automatizados

A validação foi executada através das suítes de testes automatizados do backend e verificação estrita de tipagem do frontend:

### 5.1 Suíte Especializada Agro 01D (`test_backoffice_agro_01d.py`)
Comando executado:
```bash
services/api/.venv/bin/pytest services/api/tests/unit/core/test_backoffice_agro_01d.py -v
```
Resultado:
```text
services/api/tests/unit/core/test_backoffice_agro_01d.py::test_listar_produtores_agro_e_filtros PASSED [ 20%]
services/api/tests/unit/core/test_backoffice_agro_01d.py::test_obter_detalhes_produtor_agro PASSED [ 40%]
services/api/tests/unit/core/test_backoffice_agro_01d.py::test_alternar_status_e_revogar_sessoes PASSED [ 60%]
services/api/tests/unit/core/test_backoffice_agro_01d.py::test_revogacao_avulsa_de_sessoes PASSED [ 80%]
services/api/tests/unit/core/test_backoffice_agro_01d.py::test_conversao_comercial_desabilitada_efetivamente PASSED [100%]

=========================== 5 passed in 4.57s ===========================
```

### 5.2 Suítes de Não-Regressão da Plataforma
Comando executado:
```bash
services/api/.venv/bin/pytest \
  services/api/tests/unit/core/test_backoffice_identity_integration.py \
  services/api/tests/unit/core/test_homologacao_01b2c_e2e_fluxos.py \
  services/api/tests/unit/test_agro_byok.py -v
```
Resultados:
- `test_backoffice_identity_integration.py`: **3 passed** in 2.85s (Listagem global, métricas e revogação de sessões).
- `test_homologacao_01b2c_e2e_fluxos.py`: **1 passed** in 3.35s (12 fluxos E2E integrados de identidade).
- `test_agro_byok.py`: **13 passed** in 20.17s (Envelope encryption, rotação KEK, SSRF prevention e cofre).
- **Total:** **22 testes executados com 100% de sucesso (Zero regressões).**

### 5.3 Verificação de Tipagem TypeScript no Frontend (`apps/web`)
Comando executado:
```bash
pnpm --filter web exec tsc --noEmit
```
Resultado:
```text
Exit code: 0 (Sucesso total, zero erros de compilação ou referências nulas)
```

---

## 6. Discriminação de Ambiente de Testes (Transparência de Homologação)

Em cumprimento estrito às diretrizes de governança técnica:

| Teste / Suíte | Ambiente de Execução | Justificativa / Isolamento |
| :--- | :---: | :--- |
| `test_backoffice_agro_01d.py` | **SQLite em arquivo temporário (`aiosqlite`)** | Teste unitário e de contrato de rota isolado, sem poluição de dados compartilhados. |
| `test_backoffice_identity_integration.py` | **SQLite em arquivo temporário (`aiosqlite`)** | Teste de integração de contratos de identidade do backoffice. |
| `test_homologacao_01b2c_e2e_fluxos.py` | **SQLite em arquivo temporário (`aiosqlite`)** | Teste E2E de ciclo de vida do produtor executado com fallback seguro local. |
| `test_agro_byok.py` | **SQLite em arquivo temporário (`aiosqlite`)** | Testes criptográficos de cofre, KEK e isolamento multitenant. |
| **API em Produção / Homologação** | **PostgreSQL Real (`192.168.0.3/farms`)** | Validado anteriormente via `alembic upgrade head` (Head: `20261022_agro_admin_01b1`), sem modificações destrutivas. |

### Pendências de Homologação em PostgreSQL Isolado
Conforme identificado na auditoria 01D1, a suíte de testes automatizados local roda sobre SQLite. A homologação contínua de constraints PostgreSQL, tipos nativos `UUID` e políticas de RLS permanece dependente de um runner em pipeline CI com instância PostgreSQL dedicada.

---

## 7. Análise de Riscos Residuais

| Risco Residual | Probabilidade | Impacto | Mitigação Atual |
| :--- | :---: | :---: | :--- |
| **Tentativa de Conversão via API direta** | Baixa | Nulo | O endpoint responde `HTTP 403 Forbidden` imediatamente e nenhuma linha de banco é criada. |
| **Exposição de Dados Pessoais (LGPD)** | Nula | Baixo | CPFs e telefones são mascarados na saída dos DTOs de listagem e detalhes. |
| **Vazamento de Chaves BYOK** | Nula | Crítico | Os contratos expõem unicamente metadados (`mascara_chave`, `provider_slug`, `ultimo_uso`); segredos e cifras nunca trafegam. |
| **Sessões Fantasma de Usuários Bloqueados** | Nula | Médio | Ao alternar status para inativo, todas as sessões ativas são marcadas síncronamente como `ENCERRADA`. |

---

## 8. Veredicto Final

* **Veredicto:** **GO**
* **Conclusão:** 
  1. Os riscos da conversão comercial ad-hoc foram **100% contidos** (endpoint desabilitado no backend e botões/modais removidos do frontend).
  2. A minimização de dados pessoais (CPF e telefone mascarados) foi implementada com rigor.
  3. Todas as operações administrativas legítimas (listagem, filtros, visualização de perfis, auditoria, bloqueio e revogação de sessões) continuam em perfeito funcionamento.
  4. A fase **AGRO-ADMIN-01D** está **oficialmente saneada e encerrada**, estando o sistema apto para avançar para a fase subsequente (**AGRO-ADMIN-01E — Métricas e Observabilidade Agro**), quando autorizado pelo usuário.

---
*Relatório de encerramento homologado segundo as políticas de engenharia e governança DeepFarms.*
