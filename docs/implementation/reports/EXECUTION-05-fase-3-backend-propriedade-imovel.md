# EXECUTION-05 - Fase 3 Backend da Convergencia Propriedades x Imoveis Rurais

## Objetivo
Implementar a camada backend da entidade canonica `PropriedadeImovel`, respeitando a norma territorial/fundiaria, o `tenant isolation` e a fonte oficial de cada dominio.

## Resultado
Fase 3 concluida com sucesso.

## Arquivos criados
- `services/api/core/cadastros/propriedade_imovel/__init__.py`
- `services/api/core/cadastros/propriedade_imovel/models.py`
- `services/api/core/cadastros/propriedade_imovel/schemas.py`
- `services/api/core/cadastros/propriedade_imovel/service.py`
- `services/api/core/cadastros/propriedade_imovel/router.py`
- `services/api/tests/unit/propriedade_imovel/test_service.py`
- `services/api/tests/integration/propriedade_imovel/test_router.py`

## Arquivos modificados
- `services/api/core/models/__init__.py`
- `services/api/core/cadastros/propriedades/propriedade_models.py`
- `services/api/imoveis/models/imovel.py`
- `services/api/main.py`

## Model
`PropriedadeImovel` foi criado e mapeado para a tabela `propriedade_imovel`.

Cobertura implementada:
- campos obrigatorios e opcionais da entidade canonica
- enum oficial `TipoVinculoPropriedadeImovel`
- constraints de tipo, datas, percentual e area
- indices operacionais e de consulta
- indice parcial para principalidade ativa
- relacoes com `Propriedade` e `ImovelRural`

## Schemas
Os schemas Pydantic foram criados:
- `PropriedadeImovelBase`
- `PropriedadeImovelCreate`
- `PropriedadeImovelUpdate`
- `PropriedadeImovelRead`
- `PropriedadeImovelList`

Validações cobertas:
- `tipo_vinculo` com valores oficiais
- `data_inicio` obrigatoria na criacao
- `origem_documental` obrigatoria e nao vazia
- `percentual_vinculado` entre 0 e 100
- `area_vinculada` nao negativa
- `data_fim >= data_inicio`
- `tenant_id` nao exposto livremente no payload

## Service
O service dedicado foi criado com as regras de negocio do vinculo:
- valida tenant atual
- valida existencia de propriedade e imovel rural no tenant
- valida origem documental
- valida vigencia
- valida area e percentual
- impede segundo vinculo principal ativo sobreposto na mesma propriedade
- preserva historico na inativacao
- nao altera titularidade nem operacao

## Router
O router FastAPI foi criado e registrado em `main.py`.

Endpoints disponiveis:
- `GET /api/v1/propriedade-imovel`
- `GET /api/v1/propriedade-imovel/{id}`
- `POST /api/v1/propriedade-imovel`
- `PATCH /api/v1/propriedade-imovel/{id}`
- `DELETE /api/v1/propriedade-imovel/{id}`

Filtros suportados:
- `propriedade_id`
- `imovel_rural_id`
- `tipo_vinculo`
- `ativo`
- `vinculo_principal`

## Testes unitarios
Cobertura criada para:
- criacao valida
- origem documental ausente
- propriedade inexistente
- imovel inexistente
- tenant divergente
- percentual invalido
- area negativa
- data fim menor que data inicio
- segundo vinculo principal invalido
- vinculo secundario valido

## Testes de integracao
Cobertura criada para:
- listar vinculos do tenant
- obter vinculo por id
- criar vinculo
- atualizar vinculo
- inativar vinculo
- impedir acesso cross-tenant
- registrar o router no `main.app`

## Validacoes executadas
- `alembic heads`
- `pytest tests/unit/propriedade_imovel/test_service.py tests/integration/propriedade_imovel/test_router.py -q`
- validacao estatica dos novos modulos com `py_compile` durante a implementacao

Resultado das validacoes:
- `alembic heads` retornou apenas `add_propriedade_imovel (head)`
- a suite focada passou: `17 passed`

## Observacoes
- O worktree geral continua com alteracoes externas a esta tarefa, herdadas do contexto do repositorio.
- Foram observados avisos deprecados de Pydantic em outros modulos ja existentes do backend; nao bloqueiam esta entrega.

## Resposta objetiva
1. Model foi criado: sim.
2. Schemas foram criados: sim.
3. Service foi criado: sim.
4. Router foi criado e registrado: sim.
5. Testes unitarios foram criados: sim.
6. Testes de integracao foram criados: sim.
7. Validacoes executadas: `alembic heads`, `pytest` focalizado e validacao estatica.
8. Pode avancar para Fase 4: sim.
