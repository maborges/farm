"""Carga inicial idempotente da Base de Conhecimento."""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session_maker
from core.models.knowledge_base import ConhecimentoArtigo, ConhecimentoCategoria

KB_INICIAL = {
    "Comece por aqui": ("BookOpen", 10, [
        ("Configure sua conta e equipe", "configurar-conta-equipe", """# Configure sua conta e equipe

Use **Configurações** para completar os dados da organização, enviar a logo e definir idioma e contatos.

## Próximos passos

1. Acesse **Configurações > Organização**.
2. Revise os dados do responsável e envie a identidade visual.
3. Em **Usuários e permissões**, convide cada pessoa com o acesso adequado.

> Mantenha pelo menos uma pessoa administradora ativa para não perder o acesso à conta.
"""),
        ("Cadastre a primeira propriedade e seus talhões", "primeira-propriedade-talhoes", """# Cadastre a primeira propriedade e seus talhões

A propriedade organiza a operação e os talhões delimitam as áreas de produção.

1. Abra **Cadastros > Propriedades** e crie a unidade produtiva.
2. Informe localização, área e dados operacionais.
3. Adicione os talhões no mapa ou registre-os manualmente.
4. Vincule os talhões à safra antes de iniciar o planejamento.
"""),
    ]),
    "Planejamento e operação agrícola": ("Sprout", 20, [
        ("Planeje uma safra", "planejar-safra", """# Planeje uma safra

Em **Agrícola > Safras**, informe cultura, período, talhões e metas. Depois registre o orçamento e as operações previstas.

## Boa prática

Crie uma safra por ciclo produtivo. Assim, custos, aplicações, colheita e resultados ficam comparáveis no mesmo contexto.
"""),
        ("Registre atividades no caderno de campo", "registrar-caderno-campo", """# Registre atividades no caderno de campo

O caderno concentra aplicações, serviços, observações e evidências da execução.

1. Selecione a safra e o talhão.
2. Registre data, operação, responsáveis e insumos.
3. Anexe fotos ou documentos quando necessário.
4. Revise os dados antes de gerar relatórios ou assinaturas.
"""),
        ("Acompanhe mapas, análises e prescrições", "mapas-analises-prescricoes", """# Mapas, análises e prescrições

Use as análises de solo, mapas e prescrições para transformar dados técnicos em ações por área.

As recomendações devem ser revisadas por responsável técnico antes da aplicação em campo.
"""),
    ]),
    "Compras, estoque e frota": ("Package", 30, [
        ("Controle compras e estoque", "controle-compras-estoque", """# Controle compras e estoque

Cadastre fornecedores e produtos antes de registrar cotações, pedidos e entradas.

As entradas atualizam o saldo do estoque. Ao vincular um insumo à operação agrícola, o consumo passa a compor os custos da safra.
"""),
        ("Acompanhe uso e manutenção da frota", "uso-manutencao-frota", """# Uso e manutenção da frota

Em **Operacional > Frota**, mantenha equipamentos, horímetros e planos de manutenção atualizados.

Registre abastecimentos, jornadas e intervenções para acompanhar disponibilidade, consumo e custo por operação.
"""),
    ]),
    "Pecuária": ("Beef", 40, [
        ("Organize o rebanho e os manejos", "organizar-rebanho-manejos", """# Organize o rebanho e os manejos

Cadastre os animais ou lotes, informe origem, categoria e localização. Registre pesagens, movimentações, sanidade e demais manejos na ordem em que acontecem.

Essa rotina preserva a rastreabilidade e melhora os indicadores produtivos e econômicos.
"""),
        ("Registre compras, vendas e custos do rebanho", "compras-vendas-custos-rebanho", """# Compras, vendas e custos do rebanho

Vincule cada compra ou venda aos animais, lote e documentos correspondentes. Use os relatórios para acompanhar margem, ganho de peso e custo por categoria.
"""),
    ]),
    "Financeiro e documentos fiscais": ("HandCoins", 50, [
        ("Acompanhe caixa, contas e custos", "caixa-contas-custos", """# Caixa, contas e custos

No módulo **Financeiro**, registre receitas, despesas e vencimentos. Faça a conciliação quando houver movimentação bancária e classifique os lançamentos para obter relatórios consistentes.

Quando a despesa estiver ligada a uma safra, operação ou rebanho, faça o vínculo para refletir o custo no resultado correspondente.
"""),
        ("Importe e consulte documentos fiscais", "documentos-fiscais", """# Documentos fiscais

Em **Financeiro > Documentos fiscais**, envie o XML ou consulte a nota quando a integração estiver habilitada.

Confira fornecedor, itens, valores e vínculos com compras antes de concluir o lançamento financeiro.
"""),
    ]),
    "Indicadores, IA e suporte": ("Lightbulb", 60, [
        ("Leia os painéis e relatórios", "paineis-relatorios", """# Painéis e relatórios

Os painéis reúnem informações da operação, produção e finanças. Use os filtros de período, propriedade, safra e atividade para analisar o contexto correto antes de tomar decisões.
"""),
        ("Use os recursos de IA com segurança", "recursos-ia-seguranca", """# Recursos de IA com segurança

Os recursos de IA ajudam a interpretar dados, sugerir ações e organizar informações. Revise cada sugestão com base nos dados da fazenda e na orientação técnica responsável.

Não use sugestões automáticas como substituição de registros operacionais ou de decisões técnicas obrigatórias.
"""),
        ("Obtenha ajuda e envie uma solicitação", "obter-ajuda-suporte", """# Obtenha ajuda

Pesquise nesta Base de Conhecimento antes de abrir uma solicitação. Se precisar falar com a equipe, acesse **Configurações > Suporte** e descreva o que ocorreu, incluindo data, tela e mensagens exibidas.
"""),
    ]),
}


async def seed_kb() -> None:
    """Cria apenas categorias e artigos ausentes, sem alterar conteúdo existente."""
    async with async_session_maker() as session:
        await seed_kb_with_session(session)


async def seed_kb_with_session(session: AsyncSession) -> None:
    """Aplica as categorias e artigos à sessão da carga inicial."""
    for nome, (icone, ordem, artigos) in KB_INICIAL.items():
        categoria = await _find_or_create_category(session, nome, icone, ordem)
        await _create_missing_articles(session, categoria, artigos)
    await session.commit()


async def _find_or_create_category(
    session: AsyncSession, nome: str, icone: str, ordem: int
) -> ConhecimentoCategoria:
    """Localiza uma categoria pelo nome ou cria a categoria inicial."""
    categoria = await session.scalar(select(ConhecimentoCategoria).where(ConhecimentoCategoria.nome == nome))
    if categoria:
        return categoria
    categoria = ConhecimentoCategoria(nome=nome, icone=icone, ordem=ordem)
    session.add(categoria)
    await session.flush()
    return categoria


async def _create_missing_articles(
    session: AsyncSession, categoria: ConhecimentoCategoria, artigos: list[tuple[str, str, str]]
) -> None:
    """Inclui somente artigos cujos slugs ainda não existem."""
    for titulo, slug, conteudo in artigos:
        artigo_id = await session.scalar(select(ConhecimentoArtigo.id).where(ConhecimentoArtigo.slug == slug))
        if not artigo_id:
            session.add(ConhecimentoArtigo(
                categoria_id=categoria.id, titulo=titulo, slug=slug, conteudo=conteudo, is_publico=True
            ))


if __name__ == "__main__":
    asyncio.run(seed_kb())
