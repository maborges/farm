# Relatório de Execução - Fase 32: Passaporte Público de Rastreabilidade com QR Code

**Tarefa**: EXECUTION-34
**Objetivo**: Criar uma experiência pública de validação de Passaporte de Rastreabilidade por link/QR Code, sem autenticação, preservando segurança, privacidade e tenant isolation.

## O que foi implementado

### 1. Backend API Pública
- **Schema `PassaportePublicoResponse`**: Criado um schema específico para expor apenas os dados não sensíveis do passaporte (código, título, data de publicação, status e token público).
- **Endpoint GET `/api/v1/public/passaportes/{public_token}`**: Endpoint de leitura pública autenticada apenas via `public_token`, sem checagem de tenant. O backend só retorna passaportes que possuam status `PUBLICADO` e flag `publico=True`.
- **Geração de Token**: A função `atualizar_status_passaporte_rastreabilidade` foi adaptada para gerar um UUID (`public_token`) e salvar o timestamp (`publicado_publicamente_em`) no momento em que um passaporte é setado para `PUBLICADO` com `publico=True`.
- **Testes Unitários**: Corrigidos os testes de integração do `public_router.py` garantindo isolamento correto com o banco assíncrono e mock de sessões com pytest.

### 2. Frontend Interface Pública
- **Página de Visualização Pública**: Desenvolvida a página dinâmica Next.js em `apps/web/src/app/public/passaportes/[token]/page.tsx`. Ela acessa os dados da API pública e apresenta os detalhes de rastreabilidade (com mock de hash de blockchain, validado pelo `snapshot_hash`).
- **Segurança de Renderização**: Por ser um Server Component e não carregar estado de sessão (`user`, `tenant_id`), a página atende aos critérios de privacidade estritos exigidos pela Fase 32.

### 3. Frontend Dashboard Autenticado
- **QR Code**: Adicionada a ação "Ver QR Code" no botão dos passaportes publicados na interface `RelatoriosPassaportesClient.tsx`. O QR Code é gerado via serviço externo (`api.qrserver.com`) apontando diretamente para o link do Passaporte Público.
- **Opção de Publicar**: Implementada ação na tabela para alterar o status do passaporte para `PUBLICADO`, instanciando a mutation correspondente do `useUpdatePassaporteStatus`. O passaporte gera a URL copiável que pode ser divulgada publicamente.
- **Type Safety**: Adicionados os novos campos `public_token`, `publico`, e `publicado_publicamente_em` nas interfaces TypeScript do frontend (`service.ts`).
- **Testes E2E (Playwright)**: Atualizado o arquivo de teste `certificacoes-esg-relatorios-passaportes.spec.ts` para cobrir o fluxo de publicação do passaporte e a abertura do modal de QR Code.

## Regras Atendidas
- ✅ Não exige login na página pública.
- ✅ O endpoint não permite nenhuma alteração (somente GET).
- ✅ Nenhuma modificação em `Propriedade`, `Imovel Rural` e `PropriedadeImovel` foi executada.
- ✅ Segurança e Tenant Isolation mantidos.

## Conclusão
A emissão do Passaporte Rastreabilidade em sua forma pública foi finalizada com sucesso, viabilizando a comprovação das qualidades do lote agrícola de forma universal e amigável.
