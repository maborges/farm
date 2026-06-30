# RC-01B — AUDITORIA DE COLABORADOR: PESSOA × COLABORADOR RH

## 1. Resumo executivo

A codebase atual não trata `ColaboradorRH` como especializacao obrigatoria de `Pessoa`.

As evidencias encontradas mostram um modelo hibrido:

- `Pessoa` existe como cadastro canônico potencial em `services/api/core/cadastros/pessoas/`.
- `ColaboradorRH` possui `pessoa_id`, mas a FK e opcional.
- `ColaboradorRH` tambem armazena dados proprios, principalmente `nome` e `cpf`.
- RH, custos, SST, EPI, caderno de campo e Campo PWA continuam operando principalmente sobre `colaborador_id`, `trabalhador_id` e `nome_trabalhador`.
- O backend de RH nao exige `Pessoa` na criacao de colaborador.
- O frontend web de RH ja tenta caminhar para `pessoa_id`, mas isso ainda nao esta consolidado no contrato real da API.

Conclusao objetiva: para a versao 1.0, a evidencia nao sustenta tornar `Pessoa` obrigatoria imediatamente para novos `ColaboradorRH` sem antes criar uma camada de resolucao canonica de trabalhador. A classificacao arquitetural encontrada e `Modelo C`, com decisao recomendada `Opcao D`.

## 2. Inventario

| Conceito | Model/Tabela | Owner | FK para Pessoa? | Dados duplicados? | Uso | Risco |
| --- | --- | --- | ---: | ---: | --- | --- |
| Pessoa | `Pessoa` / `cadastros_pessoas` | Core Cadastros | N/A | N/A | Cadastro mestre de pessoas | Medio |
| ColaboradorRH | `ColaboradorRH` / `rh_colaboradores` | RH | Sim, opcional | Sim | RH, Campo, custos, SST, EPI | Alto |
| LancamentoDiaria | `LancamentoDiaria` / `rh_lancamentos_diarias` | RH | Nao | Nao | Diario de mao de obra e custo | Alto |
| Empreitada | `Empreitada` / `rh_empreitadas` | RH | Nao | Nao | Contratacao operacional e custo | Alto |
| EntregaSegurancaRH | `EntregaSegurancaRH` / `rh_seguranca_entregas` | RH | Indireta via `colaborador_id` | Nao | EPI e seguranca | Medio |
| DocumentoSST | `DocumentoSST` / `rh_seguranca_documentos` | RH | Indireta via `colaborador_id` opcional | Nao | SST e historico | Medio |
| EPIEntrega | `EPIEntrega` / `epi_entregas` | Agricola Caderno | Nao | Sim | Caderno e rastreabilidade operacional | Alto |
| CachedColaborador | `CachedColaborador` / IndexedDB local | Campo PWA | Nao | Sim | Cache offline de trabalhadores | Alto |
| `trabalhador_id` | Campo em `epi_entregas` e payloads | Agricola/Campo | Nao | Sim | Referencia operacional de trabalhador | Alto |
| `nome_trabalhador` | Campo em `epi_entregas` e payloads | Agricola/Campo | Nao | Sim | Compatibilidade textual e auditoria | Alto |
| `operador_id` | Campo em tarefas/campo | Campo | Nao | Parcial | Execucao operacional | Medio |
| `usuario_id` | Campo em sessao/caderno/campo | Auth/Campo | Nao | Parcial | Identidade de acesso e autoria | Medio |

## 3. Models

### 3.1 `ColaboradorRH`

Arquivo: `services/api/rh/models.py`

Evidencias principais:

- tabela `rh_colaboradores`
- `pessoa_id = Column(UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id"), nullable=True)`
- `nome = Column(String(255), nullable=False)`
- `cpf = Column(String(14), nullable=True)`
- `cargo`, `tipo_contrato`, `valor_diaria`, `valor_hora`, `data_admissao`, `data_demissao`

Leitura arquitetural:

- o model permite vinculo com `Pessoa`, mas nao o exige;
- o model duplica identidade minima do trabalhador;
- o model serve simultaneamente como cadastro de funcionario, diarista, empreiteiro, terceiro e PJ.

### 3.2 Modelos consumidores de colaborador

Ainda em `services/api/rh/models.py`:

- `LancamentoDiaria.colaborador_id` e obrigatorio
- `Empreitada.colaborador_id` e obrigatorio
- `EntregaSegurancaRH.colaborador_id` e obrigatorio
- `DocumentoSST.colaborador_id` e opcional
- `EsocialEvento` aceita `colaborador_id` opcional e `colaborador_nome`

Leitura arquitetural:

- os fluxos criticos de RH dependem diretamente de `ColaboradorRH`;
- `Pessoa` nao e a chave operacional principal desses fluxos.

### 3.3 Modelos do caderno e Campo

Arquivos:

- `services/api/agricola/caderno/models.py`
- `services/api/campo/models.py`

Evidencias:

- `EPIEntrega` armazena `trabalhador_id` opcional e `nome_trabalhador` obrigatorio
- `CadernoCampoEntrada` usa `usuario_id` para autoria de lancamento
- `TarefaCampo` possui `user_id` obrigatorio e `operador_id` opcional sem FK canônica para `Pessoa`

Leitura arquitetural:

- ha separacao entre autor do lancamento (`Usuario`) e trabalhador operacional (`ColaboradorRH` ou texto);
- a rastreabilidade do trabalhador ainda admite fallback textual.

## 4. Tabelas

Tabelas principais identificadas:

- `cadastros_pessoas`
- `rh_colaboradores`
- `rh_lancamentos_diarias`
- `rh_empreitadas`
- `rh_seguranca_entregas`
- `rh_seguranca_documentos`
- `rh_esocial_eventos`
- `epi_entregas`
- tabelas locais do Campo PWA em IndexedDB (`colaboradores`, `sessions`, `pendingEvents`)

Evidencia de intencao arquitetural:

Arquivo: `services/api/migrations/versions/rh_colaborador_nome_cpf.py`

Essa migration:

- adiciona `nome` e `cpf` em `rh_colaboradores`;
- torna `pessoa_id` opcional.

Isso confirma que a duplicacao de dados em `ColaboradorRH` nao e acidental. Ela foi introduzida deliberadamente para suportar fluxos legados e operacionais.

## 5. Rotas

Arquivos auditados:

- `services/api/rh/router.py`
- `services/api/agricola/caderno/router.py`
- `services/api/campo/router.py`

### 5.1 RH

Rotas observadas:

- `GET/POST /rh/colaboradores`
- `GET/POST /rh/diarias`
- `POST /rh/diarias/pagar-lote`
- `GET/POST /rh/empreitadas`
- `PATCH /rh/empreitadas/{id}/concluir`
- rotas de seguranca/SST/EPI baseadas em `colaborador_id`

Evidencia:

- o CRUD e os fluxos financeiros de RH sao centrados em `ColaboradorRH`;
- nao existe exigencia estrutural de `Pessoa` para entrada nesses fluxos.

### 5.2 Caderno / EPI

O caderno recebe e persiste trabalhador por:

- `trabalhador_id` opcional
- `nome_trabalhador` obrigatorio

Evidencia:

- o backend continua aceitando identidade operacional nao normalizada.

### 5.3 Campo

As rotas e modelos de campo operam com:

- sessao por `Usuario`
- operador/trabalhador por ids operacionais e payloads sincronizados

Evidencia:

- `Pessoa` nao e a fonte exigida pelo fluxo de campo.

## 6. Frontend Web

Arquivos auditados:

- `apps/web/src/app/(dashboard)/dashboard/rh/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/rh/folha-pagamento/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/rh/ponto/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/rh/empreitadas/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/rh/seguranca/SegurancaClient.tsx`
- `apps/web/src/components/agricola/caderno/EPIEntregaForm.tsx`

### 6.1 Tela principal de RH

Evidencias em `dashboard/rh/page.tsx`:

- consulta `/rh/colaboradores`
- consulta `/cadastros/pessoas`
- o formulario de novo colaborador usa `pessoa_id`, `cargo`, `tipo_contrato`, `valor_diaria`, `data_admissao`
- a listagem faz fallback de exibicao entre `colaborador.nome` e `Pessoa.nome_exibicao`

Conclusao:

- o frontend ja expressa a intencao de usar `Pessoa` como base;
- o backend publico ainda nao segue esse contrato;
- existe desalinhamento real entre UX e API.

### 6.2 Outras telas de RH e seguranca

Evidencias:

- folha, ponto, empreitadas e seguranca seguem usando `colaborador_id`
- `EPIEntregaForm.tsx` ainda pede `nome_trabalhador` textual

Conclusao:

- os consumidores web ainda dependem do modelo colaborador-centrico;
- a especializacao obrigatoria de `Pessoa` nao esta refletida na UX inteira.

## 7. Campo PWA

Arquivos auditados:

- `apps/campo/src/lib/db.ts`
- `apps/campo/src/lib/sync/pull.ts`
- `apps/campo/src/app/(campo)/campo/epi/page.tsx`

Evidencias:

- `CachedColaborador` local contem apenas `id`, `nome`, `cpf?`, `cargo?`
- nao ha `pessoa_id` no cache offline
- o sync baixa `colaboradores` nesse formato reduzido
- o fluxo offline de EPI persiste:
  - `trabalhador_id`
  - `nome_trabalhador`

Conclusao:

- o Campo PWA depende de uma projecao simplificada de `ColaboradorRH`;
- o modelo offline ainda nao suporta `Pessoa` como referencia canonica direta;
- qualquer obrigatoriedade imediata de `Pessoa` quebraria a premissa atual de compatibilidade offline se nao houver camada intermediaria.

## 8. Testes

Arquivos auditados:

- `services/api/tests/integration/test_rh.py`
- `services/api/tests/unit/agricola/test_epi_offline_sync.py`
- `services/api/tests/test_launch_core01_operational_cost_engine.py`
- `services/api/tests/unit/rh/test_seguranca_router.py`

### 8.1 RH

Os testes de integracao criam colaborador com payload independente:

- `nome`
- `tipo_contrato`
- `valor_diaria`
- `unidade_produtiva_id`
- `cargo`

Sem `pessoa_id`.

### 8.2 EPI offline

Os testes validam coexistencia de:

- `trabalhador_id`
- `nome_trabalhador`

Isso prova que a compatibilidade textual esta ativa e coberta.

### 8.3 Custos e DRE

Os testes do motor operacional criam `ColaboradorRH` diretamente e derivam:

- despesas RH
- alocacoes operacionais
- detalhamento de DRE com `RH_DIARIA` e `RH_EMPREITADA`

Conclusao:

- a base de custo de mao de obra ainda e `ColaboradorRH`;
- `Pessoa` nao participa do fluxo testado de custo operacional.

## 9. Fluxos

### 9.1 Cadastro de colaborador

Fluxo real encontrado:

`dados proprios do colaborador -> ColaboradorRH -> RH`

Observacao:

- a UI web ja tenta introduzir `Pessoa`, mas o backend continua aceitando o cadastro independente como fluxo principal comprovado.

### 9.2 Ponto / diaria

`ColaboradorRH -> LancamentoDiaria -> Despesa -> CostAllocation -> DRE`

Observacao:

- custo de mao de obra depende do colaborador operacional, nao de `Pessoa`.

### 9.3 Empreitada

`ColaboradorRH/equipe -> Empreitada -> Despesa -> CostAllocation`

Observacao:

- o fluxo economico tambem e colaborador-centrico.

### 9.4 Campo PWA

`sync -> cache local de colaboradores -> tarefa/execucao -> eventos offline`

Observacao:

- o app de campo opera sobre projeção simplificada de colaborador, sem `Pessoa`.

### 9.5 Caderno de campo / EPI

`trabalhador selecionado ou texto -> EPIEntrega/Caderno -> rastreabilidade`

Observacao:

- ainda existe trilha textual de trabalhador fora de qualquer vinculo obrigatorio com `Pessoa`.

### 9.6 SST / seguranca

`ColaboradorRH -> entrega/documento/evento -> historico`

Observacao:

- o eixo mestre segue em `ColaboradorRH`.

## 10. Arquitetura encontrada

Classificacao: **Modelo C**

> `ColaboradorRH` tem `pessoa_id`, mas ainda mantem dados proprios e pode existir sem `Pessoa`.

Justificativa baseada na codebase:

- a FK `pessoa_id` e opcional no model;
- o create schema publico nao exige nem expoe `Pessoa` como base obrigatoria;
- migration dedicada adicionou `nome` e `cpf` diretamente em `rh_colaboradores`;
- Campo PWA cacheia colaborador sem `pessoa_id`;
- Caderno e EPI aceitam `nome_trabalhador` textual;
- custos, diarias e empreitadas dependem de `colaborador_id`.

Leitura objetiva:

- `ColaboradorRH` hoje e simultaneamente funcionario, diarista, empreiteiro, terceiro e recurso operacional de custo;
- `Pessoa` nao e ainda a ancora operacional obrigatoria do trabalhador.

## 11. Riscos

Riscos estruturais identificados:

- colaborador sem pessoa correspondente
- pessoa sem colaborador correspondente
- duplicidade de `nome` e `cpf` entre `Pessoa` e `ColaboradorRH`
- divergencia entre `nome_trabalhador` textual e cadastro real
- trabalhador duplicado entre `Pessoa`, `ColaboradorRH`, `Usuario` e texto livre
- custos de mao de obra sem referencia canônica de pessoa
- SST/EPI sem rastreabilidade mestre unificada
- Campo PWA dependente de cache simplificado e legado
- desalinhamento entre frontend web de RH e contrato atual da API
- risco LGPD/PII pela distribuicao de CPF em multiplas estruturas

Risco adicional relevante:

- tornar `Pessoa` obrigatoria agora quebraria contratos implícitos ainda ativos em RH, Campo, caderno, SST, custos e testes.

## 12. Decisao

Decisao escolhida: **Opcao D — Criar camada de resolucao canonica de trabalhador antes de tornar vinculo obrigatorio.**

Justificativa:

- existe evidencia suficiente de que `Pessoa` e o candidato natural a master person data;
- nao existe evidencia suficiente de que o ecossistema consumidor ja opera de forma segura com `Pessoa` obrigatoria;
- os fluxos criticos ainda dependem de `ColaboradorRH`, `colaborador_id`, `trabalhador_id` e `nome_trabalhador`;
- Campo PWA e caderno mantem compatibilidade offline e textual que nao pode ser ignorada na v1.0.

Resposta objetiva ao objetivo desta auditoria:

`ColaboradorRH` nao deve continuar como cadastro totalmente independente a longo prazo, mas tambem nao deve se tornar especializacao obrigatoria de `Pessoa` imediatamente sem uma camada canonica intermediaria de resolucao de trabalhador.

## 13. Plano recomendado

Plano documental recomendado, sem implementacao nesta execucao:

1. Definir um resolver canonico de trabalhador com prioridade explicita:
   `ColaboradorRH.pessoa_id -> ColaboradorRH -> campos textuais legados`.
2. Mapear todos os payloads que hoje usam `colaborador_id`, `trabalhador_id`, `nome_trabalhador` e `operador_id`.
3. Introduzir leitura canonica sem remover compatibilidade com RH, Campo PWA, custos, SST e caderno.
4. Tornar `Pessoa` obrigatoria apenas para novos colaboradores quando:
   - backend de RH aceitar esse fluxo oficialmente;
   - Campo PWA sincronizar metadados canonicos;
   - formularios legados deixarem de depender de texto livre como fonte primaria;
   - testes cobrirem compatibilidade com dados antigos.
5. Depois dessa camada, avaliar consolidacao progressiva de CPF/nome para reduzir duplicidade e risco LGPD.

## 14. Pergunta final obrigatoria

**Para a versao 1.0 do AgroSaaS, `ColaboradorRH` nao deve nem continuar como cadastro totalmente independente nem ser convertido imediatamente em especializacao obrigatoria de `Pessoa`; a evidencia da codebase indica que deve existir antes uma camada de resolucao canonica de trabalhador para preservar compatibilidade com Campo, RH, custos e dados legados.**
