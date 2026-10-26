# AGRO-ADMIN-01H2D0 — Viabilidade de Homologação por Clone PostgreSQL Isolado

**Modalidade:** auditoria de viabilidade, somente leitura  
**Veredicto:** **NO-GO para clonar com as fontes atualmente evidenciadas**

## 1. Fontes elegíveis e inventário de evidências

Foram lidos integralmente os relatórios 01H2B1, 01H2C, 01H2C1 e 01H2C2. A inspeção ficou restrita aos relatórios, exemplos de configuração e nomes/valores de conexão necessários para reconhecer o destino; nenhum banco foi consultado nesta fase.

| Fonte possível | Evidência existente | Elegibilidade atual |
|---|---|---|
| PostgreSQL de desenvolvimento/local | `services/api/.env.local` contém uma URL PostgreSQL para o host `192.168.0.2`, database `farms`, sem porta explicitada na URL. O relatório MIGRATION-METADATA-01D, de auditoria anterior e read-only, registra no servidor `farms` e `postgres` como databases disponíveis e uma tentativa de `CREATEDB` negada. 01H2B1 classifica o destino local como compartilhado e proibido para o laboratório. | **Não elegível para uso direto ou clone agora.** Destino compartilhado; não há confirmação atual de estado, versão, revision, conteúdo, sanitização nem autorização de exportação. |
| Backup exclusivamente sintético | Nenhum caminho, manifesto, evidência de origem ou backup sintético foi identificado nos documentos/configurações inspecionados. | **Elegibilidade pendente.** É a alternativa preferível se for comprovado que o backup contém somente dados fabricados e nenhum segredo. |
| Clean install da baseline | 01H2C2 mantém o clean install bloqueado: revisão Alembic histórica, duas linhagens não reconciliadas e efeitos DDL/DML/seeds ainda não classificados. | **Não disponível.** Clone não resolveria o blocker do clean install nem provaria sua correção. |

O `DATABASE_URL` local contém credencial configurada. O valor não é reproduzido neste relatório e não deve ser copiado para o laboratório. Não se avaliou se há outros segredos, dados pessoais, comerciais, tokens ou credenciais armazenados nas tabelas. A ausência deles **não está comprovada**.

### Estado PostgreSQL e compatibilidade

- **Versão PostgreSQL:** não identificada por evidência documental/configuração. A auditoria 01D registrou comandos de consulta, não evidência suficiente aqui para atribuir versão. Nenhuma consulta foi repetida.
- **Estado de `farms`:** existe evidência histórica de servidor/database compartilhado e de comparação de catálogo contra referência datada de 2026-09-08. Isso não demonstra o estado atual do schema nem sua adequação ao checkout atual.
- **Revisão Alembic registrada na origem:** desconhecida. Os relatórios 01D/01D2 listam `alembic current` como etapa futura; não há resultado comprovado da origem que possamos usar.
- **Models do checkout:** a análise 01H2C2 registra metadata atual com 377 models e 348 tabelas selecionadas. Isso não comprova que o schema compartilhado seja compatível; os relatórios de baseline destacam diferença de versão e ausência de prova PostgreSQL atual.
- **Dados reais/credenciais:** configuração de acesso com credencial presente; conteúdo de dados e credenciais persistidas é desconhecido. Portanto, não há base para afirmar que uma cópia seria sanitizada.

## 2. Comparação das alternativas

| Alternativa | Pré-requisitos | Riscos/limitações | Prazo técnico relativo | Avaliação |
|---|---|---|---|---|
| **A. Clone sanitizado do desenvolvimento** | Aprovação do proprietário da origem; inventário de dados e segredos; metodologia de sanitização comprovável antes da transferência; exportação allowlist; destino isolado; validação de catálogo e revisão Alembic | A origem é compartilhada e contém credencial de conexão; os dados podem ser pessoais/comerciais. Sanitizar só depois de transferir uma cópia bruta não satisfaz o requisito. Não prova clean install nem recupera migrations omitidas. | **Alto** enquanto não houver classificação e transformação segura; indeterminado | **NO-GO agora**. Só reavaliar se for possível demonstrar sanitização pré-transferência e autorização. |
| **B. Restauração de backup exclusivamente sintético** | Backup rastreável com atestado de que todos os dados são fabricados; inventário de schema, revision, versão PG e segredos; restauração em PostgreSQL dedicado | Um dump “de teste” pode conter dados reais/segredos se não houver proveniência. Não prova instalação vazia. A restauração pode precisar de versão/extensões/roles compatíveis. | **Baixo a médio**, caso exista e sua proveniência esteja pronta; no momento não localizado | **Recomendada como próxima opção a investigar**, ainda não elegível até comprovação documental. |
| **C. Clean install após regularização do baseline** | Resolver topologia Alembic, DDL/DML/seeds históricos, UNIQUE/CHECK, versão do `alembic_version`; prova em PostgreSQL descartável | Atualmente bloqueado. Não fornece dados de negócio e não prova migração/upgrades por si só. | **Alto** e indeterminado, condicionado à engenharia da baseline | **NO-GO atual**, independente do clone. |

Se um backup sintético existente for comprovado, **B é a estratégia recomendada** para homologação funcional inicial. Não foi localizado um backup elegível nesta auditoria. A alternativa A não é recomendada sem sanitização comprovada antes do transporte dos dados.

## 3. Procedimento de sanitização para eventual clone

Este procedimento é uma condição futura, não uma autorização para copiar:

1. Proprietário de dados e responsável de segurança aprovam a origem, propósito, escopo de tabelas e retenção.
2. Inventariar tabelas, colunas, arquivos, funções de integração e configurações que possam conter PII, informação comercial, tokens, hashes, documentos, anexos, geolocalização ou segredos.
3. Classificar o conteúdo sem exportar valores. Se não houver classificação verificável, abortar.
4. Produzir um artefato **já sanitizado antes da transferência** usando uma transformação revisada, allowlist de tabelas/colunas e dados sintéticos determinísticos. Remover/rotacionar credenciais, sessões, tokens, hashes de autenticação, emails/telefones/CPFs, documentos, anexos e dados indiretos identificáveis. Não transportar logs/filas/outbox com payloads reais.
5. Validar o artefato sanitizado no ambiente controlado, ainda antes de disponibilizá-lo à homologação: varredura automatizada de padrões sensíveis, contagens por tabela, auditoria de arquivos e confirmação de que os dados restantes são sintéticos. Registrar digest e revisão do processo sem registrar valores.
6. Se a sanitização não puder ser executada e provada antes da transferência, não exportar nem restaurar a origem. Usar somente backup sintético comprovado ou aguardar clean install.

Não é aceitável restaurar uma cópia bruta na instância de homologação e sanitizá-la depois: nesse ponto os dados já foram transferidos para o laboratório.

## 4. Plano de isolamento

Se uma fonte aprovada surgir, provisionar **uma nova instância PostgreSQL dedicada**, bind apenas em `127.0.0.1:5433`, database próprio de homologação e role exclusivo, sem permissões ou credenciais do database original. A configuração deve ser construída a partir do exemplo, sem copiar dotenv comercial.

- PostgreSQL: dedicado e identificado por database/user/host/porta antes de qualquer restauração.
- Redis: instância independente em `127.0.0.1:6380`, senha sintética e marcador próprio; nunca reutilizar o Redis local/comercial.
- Storage: `/tmp/deepfarms-agro-hml-<id>/uploads` novo, permissões restritas, sem mount ou diretório de uploads comercial.
- APIs: somente loopback nas portas `8001` e `8002`, com envs específicos e `STAGING_INSTANCE_ID` igual ao manifesto.
- Backoffice/PWA: `3001` e `3005`, URLs internas apontando às APIs do laboratório.
- Credenciais: chaves de aplicação sintéticas; nenhuma chave de provedor, gateway, pagamento, TARA, Sankhya ou segredo originário. Integrações externas desligadas ou substituídas por mocks.
- Egress: bloquear destinos de produção e chamadas faturáveis. Nenhum RDS, DNS/endpoint comercial ou serviço produtivo configurado.
- Descarte: capturar evidências redigidas; parar somente processos identificados como laboratório; remover database/instância, Redis e storage exclusivos conforme autorização de descarte. Não remover serviços compartilhados.

Portas não provam isolamento: a instância lógica, usuário, database, caminho de arquivos e serviço Redis também precisam ser exclusivos.

## 5. Critérios de compatibilidade no destino

Antes de iniciar aplicações, comparar o destino com um manifesto de origem sanitizado e a versão do checkout:

1. Confirmar identidade do servidor e database, versão PG, usuário, porta, permissões, extensões e ausência de acesso ao host original.
2. Ler `farms.alembic_version` em read-only; registrar revision(s) e confirmar que o revision ID existe no checkout. Ausência ou revision desconhecida é bloqueio. Não rodar `stamp`, migrations, downgrade ou reparo automático.
3. Comparar tabelas/colunas e defaults com os models/contrato atuais; listar diferenças sem alterá-las.
4. Comparar UNIQUE, CHECK, FKs e índices por nome/definição, incluindo integridade referencial e colisões.
5. Comparar ENUMs/labels, sequences/ownership, schema `farms`, RLS enabled/forced, policies, funções e triggers.
6. Verificar configuração de autenticação e usuários sintéticos: não usar credenciais de usuários existentes. Preferir um tenant e contas sintéticas criadas conforme o procedimento aprovado, sem copiar identidades reais.
7. Confirmar que dependências requeridas pelo DeepFarms Agro estão presentes: tabelas/campos de conta/tenant, sessões/autenticação, configurações/feature flags, cotas climáticas, mercado/DERAL, dashboard e storage local.
8. Registrar resultado como compatibilidade do clone com o checkout (GO/NO-GO por objeto). Uma diferença não será “corrigida” por migration nesta etapa.

Dados sanitizados ainda podem não representar combinações de estado reais; compatibilidade funcional do clone não substitui criação limpa nem upgrade de produção.

## 6. Cobertura funcional possível

Após todos os gates e autorização de execução, o clone/backup sintético pode suportar:

- autenticação e cadastro usando usuários/tenants sintéticos;
- sessões, cookies e heartbeat em duas APIs independentes;
- Redis compartilhado entre processos, rate limits, cache e cotas concorrentes com provedores simulados;
- configurações, feature flags e permissões;
- Mercado e snapshots DERAL com fixtures locais;
- bibliotecas globais, dashboard e matriz de homologação;
- storage local isolado;
- rotas offline/sincronização realmente implementadas na PWA.

Um clone de schema compatível permite observar comportamento com dados relacionais representativos. Não permite declarar que o baseline cria banco vazio corretamente, nem comprova upgrades a partir de um database novo. Clean install e homologação funcional são evidências distintas.

## 7. Sequência proposta de homologação (não executada)

1. Aprovar formalmente origem e estratégia de sanitização; preferir backup sintético comprovado.
2. Provisionar PostgreSQL/Redis dedicados, role exclusivo, storage novo e firewall/egress restritos.
3. Transferir/restaurar somente artefato já sanitizado e autorizado; não tocar na origem.
4. Verificar identidade, proveniência, revisão Alembic, vazio/escopo esperado e catálogo completo; interromper diante de qualquer divergência sem correção automática.
5. Aplicar gate de isolamento e gerar envs sintéticos; confirmar que o destino efetivo não é comercial/produção.
6. Somente após GO/autorizações, inicializar duas APIs em `8001/8002`, Backoffice em `3001` e PWA em `3005`.
7. Rodar autenticação/heartbeat, compartilhamento Redis, cotas concorrentes, configuração/flags, mercado/DERAL, dashboard, storage e cenários offline/sync.
8. Guardar logs, checksums e resultados sem DSNs, tokens, PII ou payloads sensíveis.
9. Encerrar os processos identificados, arquivar evidência redigida e descartar apenas os recursos dedicados do laboratório.

Nenhuma etapa acima foi executada.

## 8. Bloqueios e riscos

- A origem local conhecida aponta para PostgreSQL compartilhado e tem credencial configurada; não pode ser fonte direta.
- Estado atual, versão PostgreSQL e revision Alembic da origem não foram comprovados.
- Presença/ausência de PII, dados comerciais e segredos nas tabelas/arquivos é desconhecida.
- Nenhuma metodologia nem artefato de sanitização pré-transferência foi encontrado.
- Backup exclusivamente sintético não localizado.
- PostgreSQL/Redis dedicados nas portas de laboratório não foram comprovados disponíveis; 01H2C registra `redis-server`/`redis-cli` ausentes do PATH naquela verificação, não uma confirmação de estado atual.
- Clean install permanece bloqueado por 01H2C2 e não é resolvido por clone.
- Diferenças estruturais ou funcionais no clone não autorizam migrations nem repairs automáticos.

## 9. Veredicto e condições de reavaliação

**Veredicto: NO-GO para clone ou homologação agora.** Não há fonte elegível comprovada, não existe prova de sanitização anterior à transferência e faltam identidade/revision/versão do alvo. A origem local compartilhada não deve ser copiada.

Reavaliar primeiro a alternativa **B** quando for apresentado backup com proveniência sintética verificável, ou a alternativa **A** depois de aprovada uma transformação que gere artefato sanitizado antes de qualquer transferência. Em ambos os casos exigir PostgreSQL e Redis dedicados, identidade/catalog validation e autorização operacional. A futura homologação funcional não substitui a prova de clean install.

Nenhum dump, restore, cópia, conexão, migration, serviço, alteração de código/configuração comercial, commit, push, merge ou deploy foi executado nesta fase. Aguardar autorização.
