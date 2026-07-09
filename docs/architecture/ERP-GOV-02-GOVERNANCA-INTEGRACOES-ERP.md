# ERP-GOV-02 - Governanca Oficial das Integracoes ERP

Status: APROVADA
Categoria: Governanca Arquitetural
Tipo: Guardrail Obrigatorio
Data: 2026-07-09

## 1. Objetivo

Transformar as arquiteturas:

- `ERP-DOMAIN-01`
- `ERP-CONSOLE-01`

em um conjunto oficial de guardrails obrigatorios para qualquer integracao ERP do AgroSaaS.

Este documento e normativo.

Ele nao cria nova arquitetura paralela.

Ele consolida e especializa, para ERP, as regras ja definidas em:

- `INTEGRATIONS-ARCH-01`
- `INTEGRATIONS-ARCH-02`
- `INTEGRATIONS-LIFECYCLE-01`
- `ERP-DOMAIN-01`
- `ERP-CONSOLE-01`

## 2. Precedencia normativa

Precedencia oficial:

1. `INTEGRATIONS-ARCH-01` define o dominio Integracoes, seus escopos oficiais e a separacao tenant/backoffice.
2. `INTEGRATIONS-ARCH-02` define o runtime generico de provider, configuracao, features, politicas e health.
3. `INTEGRATIONS-LIFECYCLE-01` define lifecycle, auditoria operacional, revogacao e versionamento.
4. `ERP-DOMAIN-01` define ownership, direcao, conflito e obrigatoriedade por entidade ERP.
5. `ERP-CONSOLE-01` define a camada administrativa oficial do console ERP.
6. `ERP-GOV-02` define os guardrails obrigatorios de conformidade para qualquer provider ERP.

Regra:

- nenhum provider ERP pode contradizer documentos anteriores;
- nenhuma implementacao ERP pode criar segunda regra equivalente quando a regra oficial ja existir.

## 3. Principios obrigatorios

Principios oficiais:

- dominio antes do provider;
- provider nunca redefine arquitetura;
- adapter nunca redefine dominio;
- console nunca substitui adapter;
- Wizard nunca configura ERP;
- onboarding nunca configura ERP;
- ownership oficial vem da matriz ERP, nao do provider;
- observabilidade e parte obrigatoria da integracao, nao acessorio;
- configuracao do cliente pertence ao console ERP do tenant;
- backoffice observa e suporta, mas nao assume o papel de console principal do cliente.

## 4. Guardrails de ownership

Nenhum adapter ERP pode:

- alterar o owner oficial de uma entidade definido em `ERP-DOMAIN-01`;
- assumir autoria de dados operacionais do AgroSaaS;
- transformar entidade compartilhada em entidade exclusiva do provider;
- usar restricao tecnica do provider como justificativa para mudar o owner da entidade.

Regras obrigatorias:

- entidades operacionais agricolas, pecuarias, territoriais e analiticas permanecem com master AgroSaaS;
- entidades fiscais, contabeis e financeiras administrativas permanecem com master ERP;
- entidades compartilhadas exigem direcao, politica de conflito e estrategia de reconciliacao explicitas;
- qualquer divergencia de ownership e uma violacao arquitetural.

## 5. Guardrails de escopo

Escopos ERP permitidos:

- `TENANT`
- `ESTABELECIMENTO`

Escopos ERP proibidos:

- `UNIDADE_PRODUTIVA`
- `TALHAO`
- `SAFRA`
- `CULTIVO`
- qualquer escopo operacional rural

Regras:

- resolucao de provider ERP acontece por escopo administrativo;
- nenhum provider ERP pode ser configurado por entidade operacional;
- se um caso real demandar granularidade operacional, a solicitacao deve voltar para arquitetura antes de qualquer implementacao;
- a existencia de `PLATFORM` ou `USUARIO` no runtime generico nao autoriza uso desses escopos para governanca ERP sem nova aprovacao arquitetural.

## 6. Guardrails de adapter

Todo adapter ERP obrigatoriamente deve:

- declarar `provider`;
- declarar versao;
- declarar metodo de autenticacao;
- declarar capabilities;
- declarar entidades suportadas;
- declarar entidades nao suportadas;
- declarar modos de sincronizacao por entidade;
- declarar estrategia de `external_id`;
- declarar estrategia de chave composta, quando existir;
- declarar limites operacionais relevantes;
- declarar politicas de retry e rate limit;
- declarar health check;
- declarar teste de conexao;
- declarar diagnostico;
- declarar eventos suportados, quando houver.

Todo adapter ERP obrigatoriamente deve reutilizar o runtime oficial:

- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationCredential`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationVersion`
- `IntegrationJob`
- `IntegrationHealth`
- `ExternalRecordAssociation`

Proibicoes:

- adapter "livre" sem contrato explicito;
- adapter com tabela paralela para lifecycle, health, policy ou mapeamento quando o runtime oficial ja cobre o caso;
- adapter redefinir ownership, escopo ou responsabilidades de camada.

## 7. Guardrails de configuracao

Toda configuracao ERP do cliente deve partir do Console ERP.

Proibido:

- URL hardcoded como fonte primaria de configuracao do cliente;
- credencial em codigo;
- endpoint fixo por cliente dentro do adapter;
- token, segredo ou certificado exposto em tela, log ou relatorio;
- configuracao principal feita no backoffice;
- Wizard atuar como origem de configuracao ERP.

Obrigatorio:

- configuracao versionada;
- snapshot mascarado quando houver historico;
- teste de conexao antes de ativacao;
- auditoria de alteracao de URL, credencial, escopo e capability;
- historico de quem alterou, quando alterou e qual validacao foi executada.

## 8. Guardrails de observabilidade

Nenhuma integracao ERP pode operar como caixa-preta.

Toda integracao ERP obrigatoriamente deve possuir:

- health;
- diagnostico;
- teste de conexao;
- jobs;
- logs;
- timeline;
- reprocessamento controlado;
- reconciliacao manual para conflitos ou associacoes pendentes.

Regras:

- health nao substitui lifecycle;
- job nao substitui policy;
- timeline nao substitui log estruturado;
- observabilidade do tenant e observabilidade do backoffice devem reutilizar o mesmo runtime, com responsabilidades diferentes;
- se nao houver capacidade minima de suporte e auditoria, a integracao e nao conforme.

## 9. Guardrails de mapeamentos

`ExternalRecordAssociation` e a unica fonte oficial de relacionamento entre registros internos e externos.

Obrigatorio:

- usar `ExternalRecordAssociation` para de-para entre entidade AgroSaaS e entidade ERP;
- registrar historico de reconciliacao, conflito, supersessao e reativacao no mecanismo oficial;
- associacoes pendentes ou conflitantes devem permanecer auditaveis.

Proibido:

- segunda tabela de de-para para o mesmo fim;
- segunda estrategia de associacao sem aprovacao arquitetural;
- gravar external IDs diretamente nas entidades de negocio como substituto do mapeamento oficial.

Excecao:

- um campo externo pode existir na entidade de negocio apenas quando for atributo funcional do dominio e nao estrategia paralela de mapeamento.

## 10. Guardrails de sincronizacao

Nenhuma sincronizacao ERP pode existir sem:

- owner definido;
- direcao definida;
- politica definida;
- tratamento de conflito definido;
- estrategia de reprocessamento definida;
- capability declarada;
- modo de sincronizacao permitido para a entidade;
- evidencias de observabilidade.

Regras:

- toda entidade compartilhada deve ter regra explicita de conflito;
- sincronizacao bidirecional sem controle e proibida;
- sync sem `IntegrationSyncPolicy` e nao conforme;
- cargas iniciais, sync incremental e reprocessamentos devem respeitar o mesmo ownership oficial;
- reprocessar nao pode alterar ownership nem escopo.

## 11. Guardrails de permissao

Permissoes minimas obrigatorias para operacao ERP:

- `integrations:view`
- `integrations:configure`
- `integrations:test`
- `integrations:sync`
- `integrations:logs:view`

Permissoes minimas obrigatorias para backoffice:

- `backoffice:integrations:observe`
- `backoffice:integrations:support`

Regras:

- tenant configura e opera sua integracao no proprio console;
- backoffice observa, diagnostica e apoia;
- credenciais e alteracoes criticas exigem permissao administrativa do tenant;
- nenhuma rota ERP deve ficar sem protecao de permissao adequada.

## 12. Guardrails de evolucao

Toda nova integracao ERP deve responder obrigatoriamente, antes da implementacao:

1. Reutiliza o runtime oficial atual?
2. Cria duplicidade de tabela, rota, tela, contrato ou documentacao?
3. Viola ownership definido em `ERP-DOMAIN-01`?
4. Viola escopo permitido para ERP?
5. Contorna o Console ERP?
6. Introduz adapter sem declaracao de capability e policy?
7. Remove ou enfraquece observabilidade?
8. Introduz segunda estrategia de mapeamento?
9. Introduz fluxo operacional no onboarding ou no Wizard?
10. Cria regra provider-specific que deveria ser regra de dominio?

Se qualquer resposta for positiva, a proposta deve voltar para revisao arquitetural antes de prosseguir.

## 13. Checklist obrigatorio para novos providers

Checklist de entrada oficial:

- arquitetura generica auditada;
- provider identificado e classificado;
- capabilities declaradas;
- entidades suportadas e nao suportadas declaradas;
- ownership validado contra `ERP-DOMAIN-01`;
- escopo validado contra `TENANT` ou `ESTABELECIMENTO`;
- politicas de sincronizacao definidas;
- estrategia de `external_id` definida;
- `ExternalRecordAssociation` adotado;
- `IntegrationJob` adotado;
- `IntegrationHealth` adotado;
- `IntegrationSyncPolicy` adotado;
- health check disponivel;
- teste de conexao disponivel;
- diagnostico disponivel;
- logs disponiveis;
- reconciliacao manual prevista;
- documentacao concluida;
- riscos provider-specific documentados.

Sem checklist aprovado:

- o provider nao pode ser incorporado oficialmente.

## 14. Criterios de conformidade

Niveis oficiais:

- `CONFORME`
- `CONFORME COM RESSALVAS`
- `NAO CONFORME`

### 14.1 CONFORME

Aplicavel quando:

- ownership, escopo e runtime oficial sao respeitados;
- observabilidade minima existe;
- configuracao nao depende de fluxo paralelo;
- nao ha duplicidade relevante de conceitos.

### 14.2 CONFORME COM RESSALVAS

Aplicavel quando:

- a fundacao tecnica esta correta;
- existem lacunas de UX, naming, cobertura ou fluxo administrativo;
- nao ha violacao grave de ownership ou escopo;
- existe plano claro de consolidacao.

### 14.3 NAO CONFORME

Aplicavel quando:

- ha violacao de ownership;
- ha configuracao ERP por escopo operacional;
- ha mapeamento paralelo;
- ha integracao sem policy ou sem observabilidade;
- o provider redefine arquitetura;
- o backoffice substitui o console do tenant.

## 15. Criterios de depreciacao

Devem ser tratados como legado, consolidacao ou depreciacao:

- rota legada `/configuracoes/integracoes` como ponto principal para ERP;
- qualquer fluxo que configure ERP fora do Console ERP do tenant;
- qualquer configuracao ERP por `UnidadeProdutiva`;
- nomenclatura Sankhya-first em ativos que passaram a ser genericos de ERP;
- segunda tabela de mapeamento externo;
- hardcode de URL de provider como configuracao primaria;
- qualquer fluxo paralelo que replique lifecycle, health, logs ou policy oficiais.

Regra:

- depreciar nao significa remover de imediato;
- depreciar significa impedir expansao funcional e consolidar para o fluxo oficial.

## 16. Matriz de responsabilidades por camada

Sequencia oficial:

```text
Wizard
  -> Console ERP
    -> Adapter
      -> Provider
        -> ERP
```

Responsabilidades exclusivas:

- Wizard:
  - orientar;
  - verificar pre-requisitos;
  - apontar pendencias;
  - bloquear ou alertar;
  - nunca configurar ERP.
- Console ERP:
  - configurar;
  - validar;
  - versionar;
  - monitorar;
  - operar sync manual permitido;
  - reconciliar;
  - nunca executar sem adapter.
- Adapter:
  - traduzir contrato generico para contrato do provider;
  - aplicar regras de capability, policy e mapeamento;
  - nunca redefinir ownership ou escopo.
- Provider:
  - expor capacidades e restricoes tecnicas;
  - autenticar;
  - receber e devolver dados;
  - nunca definir regra de dominio AgroSaaS.
- ERP:
  - permanecer como sistema administrativo oficial quando assim definido pela matriz;
  - nunca absorver responsabilidade operacional do AgroSaaS por conveniencia tecnica.

## 17. Requisitos obrigatorios de auditoria

Toda execucao futura de implementacao ERP deve apresentar:

- arquivos reutilizados;
- arquivos estendidos;
- duplicidades evitadas;
- riscos de duplicidade remanescentes;
- riscos de divergencia arquitetural;
- impacto no runtime oficial;
- justificativa para qualquer nova estrutura;
- justificativa para qualquer item provider-specific;
- classificacao final de conformidade.

## 18. Aplicacao pratica ao v1 atual

Aplicacao oficial para v1:

- reutilizar o dominio de integracoes existente;
- reutilizar o runtime canonico ja persistido;
- reutilizar o Console ERP do tenant em `/dashboard/settings/integracoes/erp`;
- manter backoffice como observabilidade e suporte;
- tratar Sankhya como provider de referencia, nao como regra geral do dominio ERP;
- consolidar fluxos legados para o console ERP oficial.

## 19. Veredicto normativo

A partir deste documento:

- nenhuma integracao ERP nova pode nascer fora do runtime oficial;
- nenhum provider ERP pode ser oficializado sem checklist arquitetural;
- nenhuma excecao de ownership, escopo ou mapeamento pode ser tratada como detalhe de implementacao;
- toda divergencia passa a ser item formal de auditoria e conformidade.
