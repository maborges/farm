# TERRITORY-CONVERGENCE-01E — Conversão das Leituras e Desativação Controlada

## Resumo da Fase

Nesta fase (01E), consolidamos o caminho oficial de leitura territorial (`UnidadeProdutiva` → `ExploracaoRural` → `Propriedade` → `PropriedadeImovel` → `ImovelRural`), mitigando a dependência do vínculo legado e dos campos achatados da `UnidadeProdutiva`.

## Implementações

1. **TerritoryReadService**
   Foi criado o serviço oficial de leitura em `core/services/territory_read_service.py`, que executa a resolução territorial em 7 etapas, garantindo:
   - Resolução da associação canônica (`PropriedadeImovel`).
   - Identificação do vínculo principal e secundários.
   - Fallback para o legado (`ImovelRural.unidade_produtiva_id` e campos de texto) apenas quando estritamente necessário.
   - Geração de telemetria rica (`[TerritoryRead] source=... state=...`).

2. **Refatoração do Overlay**
   O método `UnidadeProdutivaService._aplicar_overlay_territorial` foi reescrito para utilizar o `TerritoryReadService`. Ele preenche os campos achatados da resposta Pydantic para não quebrar clientes antigos, ao mesmo tempo em que injeta a árvore completa de leitura (`territorio: TerritoryReadView`) na resposta da API.

3. **Desativação Parcial do Sincronizador Legado**
   O método `UnidadeProdutivaService._sincronizar_vinculo_fundiario` foi atualizado com um bypass inteligente: se o `TerritoryReadService` identificar uma fonte canônica (`CANONICAL_PROPERTY_ASSOCIATION`), a auto-criação legada é abortada (`NOOP_CANONICAL_LINK_EXISTS`), prevenindo lixo de dados.

4. **Frontend Modernizado**
   - Os schemas de UI foram atualizados para incluir o nó `territorio`.
   - A listagem geral de UPs e a página de detalhes agora extraem prioritariamente os identificadores (NIRF, CAR, Matrícula) do Imóvel Principal oficial.
   - Foram implementados alertas (ícones na tabela e banners no detalhe) que avisam caso haja ambiguidade ou se a unidade produtar ainda depende de fallbacks legados.
   - Foi criada uma seção dedicada para visualização dos *Imóveis Secundários*.

5. **Guardrails Atualizados**
   O AST foi atualizado para isolar e permitir as chamadas temporárias do `TerritoryReadService` até que todos os fluxos sejam portados.

## Próximos Passos (Fase 01F)
Após monitorarmos a telemetria gerada por esta fase e convalidarmos o abandono dos campos locais, a fase 01F (Drops) executará as deleções físicas das colunas e tabelas legadas que já não sustentam a arquitetura.
