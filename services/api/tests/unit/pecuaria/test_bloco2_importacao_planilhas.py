from __future__ import annotations

import io
import uuid
import zipfile
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from agricola.custos.models import CostAllocation
from agricola.cultivos.models import Cultivo
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from campo.models import TarefaCampo
from core.cadastros.pessoas.models import Pessoa
from core.cadastros.produtos.models import Produto
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.measurements.models import UnidadeMedida
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import Deposito, EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.producao.models import ProducaoLeite
from pecuaria.services.importacao_service import ImportacaoPecuariaService, OpcoesImportacao
from pecuaria.services.importacao_templates import (
    gerar_template_planilha,
    sugerir_mapeamento_colunas,
)
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService
from pecuaria.services.planilha_parser import (
    MAX_IMPORT_ROWS,
    MAX_UPLOAD_BYTES,
    gerar_csv_bytes,
    gerar_xlsx_bytes,
    ler_planilha_bytes,
    parse_date_br,
    parse_float_br,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Animal.__table__.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    UnidadeProdutiva.__table__,
                    AreaRural.__table__,
                    Safra.__table__,
                    ProductionUnit.__table__,
                    Cultivo.__table__,
                    UnidadeMedida.__table__,
                    Produto.__table__,
                    Deposito.__table__,
                    Pessoa.__table__,
                    LoteAnimal.__table__,
                    ManejoLote.__table__,
                    Animal.__table__,
                    EventoAnimal.__table__,
                    ProducaoLeite.__table__,
                    TarefaCampo.__table__,
                    EstoqueMovimento.__table__,
                    CostAllocation.__table__,
                    LancamentoFinanceiro.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _montar_xlsx_com_estilo_data_e_celula_esparsa() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Dados" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
            '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/>'
            "</cellXfs></styleSheet>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1">'
            '<c r="A1" t="inlineStr"><is><t>Brinco</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>Observacao</t></is></c>'
            '<c r="C1" t="inlineStr"><is><t>Data</t></is></c>'
            "</row>"
            '<row r="2">'
            '<c r="A2" t="inlineStr"><is><t>BR-001</t></is></c>'
            '<c r="C2" s="1"><v>46346</v></c>'
            "</row>"
            "</sheetData></worksheet>",
        )
    return buf.getvalue()


async def _criar_contexto_basico(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    outro_tenant_id = uuid.uuid4()
    fazenda_id = uuid.uuid4()
    piquete_id = uuid.uuid4()
    session.add_all([
        Tenant(id=tenant_id, nome="T1", slug="t1", documento="11111111000101"),
        Tenant(id=outro_tenant_id, nome="T2", slug="t2", documento="22222222000102"),
        UnidadeProdutiva(id=fazenda_id, tenant_id=tenant_id, nome="Fazenda Teste"),
        AreaRural(
            id=piquete_id,
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            tipo="PIQUETE",
            nome="Pasto Mombaça Norte",
            area_hectares=25.0,
            ativo=True,
        ),
    ])
    await session.commit()
    return tenant_id, outro_tenant_id, fazenda_id, piquete_id


def test_parser_csv_ptbr_latin1_xlsx_esparsa_e_formula_injection() -> None:
    csv_bom = (
        "\ufeffLote;Cabeças;Peso Médio;Valor Compra;Data\n"
        "Lote A;15;450,5;R$ 30.000,00;20/11/2026\n"
        "Lote B;10;380.25;12500.50;2026-11-20\n"
    ).encode("utf-8")
    planilha = ler_planilha_bytes("rebanho.csv", csv_bom)
    assert planilha.formato == "csv"
    assert len(planilha.rows) == 2
    assert planilha.rows[0][0] == 2
    assert parse_float_br(planilha.rows[0][1]["Peso Médio"]) == pytest.approx(450.5)
    assert parse_float_br(planilha.rows[0][1]["Valor Compra"]) == pytest.approx(30000.0)
    assert parse_date_br(planilha.rows[0][1]["Data"]) == date(2026, 11, 20)
    assert parse_date_br(planilha.rows[1][1]["Data"]) == date(2026, 11, 20)

    csv_latin1 = "Brinco,Raça,Categoria\nBR-99,Mestiço,Bezerros\n".encode("cp1252")
    planilha_cp = ler_planilha_bytes("animais.csv", csv_latin1)
    assert planilha_cp.rows[0][1]["Raça"] == "Mestiço"

    xlsx_bytes = gerar_xlsx_bytes(
        "Lotes",
        ["Identificacao", "Cabecas", "Observacao"],
        [["Lote X", 20, "Teste"], ["Lote Y", 15, "=CMD|' /C calc'!A0"]],
    )
    lida_xlsx = ler_planilha_bytes("lotes.xlsx", xlsx_bytes)
    assert lida_xlsx.formato == "xlsx"
    assert lida_xlsx.rows[0][1]["Identificacao"] == "Lote X"
    assert lida_xlsx.rows[0][1]["Cabecas"] == "20"
    assert lida_xlsx.rows[1][1]["Observacao"].startswith("'=")

    esparsa = _montar_xlsx_com_estilo_data_e_celula_esparsa()
    lida_esparsa = ler_planilha_bytes("esparsa.xlsx", esparsa)
    assert lida_esparsa.rows[0][1]["Brinco"] == "BR-001"
    assert lida_esparsa.rows[0][1]["Observacao"] == ""
    assert lida_esparsa.rows[0][1]["Data"] == "2026-11-20"

    csv_formula = gerar_csv_bytes(["Texto", "Numero"], [["=SUM(A1:A2)", -10], ["+1+1", 25]])
    texto_csv = csv_formula.decode("utf-8-sig")
    assert "'=SUM(A1:A2)" in texto_csv
    assert "'+1+1" in texto_csv
    assert ";-10" in texto_csv


def test_parser_rejeita_arquivos_inseguros_xxe_zip_slip_magic_e_limites() -> None:
    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("macro.xlsm", b"PK\x03\x04...")

    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("falso.xlsx", b"texto plano disfarcado")

    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("zip_disfarcado.csv", b"PK\x03\x04conteudo")

    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("nulo.csv", b"col1;col2\nval\x00;ok\n")

    # XXE / DTD em XML interno do XLSX
    xxe_buf = io.BytesIO()
    with zipfile.ZipFile(xxe_buf, "w") as zf:
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><worksheet/>',
        )
    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("xxe.xlsx", xxe_buf.getvalue())

    # Zip Slip
    slip_buf = io.BytesIO()
    with zipfile.ZipFile(slip_buf, "w") as zf:
        zf.writestr("../evil.xml", "<x/>")
    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("slip.xlsx", slip_buf.getvalue())

    # Tamanho acima do limite
    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("grande.csv", b"a" * (MAX_UPLOAD_BYTES + 1))

    # Linhas acima do limite
    linhas = ["brinco"] + [f"BR-{idx}" for idx in range(MAX_IMPORT_ROWS + 1)]
    excesso_csv = "\n".join(linhas).encode("utf-8")
    with pytest.raises(BusinessRuleError):
        ler_planilha_bytes("muitas_linhas.csv", excesso_csv)


def test_templates_round_trip_para_todos_os_tipos() -> None:
    for tipo in ("LOTES", "ANIMAIS", "PESAGENS"):
        for formato in ("xlsx", "csv"):
            conteudo, media_type, filename = gerar_template_planilha(tipo, formato)
            assert len(conteudo) > 20
            assert filename.endswith(f".{formato}")
            assert media_type
            lida = ler_planilha_bytes(filename, conteudo)
            assert len(lida.rows) >= 2
            mapeamento = sugerir_mapeamento_colunas(tipo, lida.headers)
            assert any(valor is not None for valor in mapeamento.values())


@pytest.mark.asyncio
async def test_importacao_lotes_preview_execucao_conflitos_e_erros(async_session: AsyncSession) -> None:
    tenant_id, _, fazenda_id, piquete_id = await _criar_contexto_basico(async_session)
    service = ImportacaoPecuariaService(async_session, tenant_id)

    csv_inicial = (
        "Lote;Modo;Categoria;Raça;Cabeças;Peso Médio;Pasto;Rendimento Carcaça;Valor Compra;Cotação\n"
        "Lote Engorda 01;POR_LOTE;Novilhos;Nelore;25;420,5;pasto mombaca norte;52;62500;315\n"
        "Lote Pasto Desconhecido;;Recria;Angus;12;310;Pasto Inexistente;;;;\n"
    ).encode("utf-8")

    preview = await service.previsualizar(
        OpcoesImportacao(tipo="LOTES", unidade_produtiva_id=fazenda_id),
        "lotes.csv",
        csv_inicial,
    )
    assert preview.total_linhas == 2
    assert preview.a_criar == 2
    assert preview.com_erro == 0
    assert preview.avisos_total >= 1
    assert preview.mapeamento_aplicado["identificacao"] == "Lote"
    assert preview.mapeamento_aplicado["piquete"] == "Pasto"
    assert len((await async_session.execute(select(LoteAnimal))).scalars().all()) == 0

    execucao = await service.executar(
        OpcoesImportacao(tipo="LOTES", unidade_produtiva_id=fazenda_id),
        "lotes.csv",
        csv_inicial,
    )
    await async_session.commit()
    assert execucao.criados == 2
    assert execucao.erros == 0

    lote_1 = await async_session.scalar(
        select(LoteAnimal).where(LoteAnimal.identificacao == "Lote Engorda 01")
    )
    assert lote_1 is not None
    assert lote_1.area_id == piquete_id
    assert lote_1.quantidade_cabecas == 25
    assert lote_1.peso_medio_kg == pytest.approx(420.5)
    assert lote_1.peso_inicial_medio_kg == pytest.approx(420.5)
    assert lote_1.rendimento_carcaca_pct == pytest.approx(52.0)
    assert lote_1.valor_aquisicao_total == pytest.approx(62500.0)
    assert lote_1.cotacao_arroba_override == pytest.approx(315.0)

    # Conflito IGNORAR não altera o registro existente
    csv_reimport = (
        "identificacao;categoria;raca;quantidade_cabecas;peso_medio_kg\n"
        "Lote Engorda 01;Novilhos;Nelore;40;450\n"
        ";Novilhos;Nelore;10;300\n"
    ).encode("utf-8")
    with pytest.raises(BusinessRuleError):
        await service.executar(
            OpcoesImportacao(
                tipo="LOTES",
                unidade_produtiva_id=fazenda_id,
                modo_conflito="IGNORAR",
                ignorar_linhas_com_erro=False,
            ),
            "reimport.csv",
            csv_reimport,
        )

    exec_parcial = await service.executar(
        OpcoesImportacao(
            tipo="LOTES",
            unidade_produtiva_id=fazenda_id,
            modo_conflito="IGNORAR",
            ignorar_linhas_com_erro=True,
        ),
        "reimport.csv",
        csv_reimport,
    )
    await async_session.commit()
    assert exec_parcial.ignorados == 1
    assert exec_parcial.erros == 1
    await async_session.refresh(lote_1)
    assert lote_1.quantidade_cabecas == 25

    # Conflito ATUALIZAR atualiza normalmente, exceto se tentar rebaixar lote com animal individual ativo
    async_session.add(
        Animal(
            tenant_id=tenant_id,
            unidade_produtiva_id=fazenda_id,
            lote_id=lote_1.id,
            numero_brinco="BR-TRV-1",
            categoria="BOI",
            sexo="CASTRADO",
            status="ATIVO",
        )
    )
    lote_1.modo_gestao = "INDIVIDUAL"
    await async_session.commit()

    csv_rebaixar = (
        "identificacao;modo_gestao;categoria;raca;quantidade_cabecas;peso_medio_kg\n"
        "Lote Engorda 01;POR_LOTE;Novilhos;Nelore;25;430\n"
    ).encode("utf-8")
    prev_trava = await service.previsualizar(
        OpcoesImportacao(tipo="LOTES", unidade_produtiva_id=fazenda_id, modo_conflito="ATUALIZAR"),
        "trava.csv",
        csv_rebaixar,
    )
    assert prev_trava.com_erro == 1
    assert "INDIVIDUAL" in prev_trava.linhas_erro[0].erros[0] or "individuais" in prev_trava.linhas_erro[0].erros[0]


@pytest.mark.asyncio
async def test_importacao_animais_normalizacao_lote_automatico_e_multitenant(
    async_session: AsyncSession,
) -> None:
    tenant_id, outro_tenant_id, fazenda_id, _ = await _criar_contexto_basico(async_session)
    lote_coletivo = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Coletivo Existente",
        modo_gestao="POR_LOTE",
        categoria="Bezerros",
        raca="Nelore",
        quantidade_cabecas=10,
        peso_medio_kg=200.0,
    )
    async_session.add(lote_coletivo)
    await async_session.commit()

    service = ImportacaoPecuariaService(async_session, tenant_id)
    outro_service = ImportacaoPecuariaService(async_session, outro_tenant_id)

    csv_animais = (
        "Brinco;Lote;Categoria;Sexo;Raça;Peso;Valor Aquisição;Data Entrada\n"
        "BR-101;Lote Coletivo Existente;Vaca de Corte;;Nelore;460,5;R$ 4.200,00;2026-11-10\n"
        "BR-102;Lote Novo Matrizes;Novilho;;Angus;380;3900;2026-11-10\n"
        "BR-103;Lote Novo Matrizes;Boi Gordo;;Brangus;520;5100;2026-11-10\n"
    ).encode("utf-8")

    with pytest.raises(EntityNotFoundError):
        await outro_service.previsualizar(
            OpcoesImportacao(tipo="ANIMAIS", unidade_produtiva_id=fazenda_id),
            "animais.csv",
            csv_animais,
        )

    exec_animais = await service.executar(
        OpcoesImportacao(
            tipo="ANIMAIS",
            unidade_produtiva_id=fazenda_id,
            criar_lotes_automaticamente=True,
        ),
        "animais.csv",
        csv_animais,
    )
    await async_session.commit()

    assert exec_animais.criados == 3
    assert exec_animais.lotes_criados_automaticamente == 1
    assert exec_animais.erros == 0

    br101 = await async_session.scalar(select(Animal).where(Animal.numero_brinco == "BR-101"))
    br102 = await async_session.scalar(select(Animal).where(Animal.numero_brinco == "BR-102"))
    br103 = await async_session.scalar(select(Animal).where(Animal.numero_brinco == "BR-103"))
    assert br101 is not None and br101.categoria == "VACA_CORTE" and br101.sexo == "FEMEA"
    assert br102 is not None and br102.categoria == "GARROTE" and br102.sexo == "MACHO"
    assert br103 is not None and br103.categoria == "BOI" and br103.sexo == "CASTRADO"
    assert br101.valor_aquisicao == pytest.approx(4200.0)
    assert br101.data_ultima_pesagem == date(2026, 11, 10)

    pesagens_iniciais = (await async_session.execute(select(EventoAnimal))).scalars().all()
    assert len(pesagens_iniciais) == 3

    await async_session.refresh(lote_coletivo)
    assert lote_coletivo.modo_gestao == "INDIVIDUAL"
    assert lote_coletivo.quantidade_cabecas == 1
    assert lote_coletivo.peso_medio_kg == pytest.approx(460.5)

    lote_novo = await async_session.scalar(
        select(LoteAnimal).where(LoteAnimal.identificacao == "Lote Novo Matrizes")
    )
    assert lote_novo is not None
    assert lote_novo.modo_gestao == "INDIVIDUAL"
    assert lote_novo.quantidade_cabecas == 2
    assert lote_novo.peso_medio_kg == pytest.approx(450.0)

    # Brinco duplicado na planilha + atualização de existente
    csv_dup = (
        "numero_brinco;categoria;raca;peso_atual_kg;lote\n"
        "BR-102;BOI;Angus;410;Lote Novo Matrizes\n"
        "BR-102;BOI;Angus;415;Lote Novo Matrizes\n"
    ).encode("utf-8")
    prev_dup = await service.previsualizar(
        OpcoesImportacao(tipo="ANIMAIS", unidade_produtiva_id=fazenda_id, modo_conflito="ATUALIZAR"),
        "dup.csv",
        csv_dup,
    )
    assert prev_dup.a_atualizar == 1
    assert prev_dup.com_erro == 1

    prev_ign = await service.previsualizar(
        OpcoesImportacao(tipo="ANIMAIS", unidade_produtiva_id=fazenda_id, modo_conflito="IGNORAR"),
        "dup_ign.csv",
        csv_dup,
    )
    assert prev_ign.a_ignorar == 1
    assert prev_ign.com_erro == 1


@pytest.mark.asyncio
async def test_importacao_pesagens_hibrida_individual_e_coletiva_com_gmd(
    async_session: AsyncSession,
) -> None:
    tenant_id, _, fazenda_id, _ = await _criar_contexto_basico(async_session)
    lote_ind = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Individual 01",
        modo_gestao="INDIVIDUAL",
        categoria="BOI",
        raca="Nelore",
        quantidade_cabecas=1,
        peso_medio_kg=400.0,
    )
    lote_col = LoteAnimal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        identificacao="Lote Coletivo 01",
        modo_gestao="POR_LOTE",
        categoria="Novilhos",
        raca="Nelore",
        quantidade_cabecas=10,
        peso_medio_kg=400.0,
        peso_inicial_medio_kg=None,
    )
    async_session.add_all([lote_ind, lote_col])
    await async_session.flush()

    animal = Animal(
        tenant_id=tenant_id,
        unidade_produtiva_id=fazenda_id,
        lote_id=lote_ind.id,
        numero_brinco="BR-PES-01",
        categoria="BOI",
        sexo="CASTRADO",
        peso_atual_kg=400.0,
        data_ultima_pesagem=date(2026, 10, 1),
        status="ATIVO",
    )
    async_session.add(animal)
    await async_session.commit()

    service = ImportacaoPecuariaService(async_session, tenant_id)
    csv_pesagens = (
        "Brinco;Lote;Data;Peso (kg);Peso Total (kg);Cabecas;Observacao\n"
        "BR-PES-01;;2026-10-31;430;;;Ganho individual\n"
        ";Lote Coletivo 01;2026-10-01;;4000;10;Primeira pesagem coletiva\n"
        ";Lote Coletivo 01;2026-10-31;;4300;10;Segunda pesagem coletiva\n"
    ).encode("utf-8")

    exec_1 = await service.executar(
        OpcoesImportacao(tipo="PESAGENS", unidade_produtiva_id=fazenda_id),
        "pesagens.csv",
        csv_pesagens,
    )
    await async_session.commit()
    assert exec_1.criados == 3
    assert exec_1.erros == 0

    await async_session.refresh(animal)
    await async_session.refresh(lote_ind)
    await async_session.refresh(lote_col)
    assert animal.peso_atual_kg == pytest.approx(430.0)
    assert animal.data_ultima_pesagem == date(2026, 10, 31)
    assert lote_ind.peso_medio_kg == pytest.approx(430.0)
    assert lote_col.peso_medio_kg == pytest.approx(430.0)
    assert lote_col.peso_inicial_medio_kg == pytest.approx(400.0)

    indicadores = await LoteIndicadoresService(async_session, tenant_id).resumir(lote_col.id)
    assert indicadores.gmd_medio_kg_dia == pytest.approx(1.0)
    assert indicadores.arrobas_produzidas == pytest.approx(10.0)

    # Reimportação idêntica em IGNORAR pula a individual existente sem duplicar
    csv_re = "Brinco;Data;Peso (kg)\nBR-PES-01;2026-10-31;440\n".encode("utf-8")
    exec_ign = await service.executar(
        OpcoesImportacao(
            tipo="PESAGENS",
            unidade_produtiva_id=fazenda_id,
            modo_conflito="IGNORAR",
        ),
        "re_ign.csv",
        csv_re,
    )
    await async_session.commit()
    assert exec_ign.ignorados == 1
    await async_session.refresh(animal)
    assert animal.peso_atual_kg == pytest.approx(430.0)

    # Em ATUALIZAR atualiza a pesagem da mesma data
    exec_upd = await service.executar(
        OpcoesImportacao(
            tipo="PESAGENS",
            unidade_produtiva_id=fazenda_id,
            modo_conflito="ATUALIZAR",
        ),
        "re_upd.csv",
        csv_re,
    )
    await async_session.commit()
    assert exec_upd.atualizados == 1
    await async_session.refresh(animal)
    assert animal.peso_atual_kg == pytest.approx(440.0)

    # Erros de pesagem inválida
    csv_erro = (
        "Brinco;Lote;Data;Peso (kg)\n"
        "BR-NAO-EXISTE;;2026-11-01;400\n"
        "BR-PES-01;;2026-11-01;0\n"
    ).encode("utf-8")
    prev_erro = await service.previsualizar(
        OpcoesImportacao(tipo="PESAGENS", unidade_produtiva_id=fazenda_id),
        "erros.csv",
        csv_erro,
    )
    assert prev_erro.com_erro == 2
