# RC-01 — Auditoria Profunda do Domínio Pessoas

## 1. Resumo executivo

Esta auditoria encontrou um **modelo híbrido** para o domínio Pessoas no AgroSaaS.

Existe uma fonte canônica clara em `services/api/core/cadastros/pessoas/`, centrada em:

- `Pessoa` (`cadastros_pessoas`)
- `PessoaDocumento`
- `PessoaContato`
- `PessoaEndereco`
- `PessoaBancario`
- `TipoRelacionamento`
- `PessoaRelacionamento`

Essa estrutura já modela explicitamente a ideia de **Pessoa + papéis** e já é consumida por partes relevantes da plataforma, especialmente:

- Comercialização
- Financeiro
- Frota / Operacional
- Pecuária
- Frontend de cadastros centrais

Porém, a adoção ainda não é uniforme. A codebase mantém, ao mesmo tempo:

- entidades legadas/especializadas com dados próprios;
- campos textuais de compatibilidade;
- cadastros independentes sem vínculo obrigatório com `Pessoa`;
- identidade de usuário separada da entidade de pessoa.

As principais evidências são:

- `Fornecedor` ainda existe como tabela própria em `compras_fornecedores`, embora já possa apontar para `pessoa_id`;
- `ColaboradorRH` ainda aceita criação independente por `nome` e `cpf`, com `pessoa_id` opcional;
- `Usuario` carrega dados civis (`cpf`, `telefone`, `nome_completo`) sem FK para `Pessoa`;
- `LeadCRM` mantém nome, empresa, documento e contato em tabela própria, sem reutilizar `Pessoa`;
- `Despesa` e `Receita` ainda mantêm `fornecedor` e `cliente` como texto livre, embora documentem preferência por `pessoa_id`.

Conclusão objetiva:

- **Existe uma fonte canônica candidata para Master Person Data:** `Pessoa`.
- **Ela ainda não é a única fonte de verdade operacional do sistema.**
- **Há inconsistências estruturais suficientes para impedir afirmar que o domínio Pessoas já está pronto como Master Person Data definitivo da versão 1.0.**

Decisão desta auditoria: **Opção C**.

---

## 2. Escopo auditado

### Backend auditado

- `services/api/core/`
- `services/api/rh/`
- `services/api/financeiro/`
- `services/api/operacional/`
- `services/api/pecuaria/`

### Frontend auditado

- `apps/web/`
- `apps/campo/`

### Diretórios solicitados mas não encontrados como módulos próprios

Não foram encontrados diretórios dedicados para:

- `services/api/comercializacao/`
- `services/api/crm/`
- `services/api/esg/`
- `services/api/certificacoes/`
- `services/api/auth/`
- `services/api/users/`
- `services/api/security/`

Na codebase atual:

- Comercialização está sob `services/api/financeiro/comercializacao/`
- CRM está em `services/api/core/models/crm.py`
- Auth/usuários está em `services/api/core/models/auth.py` e rotas/serviços de `core`
- Certificações/ESG aparecem em migrations, testes e frontend, sem um módulo backend separado dentro dos diretórios solicitados

---

## 3. Arquitetura encontrada

### Classificação

**C) Modelo híbrido**

### Justificativa baseada na codebase

O sistema já possui uma arquitetura explícita do tipo:

`Pessoa -> Papéis/Relacionamentos -> Consumidores`

Isso aparece no conjunto:

- `cadastros_pessoas`
- `cadastros_tipos_relacionamento`
- `cadastros_pessoa_relacionamentos`

Mas essa arquitetura convive com:

- cadastros próprios de módulos;
- dados duplicados em tabelas especializadas;
- compatibilidade por texto livre;
- identidade/autenticação desacoplada de `Pessoa`.

Portanto, a arquitetura real não é puramente:

- nem “Pessoa + roles” já consolidado de ponta a ponta;
- nem “cadastros totalmente independentes”;
- e sim um estado de transição híbrido.

---

## 4. Inventário completo

| Conceito | Model | Tabela | Owner | Uso atual | Status | Risco |
| --- | --- | --- | --- | --- | --- | --- |
| Pessoa | `Pessoa` | `cadastros_pessoas` | Core / Cadastros | Cadastro mestre de indivíduo ou organização | Ativo e canônico em intenção | Médio |
| Documento de Pessoa | `PessoaDocumento` | `cadastros_pessoas_documentos` | Core / Cadastros | CPF/CNPJ/IE e afins | Ativo | Baixo |
| Contato de Pessoa | `PessoaContato` | `cadastros_pessoas_contatos` | Core / Cadastros | E-mail, telefone, WhatsApp | Ativo | Baixo |
| Endereço de Pessoa | `PessoaEndereco` | `cadastros_pessoas_enderecos` | Core / Cadastros | Endereços operacionais/fiscais | Ativo | Baixo |
| Bancário de Pessoa | `PessoaBancario` | `cadastros_pessoas_bancario` | Core / Cadastros | Dados bancários | Ativo | Baixo |
| Tipo de Relacionamento | `TipoRelacionamento` | `cadastros_tipos_relacionamento` | Core / Cadastros | Catálogo de papéis como FORNECEDOR, CLIENTE, FUNCIONARIO | Ativo | Baixo |
| Relacionamento de Pessoa | `PessoaRelacionamento` | `cadastros_pessoa_relacionamentos` | Core / Cadastros | Liga pessoa a papel e unidade produtiva | Ativo | Baixo |
| Consentimento LGPD | `PessoaConsentimento` | `cadastros_pessoas_consentimentos` | Core / Cadastros | LGPD | Ativo | Baixo |
| Log de acesso PII | `PessoaAcessoLog` | `cadastros_pessoas_acesso_log` | Core / Cadastros | Auditoria de acesso | Ativo | Baixo |
| PII de Pessoa | `PessoaPII` | `cadastros_pessoas_pii` | Core / Cadastros | Dados sensíveis separados | Ativo | Médio |
| Fornecedor | `Fornecedor` | `compras_fornecedores` | Operacional / Compras | CRUD legado de fornecedor com ponte para `Pessoa` | Ativo e híbrido | Alto |
| Colaborador | `ColaboradorRH` | `rh_colaboradores` | RH | Colaborador/funcionário operacional | Ativo e híbrido | Alto |
| Usuário | `Usuario` | `usuarios` | Core / Auth | Credencial e identidade de acesso | Ativo e independente de `Pessoa` | Alto |
| Vínculo Usuário-Tenant | `TenantUsuario` | `tenant_usuarios` | Core / Auth | Membro do tenant | Ativo | Médio |
| Vínculo Usuário-Unidade | `UnidadeProdutivaUsuario` | `unidade_produtiva_usuarios` | Core / Auth | Escopo por unidade produtiva | Ativo | Médio |
| Perfil de Acesso | `PerfilAcesso` | `perfis_acesso` | Core / Auth | Perfil/permissões | Ativo | Baixo |
| Lead CRM | `LeadCRM` | `crm_leads` | Core / CRM | Prospect comercial pré-conversão | Ativo e independente | Médio |
| Atividade CRM | `AtividadeCRM` | `crm_atividades` | Core / CRM | Follow-up de lead | Ativo | Baixo |
| Pipeline CRM | `PipelineEstagio` | `crm_pipeline_estagios` | Core / CRM | Estágios do pipeline | Ativo | Baixo |
| Comprador de comercialização | FK `comprador_id -> Pessoa` | `financeiro_comercializacoes` | Financeiro / Comercialização | Compra/venda agrícola usa pessoa canônica | Ativo e canônico | Baixo |
| Cliente financeiro | FK `pessoa_id` + texto `cliente` | `fin_receitas` | Financeiro | Contas a receber | Ativo e híbrido | Médio |
| Fornecedor financeiro | FK `pessoa_id` + texto `fornecedor` | `fin_despesas` | Financeiro | Contas a pagar | Ativo e híbrido | Médio |
| Trabalhador EPI/Caderno | `ColaboradorRH` + campos textuais | `caderno_campo_entradas` / payloads | Campo PWA / Agrícola | Fluxos de EPI e caderno | Ativo e legado operacional | Alto |

---

## 5. Entidades encontradas

### Fonte canônica explícita

O model `Pessoa` contém a descrição:

> “Entidade central: qualquer indivíduo ou organização relacionada ao tenant.”

Isso é a evidência mais forte de intenção arquitetural.

Além disso, `TipoRelacionamento` e `PessoaRelacionamento` materializam papéis como:

- fornecedor
- cliente
- funcionário
- prestador
- parceiro

Logo, o domínio central de pessoas já foi pensado para suportar múltiplos papéis sem multiplicar cadastros.

### Entidades paralelas ou especializadas

As entidades abaixo continuam ativas com dados próprios:

- `Fornecedor`
- `ColaboradorRH`
- `Usuario`
- `LeadCRM`

Elas não são apenas projeções de leitura. Elas têm:

- model próprio;
- armazenamento próprio;
- rotas/CRUD próprios ou uso funcional próprio;
- campos redundantes em relação a `Pessoa`.

---

## 6. Models

### Core / Cadastros

Arquivo principal:

- `services/api/core/cadastros/pessoas/models.py`

Models relevantes:

- `Pessoa`
- `PessoaDocumento`
- `PessoaContato`
- `PessoaEndereco`
- `PessoaBancario`
- `TipoRelacionamento`
- `PessoaRelacionamento`
- `PessoaConsentimento`
- `PessoaAcessoLog`
- `PessoaPII`

### Compras

Arquivo principal:

- `services/api/operacional/models/compras.py`

Model relevante:

- `Fornecedor`

Achado principal:

- `Fornecedor` possui `pessoa_id`, mas continua armazenando nome, documento e contatos próprios.

### RH

Arquivo principal:

- `services/api/rh/models.py`

Model relevante:

- `ColaboradorRH`

Achados principais:

- `pessoa_id` existe, mas é opcional;
- `nome` e `cpf` também são persistidos em `rh_colaboradores`;
- a especialização não é estritamente derivada de `Pessoa`.

### Auth / Usuários

Arquivo principal:

- `services/api/core/models/auth.py`

Models relevantes:

- `Usuario`
- `PerfilAcesso`
- `TenantUsuario`
- `UnidadeProdutivaUsuario`
- `ConviteAcesso`
- `TokenRecuperacaoSenha`
- `TentativaLogin`

Achado principal:

- `Usuario` armazena `cpf`, `telefone` e `nome_completo`, mas não referencia `Pessoa`.

### CRM

Arquivo principal:

- `services/api/core/models/crm.py`

Models relevantes:

- `LeadCRM`
- `AtividadeCRM`
- `PipelineEstagio`

Achado principal:

- `LeadCRM` mantém dados de pessoa/empresa próprios, sem integração nativa com `Pessoa`.

### Financeiro

Arquivos relevantes:

- `services/api/financeiro/models/despesa.py`
- `services/api/financeiro/models/receita.py`
- `services/api/financeiro/comercializacao/models.py`

Achados principais:

- `Despesa.pessoa_id` substitui fornecedor textual quando disponível;
- `Receita.pessoa_id` substitui cliente textual quando disponível;
- `ComercializacaoCommodity.comprador_id` aponta diretamente para `cadastros_pessoas.id`.

---

## 7. Tabelas

### Tabelas centrais de pessoas

- `cadastros_pessoas`
- `cadastros_pessoas_documentos`
- `cadastros_pessoas_contatos`
- `cadastros_pessoas_enderecos`
- `cadastros_pessoas_bancario`
- `cadastros_tipos_relacionamento`
- `cadastros_pessoa_relacionamentos`
- `cadastros_pessoas_consentimentos`
- `cadastros_pessoas_acesso_log`
- `cadastros_pessoas_pii`

### Tabelas paralelas relevantes

- `compras_fornecedores`
- `rh_colaboradores`
- `usuarios`
- `tenant_usuarios`
- `unidade_produtiva_usuarios`
- `crm_leads`
- `crm_atividades`
- `crm_pipeline_estagios`
- `fin_despesas`
- `fin_receitas`
- `financeiro_comercializacoes`

---

## 8. Rotas

### Cadastro mestre de pessoas

Em `services/api/core/cadastros/pessoas/router.py`:

- `GET /cadastros/pessoas`
- `POST /cadastros/pessoas`
- `GET /cadastros/pessoas/{pessoa_id}`
- `PATCH /cadastros/pessoas/{pessoa_id}`
- `POST /cadastros/pessoas/{pessoa_id}/anonimizar`
- `GET /cadastros/pessoas/{pessoa_id}/pii`
- `PATCH /cadastros/pessoas/{pessoa_id}/pii`
- CRUD auxiliar de contatos/endereços
- `GET/POST/DELETE /cadastros/tipos-relacionamento`

### Compras / fornecedor legado

Em `services/api/operacional/routers/compras.py`:

- `GET /compras/fornecedores`
- `POST /compras/fornecedores`
- `GET /compras/fornecedores/{fornecedor_id}`
- `PUT /compras/fornecedores/{fornecedor_id}`

O CRUD público continua sendo do `Fornecedor` legado.

### RH / colaborador

Em `services/api/rh/router.py`:

- `GET /rh/colaboradores`
- `POST /rh/colaboradores`
- `DELETE /rh/colaboradores/{colaborador_id}`

O CRUD público continua sendo de `ColaboradorRH`, não de `Pessoa`.

### Comercialização

Em `services/api/financeiro/comercializacao/`:

- filtros e criação usam `comprador_id`
- `comprador_id` é FK para `Pessoa`

Aqui o consumidor já opera diretamente sobre a base canônica.

---

## 9. Frontend

### Cadastro central

O frontend web possui área dedicada:

- `apps/web/src/app/(dashboard)/cadastros/pessoas/`

No menu lateral:

- “Pessoas & Parceiros”

Isso confirma que a UX já reconhece uma área mestre unificada.

### RH

Em `apps/web/src/app/(dashboard)/dashboard/rh/page.tsx`:

- a tela consulta `/cadastros/pessoas`;
- a UI orienta que a pessoa esteja cadastrada previamente;
- há tentativa de usar `pessoa_id` como base para seleção.

Porém, o backend oficial de criação de colaborador ainda recebe:

- `nome`
- `cpf`
- `cargo`
- `tipo_contrato`

Sem `pessoa_id` como contrato principal.

Isso indica **desalinhamento entre intenção do frontend e contrato efetivo do backend**.

### Compras

Em `apps/web/src/app/(dashboard)/dashboard/operacional/fornecedores/FornecedoresClient.tsx`:

- o fluxo continua usando `/compras/fornecedores`

Ou seja, a UX de fornecedores ainda está ancorada no cadastro legado.

### Comercialização

Em `apps/web/src/app/(dashboard)/dashboard/financeiro/comercializacoes/page.tsx`:

- a tela busca pessoas em `/cadastros/pessoas`
- o formulário exige `comprador_id`

Aqui o frontend já consome a fonte canônica.

### ESG / Certificações

Em `apps/web/src/services/certificacoes-esg/service.ts`:

existem múltiplos contratos com:

- `responsavel_pessoa_id`

Isso mostra que novos fluxos já assumem `Pessoa` como referência de responsável.

---

## 10. Campo PWA

Em `apps/campo/`, o padrão encontrado ainda é orientado a colaborador/trabalhador, não a `Pessoa`.

Achados principais:

- `apps/campo/src/lib/db.ts` usa cache de colaboradores;
- `apps/campo/src/app/(campo)/campo/epi/page.tsx` trabalha com `db.colaboradores`;
- fluxos de EPI e caderno usam:
  - `trabalhador_id`
  - `nome_trabalhador`

No backend agrícola:

- `services/api/agricola/caderno/models.py`
- `services/api/agricola/caderno/schemas.py`
- `services/api/agricola/caderno/service.py`

continuam aceitando e persistindo `trabalhador_id` e `nome_trabalhador`.

Portanto:

- Campo PWA depende hoje de uma projeção operacional de colaborador;
- ainda não consome `Pessoa` como entidade mestre universal.

---

## 11. Testes existentes

### Pessoas

Em `services/api/tests/integration/test_cadastros.py` existem testes de:

- criação de pessoa;
- atualização;
- filtragem por relacionamento;
- uso dos endpoints de `/cadastros/pessoas`.

### Compras / fornecedor

Em `services/api/tests/integration/operacional/test_compras.py`:

- existe teste explícito garantindo que criar fornecedor:
  - resolve uma `Pessoa` canônica;
  - reutiliza o legado;
  - não duplica registros/documentos.

Em `services/api/tests/unit/operacional/test_fornecedores_service.py`:

- há testes para:
  - `resolve_fornecedor`
  - `salvar_fornecedor_legado`
  - reutilização por documento
  - isolamento por tenant

Isso confirma que a coexistência `Pessoa + Fornecedor legado` é intencional e ativa.

### RH

Em `services/api/tests/integration/test_rh.py`:

- há referência a `xfail` para constraint de CPF ainda não implementada em `rh_colaboradores`.

Isso reforça fragilidade estrutural no cadastro de colaborador.

### Campo / colaborador

Em `services/api/tests/unit/agricola/test_epi_offline_sync.py`:

- os testes usam `ColaboradorRH`;
- persistem `trabalhador_id` e `nome_trabalhador`;
- validam compatibilidade com esse fluxo legado.

### Comercialização

Em `services/api/tests/unit/financeiro/test_comercializacao.py` e testes correlatos:

- `comprador_id` é tratado como referência principal.

### Certificações / ESG

Há testes backend e frontend usando:

- `responsavel_pessoa_id`

O contrato funcional já pressupõe pessoa canônica para responsável.

### Conftest global

Em `services/api/tests/conftest.py`:

- o setup insere um `usuario`;
- e insere uma `pessoa` separada com o mesmo UUID por convenção;
- não existe vínculo estrutural obrigatório entre ambos.

Esse é um indício relevante de duplicidade arquitetural tolerada pelos testes.

---

## 12. Fluxos auditados

### Fluxo 1: Cadastro mestre de pessoa

`Pessoa` é criada por:

- `POST /cadastros/pessoas`

Ela pode receber:

- documentos
- contatos
- endereços
- dados bancários
- papéis via relacionamentos

### Fluxo 2: Compras

Fluxo real encontrado:

`Fornecedor legado -> resolve_fornecedor -> Pessoa -> TipoRelacionamento FORNECEDOR -> PessoaRelacionamento -> compras/financeiro`

Quem cria:

- CRUD de `Fornecedor`

Quem consome:

- compras
- histórico de fornecedor
- integrações de despesa/fornecedor

Conclusão:

- fornecedor ainda não nasce diretamente como `Pessoa`;
- há bridge para sincronizar com a base canônica.

### Fluxo 3: RH

Fluxo real encontrado:

`ColaboradorRH (nome/cpf próprios, pessoa_id opcional) -> diárias / empreitadas / SST / Campo`

Quem cria:

- `/rh/colaboradores`

Quem consome:

- RH
- eSocial
- diárias
- SST
- Campo PWA / EPI / caderno

Conclusão:

- funcionário/colaborador não deriva obrigatoriamente de `Pessoa`.

### Fluxo 4: Financeiro

Fluxo real encontrado:

`Pessoa (opcional) -> Receita/Despesa (pessoa_id) -> legado textual fallback`

Conclusão:

- Financeiro já reconhece `Pessoa` como referência preferencial;
- mas ainda aceita texto livre para compatibilidade.

### Fluxo 5: Comercialização

Fluxo real encontrado:

`Pessoa -> comprador_id -> ComercializacaoCommodity -> Receita`

Conclusão:

- comprador já usa a base canônica.

### Fluxo 6: CRM

Fluxo real encontrado:

`LeadCRM independente -> pipeline/atividades -> eventual conversão`

Conclusão:

- CRM não está modelado sobre `Pessoa`.

### Fluxo 7: Usuário e segurança

Fluxo real encontrado:

`Usuario -> TenantUsuario -> UnidadeProdutivaUsuario -> perfis/permissões`

Conclusão:

- `Usuario` representa autenticação e acesso;
- mas também acumula atributos pessoais;
- sem ligação canônica com `Pessoa`.

---

## 13. Grafo de dependências

### Grafo principal encontrado

`Pessoa`

↓

`TipoRelacionamento`

↓

`PessoaRelacionamento`

↓

`Comercialização (comprador_id)`

↓

`Receita (pessoa_id)`

↓

`Relatórios financeiros`

### Grafo de compras

`Pessoa`

↓

`Fornecedor (legado com pessoa_id)`

↓

`Compras`

↓

`Despesa (pessoa_id ou fornecedor texto)`

↓

`Custos / DRE`

### Grafo de RH e Campo

`Pessoa (opcional)`

↓

`ColaboradorRH`

↓

`Diárias / Empreitadas / SST`

↓

`Campo PWA / EPI / Caderno`

### Grafo de usuários

`Usuario`

↓

`TenantUsuario`

↓

`UnidadeProdutivaUsuario`

↓

`Permissões / acesso`

### Grafo de CRM

`LeadCRM`

↓

`AtividadeCRM`

↓

`Conversão comercial`

### Leitura consolidada do grafo

Há pelo menos **quatro eixos de representação de pessoa** coexistindo:

1. `Pessoa` canônica
2. `Fornecedor` legado sincronizado
3. `ColaboradorRH` híbrido
4. `Usuario` independente

Além disso:

5. `LeadCRM` funciona como representação comercial pré-conversão

---

## 14. Fonte canônica

### Fonte canônica identificada

A única entidade com evidência suficiente para ser considerada a base canônica do domínio Pessoas é:

- `Pessoa` em `services/api/core/cadastros/pessoas/models.py`

### Motivos

1. O model a descreve como “entidade central”.
2. Existe um subsistema completo de documentos, contatos, endereços, bancário e LGPD.
3. Existe modelagem de papéis via `TipoRelacionamento` e `PessoaRelacionamento`.
4. Módulos novos ou mais consolidados já a consomem diretamente:
   - comercialização
   - partes do financeiro
   - frota
   - pecuária
   - frontend ESG/certificações

### Limite da conclusão

Apesar disso, a auditoria **não permite afirmar** que `Pessoa` já é a única fonte de verdade operacional do produto.

Ela é a fonte canônica **arquitetural**, mas ainda não a fonte única **funcional**.

---

## 15. Auditoria funcional por domínio

### Compras

**Fornecedor é uma Pessoa?**

Resposta:

- Arquiteturalmente, deveria ser representado por `Pessoa` + papel `FORNECEDOR`.
- Funcionalmente, ainda existe `Fornecedor` como entidade própria em `compras_fornecedores`.

Conclusão:

- **Fornecedor é híbrido.**

### RH

**Funcionário deriva de Pessoa?**

Resposta:

- Parcialmente.
- `ColaboradorRH` possui `pessoa_id`, mas a criação oficial continua independente.

Conclusão:

- **Funcionário/colaborador não deriva obrigatoriamente de `Pessoa`.**

### CRM

**Cliente é Pessoa?**

Resposta:

- Em comercialização/financeiro, cliente/comprador pode ser `Pessoa`.
- Em CRM, `LeadCRM` é entidade separada.

Conclusão:

- **Não existe uma única representação unificada entre CRM e cliente operacional.**

### Comercialização

**Comprador, corretora, exportadora são Pessoas?**

Resposta:

- No fluxo implementado de comercialização agrícola, comprador é `Pessoa` via `comprador_id`.
- Não foi encontrada entidade própria separada para comprador nesse módulo.

Conclusão:

- **Comercialização já reutiliza a base canônica.**

### Pecuária

**Veterinário, responsável técnico, prestador compartilham cadastro?**

Resposta:

- Há consumo de `Pessoa` em partes da pecuária e operacional.
- Não foi encontrada, nesta auditoria, uma entidade canônica exclusiva de veterinário separada do restante.

Conclusão:

- **A tendência encontrada é usar `Pessoa`, mas sem evidência de consolidação total do domínio.**

### ESG

**Auditor, certificadora, consultoria compartilham cadastro?**

Resposta:

- Os contratos de frontend e migrations usam `responsavel_pessoa_id`.

Conclusão:

- **Os fluxos novos apontam para reaproveitar `Pessoa`.**

### Segurança

**Usuário representa Pessoa ou apenas credencial?**

Resposta:

- `Usuario` representa autenticação, vínculo de acesso e credenciais.
- Porém também armazena atributos de pessoa.
- Não há FK canônica para `Pessoa`.

Conclusão:

- **Usuário é uma identidade de autenticação independente, não uma especialização formal de `Pessoa`.**

---

## 16. Duplicidades encontradas

### Duplicidade 1: Pessoa x Usuário

Campos sobrepostos:

- nome
- CPF
- telefone

Problema:

- o mesmo indivíduo pode existir em `usuarios` e `cadastros_pessoas` sem vínculo estrutural.

### Duplicidade 2: Pessoa x ColaboradorRH

Campos sobrepostos:

- nome
- CPF

Problema:

- colaborador pode nascer fora do cadastro mestre.

### Duplicidade 3: Pessoa x Fornecedor

Campos sobrepostos:

- razão/nome fantasia
- documento
- e-mail
- telefone

Problema:

- fornecedor continua com tabela operacional própria, ainda que sincronizada.

### Duplicidade 4: Pessoa x LeadCRM

Campos sobrepostos:

- nome
- empresa
- documento
- e-mail
- telefone

Problema:

- CRM captura dados equivalentes de pessoa/empresa sem base comum.

### Duplicidade 5: Pessoa x texto livre financeiro

Campos sobrepostos:

- `fin_despesas.fornecedor`
- `fin_receitas.cliente`

Problema:

- lançamentos podem existir sem chave canônica.

---

## 17. Conflitos de nomenclatura e sobreposição

Conflitos observados:

- `Pessoa` vs `Usuario`
- `Pessoa` vs `Fornecedor`
- `Pessoa` vs `ColaboradorRH`
- `cliente` textual em `Receita` vs cliente como `Pessoa`
- `fornecedor` textual em `Despesa` vs fornecedor como `Pessoa`
- `trabalhador`/`colaborador` no Campo PWA vs `Pessoa` no cadastro mestre

Sobreposições funcionais:

- identidade civil
- papel comercial
- papel trabalhista
- contato operacional
- responsável por fluxo
- vínculo de autenticação

Esses conceitos ainda não foram isolados de forma uniforme.

---

## 18. Riscos

### Risco 1: Duplicidade cadastral

Mesmo ator pode ser cadastrado em:

- `Pessoa`
- `Usuario`
- `ColaboradorRH`
- `Fornecedor`
- `LeadCRM`

### Risco 2: Divergência de payloads

Cada módulo pede campos diferentes para representar praticamente o mesmo conceito.

### Risco 3: Ownership difuso

Hoje não está uniformemente imposto na prática que:

- todo fornecedor seja uma pessoa;
- todo colaborador seja uma pessoa;
- todo usuário tenha uma pessoa correspondente.

### Risco 4: Compatibilidade longa demais

Campos textuais legados e wrappers especializados podem perpetuar inconsistência se não houver consolidação posterior.

### Risco 5: UX confusa

Usuário pode precisar decidir entre:

- cadastrar em Pessoas;
- cadastrar em Fornecedores;
- cadastrar em RH;
- convidar como Usuário.

Sem uma narrativa única de quem é a entidade principal.

### Risco 6: Integrações e relatórios

Relatórios, contratos e lançamentos financeiros podem misturar:

- pessoa canônica;
- texto livre;
- cadastro legado.

Isso dificulta rastreabilidade e deduplicação.

---

## 19. Legado identificado

Legado ativo confirmado por evidência:

- `compras_fornecedores`
- `rh_colaboradores` com `nome/cpf` próprios
- `fin_despesas.fornecedor`
- `fin_receitas.cliente`
- payloads do Campo PWA com `nome_trabalhador`
- `Usuario` sem integração estrutural com `Pessoa`

Não há evidência de que esse legado esteja morto ou inutilizado.

Ao contrário:

- há rotas ativas;
- há testes ativos;
- há uso em frontend e PWA.

---

## 20. UX observada

### Cadastros difíceis ou potencialmente confusos

1. Fornecedor

- existe tela própria de fornecedor;
- existe base de pessoas;
- há sincronização oculta.

2. Colaborador

- frontend aponta para pessoa pré-cadastrada;
- backend ainda aceita colaborador independente.

3. Usuário

- convite e acesso vivem em `Usuario`;
- não há explicação estrutural de relação com `Pessoa`.

### Dependências escondidas

- compras cria/resolve `Pessoa` por trás do CRUD de fornecedor;
- financeiro prefere `pessoa_id`, mas ainda aceita texto;
- Campo trabalha com `ColaboradorRH`, não com `Pessoa`.

### Passos redundantes

Potencialmente o mesmo ator pode ser repetido como:

- pessoa/parceiro;
- fornecedor;
- colaborador;
- usuário;
- lead.

---

## 21. Decisão

### Opção escolhida

**Opção C — Existe necessidade de consolidação arquitetural.**

### Motivo exato

O domínio Pessoas já possui uma base canônica bem definida, mas ainda não possui adoção uniforme suficiente para ser tratado como Master Person Data definitivo da plataforma.

Os bloqueios objetivos são:

1. `Usuario` não referencia `Pessoa`;
2. `ColaboradorRH` não depende obrigatoriamente de `Pessoa`;
3. `Fornecedor` continua com CRUD e tabela próprios;
4. Financeiro ainda aceita cliente/fornecedor em texto livre;
5. CRM mantém representação própria de pessoa/empresa;
6. Campo PWA permanece ancorado em colaborador/trabalhador e payload textual.

---

## 22. Plano recomendado (somente documental)

### Objetivo do plano

Consolidar `Pessoa` como Master Person Data sem remoção destrutiva imediata.

### Sequência recomendada

1. Congelar `Pessoa` como fonte canônica oficial do domínio.
2. Mapear formalmente papéis suportados por `TipoRelacionamento`.
3. Criar camada explícita de resolução canônica para:
   - fornecedor
   - cliente/comprador
   - colaborador
   - responsável técnico
   - prestador
4. Tratar `Usuario` como identidade de autenticação e definir relação canônica com `Pessoa`.
5. Tornar `ColaboradorRH` uma especialização obrigatória de `Pessoa` em fluxo novo.
6. Transformar `Fornecedor` em wrapper compatível de `Pessoa`, sem criação paralela autônoma no fluxo novo.
7. Reduzir progressivamente o uso de:
   - `fin_despesas.fornecedor`
   - `fin_receitas.cliente`
   - `nome_trabalhador` como fonte primária
8. Definir estratégia explícita para CRM:
   - lead separado até conversão;
   - ou ponte formal de conversão para `Pessoa`.

### O que esta auditoria não recomenda fazer agora

- remover tabelas;
- remover rotas;
- forçar migração destrutiva;
- assumir que `Usuario` pode ser fundido com `Pessoa` sem análise própria.

---

## 23. Respostas objetivas aos critérios de aceite

### Existe uma única entidade mestre de Pessoas?

**Não na operação completa do sistema.**

Existe uma candidata canônica clara:

- `Pessoa`

Mas ela não é a única fonte funcional de verdade hoje.

### Existe uma única entidade para Fornecedor?

**Não.**

Hoje coexistem:

- `Pessoa` com papel `FORNECEDOR`
- `Fornecedor` em `compras_fornecedores`

### Cliente reutiliza a mesma base?

**Parcialmente.**

- Comercialização usa `Pessoa`
- `Receita` suporta `pessoa_id`
- CRM não reutiliza `Pessoa` para leads
- `Receita` ainda aceita `cliente` textual

### Funcionário reutiliza a mesma base?

**Parcialmente.**

- `ColaboradorRH` possui `pessoa_id`
- mas a criação oficial ainda é independente de `Pessoa`

### Usuário representa Pessoa ou apenas autenticação?

**Principalmente autenticação/acesso, mas com sobreposição indevida de dados pessoais.**

Não há relação estrutural obrigatória com `Pessoa`.

### Existem duplicidades?

**Sim.**

As mais relevantes estão entre:

- `Pessoa` e `Usuario`
- `Pessoa` e `ColaboradorRH`
- `Pessoa` e `Fornecedor`
- `Pessoa` e `LeadCRM`
- `Pessoa` e campos textuais do financeiro

### Existem conceitos sobrepostos?

**Sim.**

Principalmente:

- identidade civil;
- papel comercial;
- papel trabalhista;
- contato operacional;
- credencial de acesso.

### Existe legado?

**Sim, e ele está ativo.**

### Há risco arquitetural?

**Sim.**

O risco é relevante para consistência cadastral, UX e rastreabilidade.

### O domínio Pessoas está pronto para a versão 1.0?

**Não como Master Person Data definitivo.**

Está suficientemente avançado para apontar uma base canônica, mas ainda não consolidado para servir sozinho como fonte única de verdade.

---

## 24. Resposta final obrigatória

**O domínio Pessoas do AgroSaaS ainda não possui uma arquitetura suficientemente consistente para servir como Master Person Data definitivo da versão 1.0. A codebase já contém uma fonte canônica clara em `Pessoa` (`cadastros_pessoas`), mas coexistem cadastros paralelos, wrappers legados, campos textuais e identidade de usuário desacoplada, o que caracteriza inconsistências estruturais que devem ser resolvidas antes do lançamento do produto como arquitetura mestre de pessoas.**
