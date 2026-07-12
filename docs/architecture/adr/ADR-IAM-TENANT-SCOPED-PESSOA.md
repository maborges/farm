# ADR: Vínculo IAM Tenant-Scoped entre Usuário e Pessoa

**Status:** Proposed / Aceito (Fase 0)
**Contexto:** Integração entre a Identidade Global de Acesso (`Usuario`) e a Identidade Operacional Local (`Pessoa`), sob governança multi-tenant e RLS.

## 1. Contexto e Problema

O AgroSaaS utiliza um modelo de autenticação *cross-tenant*, onde `Usuario` é uma entidade global. O acesso a um determinado *tenant* é regido por `TenantUsuario`. 
As operações físicas e comerciais (Caderno de Campo, RH, ERP) são orquestradas localmente pela entidade `Pessoa` (tenant-scoped).
Atualmente, não existe um vínculo duro no banco de dados entre quem loga (`TenantUsuario`) e quem ele fisicamente é (`Pessoa`). Isso dificulta auditorias de rastreabilidade e experiências "One-Click" no PWA.

Precisamos materializar um vínculo opcional, garantindo o isolamento (Row Level Security) e a correção da cardinalidade.

## 2. Opções Consideradas

1. **`TenantUsuario.pessoa_id` como Foreign Key Simples.**
   - *Prós:* Simples, não requer restruturação das PKs.
   - *Contras:* O banco de dados, em nível de foreign key padrão, não garante que `Pessoa.tenant_id == TenantUsuario.tenant_id`.

2. **`TenantUsuario.pessoa_id` com Foreign Key Composta `(tenant_id, pessoa_id)`.**
   - *Prós:* Garantia absoluta e blindada de integridade tenant-scoped no motor relacional.
   - *Contras:* Exige que `Pessoa` tenha uma *Unique Constraint* em `(id, tenant_id)`, o que altera a topologia de tabelas.

3. **Tabela Associativa `UsuarioPessoa` tenant-scoped.**
   - *Prós:* Permite mapeamentos complexos N:N.
   - *Contras:* Over-engineering. Um usuário em um tenant atua fisicamente como um indivíduo.

4. **Vínculo lógico via Serviço sem FK física.**
   - *Prós:* Zero migrations.
   - *Contras:* Perda de integridade, risco de deleção em cascata deixar registros órfãos, violação do `EVENTS-ARCH`.

## 3. Decisão

Selecionou-se uma variação reforçada da **Opção 1 (FK Simples com Políticas e Validadores)**:
Implementar a coluna `pessoa_id (UUID, nullable=True, FK para cadastros_pessoas.id, ON DELETE SET NULL)` diretamente na tabela `TenantUsuario`.

**Justificativa Técnica:**
- **Isolamento (RLS):** Como o PostgreSQL já utiliza políticas estritas de Row Level Security baseadas na sessão (jwt `tenant_id`), a leitura e escrita de `Pessoa` são automaticamente protegidas. Um usuário malicioso não consegue vincular uma pessoa de outro tenant porque a query de validação retornará nulo (vazada no RLS).
- **Validação de Serviço:** A API de criação/associação deverá checar se `pessoa.tenant_id == tenant_id` antes de emitir o `UPDATE`.
- **ON DELETE SET NULL:** Garante que, se uma `Pessoa` for anonimizada/excluída por exigência da LGPD, o `TenantUsuario` não é apagado (pois o owner não perde seu acesso, apenas seu rastro operacional).
- **Sem UNIQUE CONSTRAINT rigorosa:** Não colocaremos `UNIQUE (pessoa_id, tenant_id)` na tabela `TenantUsuario`. Se o produtor tem duas contas de e-mail (uma de uso geral e uma administrativa corporativa) logadas no mesmo tenant, ele pode, se desejar, atrelar ambas à sua única `Pessoa` física, minimizando duplicação civil.

## 4. Impacto

- **Positivo:** Resolverá definitivamente o roteamento de responsabilidade entre Identidade e Operação, simplificando logs de auditoria e eliminando ambiguidades no apontamento móvel.
- **Negativo:** Requer migration e alteração nas rotas de Convite/Aceite, bem como tela de pareamento no Admin.
- **Momento Adequado:** Fase 3 (Pós-Piloto). O piloto rodará sem essa trava para facilitar a fricção mínima no Go-Live.
