"""Consulta somente leitura consSitNFe com mTLS e configuração segregada por tenant."""
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from core.config import settings
from financeiro.services.documento_xml import MAX_XML, NS, arvore, raiz_segura, texto, validar_chave
from financeiro.services.documentos_fiscais import buscar_nota, registrar


def configuracao(tenant_id, chave: str, ambiente: str):
    """Obtém certificado e autorizadora de arquivo protegido do tenant."""
    if not settings.nfe_consulta_config_dir:
        raise HTTPException(503, 'Consulta SEFAZ não configurada. Configure o certificado do cliente; a consulta pública continua disponível.')
    try:
        config = json.loads((Path(settings.nfe_consulta_config_dir) / f'{tenant_id}.json').read_text())
        url = config['endpoints'][ambiente][chave[:2]]
        parts = urlsplit(url)
        if parts.scheme != 'https' or not (parts.hostname or '').endswith('.gov.br') or parts.username or parts.password:
            raise ValueError('URL não oficial')
        context = ssl.create_default_context(cafile=config.get('ca_file'))
        context.load_cert_chain(config['cert_file'], config['key_file'])
        return url, context
    except (OSError, ValueError, KeyError, TypeError, ssl.SSLError) as exc:
        raise HTTPException(503, 'Certificado ou autorizadora SEFAZ indisponível para este cliente, UF e ambiente.') from exc


def envelope(chave: str, ambiente: str) -> bytes:
    """Cria exclusivamente a operação de consulta de situação."""
    validar_chave(chave)
    if ambiente not in ('1', '2'):
        raise HTTPException(422, 'Informe o ambiente de origem da nota.')
    return f'''<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"><soap:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">
    <consSitNFe xmlns="{NS['n']}" versao="4.00"><tpAmb>{ambiente}</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe></consSitNFe>
    </nfeDadosMsg></soap:Body></soap:Envelope>'''.encode()


def interpretar(raw: bytes, chave: str, ambiente: str):
    """Aceita somente resposta da mesma chave e ambiente, preservando evidência."""
    root = raiz_segura(raw)
    resposta = root if root.tag == '{' + NS['n'] + '}retConsSitNFe' else root.find('.//n:retConsSitNFe', NS)
    if resposta is None or texto(resposta, 'tpAmb') != ambiente or texto(resposta, 'chNFe') != chave:
        raise ValueError('Resposta SEFAZ incompatível com o documento consultado.')
    status = texto(resposta, 'cStat')
    protocolo = resposta.find('n:protNFe/n:infProt', NS)
    if status in ('100', '150') and (protocolo is None or texto(protocolo, 'chNFe') != chave or not texto(protocolo, 'nProt')):
        raise ValueError('Autorização sem protocolo correspondente.')
    return {'estado': 'consultada', 'cstat': status, 'motivo': texto(resposta, 'xMotivo'),
            'em': datetime.now(timezone.utc).isoformat(), 'ambiente': ambiente,
            'protocolo': arvore(protocolo) if protocolo is not None else {},
            'xml_retorno': raw.decode('utf-8-sig')}


async def requisitar(url, context, body):
    """Consulta com TLS verificado, timeout e limite de resposta, sem redirects."""
    headers = {'Content-Type': 'application/soap+xml; charset=utf-8; action="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4/nfeConsultaNF"'}
    async with httpx.AsyncClient(verify=context, timeout=20, follow_redirects=False) as client:
        async with client.stream('POST', url, content=body, headers=headers) as response:
            response.raise_for_status()
            raw = b''
            async for chunk in response.aiter_bytes():
                raw += chunk
                if len(raw) > MAX_XML:
                    raise ValueError('Resposta SEFAZ excede o limite.')
    return raw


async def consultar(session, tenant_id, nota_id):
    """Registra o retorno oficial; falhas não transformam documento em autorizado."""
    nota = await buscar_nota(session, tenant_id, nota_id)
    if not nota.chave_acesso:
        raise HTTPException(422, 'Informe uma chave de acesso ou importe o XML.')
    gestao = nota.gestao or {}
    ambiente = gestao.get('ambiente', '1')
    anterior = gestao.get('consulta', {}).get('em')
    if anterior and (datetime.now(timezone.utc) - datetime.fromisoformat(anterior)).total_seconds() < 60:
        raise HTTPException(429, 'Aguarde um minuto antes de consultar novamente.')
    url, context = configuracao(tenant_id, nota.chave_acesso, ambiente)
    try:
        raw = await requisitar(url, context, envelope(nota.chave_acesso, ambiente))
        retorno = interpretar(raw, nota.chave_acesso, ambiente)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, 'Não foi possível confirmar a situação na SEFAZ. Tente novamente mais tarde.') from exc
    nota.gestao = registrar({**gestao, 'consulta': retorno}, 'Consulta SEFAZ', {'cstat': retorno['cstat'], 'motivo': retorno['motivo']})
    nota.status_sefaz = {'100': 'autorizada', '150': 'autorizada', '101': 'cancelada',
                         '155': 'cancelada', '110': 'denegada', '301': 'denegada',
                         '302': 'denegada'}.get(retorno['cstat'], nota.status_sefaz)
    nota.numero_protocolo = retorno.get('protocolo', {}).get('nProt') or nota.numero_protocolo
    await session.commit()
    await session.refresh(nota)
    return nota
