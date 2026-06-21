# EXECUTION-24 - Fase 22 API Pública Protegida Certificações/ESG Lote 2

## Objetivo
Expor a API pública protegida do domínio consumidor Certificações/ESG para evidências, não conformidades e planos de ação, mantendo isolamento por tenant e sem tocar na base territorial/fundiária canônica.

## Estratégia aplicada
- Router dedicado em `services/api/certificacoes_esg/router.py`.
- Registro do router em `services/api/main.py` sob `/api/v1`.
- Schemas de entrada com `extra="forbid"` para bloquear `tenant_id` e campos inesperados.
- Serviços reutilizados para garantir leitura/escrita apenas no domínio de certificação.
- Filtros GET expostos para evidências, não conformidades e planos de ação.
- Mapa de rotas atualizado para refletir o novo domínio.

## Endpoints criados
- `POST /api/v1/certificacoes-esg/evidencias`
- `GET /api/v1/certificacoes-esg/evidencias`
- `POST /api/v1/certificacoes-esg/nao-conformidades`
- `GET /api/v1/certificacoes-esg/nao-conformidades`
- `PATCH /api/v1/certificacoes-esg/nao-conformidades/{id}/status`
- `POST /api/v1/certificacoes-esg/planos-acao`
- `GET /api/v1/certificacoes-esg/planos-acao`
- `PATCH /api/v1/certificacoes-esg/planos-acao/{id}/status`

## Filtros suportados
- Evidências: `programa_id`, `checklist_id`, `criterio_id`, `avaliacao_id`, `propriedade_id`, `imovel_rural_id`, `propriedade_imovel_id`, `tipo_evidencia`, `publico`
- Não conformidades: `programa_id`, `checklist_id`, `criterio_id`, `avaliacao_id`, `evidencia_id`, `propriedade_id`, `imovel_rural_id`, `propriedade_imovel_id`, `severidade`, `status`
- Planos de ação: `programa_id`, `nao_conformidade_id`, `evidencia_id`, `responsavel_pessoa_id`, `propriedade_id`, `imovel_rural_id`, `propriedade_imovel_id`, `prioridade`, `status`

## Validações realizadas
- `py_compile` dos arquivos novos/alterados: OK.
- Testes unitários e de integração do router: OK.
- Testes unitários do domínio Certificações/ESG (`schemas`, `service`, `bootstrap`): OK.
- `alembic heads`: head atual permanece `20260621_certificacao_esg_status_nao_conformidade`.

## Resultado
- Router registrado com sucesso.
- Tenant isolation preservado por dependência de sessão/tenant atual.
- Payload não aceita `tenant_id` livremente.
- Status inválido é rejeitado pela tipagem oficial em enum.
- Não houve necessidade de migration nesta fase.

## Riscos e pendências
- Persistem warnings antigos de Pydantic em outras áreas do projeto.
- Não houve validação runtime contra banco nesta fase, pois o escopo era a API e seus testes.
- Próximo passo natural: cobertura E2E autenticada para os novos endpoints ou validação funcional com banco disponível, se necessário.
