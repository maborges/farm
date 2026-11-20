# Carga inicial de implantação

Este diretório coordena somente dados globais necessários ao primeiro uso da
API. Não cria schema nem substitui Alembic. Execute-o somente depois que o
processo de instalação aprovado tiver criado as tabelas.

## Cargas

1. `seed_catalogos.py`: carrega unidades, categorias de produto, fases de
   operação, tipos de relacionamento e sugestões globais de tipos de serviço.
   Os dados estão definidos nos respectivos arquivos `seed_*.py` deste diretório.
   As unidades de serviço (`DIA`, `KM`, `SC`) são códigos textuais aceitos pelo
   cadastro de serviços; não são unidades conversíveis de `unidades_medida`.
2. `seed_perfis.py`: cria/atualiza somente os cinco perfis globais aprovados
   para esta carga, incluindo `Owner`, exigido pelo cadastro de um novo tenant.
   Usa IDs estáveis e interrompe a carga se já existir um perfil global com o
   mesmo nome e outro ID. Não remove outros registros existentes.
3. `seed_plans.py`: carrega o snapshot dos planos que estavam ativos no banco de
   referência (no painel, “Pausar Vendas” marca `ativo=False`). Mantém IDs fixos
   e insere somente IDs ausentes, sem reativar nem sobrescrever planos já
   existentes. O snapshot atual contém os três planos registrados como ativos;
   preços e módulos serão revisados depois da carga.
4. `seed_culturas.py`: cria o catálogo de culturas globais do sistema.
5. `seed_parametros_solo.py`: atualiza o V% padrão e cria as faixas globais de
   interpretação de solo para as culturas existentes; é executado após o seed
   de culturas.
6. `seed_crm_estagios.py`: cria os estágios padrão do pipeline CRM, sem
   duplicar nomes existentes.
7. `seed_kb.py`: cria as categorias e os artigos públicos da Base de
   Conhecimento, sem alterar conteúdo existente.
8. `seed_admin.py`: cria/verifica a identidade do administrador em `admin_users`
   e `usuarios`, além dos templates de e-mail.

O clean install e `initial_load` reutilizam as mesmas definições revisadas,
sem cópias divergentes. A revisão `deepfarms_clean_install_v1` também usa o
contrato central. O runner clean-install atualmente disponível
está vinculado ao laboratório D3F, não é um comando genérico para a Hostinger.

Seeds de agronomia, commodities, marcas/modelos, produtos, catálogo
fitossanitário e checklists são cargas opcionais por módulo e não são executados
pelo runner acima. O catálogo fitossanitário grava as
entradas como globais e deixa NDE sem valor padrão até validação técnica. Para usar o
catálogo de produtos, execute primeiro `initial_load/seed_tabelas_produto.py`
e depois `initial_load/seed_produtos.py`; os preços médios iniciais definidos no catálogo são valores
de referência, enquanto o custo médio móvel operacional é calculado por saldo
e depósito. Checklists também são opcionais por módulo. `seed_dev.py` e
`seed.py` são exclusivamente de desenvolvimento/demonstração e não devem ser
executados em produção. `seed_plan_pricing.py` também fica fora: contém faixas
ilustrativas e nomes de planos que não correspondem aos planos de
`seed_plans.py`. `seed_crm_ofertas.py` também fica fora: define outro catálogo
de módulos e preços comerciais, não aprovado para a implantação atual.
`test_map_configs.py` é apenas uma fixture demonstrativa que altera o primeiro
tenant encontrado e não deve ser usada como carga de implantação.

O template global de checklists pode ser carregado manualmente com
`python scripts/initial_load/seed_checklist_templates.py`. Ele não faz parte do
runner porque a adoção destes itens de processo é opcional por módulo.

De forma equivalente, a biblioteca opcional de modelos-base fitossanitários pode
ser carregada com `python scripts/initial_load/seed_modelos_fitossanitarios.py`
(suporta `--dry-run` para prévia sem escrita e `--replace-legacy-globals`,
bloqueado em produção, para substituir registros globais legados sem
`metadados.fonte_parametros`). Ela registra 78 modelos globais cobrindo 37 das
38 culturas canônicas de `seed_culturas.py` (`Sisal` fica fora porque sua
principal doença é oportunista de ferimentos e déficit hídrico, e não de
favorabilidade climática diária; `tenant_id = NULL`, `is_global = True`),
referenciados em publicações técnicas da Embrapa e UFV como material de consulta
e ponto de partida para cópia; o motor climático nunca avalia modelos globais
automaticamente antes que a fazenda os copie e personalize em Modelos
Fitossanitários. Como a tabela utiliza `FORCE ROW LEVEL SECURITY`, a gravação de
registros globais requer a migration `20261119_rls_global_catalog_admin_write`
(`alembic upgrade head`) aplicada; em ambientes que operam sob runtime restrito
(`REQUIRE_RESTRICTED_RUNTIME_ROLE=true`), configure `CATALOG_ADMIN_DATABASE_URL`
com uma role administrativa autorizada (`df_catalog_admin`).

Para a pecuária, a biblioteca opcional de modelos-base zoossanitários pode ser
carregada com `python scripts/initial_load/seed_modelos_zoosanitarios.py`
(também suporta `--dry-run` e `--replace-legacy-globals`, bloqueado em produção,
para substituir globais legados sem `metadados.fonte_parametros`). Ela registra
10 modelos globais de `"Estresse Térmico"` cobrindo todas as espécies canônicas de
`PADROES_ESTRESSE_TERMICO` (`tenant_id = NULL`, `is_global = True`) com
referências técnicas da Embrapa. O motor `InteligenciaPecuariaService` avalia
exclusivamente modelos habilitados pelo tenant em Modelos Zoossanitários, e a
carga global obedece às mesmas regras da migration
`20261119_rls_global_catalog_admin_write` e `CATALOG_ADMIN_DATABASE_URL`.

## Execução

Por padrão, o comando apenas mostra o plano. Para gravar as cargas:

```bash
python scripts/initial_load/run.py --execute
```

No Docker Compose, o serviço da API deve estar ativo e com o banco de destino
configurado no ambiente do container. Não execute contra produção sem confirmar
antes a identidade do banco.
