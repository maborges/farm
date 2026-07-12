# PERSON-PHASE-2C-DEXIE-SYNC-CATALOGO-OPERACIONAL

## 1. Contrato Backend Consumido
O bloco retornado por `GET /api/v1/sync/pull` no backend foi confirmado como contendo os campos essenciais aprovados na Fase 2B, na estrutura `pessoas_operacionais`:
- `pessoa_id`: string (UUID)
- `nome_exibicao`: string
- `unidade_produtiva_id`: string (UUID)
- `papeis`: array de strings

Nenhum PII, como CPF, cargo ou endereço, foi exposto por este payload.

## 2. Tipos Criados
Criou-se a interface local `PessoaOperacional` no Dexie (`apps/campo/src/lib/db.ts`):
```ts
export interface PessoaOperacional {
  id: string; 
  pessoa_id: string;
  nome_exibicao: string;
  unidade_produtiva_id: string;
  papeis: string[];
}
```

## 3. Chave Local Escolhida
Para possibilitar o armazenamento determinístico de uma mesma `Pessoa` em múltiplas Unidades Produtivas, definiu-se a chave primária (`id`) como sendo uma string combinada gerada pelo helper `generatePessoaOperacionalId`:
`unidade_produtiva_id:pessoa_id`

## 4. Versão Dexie
A base de dados foi incrementada para a versão `14`, garantindo a criação segura da store `pessoas_operacionais` com índices definidos sobre `id, unidade_produtiva_id, pessoa_id`. 

## 5. Stores Preservadas
Nenhum dado legado foi removido ou resetado. O update foi configurado para ser não destrutivo, preservando `caderno_events`, `caderno_server_events`, `caderno_drafts`, `sync_queue` e o legado de `colaboradores`.

## 6. Estratégia de Substituição
A store será inteiramente renovada apenas se o backend retornar o bloco `pessoas_operacionais`. A transação global limpará a store local (`await db.pessoas_operacionais.clear()`) e irá populá-la logo em seguida com os novos dados recebidos via `bulkPut`. Como a substituição está encapsulada em uma mesma Transaction Dexie que abraça todas as stores manipuladas no pull, em caso de interrupções o processo rolará um abort e não deixará o db parcialmente sincronizado.

## 7. Alterações em `pull.ts`
Foi atualizado o tipo Payload (`SyncPullPayload`) e, na transação de cache, inseriu-se o bloco para limpeza e parse seguro, incluindo normalização para deduplicar papéis através de `Array.from(new Set(p.papeis || []))`.

## 8. Compatibilidade com API antiga
Se a API legada não retornar `pessoas_operacionais`, o bloco não é modificado. 

## 9. Compatibilidade com `colaboradores`
A store `colaboradores` permanece operante em `/apps/campo/src/lib/db.ts` no `version(14)`.

## 10. Testes Executados
Como a aplicação campo ainda não possuía sistema de testes, configuramos `vitest` e `fake-indexeddb` localmente para validar a estrutura.
Os 6 testes de IndexedDB abrangeram todo escopo requerido na tarefa.

## 11. Resultados
- `npm run typecheck` - Passou com 0 erros.
- `npm run lint` - Passou com 0 erros.
- `npx vitest run` - Passou (2 test files, 6 testes).

## 12. Riscos Remanescentes
O catálogo está persistindo perfeitamente, o único risco é na Fase 2D a lógica do fallback local caso algo aconteça com a formatação offline.

## 13. Dependências da Fase 2D
A interface de usuário necessitará da função `usePessoasOperacionais(unidadeProdutivaId: string)` (que já foi disponibilizada em `src/lib/hooks/use-pessoas.ts`) para alimentar o seletor.

## 14. Recomendação de Avanço
**GO**.
A fase obedeceu estritamente aos critérios de aceite e preservou inteiramente as premissas determinísticas, de segurança e de armazenamento transacional. Autorizada a iniciação da próxima Fase (`PERSON-PHASE-2D`).
