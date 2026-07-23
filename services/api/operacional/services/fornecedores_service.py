import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.pessoas.models import (
    Pessoa,
    PessoaContato,
    PessoaDocumento,
    PessoaRelacionamento,
    TipoRelacionamento,
)
from operacional.models.compras import Fornecedor


FORNECEDOR_CODIGO = "FORNECEDOR"


def normalizar_documento(documento: str | None) -> str | None:
    if not documento:
        return None
    normalizado = re.sub(r"\D", "", documento)
    return normalizado or None


def tipo_documento_fornecedor(documento: str | None) -> str | None:
    normalizado = normalizar_documento(documento)
    if len(normalizado or "") == 11:
        return "CPF"
    if len(normalizado or "") == 14:
        return "CNPJ"
    return None


async def _buscar_pessoa_por_documento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    documento: str | None,
) -> Pessoa | None:
    normalizado = normalizar_documento(documento)
    tipo_documento = tipo_documento_fornecedor(documento)
    if not normalizado or not tipo_documento:
        return None

    candidatos = {normalizado}
    if documento:
        candidatos.add(documento)

    stmt = (
        select(Pessoa)
        .join(PessoaDocumento, PessoaDocumento.pessoa_id == Pessoa.id)
        .where(
            Pessoa.tenant_id == tenant_id,
            PessoaDocumento.tipo == tipo_documento,
            PessoaDocumento.numero.in_(candidatos),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _buscar_pessoa_fornecedor_por_nome(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    nome: str,
) -> Pessoa | None:
    stmt = (
        select(Pessoa)
        .join(PessoaRelacionamento, PessoaRelacionamento.pessoa_id == Pessoa.id)
        .join(TipoRelacionamento, TipoRelacionamento.id == PessoaRelacionamento.tipo_id)
        .where(
            Pessoa.tenant_id == tenant_id,
            Pessoa.nome_exibicao == nome,
            Pessoa.ativo == True,
            TipoRelacionamento.codigo == FORNECEDOR_CODIGO,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _buscar_fornecedor_legado_por_pessoa(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    pessoa_id: uuid.UUID,
) -> Fornecedor | None:
    stmt = (
        select(Fornecedor)
        .where(
            Fornecedor.tenant_id == tenant_id,
            Fornecedor.pessoa_id == pessoa_id,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _buscar_fornecedor_legado_por_documento(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    documento: str | None,
) -> Fornecedor | None:
    normalizado = normalizar_documento(documento)
    if not normalizado:
        return None

    stmt = (
        select(Fornecedor)
        .join(PessoaDocumento, PessoaDocumento.pessoa_id == Fornecedor.pessoa_id)
        .where(
            Fornecedor.tenant_id == tenant_id,
            PessoaDocumento.numero == normalizado,
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _obter_tipo_fornecedor(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> TipoRelacionamento:
    stmt = (
        select(TipoRelacionamento)
        .where(
            TipoRelacionamento.codigo == FORNECEDOR_CODIGO,
            or_(TipoRelacionamento.tenant_id == tenant_id, TipoRelacionamento.tenant_id.is_(None)),
        )
        .order_by(TipoRelacionamento.tenant_id.is_not(None).desc())
        .limit(1)
    )
    tipo = (await session.execute(stmt)).scalar_one_or_none()
    if tipo:
        return tipo

    tipo = TipoRelacionamento(
        tenant_id=None,
        codigo=FORNECEDOR_CODIGO,
        nome="Fornecedor",
        descricao="Fornecedor criado a partir do modulo de Compras",
        cor="#2563EB",
        icone="truck",
        sistema=False,
        ativo=True,
    )
    session.add(tipo)
    await session.flush()
    return tipo


async def _garantir_relacionamento_fornecedor(
    session: AsyncSession,
    pessoa_id: uuid.UUID,
    tipo_id: uuid.UUID,
) -> None:
    stmt = (
        select(PessoaRelacionamento)
        .where(
            PessoaRelacionamento.pessoa_id == pessoa_id,
            PessoaRelacionamento.tipo_id == tipo_id,
        )
        .limit(1)
    )
    relacionamento = (await session.execute(stmt)).scalar_one_or_none()
    if relacionamento:
        return

    session.add(PessoaRelacionamento(pessoa_id=pessoa_id, tipo_id=tipo_id))
    await session.flush()


async def _sincronizar_contato(
    session: AsyncSession,
    pessoa_id: uuid.UUID,
    tipo: str,
    valor: str | None,
) -> None:
    """Cria ou atualiza o contato principal do tipo informado — roda sempre
    (não só na criação da Pessoa), para que edições no cadastro de Fornecedor
    fiquem sincronizadas com a aba de Contatos da Pessoa."""
    if not valor:
        return

    stmt = (
        select(PessoaContato)
        .where(
            PessoaContato.pessoa_id == pessoa_id,
            PessoaContato.tipo == tipo,
            PessoaContato.principal == True,
        )
        .limit(1)
    )
    contato = (await session.execute(stmt)).scalar_one_or_none()
    if contato:
        if contato.valor != valor:
            contato.valor = valor
            session.add(contato)
    else:
        session.add(PessoaContato(pessoa_id=pessoa_id, tipo=tipo, valor=valor, principal=True))


async def _sincronizar_documento(
    session: AsyncSession,
    pessoa_id: uuid.UUID,
    tipo_documento: str,
    numero: str,
    razao_social: str | None,
    nome_fantasia: str | None,
) -> None:
    stmt = (
        select(PessoaDocumento)
        .where(PessoaDocumento.pessoa_id == pessoa_id, PessoaDocumento.tipo == tipo_documento)
        .limit(1)
    )
    doc = (await session.execute(stmt)).scalar_one_or_none()
    if doc:
        doc.numero = numero
        if tipo_documento == "CNPJ":
            doc.razao_social = razao_social or doc.razao_social
            doc.nome_fantasia = nome_fantasia or doc.nome_fantasia
        else:
            doc.nome_completo = nome_fantasia or doc.nome_completo
        session.add(doc)
    else:
        session.add(
            PessoaDocumento(
                pessoa_id=pessoa_id,
                tipo=tipo_documento,
                numero=numero,
                razao_social=razao_social if tipo_documento == "CNPJ" else None,
                nome_fantasia=nome_fantasia if tipo_documento == "CNPJ" else None,
                nome_completo=nome_fantasia if tipo_documento == "CPF" else None,
            )
        )


async def resolve_fornecedor(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    nome_fantasia: str,
    cnpj_cpf: str | None = None,
    razao_social: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
) -> Pessoa:
    """Resolve (ou cria) a Pessoa canônica de um fornecedor, sempre
    sincronizando documento e contatos — inclusive em atualizações, não só
    na criação (bug corrigido: antes só sincronizava na primeira vez)."""
    nome_exibicao = nome_fantasia or razao_social or "Fornecedor"
    documento = normalizar_documento(cnpj_cpf)
    tipo_documento = tipo_documento_fornecedor(cnpj_cpf)

    pessoa = await _buscar_pessoa_por_documento(session, tenant_id, cnpj_cpf)
    if not pessoa and not documento:
        pessoa = await _buscar_pessoa_fornecedor_por_nome(session, tenant_id, nome_exibicao)

    if not pessoa:
        pessoa = Pessoa(
            tenant_id=tenant_id,
            tipo="PJ" if tipo_documento == "CNPJ" or not tipo_documento else "PF",
            nome_exibicao=nome_exibicao,
            base_legal="CONTRATO",
            ativo=True,
        )
        session.add(pessoa)
        await session.flush()

    if documento and tipo_documento:
        await _sincronizar_documento(session, pessoa.id, tipo_documento, documento, razao_social, nome_fantasia)

    await _sincronizar_contato(session, pessoa.id, "EMAIL", email)
    await _sincronizar_contato(session, pessoa.id, "TELEFONE", telefone)

    tipo_fornecedor = await _obter_tipo_fornecedor(session, tenant_id)
    await _garantir_relacionamento_fornecedor(session, pessoa.id, tipo_fornecedor.id)
    return pessoa


async def obter_dados_exibicao_fornecedor(session: AsyncSession, pessoa_id: uuid.UUID) -> dict:
    """Monta nome_fantasia/razao_social/cnpj_cpf/email/telefone a partir de
    Pessoa/PessoaDocumento/PessoaContato — única fonte de verdade desses dados."""
    pessoa = await session.get(Pessoa, pessoa_id)

    doc_stmt = select(PessoaDocumento).where(
        PessoaDocumento.pessoa_id == pessoa_id,
        PessoaDocumento.tipo.in_(["CNPJ", "CPF"]),
    ).limit(1)
    documento = (await session.execute(doc_stmt)).scalar_one_or_none()

    email_stmt = select(PessoaContato).where(
        PessoaContato.pessoa_id == pessoa_id, PessoaContato.tipo == "EMAIL"
    ).order_by(PessoaContato.principal.desc()).limit(1)
    contato_email = (await session.execute(email_stmt)).scalar_one_or_none()

    tel_stmt = select(PessoaContato).where(
        PessoaContato.pessoa_id == pessoa_id, PessoaContato.tipo.in_(["TELEFONE", "CELULAR"])
    ).order_by(PessoaContato.principal.desc()).limit(1)
    contato_telefone = (await session.execute(tel_stmt)).scalar_one_or_none()

    return {
        "nome_fantasia": (documento.nome_fantasia if documento else None) or (pessoa.nome_exibicao if pessoa else None),
        "razao_social": documento.razao_social if documento else None,
        "cnpj_cpf": documento.numero if documento else None,
        "email": contato_email.valor if contato_email else None,
        "telefone": contato_telefone.valor if contato_telefone else None,
    }


async def salvar_fornecedor_legado(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    nome_fantasia: str,
    cnpj_cpf: str | None = None,
    razao_social: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    condicoes_pagamento: str | None = None,
    prazo_entrega_dias: int | None = None,
    avaliacao: float | None = None,
    fornecedor: Fornecedor | None = None,
) -> tuple[Fornecedor, bool]:
    pessoa = await resolve_fornecedor(
        session,
        tenant_id,
        nome_fantasia=nome_fantasia,
        cnpj_cpf=cnpj_cpf,
        razao_social=razao_social,
        email=email,
        telefone=telefone,
    )

    created = False
    if fornecedor is None:
        fornecedor = await _buscar_fornecedor_legado_por_pessoa(session, tenant_id, pessoa.id)
        if fornecedor is None:
            fornecedor = await _buscar_fornecedor_legado_por_documento(session, tenant_id, cnpj_cpf)
        if fornecedor is None:
            fornecedor = Fornecedor(tenant_id=tenant_id, pessoa_id=pessoa.id)
            created = True

    fornecedor.pessoa_id = pessoa.id
    fornecedor.condicoes_pagamento = condicoes_pagamento
    fornecedor.prazo_entrega_dias = prazo_entrega_dias
    fornecedor.avaliacao = avaliacao

    session.add(fornecedor)
    await session.flush()
    return fornecedor, created
