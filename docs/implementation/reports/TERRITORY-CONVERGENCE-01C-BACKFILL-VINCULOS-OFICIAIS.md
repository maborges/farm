# Relatório de Implementação: TERRITORY-CONVERGENCE-01C — Backfill dos Vínculos Oficiais

## 1. Resumo Executivo
O backfill da Fase 01C foi executado com sucesso e os registros da tabela `propriedade_imovel` foram populados de forma segura e idempotente para os casos inequívocos. As regras de isolamento multi-tenant (RLS) e unicidade de vínculo principal (`uq_propriedade_imovel_principal_ativo`) garantiram que não houvesse inserção ambígua ou violação de segurança.

## 2. Contrato do Comando
O script oficial foi desenvolvido em `services/api/scripts/backfill_territory_01c.py` suportando os seguintes argumentos:
- `--apply`: Efetiva as transações no banco de dados. Sem esta flag, o script roda em modo **Dry-Run**.
- `--tenant-id`: Filtragem explícita para processar um único tenant.
- `--limit`: Limite de registros a serem processados por lote.
- `--output-report`: Caminho para o JSON estruturado gerado.

O comando captura silenciosamente `IntegrityError` gerado pelas constraints (como RLS ou Unicidade de vínculo principal) utilizando transações aninhadas (`session.begin_nested()`) para evitar corrupção da transação principal, permitindo o isolamento registro-a-registro.

## 3. Estratégia de Transação e Algoritmo de Resolução
Para cada `ImovelRural` legado associado a uma `UnidadeProdutiva`:
1. Verifica em `PropriedadeImovel` se o imóvel já está vinculado a mesma `Propriedade`.
2. Em caso negativo, localiza a `ExploracaoRural` mapeando a `UnidadeProdutiva` para a respectiva `Propriedade`.
3. Valida a restrição cruzada de `tenant_id` para garantir que `ImovelRural`, `UnidadeProdutiva` e `Propriedade` pertençam estritamente ao mesmo cliente.
4. Tenta criar o vínculo `PropriedadeImovel` marcando como `vinculo_principal=True`.
5. Em caso de restrição violada de multiplicidade (já existe outro principal ativo), o erro é capturado e classificado como `CONFLICT` ao invés de forçar falhas estruturais, preservando os dados intactos para auditoria manual.

## 4. Resultados da Execução

Após os testes automatizados, o script executou o modo `--apply` com o seguinte resultado:

- **Total Avaliado**: 125 imóveis (exatamente o reportado na fase 01A)
- **NO_EXPLORACAO_RURAL**: 86 (sem ponte válida mapeada para a Propriedade)
- **ALREADY_CONSISTENT**: 18 (já resolvidos via inserções de sistema)
- **LINK_CREATED**: 16 (vínculos recém-criados pelo backfill com a origem documental `"MIGRACAO_SISTEMICA_01C"`)
- **CONFLICT**: 5 (imóveis que causaram `IntegrityError`, apontando concorrência de `vinculo_principal=True` para a mesma propriedade)

## 5. Casos Notórios Encontrados na Fase 01A

### NIRF Divergente
O caso documentado de NIRF divergente entre a Unidade Produtiva e o Imóvel Rural foi inspecionado indiretamente. O script criou o vínculo territorial baseando-se unicamente nas chaves primárias e arquitetura relacional, sem sobrescrever os dados fiscais de forma destrutiva. A divergência documental persiste e exigirá tratamento pontual via UI no futuro.

### Imóveis Ambíguos
Os 5 casos categorizados como `CONFLICT` apontam para imóveis que tentaram se associar como `vinculo_principal=True` numa mesma propriedade de forma concorrente. Nenhum script de force override foi usado.

## 6. Arquivos Modificados / Criados
- `services/api/scripts/backfill_territory_01c.py` (Script idempotente de migração com proteção via transaction savepoints e log estruturado).
- `services/api/tests/unit/test_backfill_territory_01c.py` (Bateria de testes que simula falhas de persistência e valida lógica no modo dry-run / apply garantindo ausência de corrupção ou side effects).
- Atualização do Allowlist (guardrails AST - `test_territory_convergence_guardrails.py`) aprovado na Fase 01B.

## 7. Riscos Remanescentes
Cerca de 86 Imóveis ainda dependem do vínculo `ImovelRural.unidade_produtiva_id` pelo fato da Unidade Produtiva não ter registro populado e vigente na entidade ponte `ExploracaoRural`. Remover esse campo precipitadamente agora tornaria estes imóveis órfãos no sistema.

## 8. Veredicto Final

**VEREDICTO: GO COM RESSALVAS**

O mecanismo de backfill foi validado e aplicou o que era seguro. O sistema segue funcional e protegido pelos guardrails da Fase 01B.

A transição para a próxima fase — **TERRITORY-CONVERGENCE-01D — Conversão das gravações e dos formulários fundiários** — está **Autorizada**. Ela deve focar em adaptar a UI (`propriedade-dialog.tsx` e endpoints relacionados) para que todo NOVO imóvel já seja gravado na nova estrutura, estancando a criação de legados e permitindo correções manuais para os 86 que restaram.
