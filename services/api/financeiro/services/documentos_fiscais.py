"""Persistência, conciliação e vínculos dos documentos fiscais por tenant."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib import import_module
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, cast, or_, select, text

from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.nota_fiscal import NotaFiscal
from financeiro.services.documento_xml import ler_xml

PROCESSOS = {
    'compra': ('operacional.models.compras', 'PedidoCompra', 'numero'),
    'despesa': ('financeiro.models.despesa', 'Despesa', 'descricao'),
    'receita': ('financeiro.models.receita', 'Receita', 'descricao'),
    'safra': ('agricola.safras.models', 'Safra', 'ano_safra'),
    'comercializacao': ('financeiro.comercializacao.models', 'ComercializacaoCommodity', 'id'),
}


def registrar(gestao: dict, evento: str, detalhes: dict | None = None):
    """Registra uma mudança na linha do tempo do documento."""
    return {**gestao, 'historico': [*gestao.get('historico', []), {
        'evento': evento, 'em': datetime.now(timezone.utc).isoformat(), **(detalhes or {})}]}


async def buscar_nota(session, tenant_id: UUID, nota_id: UUID):
    """Busca bloqueada e sempre limitada ao tenant."""
    nota = await session.scalar(select(NotaFiscal).where(
        NotaFiscal.tenant_id == tenant_id, NotaFiscal.id == nota_id).with_for_update())
    if nota is None:
        raise HTTPException(404, 'Nota fiscal não encontrada.')
    return nota


async def conferir_unidade(session, tenant_id: UUID, unidade_id: UUID | None):
    """Valida a unidade e impede referência cruzada entre tenants."""
    if unidade_id is None:
        return None
    unidade = await session.scalar(select(UnidadeProdutiva).where(
        UnidadeProdutiva.id == unidade_id, UnidadeProdutiva.tenant_id == tenant_id))
    if unidade is None:
        raise HTTPException(404, 'Unidade produtiva não encontrada.')
    return unidade


async def bloquear_chave(session, tenant_id: UUID, chave: str | None):
    """Serializa importações da mesma chave no PostgreSQL sem alterar dados legados."""
    if chave and session.get_bind().dialect.name == 'postgresql':
        await session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:chave, 0))'),
                              {'chave': f'{tenant_id}:{chave}'})


async def salvar_manual(session, tenant_id: UUID, dados):
    """Registra documento informado; nenhuma situação fiscal é presumida."""
    await conferir_unidade(session, tenant_id, dados.unidade_produtiva_id)
    await bloquear_chave(session, tenant_id, dados.chave_acesso)
    if dados.chave_acesso and await session.scalar(select(NotaFiscal.id).where(
            NotaFiscal.tenant_id == tenant_id, NotaFiscal.chave_acesso == dados.chave_acesso)):
        raise HTTPException(409, 'Esta chave já está cadastrada. Abra o documento existente.')
    values = dados.model_dump(exclude={'direcao', 'observacoes', 'itens'}, exclude_none=True)
    itens = dados.itens or []
    if not itens and dados.descricao_produto:
        itens = [{'descricao': dados.descricao_produto, 'ncm': dados.ncm,
                  'quantidade': dados.quantidade, 'unidade': dados.unidade,
                  'valor_total': dados.valor_produtos}]
    gestao = {'origem': 'manual', 'direcao': dados.direcao, 'observacoes': dados.observacoes,
              'consulta': {'estado': 'nao_consultada'}, 'vinculos': [],
              'itens': [{'prod': {'xProd': item.get('descricao', ''),
                                   'NCM': item.get('ncm') or '',
                                   'qCom': str(item.get('quantidade') or 0),
                                   'uCom': item.get('unidade') or '',
                                   'vProd': str(item.get('valor_total') or 0),
                                   'vUnCom': str(item.get('valor_unitario') or 0),
                                   'CFOP': item.get('cfop') or ''}}
                      for item in itens]}
    nota = NotaFiscal(tenant_id=tenant_id, **values, gestao=registrar(gestao, 'Registro manual'))
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


def conferir_participante(unidade, values: dict, direcao: str):
    """Exige correspondência quando a unidade possui documento cadastrado."""
    import re
    if unidade and unidade.cpf_cnpj:
        campo = 'destinatario_documento' if direcao == 'entrada' else 'emitente_cpf_cnpj'
        esperado = re.sub(r'\W', '', unidade.cpf_cnpj)
        recebido = re.sub(r'\W', '', values.get(campo) or '')
        if esperado != recebido:
            values['gestao']['alertas'].append(
                'CPF/CNPJ da nota difere do documento cadastrado na unidade produtiva.')
    else:
        values['gestao']['alertas'].append('Vínculo cadastral não verificado: selecione unidade com CPF/CNPJ.')


async def importar(session, tenant_id: UUID, pedido: dict):
    """Importa ou concilia explicitamente, mantendo vínculos e registro anterior."""
    try:
        values = ler_xml(pedido['raw'])
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, str(exc) if not isinstance(exc, RecursionError) else 'XML muito aninhado.') from exc
    unidade = await conferir_unidade(session, tenant_id, pedido.get('unidade_id'))
    conferir_participante(unidade, values, pedido['direcao'])
    await bloquear_chave(session, tenant_id, values['chave_acesso'])
    existentes = list((await session.scalars(select(NotaFiscal).where(
        NotaFiscal.tenant_id == tenant_id, NotaFiscal.chave_acesso == values['chave_acesso']))).all())
    if existentes and not pedido.get('nota_id'):
        raise HTTPException(409, 'Chave já cadastrada. Abra a nota e use Anexar XML para conciliar.')
    nota = await buscar_nota(session, tenant_id, pedido['nota_id']) if pedido.get('nota_id') else NotaFiscal(tenant_id=tenant_id)
    if any(n.id != nota.id for n in existentes):
        raise HTTPException(409, 'Esta chave pertence a outro registro.')
    aplicar_importacao(nota, values, pedido)
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


def aplicar_importacao(nota, values: dict, pedido: dict):
    """Preserva documento importado e expõe divergências da conciliação manual."""
    anterior = deepcopy(nota.gestao or {})
    if anterior.get('origem') == 'xml':
        raise HTTPException(409, 'XML original já armazenado. O documento não pode ser substituído.')
    if nota.chave_acesso and nota.chave_acesso != values['chave_acesso']:
        raise HTTPException(409, 'A chave do XML difere da chave registrada.')
    diferencas = {k: {'manual': str(getattr(nota, k)), 'xml': str(v)} for k, v in values.items()
                 if k != 'gestao' and getattr(nota, k, None) is not None and str(getattr(nota, k)) != str(v)}
    values['gestao'].update(direcao=pedido['direcao'], vinculos=anterior.get('vinculos', []),
                           historico=anterior.get('historico', []), divergencias=diferencas,
                           observacoes=anterior.get('observacoes', ''))
    values['gestao'] = registrar(values['gestao'], 'XML importado', {'registro_anterior': anterior})
    for campo, valor in values.items():
        setattr(nota, campo, valor)
    nota.unidade_produtiva_id = pedido.get('unidade_id') or nota.unidade_produtiva_id
    nota.xml_original = pedido['raw']
    cstat = values['gestao'].get('protocolo_xml', {}).get('cStat')
    nota.status_sefaz = {'100': 'autorizada', '150': 'autorizada', '101': 'cancelada',
                         '155': 'cancelada', '110': 'denegada', '301': 'denegada',
                         '302': 'denegada'}.get(cstat, 'em_digitacao')
    nota.numero_protocolo = values['gestao'].get('protocolo_xml', {}).get('nProt') or None


def modelo_processo(tipo: str):
    """Resolve apenas tipos de processo autorizados pelo catálogo local."""
    if tipo not in PROCESSOS:
        raise HTTPException(422, 'Tipo de processo inválido.')
    modulo, classe, label = PROCESSOS[tipo]
    return getattr(import_module(modulo), classe), label


async def listar_processos(session, tenant_id: UUID, filtros: dict):
    """Oferece seleção de registros reais do tenant, sem IDs livres."""
    modelo, label = modelo_processo(filtros['tipo'])
    campo = getattr(modelo, label)
    stmt = select(modelo.id, campo).where(modelo.tenant_id == tenant_id)
    if filtros.get('q'):
        stmt = stmt.where(or_(cast(campo, String).ilike('%' + filtros['q'] + '%'),
                              cast(modelo.id, String) == filtros['q']))
    return [{'id': str(r[0]), 'label': str(r[1])} for r in (await session.execute(stmt.limit(30))).all()]


async def vincular(session, tenant_id: UUID, pedido: dict):
    """Associa documento a processo existente sem gerar estoque ou títulos."""
    nota = await buscar_nota(session, tenant_id, pedido['nota_id'])
    modelo, label = modelo_processo(pedido['tipo'])
    processo = await session.scalar(select(modelo).where(modelo.tenant_id == tenant_id, modelo.id == pedido['id']))
    if processo is None:
        raise HTTPException(404, 'Processo não encontrado.')
    gestao = deepcopy(nota.gestao or {})
    vinculo = {'tipo': pedido['tipo'], 'id': str(processo.id), 'label': str(getattr(processo, label))}
    links = gestao.get('vinculos', [])
    if not any(v['tipo'] == vinculo['tipo'] and v['id'] == vinculo['id'] for v in links):
        gestao['vinculos'] = [*links, vinculo]
        nota.gestao = registrar(gestao, 'Processo associado', vinculo)
        await session.commit()
        await session.refresh(nota)
    return nota
