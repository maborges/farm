# TERRITORY-UX-01B — Implementação da Separação Operacional e Fundiária na Interface

## 1. Resumo

Foi implementada a separação progressiva da interface operacional em `/cadastros/propriedades`, preservando a rota e os endpoints existentes de `cadastro-completo`, mas removendo da manutenção operacional a edição implícita de `ImovelRural`.

Resultado principal:

- o modal operacional agora se apresenta como `Unidade Produtiva`;
- a edição deixou de renderizar campos fundiários editáveis;
- o submit operacional passou a montar payload somente com `unidade_produtiva`;
- a tela de detalhe passou a tratar documentos fundiários como pertencentes ao card de `Imóveis Rurais Vinculados`;
- a interface passou a explicitar cenários N:N sem escolher imóvel arbitrariamente.

## 2. Estratégia implementada

Estratégia aplicada: **Opção B — Separação progressiva**.

Decisões:

- manter a rota `/cadastros/propriedades` por compatibilidade;
- manter `POST /api/v1/unidades-produtivas/cadastro-completo` e `PUT /api/v1/unidades-produtivas/{id}/cadastro-completo`;
- remover apenas a escrita fundiária da manutenção operacional;
- manter criação operacional simples e orientar vínculo/cadastro fundiário após salvar;
- reutilizar `visao-territorial` e a rota oficial do módulo de imóveis.

## 3. Comportamento anterior

- título do modal: `Nova Propriedade` / `Editar Propriedade`;
- mistura de dados operacionais e fundiários no mesmo formulário;
- inputs editáveis para `CAR`, `NIRF`, `CCIR`, `SIGEF` e `Matrícula`;
- mensagem de convergência territorial no modal operacional;
- submit podia incluir `imovel_rural` e `propriedade_imovel`;
- detalhe mostrava documentos fundiários como se fossem campos da UP;
- a listagem ainda reforçava semântica de `Propriedade`.

## 4. Comportamento novo

- título do modal: `Nova Unidade Produtiva` / `Editar Unidade Produtiva`;
- organização por blocos operacionais:
  - `Identificação operacional`
  - `Endereço da sede`
  - `Indicadores operacionais`
  - `Localização operacional`
- remoção completa dos inputs editáveis fundiários do modal operacional;
- remoção do aviso de convergência do modal;
- exibição de card somente leitura `Imóveis Rurais Vinculados`;
- suporte explícito a zero, um ou vários imóveis vinculados;
- detalhe da rota `/cadastros/propriedades/[id]` reposicionado como visão operacional da UP.

## 5. Títulos alterados

- `Propriedades` → `Unidades Produtivas` na página principal do cadastro operacional;
- `Nova Propriedade` → `Nova Unidade Produtiva`;
- `Editar Propriedade` → `Editar Unidade Produtiva`;
- `Dados Gerais` → `Resumo Operacional`;
- `Endereço` → `Endereço da sede`;
- `Localização & Status` → `Localização operacional`.

Compatibilidade preservada:

- a rota pública continua `/cadastros/propriedades`;
- o sidebar foi ajustado em label, sem alteração de rota;
- o card de cadastros também foi ajustado em label, sem alteração de navegação.

## 6. Campos removidos da edição operacional

Removidos do formulário operacional:

- `CAR`
- `NIRF`
- `CCIR`
- `SIGEF`
- `Matrícula`
- justificativa de alteração de área do imóvel principal
- aviso `Convergência Territorial`

Mantidos, porém explicitamente referenciais:

- `Área operacional informada`
- `Área calculada pela geometria`
- `APP de referência`
- `Reserva Legal de referência`
- `Área útil estimada`

## 7. Payload antes/depois

### Antes

O submit podia construir:

- `unidade_produtiva`
- `imovel_rural`
- `propriedade_imovel`

com base em:

- campos fundiários preenchidos;
- uso implícito de `territorio.imovel_principal`.

### Depois

O submit operacional utiliza `buildOperationalCadastroPayload(...)` e envia somente:

```ts
{
  unidade_produtiva: {
    ...
  }
}
```

Guardrails adicionados asseguram que o formulário operacional:

- não renderiza inputs fundiários editáveis;
- não constrói `imovel_rural: {...}`;
- não constrói `propriedade_imovel: {...}`.

## 8. Card de imóveis

Foi adicionado `ImoveisVinculadosCard` reutilizável.

Capacidades:

- zero imóveis:
  - mensagem `Nenhum Imóvel Rural vinculado.`
  - CTA para cadastrar imóvel
  - CTA para vincular imóvel existente
- um imóvel:
  - mostra nome, matrícula, CAR, município/UF, área oficial, status documental
  - CTA `Abrir Imóvel Rural`
- vários imóveis:
  - lista vínculos sem esconder secundários
  - indica `Principal` quando aplicável
  - mostra tipo de vínculo, área vinculada e percentual vinculado
- vários sem principal:
  - mostra aviso de ambiguidade
  - não escolhe imóvel automaticamente

## 9. Suporte N:N

Implementado no frontend:

- não depende só de `territorio.imovel_principal`;
- usa `visao-territorial` quando disponível;
- faz fallback controlado para overlay legado de `territorio`;
- deduplica itens por `imovel.id`;
- mantém ambiguidades visíveis em vez de escondê-las.

Cobertura unitária adicionada para:

- múltiplos imóveis sem principal;
- priorização da visão territorial sobre o overlay legado;
- zero imóveis.

## 10. Navegação

Navegações reaproveitadas:

- `Abrir Imóvel Rural` → `/cadastros/imoveis/{id}/visao-fundiaria`
- `Ver vínculos` → `/cadastros/propriedades/{id}/visao-territorial`
- `Cadastrar Imóvel Rural` → `/cadastros/imoveis?unidade_produtiva_id={id}`
- `Vincular imóvel existente` → visão territorial da propriedade/unidade produtiva

Não foi criado endpoint novo.

## 11. Permissões

Permissões respeitadas no card:

- CTA de criação de imóvel depende de `tenant:imoveis:create`;
- quando a permissão não existe, o botão aparece desabilitado;
- a tela operacional não volta a ganhar escrita fundiária por consequência da permissão operacional.

## 12. Arquivos alterados

Arquivos alterados diretamente nesta implementação:

- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/page.tsx`
- `apps/web/src/lib/sidebar-config.ts`
- `apps/web/src/types/global.d.ts`
- `apps/web/src/components/propriedade/imoveis-vinculados-card.tsx`
- `apps/web/src/components/propriedade/imoveis-vinculados-view-model.ts`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-operational-payload.ts`
- `apps/web/tests/e2e/cadastros-propriedades.spec.ts`

Arquivos adicionados:

- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-operational-payload.test.ts`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-operational-form-guardrail.test.ts`
- `apps/web/src/components/propriedade/imoveis-vinculados-view-model.test.ts`

Arquivo removido por estar sem consumidores em `apps/web/src` e `apps/web/tests`:

- `apps/web/src/components/propriedade/propriedade-dialog.tsx`

## 13. Testes

Executados com sucesso:

- `npm run typecheck`
- testes unitários via Playwright unit runner:
  - `buildOperationalCadastroPayload`
  - `buildLinkedImoveisViewModel`
  - `operational form guardrails`
- `npm run lint -- <arquivos alterados>` sem erros, com warnings
- `npm run build -- --webpack`
- `git diff --check`
- `git status --short`

Warnings de lint:

- `@next/next/no-img-element` em `propriedades-client.tsx` em dois pontos já existentes no padrão local do componente;
- warning de arquivo e2e ignorado ao chamar eslint diretamente no spec.

Validação e2e territorial:

- o spec `tests/e2e/cadastros-propriedades.spec.ts` foi atualizado;
- a execução real do e2e não pôde ser concluída neste ambiente em **Friday, July 17, 2026** porque:
  - `127.0.0.1:3000` não estava acessível por `curl`;
  - iniciar `next dev` em `127.0.0.1:3000` retornou `EADDRINUSE`;
  - iniciar `next dev` em `127.0.0.1:3002` retornou `EPERM`.

## 14. Validações

### `git diff --check`

Sem erros.

### `git status --short`

O worktree raiz já estava sujo antes desta entrega, inclusive com alterações fora de `apps/web`. A implementação respeitou esse estado e ficou restrita ao escopo frontend/documentação.

### `npm run build -- --webpack`

Build concluído com sucesso.

Mensagens observadas durante o build, sem relação comprovada com esta entrega:

- rotas fora do escopo com `Dynamic server usage` por uso de `cookies`, como:
  - `/suprimentos/compras`
  - `/suprimentos/compras/solicitacoes`
  - `/dashboard/backoffice/crm`

Essas mensagens não impediram a conclusão do build.

## 15. Riscos residuais

- a rota ainda é `/cadastros/propriedades`, por compatibilidade;
- a listagem e os indicadores agregados ainda usam áreas historicamente ambíguas, agora com labels operacionais/refenciais;
- o fluxo de `Vincular imóvel existente` ainda reaproveita a visão territorial, não um diálogo dedicado de vínculo;
- os warnings de `img` permanecem no arquivo do modal operacional;
- a execução e2e real ficou bloqueada por limitações do ambiente local em **Friday, July 17, 2026**.

## 16. Veredicto

**GO COM RESSALVAS**

A separação principal foi implementada:

- a interface operacional deixou de editar domínio fundiário;
- o submit operacional não envia `imovel_rural`;
- o card de vínculos passou a explicitar N:N;
- o piloto foi preservado com a mesma rota e os mesmos endpoints.

Ressalvas:

- o fluxo assistido de vínculo/cadastro fundiário ainda depende das rotas já existentes, não de um fluxo dedicado novo;
- a validação e2e territorial ficou parcialmente limitada pelo ambiente local de execução, apesar de typecheck, lint, build e testes unitários terem passado.
