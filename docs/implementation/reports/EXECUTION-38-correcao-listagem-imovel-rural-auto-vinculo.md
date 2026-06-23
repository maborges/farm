# EXECUTION-38 — Correção: ImovelRural auto-criado não aparece na listagem de Imóveis Rurais

## Causa Raiz (4 causas encadeadas)

### Causa 1 — Validações rígidas de CAR/NIRF no `criar_imovel()` silenciadas pelo sync
`criar_imovel()` valida o formato de NIRF (módulo 11, 13 dígitos) e CAR (2 letras + 12 dígitos SICAR).
Quando o usuário informa um CAR livre (ex: `"SP-123456"`) ou NIRF com formato inválido, o método lança `ValueError`.
O sync capturava essa exceção, logava warning e **retornava sem criar o ImovelRural**.

### Causa 2 — `validar_area_consistente()` bloqueava quando fazenda não tinha área
Quando `UnidadeProdutiva.area_total_ha` é `None` ou `0`, a validação calculava limite `0 × 1.10 = 0`.
Qualquer área > 0 sendo enviada ao ImovelRural excedia o limite e gerava `False`.
O sync capturava e **abandonava a criação silenciosamente**.

### Causa 3 — `UniqueConstraint('nirf')` é global (sem tenant_id)
O constraint `uq_imovel_nirf` não inclui `tenant_id`. Se qualquer tenant já tivesse o NIRF, a criação falhava com `IntegrityError`. O sync capturava e **descartava toda a operação**.

### Causa 4 — `session.rollback()` no bloco `PropriedadeImovel` desfazia o `ImovelRural`
Quando a criação do `PropriedadeImovel` falhava (ex: `uq_propriedade_imovel_principal_ativo`), o código chamava `session.rollback()`. Isso **desfazia também o `ImovelRural` já criado e flushed** na mesma sessão.

---

## Arquivos Alterados

| Arquivo | Mudança |
|---|---|
| `services/api/imoveis/services/imovel_service.py` | NOVO: método `criar_imovel_sem_validacao()` — cria ImovelRural sem validar CAR/NIRF/área |
| `services/api/core/services/unidade_produtiva_service.py` | Usa `criar_imovel_sem_validacao` no sync; passa `sigef_codigo` direto; pre-checa vínculo principal antes de tentar INSERT; substitui `session.rollback()` por `IntegrityError` catch sem rollback |
| `services/api/tests/integration/test_exec38_correcao_listagem_imovel_rural.py` | NOVO: 6 cenários de teste cobrindo a causa raiz |

---

## Migration

**Não foi necessária** nenhuma migration adicional além da `exec37_fundiario_fields` já aplicada.
A correção foi totalmente no comportamento do serviço (camada Python).

---

## Regra Implementada no CREATE

```
UnidadeProdutivaService.create_unidade_produtiva()
  └─ _sincronizar_vinculo_fundiario()
       ├─ Coleta: car, nirf, ccir, sigef, matricula do payload
       ├─ Se todos vazios → return (sem criar ImovelRural)
       ├─ Busca ImovelRural existente por OR-logic (5 campos)
       ├─ Se não encontrar → ImovelService.criar_imovel_sem_validacao()
       │    ├─ Sem validação de formato CAR/NIRF
       │    ├─ Sem validação de consistência de área
       │    ├─ Detecta NIRF duplicado global e omite (degradação segura)
       │    └─ area_total_ha = 0.0000 (mínimo seguro)
       ├─ Busca ExploracaoRural → propriedade_id
       ├─ Se não existir ExploracaoRural → return (ImovelRural criado, sem PropriedadeImovel)
       ├─ Pre-checa vínculo principal ativo (evita IntegrityError)
       ├─ Cria PropriedadeImovel com vinculo_principal=True (se disponível) ou False
       └─ Em IntegrityError → NÃO faz rollback (ImovelRural preservado na sessão)
```

---

## Regra Implementada na Listagem

A listagem **não foi alterada**. O endpoint `GET /imoveis/?unidade_produtiva_id=` já estava correto:
- `ImovelService.get_imoveis_by_fazenda(unidade_produtiva_id, tenant_id)` filtra por `ImovelRural.unidade_produtiva_id`.
- O `ImovelRural` criado por `criar_imovel_sem_validacao` recebe `unidade_produtiva_id = unidade.id`.
- Logo, ao abrir Imóveis Rurais com a fazenda selecionada, o imóvel auto-criado aparece.

O problema era que o ImovelRural **nunca chegava a ser persistido** pelas causas 1-4 acima.

---

## Método `criar_imovel_sem_validacao()` — Comportamento

| Campo | Comportamento |
|---|---|
| `area_total_ha` | Sempre `0.0000` (mínimo seguro para o constraint NOT NULL) |
| `nirf` | Aceito sem validar módulo 11; omitido se já existir globalmente |
| `car_numero` | Aceito sem validar formato SICAR |
| `ccir_numero` | Aceito sem validação |
| `sigef_codigo` | Passado diretamente |
| `numero_matricula` | Passado diretamente |
| `situacao` | Sempre `PENDENTE` (atualizada quando dados completos forem informados via ImovelRural) |
| `observacao` | `"Imóvel rural criado automaticamente a partir do cadastro operacional."` |

---

## Testes Executados

### EXEC-38 — Novos (6 cenários)
| Cenário | Descrição | Resultado |
|---|---|---|
| 1 | CAR em formato livre → cria ImovelRural | ✅ PASSED |
| 2 | ImovelRural criado aparece na listagem filtrada | ✅ PASSED |
| 3 | CAR já existente → reutiliza sem duplicar | ✅ PASSED |
| 4 | Sem dados fundiários → não cria ImovelRural | ✅ PASSED |
| 5 | PropriedadeImovel com propriedade_id e imovel_rural_id corretos | ✅ PASSED |
| 6 | NIRF inválido → cria ImovelRural sem NIRF (degradação segura) | ✅ PASSED |

### EXEC-37 — Regressão (7 cenários)
| Cenário | Resultado |
|---|---|
| 1: CAR novo → cria ImovelRural | ✅ PASSED |
| 2: CAR existente → reutiliza | ✅ PASSED |
| 3: ExploracaoRural → cria PropriedadeImovel | ✅ PASSED |
| 4: Sem dado fundiário → não cria | ✅ PASSED |
| 5: Sync idempotente | ✅ PASSED |
| 6: SIGEF → cria ImovelRural | ✅ PASSED |
| 7: Matrícula → cria ImovelRural | ✅ PASSED |

**Total: 13/13 PASSED**

### TypeScript
`pnpm exec tsc --noEmit` — sem erros (frontend não alterado)

### git diff --check
Sem trailing whitespace ou conflitos de linha

---

## Pendências Reais

- `ImovelRural.numero_matricula` não tem `UniqueConstraint` com cartório — dois imóveis sem cartório e mesma matrícula no mesmo tenant podem coexistir. Aceitável para o escopo atual.
- `area_total_ha = 0.0000` no ImovelRural auto-criado deve ser atualizado manualmente pelo usuário via tela de Imóveis Rurais. Não é atualizado automaticamente a partir da UnidadeProdutiva.

---

## Governança Preservada

- `ImovelRural` continua sendo a única fonte oficial fundiária.
- `UnidadeProdutiva` continua sendo campo de entrada/compatibilidade.
- `PropriedadeImovel` continua sendo o vínculo canônico N:N.
- Nenhum ADR violado.
- Nenhuma migration desnecessária criada.
