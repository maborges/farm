# Laboratório de demonstração — café 2026

Banco exclusivo `deepfarms_demo_lab`; tenant sintético `demonstracao`. A safra
fictícia cobre janeiro a novembro de 2026, em quatro talhões de 25 ha nas duas
fazendas modelo. A cultura é perene; a fase de plantio representa replantio de
falhas. As datas simuladas das fases estão em `dados_fase.data_simulada`;
`created_at` preserva a data real de registro no laboratório.

Há 24 tarefas concluídas e operações vinculadas ao caderno, dois depósitos,
dois saldos iniciais e quatro saídas de fertilizante, quatro romaneios de 750
sacas, quatro lotes e quatro vendas finalizadas com contas a receber. As vendas
usam preço fictício de R$ 1.000 por saca. Os movimentos de estoque foram
registrados na data real da carga; as operações e apropriações econômicas usam
as datas simuladas. O saldo inicial representa implantação, não compra.

O serviço `DREAgricolaV1Service` para a safra retorna receita bruta de
R$ 3.000.000, custos diretos de R$ 150.000, custos operacionais de R$ 40.000 e
resultado operacional de R$ 2.810.000. Cada fazenda representa metade desses
valores. As despesas administrativas rateadas estão nos custos operacionais:
duas estão pagas e duas em aberto. O DRE avisa que essas despesas não são
somadas novamente, pois já estão representadas no rateio. Não foram simuladas
deduções tributárias; a margem é apenas ilustrativa e não uma estimativa
econômica real. Duas receitas de venda foram recebidas e duas continuam em aberto.

As quatro saídas de fertilizante estão vinculadas à apropriação da mesma execução
e unidade de produção, sem duplicar o custo. A reconciliação aceita essa fonte
quando os vínculos coincidem e continua sinalizando diferenças de valor. As
políticas RLS acrescentadas são apenas do laboratório.

O acesso de demonstração foi provisionado para `demonstracao@deepfarms.com.br`;
a senha está no arquivo local restrito indicado ao operador. Login, `/auth/me`,
status de onboarding e abertura da tela `/dashboard/financeiro/dre` foram
verificados na interface local isolada. A tela abriu sem safra selecionada no
contexto inicial (Fazenda Modelo 2). A API autenticada retorna a safra 2026 e o
DRE, então a tela agora seleciona automaticamente a safra quando houver somente
uma opção; com várias, mantém a seleção manual. O typecheck do frontend passou.
O login via navegador e a API retornaram HTTP 200 na última repetição. A navegação
seguinte voltou à rota de login durante o teste automatizado, então não confirmei
visualmente os valores na tela após essa correção.

O perfil personalizado `demonstracao` foi criado no laboratório e vinculado ao
usuário owner. O JSON de permissão usa `{"granted": ["*"]}`, formato de wildcard
compreendido pelo backend e pelo frontend. O proxy da interface confirmou login
200, perfil `demonstracao`, `is_owner=true`, 30 módulos e wildcard frontend
ativo. Após a alteração, autentique novamente para atualizar o perfil guardado
na sessão do navegador.

## Abrir a demonstração local

Use dois terminais. Não altere `services/api/.env.local`: o launcher lê a
conexão local existente, troca o alvo para `deepfarms_demo_lab`, valida host e
database, força a role `deepfarms_demo_runtime` em cada pool e escuta apenas em
loopback.

Terminal 1 — API:

```sh
cd /opt/lampp/htdocs/farm/services/api
.venv/bin/python -m scripts.demo_lab_server
```

Terminal 2 — interface:

```sh
cd /opt/lampp/htdocs/farm/apps/web
BACKEND_URL=http://127.0.0.1:8017 NEXT_PUBLIC_API_URL=/api/v1 \
  pnpm run dev --hostname 127.0.0.1 --port 3035
```

Abra `http://127.0.0.1:3035/login`. As credenciais estão no arquivo local
restrito `/tmp/deepfarms-demo-lab-li9js4j6.txt`. Encerre cada processo com
`Ctrl+C`. O launcher falha fechado se a URL não identificar o banco dedicado.

As cargas usam os scripts `services/api/scripts/demo_lab_cafe*.py` e exigem o
alvo e a identidade do laboratório verificados por `demo_lab_common.py` e
`demo_lab_guard.py`. Os scripts não se destinam a produção.
