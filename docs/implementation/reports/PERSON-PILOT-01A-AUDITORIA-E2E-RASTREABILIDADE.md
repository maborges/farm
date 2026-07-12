# PERSON-PILOT-01A — Auditoria E2E da Rastreabilidade do Executor no Caderno de Campo

## 1. Diff Auditado
O diff implementado na Fase 1 focou estritamente na introdução da coluna `executado_por_pessoa_id` (separada do `usuario_id`). 
A auditoria revelou ausência de quebras estruturais, com alterações restritas ao:
- `CadernoCampoEntrada` (SQLAlchemy).
- Pydantic schemas (EntradaCreate, EntradaResponse).
- `CadernoCampoService` (Regras de tenant e atribuição).
- Dexie (`apps/campo/src/lib/db.ts`).
- `conftest.py` (Fallback de ambiente de teste).

## 2. Matriz dos Fluxos
| Fluxo | Suporte Técnico | Veredicto |
| --- | --- | --- |
| Criação online sem executor | Sim, Nullable | GO |
| Criação online com executor válido | Sim, injeta Pessoa | GO |
| Validação Tenant-Scoped | Bloqueia mismatch | GO |
| Sincronização offline PWA | `payload_operacional` OK | GO |
| Hidratação e Extratos API | Schema atualizado | GO |

## 3. Evidências Web
A API expõe o campo `executado_por_pessoa_id` em todos os endpoints REST de Caderno. Não há duplicação com `usuario_id` ou preenchimentos indevidos. Registros antigos ou incompletos retornam `null` graciosamente.

## 4. Evidências API
As rotas de Caderno de Campo foram analisadas e não apresentam acoplamento excessivo. A validação de negócio injeta o UUID verificando se o Tenant da Pessoa é igual ao do escopo atual.

## 5. Evidências Banco (Migration)
A migration gerada automaticamente inicialmente tentou dropar tabelas legadas ausentes no escopo local. O script foi reescrito (correção cirúrgica) mantendo apenas:
```python
batch_op.add_column(sa.Column('executado_por_pessoa_id', sa.Uuid(), nullable=True))
batch_op.create_foreign_key('fk_caderno_executado_por', 'cadastros_pessoas', ['executado_por_pessoa_id'], ['id'], ondelete='SET NULL')
```
Foram executados com sucesso no banco `farms`: `alembic current`, `alembic downgrade -1` e `alembic upgrade head`.

## 6. Evidências PWA e Upgrade Dexie 12 → 13
O Dexie foi inspecionado em `db.ts`. 
A versão foi atualizada sem perdas (`this.version(13)` estendendo as stores de `12`), o que é não-destrutivo. Drafts, Eventos Offline e Oficiais suportam `executado_por_pessoa_id?`. `tsc --noEmit` e `eslint` passaram.

## 7. Análise do `conftest.py`
A injeção de DDL bruto no `conftest.py` é classificada como **temporária, mas aceitável**, visto que o framework de testes executa `Base.metadata.create_all()` ignorando arquivos do Alembic. A correção assegurou a idempotência sem impactar bancos atualizados pela migration oficial.

## 8. Testes Executados
Toda a suíte de integração e unitária do Caderno de Campo e Sincronização PWA (`test_field_core02...`, `test_field_core03...`, `test_field_core05...`, `test_field_pwa01...`) rodaram com 100% de sucesso.

## 9. Herança Automática do Executor
**Correção Cirúrgica Realizada:** Durante a auditoria, identificou-se que `CadernoCampoService.garantir_evento_operacao` não respeitava o `OperacaoExecucao.operador_id`, usando sempre o fallback de `OperacaoAgricola`. O service foi ajustado para respeitar a precedência correta:
1. `OperacaoExecucao.operador_id` (executor efetivo da janela real)
2. `OperacaoAgricola.operador_id` (fallback previsto)

## 10. Pendências (Interface de Seleção)
A API e o PWA transportam os dados, contudo, a Interface do Usuário (UI) ainda carece de componentes funcionais nos formulários web/PWA para efetivamente listar e selecionar uma Pessoa.

## 11. Decisão sobre a Fase 2
A Fase 1 comprova tecnicamente o modelo de rastreabilidade (Executor físico != Registrador logado). O banco suporta LGPD (`ON DELETE SET NULL`), Tenant-Isolation, Sync-Offline e idempotência.

---

# VEREDICTOS

- **Migration:** GO (Após correção do script para evitar falhas com schema legado)
- **Backend:** GO
- **Isolamento tenant-scoped:** GO
- **Fluxo Web (API):** GO
- **Fluxo PWA online/offline:** GO
- **Upgrade Dexie:** GO
- **Compatibilidade legada:** GO
- **Herança automática do executor:** GO (após correção do Service)
- **Interface de seleção:** GO COM RESSALVAS (Pendente desenvolvimento Frontend para expor as opções ao usuário)
- **Prontidão para o Piloto:** GO COM RESSALVAS (Exige a implementação do catálogo na UI)
- **Prontidão para a Fase 2:** GO (Pode iniciar a arquitetura de apontamentos em lote)
