"""Leitura local de NF-e: extrai evidências sem atribuir validade fiscal."""
import hashlib
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

NS = {'n': 'http://www.portalfiscal.inf.br/nfe'}
MAX_XML = 2 * 1024 * 1024


def validar_chave(valor: str) -> str:
    """Valida formato e dígito da chave; não consulta sua existência."""
    if not re.fullmatch(r'[0-9]{44}', valor):
        raise ValueError('A chave deve conter 44 dígitos.')
    if not valor.strip('0'):
        raise ValueError('A chave de acesso não pode ser zerada.')
    soma = sum(int(n) * (2 + i % 8) for i, n in enumerate(reversed(valor[:43])))
    dv = 11 - soma % 11
    if int(valor[-1]) != (0 if dv >= 10 else dv):
        raise ValueError('Dígito verificador da chave inválido.')
    return valor


def numero_decimal(valor: str) -> Decimal:
    """Rejeita valores não finitos ou negativos, sem arredondar silenciosamente."""
    try:
        numero = Decimal(valor)
    except InvalidOperation as exc:
        raise ValueError('Valor numérico inválido no documento.') from exc
    if not numero.is_finite() or numero < 0 or numero > Decimal('999999999999999'):
        raise ValueError('Valor numérico fora do limite permitido.')
    return numero


def texto(node, caminho: str, padrao: str = '') -> str:
    """Lê exclusivamente elementos do namespace oficial."""
    return node.findtext('/'.join('n:' + p for p in caminho.split('/')), padrao, NS).strip()


def arvore(node) -> dict | str:
    """Preserva grupos e repetições, inclusive tributos de novos leiautes."""
    if not len(node):
        return (node.text or '').strip()
    result = dict(node.attrib)
    for child in node:
        name = child.tag.split('}')[-1]
        value = arvore(child)
        if name in result:
            previous = result[name]
            result[name] = (previous if isinstance(previous, list) else [previous]) + [value]
        else:
            result[name] = value
    return result


def raiz_segura(raw: bytes):
    """Limita tamanho e rejeita DTD/entidades; aceita XML UTF-8 de NF-e."""
    if not raw or len(raw) > MAX_XML:
        raise ValueError('Envie um XML de até 2 MB.')
    try:
        xml = raw.decode('utf-8-sig')
        if '\x00' in xml or re.search(r'<!\s*(DOCTYPE|ENTITY)', xml, re.I):
            raise ValueError('DTD e entidades não são permitidos.')
        root = ET.fromstring(xml)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError('XML inválido. Utilize o arquivo original em UTF-8.') from exc
    if sum(1 for _ in root.iter()) > 50000:
        raise ValueError('XML excede o limite de elementos.')
    return root


def conferir_identificacao(info, chave: str):
    """Confere identidade da chave com os dados declarados no XML."""
    ide = info.find('n:ide', NS)
    if ide is None or texto(ide, 'mod') not in ('55', '65'):
        raise ValueError('Somente NF-e modelo 55 e NFC-e modelo 65 são suportadas.')
    emissao = datetime.fromisoformat(texto(ide, 'dhEmi'))
    emitente = texto(info, 'emit/CNPJ') or texto(info, 'emit/CPF')
    partes = (chave[2:6] == emissao.strftime('%y%m'), chave[6:20] == emitente.zfill(14),
              chave[20:22] == texto(ide, 'mod'), int(chave[22:25]) == int(texto(ide, 'serie')),
              int(chave[25:34]) == int(texto(ide, 'nNF')), emissao.tzinfo is not None)
    if not all(partes) or texto(ide, 'tpAmb') not in ('1', '2'):
        raise ValueError('Identificação da nota diverge da chave ou do ambiente.')
    return ide, emissao


def evidencias(root, info, raw: bytes):
    """Separa evidência recebida, verificações locais e consulta remota."""
    protocolo = root.find('n:protNFe/n:infProt', NS)
    if protocolo is not None:
        if texto(protocolo, 'chNFe') != info.attrib['Id'][3:] or texto(protocolo, 'tpAmb') != texto(info, 'ide/tpAmb'):
            raise ValueError('Chave ou ambiente do protocolo diverge da nota.')
    itens = [arvore(item) for item in info.findall('n:det', NS)]
    if not itens or len(itens) > 990:
        raise ValueError('A nota deve conter entre 1 e 990 itens.')
    for item in info.findall('n:det/n:prod', NS):
        for campo in ('qCom', 'vUnCom', 'vProd'):
            numero_decimal(texto(item, campo))
    return {'origem': 'xml', 'ambiente': texto(info, 'ide/tpAmb'), 'itens': itens,
            'dados_xml': arvore(info), 'protocolo_xml': arvore(protocolo) if protocolo is not None else {},
            'sha256': hashlib.sha256(raw).hexdigest(), 'assinatura': 'nao_verificada',
            'schema': 'nao_verificado', 'consulta': {'estado': 'nao_consultada'},
            'vinculos': [], 'historico': [], 'alertas': ['Assinatura digital e XSD não verificados.', 'Situação atual na SEFAZ ainda não consultada.']}


def ler_xml(raw: bytes) -> dict:
    """Extrai uma única nota; arquivos de eventos devem ser tratados separadamente."""
    root = raiz_segura(raw)
    if root.tag not in ('{' + NS['n'] + '}nfeProc', '{' + NS['n'] + '}NFe'):
        raise ValueError('Envie o XML NFe ou nfeProc. PDF, lotes e eventos não são notas completas.')
    nodes = root.findall('.//n:infNFe', NS)
    if len(nodes) != 1:
        raise ValueError('O arquivo deve conter exatamente uma nota.')
    info = nodes[0]
    if not info.attrib.get('Id', '').startswith('NFe'):
        raise ValueError('Identificador da nota ausente.')
    chave = validar_chave(info.attrib['Id'][3:])
    ide, emissao = conferir_identificacao(info, chave)
    result = campos_principais(info, ide)
    result.update(chave_acesso=chave, data_emissao=emissao, gestao=evidencias(root, info, raw))
    return result


def campos_principais(info, ide) -> dict:
    """Normaliza o resumo; o restante permanece no documento original e no detalhe."""
    result = {'tipo': 'NF-e' if texto(ide, 'mod') == '55' else 'NFC-e',
              'numero': int(texto(ide, 'nNF')), 'serie': texto(ide, 'serie'),
              'emitente_nome': texto(info, 'emit/xNome'),
              'emitente_cpf_cnpj': texto(info, 'emit/CNPJ') or texto(info, 'emit/CPF'),
              'destinatario_nome': texto(info, 'dest/xNome') or 'Não identificado no XML',
              'destinatario_documento': texto(info, 'dest/CNPJ') or texto(info, 'dest/CPF') or None,
              'destinatario_uf': texto(info, 'dest/enderDest/UF') or None,
              'descricao_produto': texto(info, 'det/prod/xProd')[:300]}
    if not result['emitente_nome']:
        raise ValueError('Emitente ausente no XML.')
    for campo, tag in [('valor_total', 'vNF'), ('valor_produtos', 'vProd'), ('valor_icms', 'vICMS'), ('valor_frete', 'vFrete')]:
        result[campo] = numero_decimal(texto(info, 'total/ICMSTot/' + tag, '0'))
    return result
