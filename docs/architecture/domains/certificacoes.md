# Domínio Certificações do AgroSaaS

**Status:** Catálogo canônico do domínio compartilhado  
**Base normativa:** [Master Context](../agrosaas-master-context.md), [Domain Map](../agrosaas-domain-map.md), [Data Model](../agrosaas-data-model.md), [Routing Map](../agrosaas-routing-map.md), [AGRI-DOMAIN-001](../standards/AGRI-DOMAIN-001-territorial-fundiario.md), [AGRI-DOMAIN-002](../standards/AGRI-DOMAIN-002-propriedade-imovel.md)

## 1. Visão Geral

Certificações não aparecem como um único módulo autônomo de escrita no backend; elas surgem como uma capacidade transversal apoiada por Agrícola, Territorial/Fundiário, Ambiental, Caderno de Campo, Rastreabilidade e Comercialização.

Este documento formaliza essa camada como domínio compartilhado de conformidade e prova.

## 2. Objetivo

- Sustentar auditorias e programas de certificação.
- Consolidar evidências de origem, operação, ambiente e segurança.
- Produzir snapshots e passaportes de rastreabilidade.

## 3. Subdomínios

| Subdomínio | Objetivo | Entidades / fontes | Integrações | Status |
|---|---|---|---|---|
| Evidência | Reunir provas auditáveis | `CadernoExportacao`, fotos, snapshots | Agrícola, RH, Ambiental | IMPLEMENTADO |
| Passaporte | Expor origem do lote | `CadernoLoteComercial`, `LoteRastreabilidade` | Comercialização, rastreabilidade | IMPLEMENTADO |
| Selos e Programas | Organizar certificações ativas | `CertificacaoPropriedade` e dados associados | Ambiental, territorial | PARCIAL |
| Auditoria | Registrar prontidão e conformidade | logs, hashes, snapshots | Governança, AI rules | IMPLEMENTADO |

## 4. Entidades

| Entidade | Responsabilidade | Ownership | Relacionamentos | Fonte da verdade |
|---|---|---|---|---|
| `CertificacaoPropriedade` | Certificação vinculada a unidade produtiva | Compartilhado | unidade produtiva | Compartilhado |
| `LoteRastreabilidade` | Passaporte do lote | Compartilhado | safra, talhão, certificações | Agrícola / compartilhado |
| `CadernoLoteComercial` | Passaporte comercial assinado | Compartilhado | produto colhido, beneficiamento | Compartilhado |
| `CadernoExportacao` | Snapshot documental | Agrícola / compartilhado | safra, talhão, assinatura | Compartilhado |

## 5. Fluxos

```text
Território + fundiário + ambiental
↓
Operação + caderno + colheita
↓
Passaporte / snapshot
↓
Certificação / auditoria
↓
Exportação / due diligence
```

## 6. Eventos

- `PassaporteGerado`
- `SnapshotCertificacaoCriado`
- `EvidenciaPublicada`
- `CertificacaoAtivada`
- `CertificacaoVencendo`
- `AuditoriaConcluida`

## 7. Integrações

| Módulo | Integração | Dependência | Impacto |
|---|---|---|---|
| Agrícola | Safra, talhão, caderno, colheita | Alta | Base da prova operacional |
| Propriedades | Geometria e território | Alta | Base espacial |
| Imóveis Rurais | Titularidade e documentação | Alta | Base jurídica |
| Ambiental | CAR, APP, outorga, carbono | Alta | Base de conformidade |
| RH | Segurança do trabalho e treinamentos | Média | Evidência humana |
| Financeiro | Comercialização e origem de receita | Média | Auditoria de negócio |

## 8. Regras de Negócio

1. Certificação não cria uma nova verdade territorial.
2. Nenhum dado pode ter duas fontes oficiais.
3. Todo passaporte deve derivar de dados já auditáveis.
4. Snapshot de certificação deve ser imutável após publicação.
5. Certificações devem preservar a cadeia até o imóvel rural.
6. ESG, carbono e certificação são camadas transversais, não módulos concorrentes.

## 9. Fronteiras

### Pertence

- Evidências;
- Passaportes;
- Certificações ativas;
- Snapshots;
- Auditoria;
- Prontidão de exportação.

### Não pertence

- Execução agrícola;
- Titularidade fundiária;
- Cadastro territorial;
- Folha de pagamento;
- Fluxo financeiro geral.

## 10. Roadmap

| Funcionalidade | Status | Observação |
|---|---|---|
| Passaporte / snapshot | IMPLEMENTADO | Forte base documental existente. |
| Certificações por propriedade | PARCIAL | Já há entidades e rotas, mas a governança é transversal. |
| Auditoria de exportação | IMPLEMENTADO | Mantém trilha imutável. |
| Selos e programas completos | PLANEJADO | Requer integração formal por certificadora e programa. |

