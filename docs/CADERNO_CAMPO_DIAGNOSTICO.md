# Diagnóstico: Caderno de Campo (AgroSaaS)

**Data:** 08 de Maio de 2026
**Status Atual:** Estágio 3 (Avançado / Funcional)
**ID do Módulo:** `A1_PLANEJAMENTO`

## 1. Levantamento Técnico

### Models Existentes (`services/api/agricola/caderno/models.py`)
- **CadernoCampoEntrada**: Registro principal de eventos (manuais ou vinculados a operações).
- **CadernoCampoFoto**: Metadados de imagens com geolocalização (latitude/longitude).
- **VisitaTecnica**: Registro formal de visitas agronômicas com constatatações em JSON.
- **EPIEntrega**: Controle de entrega de Equipamentos de Proteção Individual para conformidade NR-31.
- **CadernoExportacao**: Histórico de PDFs gerados com rastreabilidade de assinatura.

### Endpoints Disponíveis (`services/api/agricola/caderno/router.py`)
- **Timeline**: Agregação dinâmica de `CadernoCampoEntrada` + `OperacaoAgricola` finalizadas.
- **CRUD Entradas**: Criação, detalhamento, edição e soft-delete com motivo.
- **Gestão de Fotos**: Upload e vinculação de imagens geolocalizadas.
- **Visitas e EPIs**: Fluxos dedicados para registros de RT e segurança do trabalho.
- **Exportação Multimodelo**: Geração de PDFs nos formatos: **PADRÃO, GLOBALGAP, ORGÂNICO e MAPA**.
- **Assinatura Digital**: Registro de assinatura do RT vinculado à exportação.

### Telas Existentes (`apps/web/src/app/(dashboard)/agricola/`)
- **Timeline da Safra**: Visão cronológica com KPIs (Total, Com Fotos, Alertas).
- **Filtros Avançados**: Por tipo de evento, talhão e período.
- **Timeline Global**: Visão agregada de todas as safras ativas do tenant.
- **Drawer de Detalhes**: Visualização completa de fotos e dados de auditoria.
- **Diálogos de Ação**: Exportação, Assinatura, Registro de EPI e Visita Técnica.

---

## 2. Avaliação de Fluxo e Dependências

### Fluxo de Uso Real
1. **Automático**: Quando uma operação agrícola (plantio, pulverização) é marcada como "REALIZADA", ela aparece automaticamente na timeline do caderno.
2. **Manual**: O agrônomo ou operador registra monitoramentos (pragas/doenças) ou observações climáticas via mobile/web.
3. **Conformidade**: Registros de EPI e Visitas são feitos conforme a necessidade legal.
4. **Fechamento**: O RT revisa a timeline, gera o PDF no modelo desejado e assina digitalmente.

### Dependências Core
- **Safras/Talhões**: Contexto obrigatório para todo registro.
- **Operações Agrícolas**: Fonte primária de dados automáticos.
- **Trabalhadores**: Necessário para o subfluxo de EPIs.
- **Storage**: Dependência crítica para armazenamento de evidências fotográficas e laudos.

---

## 3. Classificação: Estágio 3 (Avançado)

| Nível | Estágio | Descrição |
|-------|---------|-----------|
| 1 | Inicial | Apenas registros manuais simples em banco de dados. |
| 2 | Integrado | Integração com operações automáticas e filtros básicos. |
| **3** | **Funcional** | **Exportação PDF multimodelo, geolocalização e compliance (EPI/RT).** |
| 4 | Enterprise | Offline total, Assinatura ICP-Brasil, IA de diagnóstico e API CREA. |

---

## 4. Identificação de Fricções e Gaps

### Principais Fricções (UX/Ops)
- **Armazenamento Volátil**: Atualmente o sistema salva fotos e PDFs em `/tmp`. Em produção, isso resultará em perda de dados.
- **Edição Retroativa**: A trava de 72h existe, mas não há um fluxo de "solicitação de desbloqueio" para o gestor.
- **UX Mobile**: Apesar de responsivo, a falta de um app nativo ou modo PWA robusto dificulta o uso em áreas com sombra de sinal (comum no agro).

### Gaps para Uso Real (Compliance/Enterprise)
1. **Modo Offline**: O sistema depende 100% de conexão API para salvar registros. No campo, o "Modo Avião" é a regra, não a exceção.
2. **Validade Jurídica**: A "Assinatura" atual é apenas um registro de texto. Para auditorias rigorosas, é necessário assinatura digital (Certificado Digital) ou eletrônica (Logins/IP/Hash).
3. **Integração CREA**: Não há validação real se o CREA informado é válido ou pertence ao profissional via API do conselho.
4. **IA de Monitoramento**: O registro de pragas depende totalmente do input humano; falta o auxílio de IA para identificação por foto (mencionado nos requisitos).

---

## 5. Plano de Ação (Próximos Passos)

1. **[URGENTE] Migração de Storage**: Implementar `S3Service` para salvar fotos e PDFs fora do diretório temporal.
2. **[OFFLINE] Sync LocalStorage**: Implementar fila de sincronização no frontend para permitir registros sem internet.
3. **[COMPLIANCE] Assinatura Eletrônica**: Gerar Hash SHA-256 de cada entrada para garantir que o PDF exportado não foi adulterado.
4. **[INTEGRAÇÃO] Defensivos**: Vincular automaticamente as aplicações de defensivos ao banco de dados de carência (intervalo de segurança).

---
*Documento gerado automaticamente pelo Diagnóstico AgroSaaS v1.0*
