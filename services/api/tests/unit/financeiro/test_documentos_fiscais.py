from decimal import Decimal

import pytest

from financeiro.services.documento_xml import ler_xml, numero_decimal, validar_chave


def chave():
    base = '3526091234567800019555001000000001100000001'
    soma = sum(int(n) * (2 + i % 8) for i, n in enumerate(reversed(base)))
    dv = 11 - soma % 11
    return base + str(0 if dv >= 10 else dv)


def arquivo():
    k = chave()
    return f'''<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
    <NFe><infNFe Id="NFe{k}" versao="4.00"><ide><mod>55</mod><serie>1</serie>
    <nNF>1</nNF><dhEmi>2026-09-14T10:00:00-03:00</dhEmi><tpAmb>1</tpAmb><natOp>Venda</natOp></ide>
    <emit><CNPJ>12345678000195</CNPJ><xNome>Fornecedor</xNome></emit>
    <dest><CNPJ>98765432000198</CNPJ><xNome>Fazenda</xNome><enderDest><UF>SP</UF></enderDest></dest>
    <det nItem="1"><prod><cProd>SOJA</cProd><xProd>Soja</xProd><NCM>12019000</NCM><CFOP>5102</CFOP><uCom>KG</uCom><qCom>10.0000</qCom><vUnCom>12.34</vUnCom><vProd>123.40</vProd></prod><imposto><ICMS><ICMS00><CST>00</CST></ICMS00></ICMS></imposto></det>
    <total><ICMSTot><vProd>123.40</vProd><vNF>123.40</vNF><vICMS>0</vICMS></ICMSTot></total></infNFe></NFe>
    <protNFe><infProt><tpAmb>1</tpAmb><chNFe>{k}</chNFe><cStat>100</cStat><nProt>135260000000001</nProt><dhRecbto>2026-09-14T10:01:00-03:00</dhRecbto></infProt></protNFe></nfeProc>'''.encode()


def test_leitura_preserva_itens_e_nao_afirma_consulta_sefaz():
    nota = ler_xml(arquivo())
    assert nota['valor_total'] == Decimal('123.40')
    assert nota['gestao']['itens'][0]['prod']['CFOP'] == '5102'
    assert nota['gestao']['consulta']['estado'] == 'nao_consultada'
    assert nota['gestao']['assinatura'] == 'nao_verificada'
    assert nota['gestao']['protocolo_xml']['cStat'] == '100'


@pytest.mark.parametrize('xml', [b'<foo/>', b'<!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>', b'<NFe>', b'x' * (2 * 1024 * 1024 + 1)])
def test_rejeita_arquivo_invalido(xml):
    with pytest.raises(ValueError):
        ler_xml(xml)


def test_rejeita_protocolo_de_outra_nota():
    with pytest.raises(ValueError, match='protocolo'):
        ler_xml(arquivo().replace(f'<chNFe>{chave()}</chNFe>'.encode(), b'<chNFe>0</chNFe>'))


def test_chave_digito_verificador():
    assert validar_chave(chave()) == chave()
    with pytest.raises(ValueError):
        validar_chave(chave()[:-1] + str((int(chave()[-1]) + 1) % 10))


@pytest.mark.parametrize('valor', ['NaN', 'Infinity', '-1', '12abc'])
def test_rejeita_valores_invalidos(valor):
    with pytest.raises(ValueError):
        numero_decimal(valor)
