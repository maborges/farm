# Runbook: Implantação Assistida de Estoque

## Objetivo

Executar com segurança a carga inicial de estoque legado, gravando apenas `SALDO_INICIAL` com origem `IMPLANTACAO`, sem gerar `ENTRADA`, `AJUSTE` ou histórico operacional retroativo.

## Pré-requisitos

- Backend com migrations aplicadas:
  - `cd services/api`
  - `.venv/bin/alembic upgrade head`
- Frontend com acesso ao módulo `O2_ESTOQUE`
- Produto e depósito já cadastrados no tenant
- Usuário com permissão adequada:
  - criar sessão: `estoque:implantacao_assistida:create`
  - corrigir/revalidar: `estoque:implantacao_assistida:edit`
  - confirmar: `estoque:implantacao_assistida:approve`
  - cancelar: `estoque:implantacao_assistida:delete`
  - auditoria: `tenant:audit:view`

## Fluxo operacional

1. Acesse `/suprimentos/estoque/implantacao-assistida`.
2. Baixe o template CSV oficial.
3. Monte o arquivo legado com as colunas:
   - `produto_codigo`
   - `produto_nome`
   - `deposito_nome`
   - `quantidade`
   - `unidade`
   - `custo_unitario`
   - `lote`
   - `validade`
   - `observacoes`
4. Envie o CSV em `/suprimentos/estoque/implantacao-assistida/nova`.
5. Gere a prévia.
6. Persista a sessão.
7. Corrija linhas com `ERRO` e revise `AVISO`.
8. Revalide a sessão.
9. Consulte a aptidão de confirmação.
10. Confirme a sessão apenas quando:
    - houver ao menos um item confirmável;
    - não houver `ERRO` não ignorado;
    - o responsável aceitar explicitamente a gravação como `SALDO_INICIAL`.
11. Após confirmar, confira:
    - saldos em `/suprimentos/saldos`;
    - movimentações filtradas por `origem_tipo=IMPLANTACAO`;
    - auditoria da sessão.

## Checklist de validação

- O CSV pertence ao tenant correto.
- Produto e depósito existem no tenant.
- Depósito pertence à unidade produtiva esperada quando a sessão estiver contextualizada.
- Itens duplicados por `produto + depósito` foram resolvidos antes da confirmação.
- Avisos foram conscientemente aceitos.
- A sessão não está `CANCELADO`.
- A sessão ainda não foi `CONFIRMADO`.

## Evidências esperadas após confirmação

- Sessão com status `CONFIRMADO`
- `confirmado_em` e `confirmado_por` preenchidos
- Movimento em `estoque_movimentos` com:
  - `tipo_movimento = SALDO_INICIAL`
  - `origem = IMPLANTACAO`
  - `origem_id` referenciando a implantação
- Auditoria com ação `confirm_session`

## Casos críticos

- CSV duplicado: deve ser bloqueado por hash no mesmo tenant.
- Produto de outro tenant: deve falhar na validação/resolução.
- Depósito de outra unidade produtiva: deve falhar na correção/confirmação.
- Sessão confirmada duas vezes: deve falhar sem duplicar `SALDO_INICIAL`.
- Custo ausente: permitido como `AVISO`, nunca como alteração implícita.
- Arquivo inválido ou vazio: deve falhar no preview.

## Troubleshooting

- `relation "estoque_implantacao_sessoes" already exists` em ambiente local:
  - aplicar `alembic upgrade head` com as migrations idempotentes atuais; não recriar tabelas manualmente.
- Falha por constraint de origem em `estoque_movimentos`:
  - verificar se o banco local tem legado com `origem='LEGADO'`;
  - a migration atual preserva `LEGADO` e inclui `IMPLANTACAO`.
- Sessão não aparece na listagem:
  - confirmar `tenant_id` no contexto ativo e permissão `...:list`.

## Fora do escopo deste fluxo

- importar histórico antigo de movimentações;
- criar produto automaticamente;
- criar depósito automaticamente;
- gerar `ENTRADA` ou `AJUSTE` operacional;
- gerar impacto financeiro direto.
