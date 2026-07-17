# TERRITORY-CONVERGENCE-01J2 - Auditoria do Ciclo Propriedade/Imóvel Rural

## 1. Resumo Executivo

A auditoria confirmou que o ciclo oficial de cadastro de Propriedade e Imóvel Rural estava funcional no backend, mas a suíte de integração não estava medindo corretamente dois pontos:

- reuso do Imóvel principal quando o `imovel_rural.id` não vinha no update;
- promoção de principal em `PropriedadeImovel` com violação de constraint ao fazer a troca no mesmo flush.

Foram aplicados ajustes cirúrgicos no backend e nas asserções de teste. Após isso, a suíte PostgreSQL real passou sem falhas, e o frontend permaneceu tipando/buildando com sucesso.

## 2. Jornada Frontend Atual

Arquivos auditados:

- `apps/web/src/components/propriedade/propriedade-dialog.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/app/(dashboard)/cadastros/propriedades/[id]/propriedade-detalhe-client.tsx`
- `packages/zod-schemas/src/fazenda-schemas.ts`

Estado atual:

- a criação e a edição seguem o contrato em blocos;
- o submit preserva `imovel_rural.id` e `propriedade_imovel.id` quando presentes;
- o CEP limpa `bairro`, `cidade`, `uf`, `logradouro`, `complemento` e `numero` quando o serviço não devolve valor;
- o payload de edição não depende de campos fundiários achatados da UP;
- a invalidação das queries segue o fluxo de lista/detalhe/visões.

## 3. Jornada Backend Atual

Arquivos auditados:

- `services/api/core/services/cadastro_completo_service.py`
- `services/api/core/cadastros/propriedade_imovel/service.py`
- `services/api/core/services/territory_read_service.py`
- `services/api/core/routers/unidades_produtivas.py`
- `services/api/imoveis/services/imovel_service.py`

Decisões atuais:

- `CadastroCompletoService` preserva o contrato em blocos e não repassa campos fundiários para a UP;
- quando `imovel_rural.id` não vem no update, o service reaproveita o principal ativo existente quando há um único candidato;
- se a propriedade tem múltiplos vínculos ativos sem ID explícito, o service responde com regra de negócio, não com heurística;
- a leitura territorial não escolhe secundário arbitrariamente como principal;
- o router de cadastro completo faz rollback explícito em exceção.

## 4. Sintomas Reproduzidos

Foram reproduzidos e depois estabilizados:

- update sem `imovel_rural.id` reutilizando o principal existente;
- troca explícita de principal em propriedade com mais de um imóvel;
- rollback do update completo quando a associação falha;
- leitura territorial sem fallback arbitrário;
- contrato frontend/backend preservado em PostgreSQL real.

## 5. Criação sem Imóvel

Resultado validado:

- `POST /api/v1/unidades-produtivas/cadastro-completo`
- criação da UP e da Propriedade
- sem criação artificial de `ImovelRural`
- sem criação artificial de `PropriedadeImovel`

## 6. Criação com Imóvel

Resultado validado:

- `POST /api/v1/unidades-produtivas/cadastro-completo`
- criação da UP, Propriedade, Exploração, Imóvel Rural e vínculo canônico
- retorno com IDs oficiais
- persistência no mesmo tenant

## 7. Associação Criada

Foi confirmado que:

- o vínculo canônico é criado via `PropriedadeImovelService`;
- o principal é definido como tal no primeiro vínculo;
- vínculos secundários podem ser adicionados e promovidos explicitamente.

## 8. Carregamento do Formulário

Os dados iniciais do formulário de Propriedade carregam o contexto oficial:

- `territorio.imovel_principal`
- `territorio.imoveis_secundarios`
- `imovel_rural_id`
- `propriedade_imovel_id`

Não foi mantido fallback para campos fundiários achatados da UP.

## 9. Atualização de Imóvel Existente

Correção aplicada:

- o update sem `imovel_rural.id` agora reaproveita o principal vigente quando existe um único candidato ativo;
- a troca explícita de principal em `PropriedadeImovel` passou a fazer flush do vínculo atual antes de promover o novo, evitando violação de `uq_propriedade_imovel_principal_ativo`.

## 10. Criação Quando Associação Não Existe

O fluxo passou a:

- criar o Imóvel quando há bloco fundiário e não há vínculo resolvível;
- criar a associação canônica;
- manter idempotência nos cenários repetidos.

## 11. Múltiplos Imóveis

Foi validado:

- primeiro imóvel principal;
- segundo imóvel como secundário;
- promoção explícita de principal;
- preservação dos vínculos restantes;
- nenhum `IntegrityError` como fluxo normal.

## 12. Comportamento sem IDs

O comportamento atual é:

- com um único principal ativo, o update pode resolvê-lo explicitamente;
- com ambiguidade, o backend não adivinha e retorna regra de negócio controlada;
- não há criação silenciosa de novo imóvel apenas por ausência de ID.

## 13. RLS

Validado na suíte:

- tenant divergente não lê;
- tenant divergente não atualiza;
- tenant divergente não associa;
- tenant divergente não promove principal;
- tenant divergente não deleta.

## 14. Transações

Correções de coordenação transacional:

- o router faz rollback explícito em exceção;
- a promoção de principal no vínculo agora rebaixa o principal atual e faz flush antes de promover o novo;
- a suíte confirmou rollback no caminho de falha.

## 15. Causas-Raiz

As causas confirmadas foram:

- asserções de teste usando nome fixo, gerando falso positivo por acúmulo de dados entre execuções;
- promoção de principal em um único flush, que batia na constraint única parcial;
- necessidade de validar o contrato por ID oficial, não por heurística textual.

## 16. Correções Aplicadas

Backend:

- `services/api/core/cadastros/propriedade_imovel/service.py`
- `services/api/core/services/cadastro_completo_service.py`
- `services/api/core/services/territory_read_service.py`
- `services/api/core/routers/unidades_produtivas.py`

Frontend:

- `apps/web/src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx`
- `apps/web/src/components/propriedade/propriedade-dialog.tsx`

Testes:

- `services/api/tests/integration/territory/test_post_convergence_runtime.py`
- `services/api/tests/unit/core/test_cadastro_completo.py`
- `services/api/tests/unit/core/test_territory_read_service.py`

## 17. Contratos Finais

Contrato validado:

- `unidade_produtiva`
- `propriedade`
- `exploracao_rural`
- `imovel_rural`
- `propriedade_imovel`

Sem:

- campos fundiários dentro da UP;
- vínculo direto UP/Imóvel;
- inferência por documento/nome;
- fallback arbitrário para secundário.

## 18. Testes PostgreSQL

Suíte executada:

- `services/api/tests/integration/territory/test_post_convergence_runtime.py`

Resultado:

- `10 passed`

Suítes unitárias executadas:

- `services/api/tests/unit/core/test_cadastro_completo.py`
- `services/api/tests/unit/core/test_territory_read_service.py`
- `services/api/tests/unit/propriedade_imovel/test_visao_service.py`
- `services/api/tests/integration/propriedade_imovel/test_visao_router.py`
- `services/api/tests/unit/test_territory_convergence_guardrails.py`

Resultado agregado:

- `24 passed`

## 19. Testes Frontend

Executados com sucesso:

- `cd apps/web && npm run typecheck`
- `cd apps/web && npm run lint`
- `cd apps/web && npm run build`
- `cd apps/campo && npm run typecheck`

Observação:

- o build do web mostrou warnings de renderização dinâmica em rotas antigas, mas concluiu com sucesso.

## 20. Auditoria Física

Confirmado no PostgreSQL real com schema `farms`:

- criação completa persistiu os registros oficiais;
- update preservou IDs e não duplicou imóveis;
- segundo imóvel foi criado como secundário;
- troca de principal ficou consistente;
- rollback não deixou resíduos do payload falho;
- leitura territorial e fundiária retornaram `200`.

## 21. Riscos

- persistem warnings de depreciação do Pydantic em várias rotas legadas;
- o build do web ainda reporta warnings de uso dinâmico em rotas não relacionadas ao ciclo territorial;
- a superfície de `apps/web` segue grande e com contratos antigos em outras áreas.

## 22. Veredicto

O ciclo Propriedade/Imóvel Rural foi validado em PostgreSQL real após as correções cirúrgicas.

Checklist:

- Nova Propriedade cria Imóvel quando necessário? SIM
- Novo Imóvel é associado à Propriedade? SIM
- IDs são retornados e preservados? SIM
- Reabertura carrega dados oficiais? SIM
- Alteração atualiza o mesmo Imóvel? SIM
- Ausência de Imóvel cria e associa corretamente? SIM
- Múltiplos Imóveis são tratados sem arbitrariedade? SIM
- Não há duplicidade? SIM
- RLS funciona? SIM
- Testes representam o runtime? SIM

GO
