# INTEGRATIONS-ARCH-01 — Arquitetura Canônica do Domínio de Integrações do AgroSaaS

## 1. Objetivo

Definir a arquitetura oficial do domínio de Integrações do AgroSaaS.

Este documento responde:

- como integrações são organizadas;
- quem configura;
- quem utiliza;
- quem monitora;
- como ficam permissões;
- como ficam credenciais;
- como ficam logs, filas, jobs, eventos e observabilidade;
- como separam responsabilidades entre Plataforma, Tenant, Estabelecimento, Unidade Produtiva e Backoffice.

## 2. Motivação

Situação atual:

- o AgroSaaS já possui integrações reais, com destaque para Sankhya;
- a auditoria `SANKHYA-GOV-01` confirmou backend majoritariamente orientado a tenant;
- a mesma auditoria confirmou desalinhamento de governança, UX e segurança de credenciais;
- a plataforma ainda não possui um domínio arquitetural oficial e transversal para Integrações.

Problema:

- sem arquitetura canônica, cada nova integração tende a nascer com seu próprio modelo, RBAC, navegação, segredos, logs e fila;
- isso cria risco de arquitetura paralela, vazamento entre tenants e inconsistência de suporte.

Decisão:

- a partir deste documento, toda integração do AgroSaaS deve orbitar o domínio oficial `Integrações`;
- integrações deixam de ser apenas implementações técnicas e passam a obedecer uma governança arquitetural única.

## 3. Domínio Integrações

O domínio `Integrações` é o domínio responsável por conectar o AgroSaaS a sistemas externos, preservando:

- isolamento multi-tenant;
- contratos canônicos;
- segurança de credenciais;
- rastreabilidade operacional;
- observabilidade;
- governança entre operação do cliente e suporte da plataforma.

Papel do domínio:

- cadastrar provedores externos;
- configurar conexões e escopos;
- armazenar segredos de forma segura;
- disparar jobs de sincronização;
- registrar logs, health, métricas e eventos;
- servir de ponte entre domínios internos e sistemas externos.

Relação com outros domínios:

- Agricultura: consome clima, satélite, IoT, ERP operacional indireto, rastreabilidade externa.
- Pecuária: consome IoT, balanças, sanidade, ERPs, integrações de rastreio.
- Financeiro: consome ERP, bancos, fiscal, pagamentos, cobrança e conciliação.
- ESG: consome certificações, auditorias, passaportes, evidências e registros externos.
- Wizard: pode verificar pré-requisitos de integração, mas não cria identidades nem integrações globais.
- Eventos / Outbox: deve ser a via oficial para integrações assíncronas relevantes.
- Observabilidade: integrações devem expor status, health, métricas, retries, backlog e logs.

## 4. Taxonomia

Categorias oficiais de integração:

- ERP
- Financeiro / Bancos
- Fiscal
- Satélite
- Clima
- IoT
- Comunicação
- Armazenamento
- Webhooks
- APIs Externas
- Business Intelligence

Semântica:

- `ERP`: gestão administrativa, fiscal, contábil, financeira e corporativa.
- `Financeiro / Bancos`: extratos, boletos, cobranças, pagamentos, conciliação, open finance.
- `Fiscal`: NFe, eSocial, SPED, obrigações acessórias.
- `Satélite`: NDVI, imagens, mosaicos, sensoriamento remoto.
- `Clima`: previsão, chuva, histórico meteorológico, alertas.
- `IoT`: máquinas, telemetria, dispositivos de campo, sensores.
- `Comunicação`: e-mail, SMS, WhatsApp, notificações externas.
- `Armazenamento`: buckets, DMS, GED, arquivos corporativos.
- `Webhooks`: recebimento e emissão de eventos externos.
- `APIs Externas`: dados de mercado, commodities, compliance, terceiros.
- `Business Intelligence`: conectores analíticos, exportação de dados, warehouses, BI corporativo.

## 5. Escopos

Escopos arquiteturais oficiais:

- `PLATFORM`
- `TENANT`
- `ESTABELECIMENTO`
- `USUARIO`

### 5.1 PLATFORM

Uso correto:

- integrações administradas pela própria plataforma;
- provedores globais de entrega, observabilidade, antifraude, billing da plataforma;
- conectores internos do SaaS que não representam configuração do cliente final.

Não usar para:

- ERP do cliente;
- banco do cliente;
- credenciais do cliente;
- integração operacional de uma fazenda.

### 5.2 TENANT

Uso correto:

- integrações que representam a empresa/organização do cliente como um todo;
- ERPs corporativos;
- integrações financeiras e fiscais do produtor;
- comunicação institucional do cliente;
- BI organizacional.

Decisão oficial:

- este é o escopo padrão para integrações administrativas do cliente.

### 5.3 ESTABELECIMENTO

Uso correto:

- integrações administrativas/fiscais de matriz e filiais;
- cenários onde diferentes estabelecimentos do mesmo tenant possuem ERP, CNPJ, IE ou rotinas fiscais distintas;
- bancos, fiscal e obrigações acessórias por estabelecimento.

Decisão oficial:

- este escopo é válido e oficialmente suportado pela arquitetura;
- ele não deve ser confundido com `UnidadeProdutiva`.

### 5.4 USUARIO

Uso correto:

- integrações pessoais do usuário, não institucionais;
- calendários pessoais, e-mail individual, tokens de produtividade, conectores pessoais autorizados.

Não usar para:

- ERP;
- fiscal;
- dados corporativos do cliente.

## 6. Estabelecimentos

O AgroSaaS deve reconhecer oficialmente um domínio administrativo chamado `Estabelecimento`.

Conceitos que pertencem a esse domínio:

- Matriz
- Filial
- Centro Administrativo
- Empresa operacional/fiscal
- CNPJ
- Inscrição Estadual
- Inscrição Municipal
- Razão Social
- Endereço Fiscal

Arquitetura recomendada:

```text
Tenant
  ↓
Estabelecimento
  ↓
UnidadeProdutiva
  ↓
AreaRural
```

Semântica oficial:

- `Tenant`: fronteira SaaS, contrato, segurança, billing, isolamento lógico.
- `Estabelecimento`: fronteira administrativa/fiscal/empresarial.
- `UnidadeProdutiva`: fronteira operacional mínima da fazenda.
- `Talhão`, `Piquete`, `AreaRural`: fronteiras territoriais e operacionais.

Decisão:

- `Estabelecimento` não substitui `Tenant`;
- `Estabelecimento` não substitui `UnidadeProdutiva`;
- `Estabelecimento` é a ponte correta entre empresa administrativa e operação rural.

## 7. ERP

Premissas obrigatórias:

- ERP representa a empresa;
- ERP não representa a Unidade Produtiva;
- Unidade Produtiva pertence ao domínio operacional;
- ERP pertence ao domínio administrativo, fiscal e financeiro.

Decisão oficial:

- configuração de ERP **não deve ser por Unidade Produtiva**;
- o escopo correto do ERP é `TENANT` ou `ESTABELECIMENTO`.

### 7.1 Regra oficial do ERP

```text
Se o ERP representa toda a organização do cliente:
  escopo = TENANT

Se o ERP representa matriz/filial/CNPJ distinto:
  escopo = ESTABELECIMENTO
```

### 7.2 Quando NÃO usar Unidade Produtiva

Não usar `UnidadeProdutiva` para:

- credenciais do ERP;
- URL do ERP;
- autenticação do ERP;
- configuração fiscal;
- parâmetros administrativos do ERP.

Pode haver vínculo operacional indireto:

- uma `UnidadeProdutiva` pertence a um `Estabelecimento`;
- esse `Estabelecimento` é atendido por um ERP;
- a operação da fazenda herda a referência administrativa desse estabelecimento.

## 8. Governança

Separação oficial:

### 8.1 Console Administrativo do Tenant

Responsável por:

- configurar integração do cliente;
- armazenar parâmetros funcionais;
- testar conexão;
- executar sincronizações manuais do próprio tenant;
- consultar status, health, últimos syncs e logs do próprio tenant;
- operar integrações do dia a dia.

### 8.2 Console de Backoffice da Plataforma

Responsável por:

- observabilidade global;
- troubleshooting;
- suporte avançado;
- health cross-tenant;
- diagnóstico técnico;
- retry técnico assistido;
- auditoria operacional de integrações.

### 8.3 Responsabilidades oficiais

- quem configura: administrador do tenant ou administrador do estabelecimento, conforme o escopo;
- quem utiliza: módulos internos do AgroSaaS e usuários do tenant;
- quem monitora no dia a dia: tenant;
- quem dá suporte: backoffice;
- quem realiza troubleshooting avançado: backoffice/suporte;
- quem executa jobs automáticos: worker/infraestrutura;
- quem executa sync manual: tenant ou backoffice autorizado, com trilha de auditoria.

## 9. Segurança

Arquitetura oficial de segurança:

- credenciais nunca devem ser persistidas em texto puro;
- segredos devem ser criptografados em repouso;
- valores sensíveis devem ser mascarados na leitura;
- toda operação deve respeitar `tenant_id`;
- logs não devem expor segredo bruto;
- health e status não devem vazar dado de outro tenant;
- segredos devem ter rotação, versionamento e auditoria.

Decisão oficial:

- `IntegrationCredential` é contrato canônico separado de `IntegrationConfig`;
- leitura de credencial deve ser minimizada;
- telas de tenant não devem exibir segredo completo após gravação;
- backoffice pode visualizar estado e metadados, não necessariamente o segredo bruto.

RLS:

- integrações tenant-scoped e estabelecimento-scoped devem operar sob sessão com contexto RLS ativo;
- filtros manuais por `tenant_id` são defesa complementar, não substituto do RLS.

## 10. Observabilidade

Toda integração oficial deve expor, no mínimo:

- status configurado/não configurado;
- health atual;
- último sync;
- próximo sync;
- últimos erros;
- quantidade de retries;
- backlog/fila, quando houver;
- logs recentes;
- métricas básicas.

Saídas canônicas:

- `IntegrationHealth`
- `IntegrationLog`
- `IntegrationJob`
- `IntegrationEvent`

Normas:

- jobs devem ser idempotentes;
- falhas devem ser registradas com escopo do tenant;
- retries devem ser explícitos;
- integrações relevantes devem usar eventos e/ou outbox para desacoplamento;
- health do tenant e observabilidade global devem ser vistas diferentes sobre a mesma fonte de dados.

## 11. RBAC

Papéis e permissões oficiais:

- `Tenant Administrador`
- `Tenant Operador`
- `Backoffice`
- `Suporte`
- `Super Admin`

Separação:

- `Tenant Administrador`: configura e opera integrações do seu tenant/estabelecimento.
- `Tenant Operador`: consulta status e eventualmente executa ações restritas de uso, sem administrar credenciais.
- `Backoffice`: monitora e diagnostica.
- `Suporte`: atua em troubleshooting operacional com escopo controlado.
- `Super Admin`: governança máxima da plataforma.

Diretriz:

- permissões de integração do cliente devem nascer no namespace `tenant:*` ou `estabelecimento:*`;
- permissões de suporte/observabilidade devem nascer no namespace `backoffice:*`;
- uma tela de tenant não deve depender de permissão de backoffice.

## 12. Navegação

Navegação oficial para o cliente:

```text
Administração
  ↓
Integrações
  ↓
ERP
  ↓
Sankhya
```

Navegação oficial para backoffice:

```text
Backoffice
  ↓
Observabilidade
  ↓
Integrações
  ↓
Logs
  ↓
Health
  ↓
Diagnóstico
  ↓
Suporte
```

Regra:

- console de configuração do cliente não deve morar no backoffice;
- backoffice não é a casa canônica da configuração do ERP do tenant.

## 13. Contratos Canônicos

Contratos oficiais do domínio:

- `IntegrationProvider`
- `IntegrationConfig`
- `IntegrationCredential`
- `IntegrationHealth`
- `IntegrationJob`
- `IntegrationLog`
- `IntegrationEvent`
- `IntegrationScope`
- `IntegrationStatus`

Semântica mínima:

- `IntegrationProvider`: provedor externo, ex. Sankhya.
- `IntegrationConfig`: parâmetros funcionais da integração.
- `IntegrationCredential`: segredo, token, login, certificado, senha, chave.
- `IntegrationHealth`: fotografia atual da saúde da integração.
- `IntegrationJob`: execução de sincronização/importação/exportação/retry.
- `IntegrationLog`: trilha operacional e técnica.
- `IntegrationEvent`: fato relevante de integração para observabilidade/outbox.
- `IntegrationScope`: `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`.
- `IntegrationStatus`: ativo, inativo, erro, degradado, pendente, etc.

## 14. Aplicação ao Sankhya

### 14.1 Situação atual

- backend: majoritariamente tenant-scoped;
- frontend: exposto no backoffice;
- unidade produtiva: inexistente;
- credenciais: governança fraca;
- isolamento: lógico por tenant, com lacuna de RLS físico no módulo auditado.

### 14.2 Arquitetura proposta

- configuração principal do Sankhya deve ficar no console administrativo do tenant;
- o provedor `Sankhya` se encaixa como `IntegrationProvider` da categoria `ERP`;
- escopo padrão do Sankhya deve ser `TENANT`;
- quando o tenant possuir matriz/filiais fiscalmente distintas, o escopo recomendado passa a ser `ESTABELECIMENTO`.

### 14.3 Matriz e filiais

Modelo oficial:

```text
Tenant
  ↓
Estabelecimento (Matriz / Filial)
  ↓
ERP Sankhya
  ↓
UnidadesProdutivas vinculadas ao estabelecimento
```

Decisão:

- o ERP da matriz e o ERP da filial pertencem ao domínio administrativo;
- unidades produtivas herdam o contexto do estabelecimento;
- não se cria uma configuração ERP por fazenda.

### 14.4 Arrendamento

Cenário:

```text
Produtor A
  ↓
arrenda área de Produtor B
  ↓
usa seu próprio ERP
```

Decisão oficial:

- o AgroSaaS não precisa conhecer o ERP do proprietário da área apenas porque a área é dele;
- a integração relevante é a do agente econômico que opera a safra e gera fatos administrativos;
- o sistema deve controlar contrato, custos, produção, financeiro, rastreabilidade e acertos do operador;
- o ERP do proprietário da terra não é automaticamente parte do domínio operacional do arrendatário.

## 15. ADRs geradas

ADRs formais geradas por este documento:

- ADR-INT-01: Integrações constituem domínio arquitetural próprio.
- ADR-INT-02: ERP nunca é configurado por Unidade Produtiva.
- ADR-INT-03: Escopo padrão de ERP é `TENANT`; `ESTABELECIMENTO` é extensão oficial.
- ADR-INT-04: Console do cliente e console de backoffice são responsabilidades distintas.
- ADR-INT-05: Credenciais de integração exigem contrato canônico separado e criptografia em repouso.
- ADR-INT-06: Observabilidade global não substitui a governança de tenant.

## 16. Decisões Arquiteturais

- o domínio oficial `Integrações` passa a existir formalmente;
- `ERP` pertence ao domínio administrativo/fiscal, não ao operacional;
- `Estabelecimento` passa a ser conceito arquitetural oficial;
- `UnidadeProdutiva` não é escopo válido de configuração de ERP;
- configurações do cliente pertencem ao tenant/estabelecimento;
- backoffice observa e dá suporte, mas não é o local canônico da configuração do cliente;
- RLS e tenant isolation são mandatórios para integrações.

## 17. Limitações deliberadas da V1

- `Estabelecimento` pode ainda não estar implementado como domínio completo;
- integrações existentes podem continuar tenant-scoped como compatibilidade;
- algumas integrações ainda podem usar filtros lógicos antes da consolidação total de RLS;
- observabilidade pode permanecer heterogênea entre provedores na v1;
- Sankhya pode operar como integração por tenant no primeiro piloto sem modelagem imediata por estabelecimento.

## 18. Evoluções previstas

- detalhamento canônico de `Provider`, `ProviderDefinition`, `Connection`, `Credential`, `Feature`, `SyncPolicy` e `Health` em `INTEGRATIONS-ARCH-02`;
- `INTEGRATIONS-GOV-01` para guardrails do domínio;
- modelagem canônica de `Estabelecimento`;
- refatoração da governança Sankhya para console de tenant;
- endurecimento de segredos, rotação e mascaramento;
- padronização de jobs, filas, eventos e health;
- consolidação de permissão tenant específica para integrações.
