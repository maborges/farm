# Quarentena para revisão

Esta pasta contém arquivos retirados da raiz em 2026-10-05. Nada foi apagado.
Os itens foram classificados como artefatos gerados, instaladores locais ou scripts
pontuais sem referência ativa no projeto.

## Estrutura

- `artefatos/`: cobertura, logs, resultados de auditoria e saída de pytest;
- `configuracoes-legadas/`: configurações antigas ou com nome não convencional;
- `instaladores/`: downloads locais e instaladores que não participam do build;
- `scripts/analise/`: geradores e transformações pontuais de frontend;
- `scripts/banco/`: consultas, seeds e SQLs avulsos de manutenção;
- `scripts/correcoes/`: scripts one-shot que reescrevem código-fonte;
- `scripts/debug/`: diagnósticos manuais;
- `scripts/testes/`: scripts chamados `test_*` que estavam fora dos `testpaths`
  oficiais (`tests/` e `services/api/tests/`).

## Critérios usados

1. O arquivo não era referenciado por entrypoints, manifests ou comandos ativos.
2. Scripts de correção atuavam diretamente sobre arquivos atuais e não eram
   idempotentes; mantê-los na raiz aumentava o risco de execução acidental.
3. Testes soltos na raiz não são coletados pela configuração de `pyproject.toml`.
4. Binários baixados, logs e outputs não são dependências do projeto.

## Atenção de segurança

Alguns scripts antigos de banco contêm endpoints, IDs ou credenciais hardcoded.
Eles não devem ser executados nem retornar ao código ativo sem revisão e remoção
dessas informações. O principal caso identificado é
`scripts/banco/seed_modelos.py`.

## Arquivos preservados fora da quarentena

- configurações de build, Docker, npm/pnpm e pytest;
- `conftest.py`, pois participa da resolução de fixtures dos testes;
- documentação e arquivos de contexto dos agentes;
- `scripts/run_worker.sh`, movido da raiz para junto do entrypoint Python;
- o pacote fonte de identidade visual, movido para
  `docs/assets/branding/source/` e mantido como artefato autorizado.
