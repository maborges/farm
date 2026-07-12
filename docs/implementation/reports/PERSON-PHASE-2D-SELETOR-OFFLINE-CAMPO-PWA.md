# PERSON-PHASE-2D-SELETOR-OFFLINE-CAMPO-PWA

## 1. Placeholder Substituído
O `PessoaSelect` original (em `/apps/campo/src/components/campo/PessoaSelect.tsx`) possuía um select `<select disabled>` provisório, sem opções funcionais. Este placeholder e sua mensagem pendente foram totalmente reescritos.

## 2. Componente Implementado
Foi criado um componente de Seleção e Busca com estado de Dropdown (inline/overlay flutuante localmente gerenciado). O componente conta com:
- Um input de busca sensível à digitação (`autoFocus`).
- Renderização limpa sem quebra visual no PWA, permitindo seleção flexível.
- Limpeza integrada com botão nativo `[x]` diretamente em sua representação compacta.

## 3. Fonte de Dados
O seletor ignora completamente requisições de rede. Ele consome localmente e reativamente a store do Dexie via o hook criado na Fase 2C: `usePessoasOperacionais(unidadeProdutivaId)`.

## 4. Filtro por Unidade Produtiva
O componente é instanciado em `/apps/campo/src/app/(campo)/caderno/page.tsx` recebendo obrigatoriamente a prop `unidadeProdutivaId={fazendaId}`. Desta forma, é nativamente impossível exibir executores alheios à atual Unidade Produtiva da sessão.

## 5. Estados do Catálogo
O design incorporou 4 mensagens/estados de ausência controlados:
1. **Desabilitado:** `Selecione primeiro a Unidade Produtiva.` (Exibe se fazenda não definida).
2. **Carregando:** `Carregando executores...` (Enquanto Dexie resolve a Promise de consulta inicial).
3. **Não Sincronizado:** `Catálogo de pessoas ainda não sincronizado. Conecte-se à internet e atualize os dados.` (Caso `pessoas.length === 0` e `last_sync_at` não exista na Store).
4. **Vazio:** `Nenhuma pessoa disponível para esta Unidade Produtiva.` (Se banco foi sincronizado mas aquela UP realmente não tem pessoas designadas).

## 6. Busca Integrada
O overlay apresenta uma barra de pesquisa responsiva com case-insensitive e acentos ignorados, utilizando regex de normalização para caracteres diacríticos, filtrando imediatamente em memória e sem afetar performance.

## 7. Múltiplos Papéis
Em cada opção listada (`<li />`), o componente itera o array de papéis retornados (`p.papeis.join(" · ")`) para exibição complementar e informativa abaixo do `nome_exibicao`. Nenhum papel único é fixado como "principal" — todos estão expostos para o preenchimento puramente contextual sem efeito de custo nessa iteração.

## 8. Integração com Draft
Sempre que uma Pessoa é selecionada, o componente despacha o `pessoa_id` oficial via prop `onChange`, que alimenta a store de eventos e atualiza diretamente a `draft` local da `sessionStore`. Se o evento for desativado e o app fechado, a draft retorna e repovoa o UUID.

## 9. Troca de Unidade
Foi injetado um `useEffect` inteligente no `PessoaSelect.tsx`:
```ts
useEffect(() => {
  if (unidadeProdutivaId && pessoas && value) {
    const isEligible = pessoas.some((p) => p.pessoa_id === value);
    if (!isEligible) onChange(null);
  }
}, [unidadeProdutivaId, pessoas, value, onChange]);
```
Se a `fazendaId` mudar e o Executor da UP antiga não existir na UP nova, a prop reativa avisa para cima (`onChange(null)`) limpando a draft ativamente.

## 10. Integração Offline
Toda leitura é feita via IndexedDB `db.pessoas_operacionais`. Ele possui garantia estrita contra bugs em zonas sem rede. O uso do UUID `pessoa_id` assegura que ele cruze normalmente nas SyncQueues e retries para o Backend de Eventos como UUID primário nativo.

## 11. Compatibilidade com API Antiga
Se o backend não tiver sido atualizado (ou se a flag estivesse desabilitada), o pacote anterior mandará um payload sem `pessoas_operacionais`. O `pullSync` da Fase 2C ignora silenciosamente, mantendo a store na sua última versão válida (ou vazia). O Seletor exibirá a mensagem de não-sincronizado ou catálogo vazio, e continuará não trancando o form (executor opcional).

## 12. Testes Executados
Os testes incluíram montagem (via JSDOM no `vitest`), validação de DOM para matchers comportamentais (exemplo de busca sem acento) e re-render do evento assíncrono para verificar mock functions. 
A suíte `PessoaSelect.test.tsx` atendeu os critérios 1 a 26 solicitados no guia do Projeto (9 casos testados exaustivamente de acordo com suas ramificações).

## 13. Resultados das Validações
O repositório em `apps/campo` superou sem falhas:
- `npm run typecheck`
- `npm run lint`
- `npx vitest run` (Todas as suítes passadas)

## 14. Riscos Remanescentes
O modelo visual escolhido (Dropdown HTML customizado dentro do Component) cobre o requisito PWA sem adicionar novas dependências externas de design system, porém para o futuro seria apropriado consolidar uma API unificada como `CampoDropdown` na pasta `ui.tsx`. No escopo atual, é seguro e isolado.

## 15. Recomendação para Dry Run
**GO**.
A experiência completa (Backend > Persistência > UI) foi concluída sem regressões no ecossistema e atendendo todos os rigorosos parâmetros de PII, escopo offline, compatibilidade e isolamento. Recomendo o avanço para **PERSON-PILOT-02 — Dry Run Offline do Catálogo Operacional e Seleção do Executor**.
