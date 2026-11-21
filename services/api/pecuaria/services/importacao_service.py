"""Serviço de pré-visualização e importação em lote (Lotes, Animais e Pesagens)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.schemas.importacao_schema import (
    ImportacaoExecucaoResponse,
    ImportacaoPreviewResponse,
    LinhaImportacaoPreview,
    ModoConflitoImportacao,
    TipoImportacaoPecuaria,
)
from pecuaria.services.importacao_templates import CAMPOS_POR_TIPO, sugerir_mapeamento_colunas
from pecuaria.services.planilha_parser import (
    PlanilhaBruta,
    ler_planilha_bytes,
    normalizar_texto_chave,
    parse_date_br,
    parse_float_br,
    parse_int_br,
)

MAX_PREVIEW_ROWS = 200
MAX_ERROR_ROWS = 500

_CATEGORIA_MAP = {
    "bezerro": "BEZERRO",
    "bezerros": "BEZERRO",
    "bezerra": "BEZERRA",
    "bezerras": "BEZERRA",
    "garrote": "GARROTE",
    "garrotes": "GARROTE",
    "novilho": "GARROTE",
    "novilhos": "GARROTE",
    "recria": "GARROTE",
    "novilha": "NOVILHA",
    "novilhas": "NOVILHA",
    "novilha_corte": "NOVILHA",
    "boi": "BOI",
    "bois": "BOI",
    "boi_gordo": "BOI",
    "engorda": "BOI",
    "bois_em_engorda": "BOI",
    "vaca_corte": "VACA_CORTE",
    "vaca_de_corte": "VACA_CORTE",
    "vaca": "VACA_CORTE",
    "vacas": "VACA_CORTE",
    "vacas_paridas": "VACA_CORTE",
    "matriz": "VACA_CORTE",
    "matrizes": "VACA_CORTE",
    "touro": "TOURO",
    "touros": "TOURO",
    "vaca_leite": "VACA_LEITE",
    "vaca_de_leite": "VACA_LEITE",
    "vaca_leiteira": "VACA_LEITE",
    "novilha_leite": "NOVILHA_LEITE",
    "novilha_de_leite": "NOVILHA_LEITE",
    "novilha_leiteira": "NOVILHA_LEITE",
    "reprodutor": "REPRODUTOR",
    "reprodutores": "REPRODUTOR",
    "outro": "OUTRO",
    "outros": "OUTRO",
}

_SEXO_MAP = {
    "macho": "MACHO",
    "m": "MACHO",
    "femea": "FEMEA",
    "f": "FEMEA",
    "castrado": "CASTRADO",
    "c": "CASTRADO",
    "capao": "CASTRADO",
}

_SEXO_POR_CATEGORIA = {
    "BEZERRA": "FEMEA",
    "NOVILHA": "FEMEA",
    "VACA_CORTE": "FEMEA",
    "VACA_LEITE": "FEMEA",
    "NOVILHA_LEITE": "FEMEA",
    "BOI": "CASTRADO",
}

_ESPECIE_MAP = {
    "bovino": "BOVINO",
    "bovinos": "BOVINO",
    "gado": "BOVINO",
    "suino": "SUINO",
    "suinos": "SUINO",
    "ovino": "OVINO",
    "ovinos": "OVINO",
    "caprino": "CAPRINO",
    "caprinos": "CAPRINO",
    "equino": "EQUINO",
    "equinos": "EQUINO",
    "aves": "AVES",
    "ave": "AVES",
    "outro": "OUTRO",
    "outros": "OUTRO",
}

_STATUS_MAP = {
    "ativo": "ATIVO",
    "ativa": "ATIVO",
    "vendido": "VENDIDO",
    "vendida": "VENDIDO",
    "abatido": "ABATIDO",
    "abatida": "ABATIDO",
    "morto": "MORTO",
    "morta": "MORTO",
    "transferido": "TRANSFERIDO",
    "transferida": "TRANSFERIDO",
}


@dataclass(frozen=True)
class OpcoesImportacao:
    """Parâmetros de controle da importação enviados pelo cliente."""

    tipo: TipoImportacaoPecuaria
    unidade_produtiva_id: uuid.UUID
    modo_conflito: ModoConflitoImportacao = "ATUALIZAR"
    criar_lotes_automaticamente: bool = True
    ignorar_linhas_com_erro: bool = False
    mapeamento_colunas: dict[str, str | None] | None = None


@dataclass
class _ContextoFazenda:
    piquetes_por_nome: dict[str, AreaRural]
    lotes_por_nome: dict[str, LoteAnimal]
    lotes_por_id: dict[uuid.UUID, LoteAnimal]
    individuais_por_lote: dict[uuid.UUID, int]
    animais_por_chave: dict[tuple[str, str], Animal]
    pesagens_ind_existentes: dict[tuple[uuid.UUID, date], EventoAnimal]
    pesagens_col_existentes: dict[tuple[uuid.UUID, date], ManejoLote]


@dataclass
class _PlanoLote:
    preview: LinhaImportacaoPreview
    existente: LoteAnimal | None = None
    dados: dict[str, object] = field(default_factory=dict)


@dataclass
class _PlanoAnimal:
    preview: LinhaImportacaoPreview
    existente: Animal | None = None
    lote_chave: str | None = None
    lote_nome_original: str | None = None
    lote_existente: LoteAnimal | None = None
    dados: dict[str, object] = field(default_factory=dict)


@dataclass
class _PlanoPesagem:
    preview: LinhaImportacaoPreview
    modo: str  # INDIVIDUAL | COLETIVA
    animal: Animal | None = None
    lote: LoteAnimal | None = None
    evento_existente: EventoAnimal | None = None
    manejo_existente: ManejoLote | None = None
    dados: dict[str, object] = field(default_factory=dict)


@dataclass
class _ResultadoAvaliacao:
    planilha: PlanilhaBruta
    mapeamento: dict[str, str | None]
    previews: list[LinhaImportacaoPreview]
    planos: list[object]


class ImportacaoPecuariaService:
    """Orquestra pré-visualização e carga segura de planilhas de pecuária."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def previsualizar(
        self,
        opcoes: OpcoesImportacao,
        filename: str,
        conteudo: bytes,
    ) -> ImportacaoPreviewResponse:
        """Valida o arquivo e retorna o preview sem alterar o banco de dados.

        Args:
            opcoes: Parâmetros de tipo, fazenda, conflito e mapeamento.
            filename: Nome do arquivo para validar extensão.
            conteudo: Conteúdo binário em memória.

        Returns:
            ImportacaoPreviewResponse com mapeamento, contadores e linhas avaliadas.

        Raises:
            EntityNotFoundError: Se a fazenda não pertencer ao tenant.
            BusinessRuleError: Se o arquivo falhar na validação de leitura/segurança.
        """
        ctx = await self._carregar_contexto_fazenda(opcoes.unidade_produtiva_id, opcoes.tipo)
        avaliacao = self._avaliar_planilha(opcoes, ctx, filename, conteudo)
        return self._montar_resposta_preview(opcoes, filename, avaliacao)

    async def executar(
        self,
        opcoes: OpcoesImportacao,
        filename: str,
        conteudo: bytes,
    ) -> ImportacaoExecucaoResponse:
        """Valida e persiste lotes, animais ou pesagens de forma atômica.

        Args:
            opcoes: Parâmetros de execução e política de erros.
            filename: Nome do arquivo enviado.
            conteudo: Bytes da planilha em memória.

        Returns:
            ImportacaoExecucaoResponse com totais gravados e possíveis erros ignorados.

        Raises:
            EntityNotFoundError: Se a fazenda não pertencer ao tenant.
            BusinessRuleError: Se houver erros sem `ignorar_linhas_com_erro=True`.
        """
        ctx = await self._carregar_contexto_fazenda(opcoes.unidade_produtiva_id, opcoes.tipo)
        avaliacao = self._avaliar_planilha(opcoes, ctx, filename, conteudo)
        erros = [ln for ln in avaliacao.previews if ln.acao == "ERRO"]
        if erros and not opcoes.ignorar_linhas_com_erro:
            primeiro = erros[0]
            detalhe = "; ".join(primeiro.erros)
            raise BusinessRuleError(
                f"{len(erros)} linha(s) com erro (ex: linha {primeiro.linha_numero}: {detalhe}). "
                "Corrija ou habilite ignorar linhas inválidas."
            )

        lotes_criados, lotes_atualizados = await self._aplicar_planos(opcoes, ctx, avaliacao.planos)
        await self.session.flush()
        return self._montar_resposta_execucao(
            opcoes.tipo, avaliacao.previews, lotes_criados, lotes_atualizados
        )

    async def _carregar_contexto_fazenda(
        self,
        unidade_produtiva_id: uuid.UUID,
        tipo: TipoImportacaoPecuaria,
    ) -> _ContextoFazenda:
        fazenda = await self.session.scalar(
            select(UnidadeProdutiva).where(
                UnidadeProdutiva.id == unidade_produtiva_id,
                UnidadeProdutiva.tenant_id == self.tenant_id,
            )
        )
        if not fazenda:
            raise EntityNotFoundError(
                f"Unidade produtiva {unidade_produtiva_id} não encontrada neste tenant."
            )

        piquetes_res = (
            await self.session.execute(
                select(AreaRural).where(
                    AreaRural.tenant_id == self.tenant_id,
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                    AreaRural.tipo == TipoArea.PIQUETE.value,
                    AreaRural.ativo == True,  # noqa: E712
                )
            )
        ).scalars().all()
        piquetes_por_nome = {normalizar_texto_chave(p.nome): p for p in piquetes_res}

        lotes_res = (
            await self.session.execute(
                select(LoteAnimal).where(
                    LoteAnimal.tenant_id == self.tenant_id,
                    LoteAnimal.unidade_produtiva_id == unidade_produtiva_id,
                )
            )
        ).scalars().all()
        lotes_por_nome = {normalizar_texto_chave(lote.identificacao): lote for lote in lotes_res}
        lotes_por_id = {lote.id: lote for lote in lotes_res}

        ind_rows = (
            await self.session.execute(
                select(Animal.lote_id, func.count(Animal.id))
                .where(
                    Animal.tenant_id == self.tenant_id,
                    Animal.unidade_produtiva_id == unidade_produtiva_id,
                    Animal.status == "ATIVO",
                    Animal.lote_id.is_not(None),
                )
                .group_by(Animal.lote_id)
            )
        ).all()
        individuais_por_lote = {row[0]: int(row[1]) for row in ind_rows}

        animais_res = (
            await self.session.execute(
                select(Animal).where(
                    Animal.tenant_id == self.tenant_id,
                    Animal.unidade_produtiva_id == unidade_produtiva_id,
                )
            )
        ).scalars().all()
        animais_por_chave: dict[tuple[str, str], Animal] = {}
        animal_ids: list[uuid.UUID] = []
        for animal in animais_res:
            animal_ids.append(animal.id)
            if animal.numero_brinco:
                animais_por_chave[("BRINCO", animal.numero_brinco.strip().upper())] = animal
            if animal.numero_sisbov:
                animais_por_chave[("SISBOV", animal.numero_sisbov.strip().upper())] = animal
            if animal.microchip:
                animais_por_chave[("MICROCHIP", animal.microchip.strip().upper())] = animal

        pesagens_ind_existentes: dict[tuple[uuid.UUID, date], EventoAnimal] = {}
        pesagens_col_existentes: dict[tuple[uuid.UUID, date], ManejoLote] = {}
        if tipo == "PESAGENS":
            if animal_ids:
                evs = (
                    await self.session.execute(
                        select(EventoAnimal).where(
                            EventoAnimal.tenant_id == self.tenant_id,
                            EventoAnimal.tipo == "PESAGEM",
                            EventoAnimal.animal_id.in_(animal_ids),
                        )
                    )
                ).scalars().all()
                for ev in evs:
                    pesagens_ind_existentes[(ev.animal_id, ev.data_evento)] = ev
            lote_ids = list(lotes_por_id.keys())
            if lote_ids:
                manejos = (
                    await self.session.execute(
                        select(ManejoLote).where(
                            ManejoLote.tenant_id == self.tenant_id,
                            ManejoLote.tipo_evento == "PESAGEM",
                            ManejoLote.lote_id.in_(lote_ids),
                        )
                    )
                ).scalars().all()
                for mn in manejos:
                    pesagens_col_existentes[(mn.lote_id, mn.data_evento)] = mn

        return _ContextoFazenda(
            piquetes_por_nome=piquetes_por_nome,
            lotes_por_nome=lotes_por_nome,
            lotes_por_id=lotes_por_id,
            individuais_por_lote=individuais_por_lote,
            animais_por_chave=animais_por_chave,
            pesagens_ind_existentes=pesagens_ind_existentes,
            pesagens_col_existentes=pesagens_col_existentes,
        )

    def _avaliar_planilha(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        filename: str,
        conteudo: bytes,
    ) -> _ResultadoAvaliacao:
        planilha = ler_planilha_bytes(filename, conteudo)
        mapeamento = sugerir_mapeamento_colunas(
            opcoes.tipo, planilha.headers, opcoes.mapeamento_colunas
        )
        if opcoes.tipo == "LOTES":
            planos = self._avaliar_lotes(opcoes, ctx, planilha, mapeamento)
        elif opcoes.tipo == "ANIMAIS":
            planos = self._avaliar_animais(opcoes, ctx, planilha, mapeamento)
        else:
            planos = self._avaliar_pesagens(opcoes, ctx, planilha, mapeamento)
        previews = [plano.preview for plano in planos]  # type: ignore[attr-defined]
        return _ResultadoAvaliacao(
            planilha=planilha,
            mapeamento=mapeamento,
            previews=previews,
            planos=planos,
        )

    def _avaliar_lotes(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        planilha: PlanilhaBruta,
        mapeamento: dict[str, str | None],
    ) -> list[_PlanoLote]:
        vistas: set[str] = set()
        planos: list[_PlanoLote] = []
        for linha_num, raw_row in planilha.rows:
            planos.append(self._avaliar_linha_lote(linha_num, raw_row, mapeamento, opcoes, ctx, vistas))
        return planos

    def _avaliar_linha_lote(
        self,
        linha_num: int,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        vistas: set[str],
    ) -> _PlanoLote:
        erros: list[str] = []
        avisos: list[str] = []
        ident = self._campo(raw_row, mapeamento, "identificacao")
        if len(ident) < 2 or len(ident) > 100:
            erros.append("Identificação do lote deve ter entre 2 e 100 caracteres.")
        ident_chave = normalizar_texto_chave(ident)
        if ident_chave:
            if ident_chave in vistas:
                erros.append("Identificação de lote duplicada na planilha.")
            vistas.add(ident_chave)

        modo = self._parse_modo_lote(self._campo(raw_row, mapeamento, "modo_gestao"), erros)
        categoria = self._campo(raw_row, mapeamento, "categoria")
        if not categoria or len(categoria) > 50:
            erros.append("Categoria do lote é obrigatória (máx. 50 caracteres).")
        raca = self._campo(raw_row, mapeamento, "raca")
        if not raca or len(raca) > 50:
            erros.append("Raça do lote é obrigatória (máx. 50 caracteres).")

        qtd = self._parse_opcional_int(raw_row, mapeamento, "quantidade_cabecas", "Qtd. Cabeças", erros)
        if qtd is None:
            qtd = 1 if modo == "POR_LOTE" else 0
        elif qtd < 0 or (modo == "POR_LOTE" and qtd < 1):
            erros.append("Qtd. Cabeças deve ser >= 1 no modo POR_LOTE (ou >= 0 no INDIVIDUAL).")

        peso_medio = self._parse_nao_neg_float(raw_row, mapeamento, "peso_medio_kg", "Peso Médio", erros) or 0.0
        peso_inicial = self._parse_nao_neg_float(raw_row, mapeamento, "peso_inicial_medio_kg", "Peso Inicial", erros)
        rendimento = self._parse_nao_neg_float(raw_row, mapeamento, "rendimento_carcaca_pct", "Rendimento Carcaça", erros)
        rendimento_val = 50.0 if rendimento is None else rendimento
        if not 30.0 <= rendimento_val <= 70.0:
            erros.append("Rendimento de carcaça deve estar entre 30% e 70%.")

        valor_aquisicao = self._parse_nao_neg_float(raw_row, mapeamento, "valor_aquisicao_total", "Valor Aquisição", erros)
        cotacao = self._parse_nao_neg_float(raw_row, mapeamento, "cotacao_arroba_override", "Cotação Manual", erros)
        if cotacao is not None and cotacao <= 0:
            erros.append("Cotação manual da arroba deve ser maior que zero.")

        data_formacao = self._parse_opcional_date(raw_row, mapeamento, "data_formacao", erros) or date.today()
        piquete_nome = self._campo(raw_row, mapeamento, "piquete")
        area_id: uuid.UUID | None = None
        if piquete_nome:
            piquete = ctx.piquetes_por_nome.get(normalizar_texto_chave(piquete_nome))
            if piquete:
                area_id = piquete.id
            else:
                avisos.append(f"Piquete '{piquete_nome}' não encontrado; lote ficará sem pasto.")

        existente = ctx.lotes_por_nome.get(ident_chave) if ident_chave else None
        acao = "CRIAR"
        if existente is not None:
            if opcoes.modo_conflito == "IGNORAR":
                acao = "IGNORAR"
            else:
                acao = "ATUALIZAR"
                if modo == "POR_LOTE" and ctx.individuais_por_lote.get(existente.id, 0) > 0:
                    erros.append("Lote já possui animais individuais ativos e não pode voltar para POR_LOTE.")

        if erros:
            acao = "ERRO"

        dados_normalizados = {
            "identificacao": ident,
            "modo_gestao": modo,
            "categoria": categoria,
            "raca": raca,
            "quantidade_cabecas": qtd,
            "peso_medio_kg": round(peso_medio, 2),
            "peso_inicial_medio_kg": peso_inicial,
            "rendimento_carcaca_pct": round(rendimento_val, 2),
            "valor_aquisicao_total": valor_aquisicao,
            "cotacao_arroba_override": cotacao,
            "area_id": str(area_id) if area_id else None,
            "piquete_nome": piquete_nome or None,
            "data_formacao": data_formacao.isoformat(),
            "observacoes": self._campo(raw_row, mapeamento, "observacoes") or None,
        }
        return _PlanoLote(
            preview=LinhaImportacaoPreview(
                linha_numero=linha_num,
                acao=acao,  # type: ignore[arg-type]
                identificador=ident or f"Linha {linha_num}",
                dados=dados_normalizados,
                erros=erros,
                avisos=avisos,
            ),
            existente=existente,
            dados={
                **dados_normalizados,
                "area_id_uuid": area_id,
                "data_formacao_date": data_formacao,
            },
        )

    def _avaliar_animais(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        planilha: PlanilhaBruta,
        mapeamento: dict[str, str | None],
    ) -> list[_PlanoAnimal]:
        vistas: set[tuple[str, str]] = set()
        lotes_auto_previstos: set[str] = set()
        planos: list[_PlanoAnimal] = []
        for linha_num, raw_row in planilha.rows:
            planos.append(
                self._avaliar_linha_animal(
                    linha_num, raw_row, mapeamento, opcoes, ctx, vistas, lotes_auto_previstos
                )
            )
        return planos

    def _avaliar_linha_animal(
        self,
        linha_num: int,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        vistas: set[tuple[str, str]],
        lotes_auto_previstos: set[str],
    ) -> _PlanoAnimal:
        erros: list[str] = []
        avisos: list[str] = []
        brinco = self._campo(raw_row, mapeamento, "numero_brinco") or None
        sisbov = self._campo(raw_row, mapeamento, "numero_sisbov") or None
        microchip = self._campo(raw_row, mapeamento, "microchip") or None
        if not brinco and not sisbov and not microchip:
            erros.append("Informe ao menos Brinco, SISBOV ou Microchip.")

        chaves_linha = self._montar_chaves_animal(brinco, sisbov, microchip)
        for chave in chaves_linha:
            if chave in vistas:
                erros.append(f"Identificador {chave[0]} '{chave[1]}' duplicado na planilha.")
                break
        vistas.update(chaves_linha)

        matched_animais = {
            ctx.animais_por_chave[chave]
            for chave in chaves_linha
            if chave in ctx.animais_por_chave
        }
        if len(matched_animais) > 1:
            erros.append("Os identificadores da linha pertencem a animais diferentes já cadastrados.")
        existente = next(iter(matched_animais)) if len(matched_animais) == 1 else None

        especie = self._normalizar_enum(
            self._campo(raw_row, mapeamento, "especie") or "BOVINO", _ESPECIE_MAP, "Espécie", erros
        )
        categoria = self._normalizar_enum(
            self._campo(raw_row, mapeamento, "categoria"), _CATEGORIA_MAP, "Categoria", erros
        )
        sexo_raw = self._campo(raw_row, mapeamento, "sexo")
        if sexo_raw:
            sexo = self._normalizar_enum(sexo_raw, _SEXO_MAP, "Sexo", erros)
        else:
            sexo = _SEXO_POR_CATEGORIA.get(categoria, "MACHO")

        status_val = self._normalizar_enum(
            self._campo(raw_row, mapeamento, "status") or "ATIVO", _STATUS_MAP, "Status", erros
        )
        peso = self._parse_nao_neg_float(raw_row, mapeamento, "peso_atual_kg", "Peso Atual", erros)
        valor_aq = self._parse_nao_neg_float(raw_row, mapeamento, "valor_aquisicao", "Valor Aquisição", erros)
        data_nasc = self._parse_opcional_date(raw_row, mapeamento, "data_nascimento", erros)
        data_ent = self._parse_opcional_date(raw_row, mapeamento, "data_entrada", erros) or date.today()

        lote_nome = self._campo(raw_row, mapeamento, "lote") or None
        lote_chave = normalizar_texto_chave(lote_nome) if lote_nome else None
        lote_existente = ctx.lotes_por_nome.get(lote_chave) if lote_chave else None
        if lote_nome and lote_existente is None:
            if not opcoes.criar_lotes_automaticamente:
                erros.append(f"Lote '{lote_nome}' não existe e criação automática está desativada.")
            elif lote_chave not in lotes_auto_previstos:
                lotes_auto_previstos.add(lote_chave)  # type: ignore[arg-type]
                avisos.append(f"Lote '{lote_nome}' será criado automaticamente no modo INDIVIDUAL.")
        elif lote_existente is not None and lote_existente.modo_gestao == "POR_LOTE":
            avisos.append(f"Lote '{lote_existente.identificacao}' será promovido para INDIVIDUAL.")

        acao = "CRIAR"
        if existente is not None:
            acao = "IGNORAR" if opcoes.modo_conflito == "IGNORAR" else "ATUALIZAR"
        if erros:
            acao = "ERRO"

        identificador = brinco or sisbov or microchip or f"Linha {linha_num}"
        raca = self._campo(raw_row, mapeamento, "raca") or None
        dados_preview = {
            "numero_brinco": brinco,
            "numero_sisbov": sisbov,
            "microchip": microchip,
            "nome": self._campo(raw_row, mapeamento, "nome") or None,
            "lote": lote_nome,
            "especie": especie,
            "categoria": categoria,
            "sexo": sexo,
            "raca": raca,
            "pelagem": self._campo(raw_row, mapeamento, "pelagem") or None,
            "peso_atual_kg": peso,
            "valor_aquisicao": valor_aq,
            "data_nascimento": data_nasc.isoformat() if data_nasc else None,
            "data_entrada": data_ent.isoformat(),
            "status": status_val,
            "observacoes": self._campo(raw_row, mapeamento, "observacoes") or None,
        }
        return _PlanoAnimal(
            preview=LinhaImportacaoPreview(
                linha_numero=linha_num,
                acao=acao,  # type: ignore[arg-type]
                identificador=identificador,
                dados=dados_preview,
                erros=erros,
                avisos=avisos,
            ),
            existente=existente,
            lote_chave=lote_chave,
            lote_nome_original=lote_nome,
            lote_existente=lote_existente,
            dados={
                **dados_preview,
                "data_nascimento_date": data_nasc,
                "data_entrada_date": data_ent,
            },
        )

    def _avaliar_pesagens(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        planilha: PlanilhaBruta,
        mapeamento: dict[str, str | None],
    ) -> list[_PlanoPesagem]:
        vistas_ind: set[tuple[uuid.UUID, date]] = set()
        vistas_col: set[tuple[uuid.UUID, date]] = set()
        planos: list[_PlanoPesagem] = []
        for linha_num, raw_row in planilha.rows:
            planos.append(
                self._avaliar_linha_pesagem(
                    linha_num, raw_row, mapeamento, opcoes, ctx, vistas_ind, vistas_col
                )
            )
        return planos

    def _avaliar_linha_pesagem(
        self,
        linha_num: int,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        vistas_ind: set[tuple[uuid.UUID, date]],
        vistas_col: set[tuple[uuid.UUID, date]],
    ) -> _PlanoPesagem:
        erros: list[str] = []
        avisos: list[str] = []
        data_ev = self._parse_opcional_date(raw_row, mapeamento, "data_evento", erros)
        if data_ev is None and not erros:
            erros.append("Data da pesagem é obrigatória.")

        brinco = self._campo(raw_row, mapeamento, "numero_brinco") or None
        sisbov = self._campo(raw_row, mapeamento, "numero_sisbov") or None
        microchip = self._campo(raw_row, mapeamento, "microchip") or None
        lote_nome = self._campo(raw_row, mapeamento, "lote") or None
        obs = self._campo(raw_row, mapeamento, "observacoes") or None

        if brinco or sisbov or microchip:
            return self._avaliar_pesagem_individual(
                linha_num,
                raw_row,
                mapeamento,
                opcoes,
                ctx,
                vistas_ind,
                brinco=brinco,
                sisbov=sisbov,
                microchip=microchip,
                data_ev=data_ev,
                obs=obs,
                erros=erros,
                avisos=avisos,
            )

        return self._avaliar_pesagem_coletiva(
            linha_num,
            raw_row,
            mapeamento,
            opcoes,
            ctx,
            vistas_col,
            lote_nome=lote_nome,
            data_ev=data_ev,
            obs=obs,
            erros=erros,
            avisos=avisos,
        )

    def _avaliar_pesagem_individual(
        self,
        linha_num: int,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        vistas_ind: set[tuple[uuid.UUID, date]],
        *,
        brinco: str | None,
        sisbov: str | None,
        microchip: str | None,
        data_ev: date | None,
        obs: str | None,
        erros: list[str],
        avisos: list[str],
    ) -> _PlanoPesagem:
        chaves = self._montar_chaves_animal(brinco, sisbov, microchip)
        matched = {ctx.animais_por_chave[c] for c in chaves if c in ctx.animais_por_chave}
        if not matched:
            erros.append("Animal não encontrado na fazenda pelos identificadores informados.")
            animal = None
        elif len(matched) > 1:
            erros.append("Identificadores apontam para animais diferentes.")
            animal = None
        else:
            animal = next(iter(matched))

        peso_kg = self._parse_nao_neg_float(raw_row, mapeamento, "peso_kg", "Peso (kg)", erros)
        if peso_kg is None or peso_kg <= 0:
            erros.append("Peso individual (peso_kg) deve ser maior que zero.")

        evento_existente = None
        if animal and data_ev:
            chave_ev = (animal.id, data_ev)
            if chave_ev in vistas_ind:
                erros.append("Pesagem duplicada para este animal e data na planilha.")
            vistas_ind.add(chave_ev)
            evento_existente = ctx.pesagens_ind_existentes.get(chave_ev)

        acao = "CRIAR"
        if evento_existente is not None:
            acao = "IGNORAR" if opcoes.modo_conflito == "IGNORAR" else "ATUALIZAR"
        if erros:
            acao = "ERRO"

        ident = brinco or sisbov or microchip or f"Linha {linha_num}"
        dados_preview = {
            "modo": "INDIVIDUAL",
            "identificador": ident,
            "data_evento": data_ev.isoformat() if data_ev else None,
            "peso_kg": peso_kg,
            "observacoes": obs,
        }
        return _PlanoPesagem(
            preview=LinhaImportacaoPreview(
                linha_numero=linha_num,
                acao=acao,  # type: ignore[arg-type]
                identificador=ident,
                dados=dados_preview,
                erros=erros,
                avisos=avisos,
            ),
            modo="INDIVIDUAL",
            animal=animal,
            evento_existente=evento_existente,
            dados={**dados_preview, "data_evento_date": data_ev},
        )

    def _avaliar_pesagem_coletiva(
        self,
        linha_num: int,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        vistas_col: set[tuple[uuid.UUID, date]],
        *,
        lote_nome: str | None,
        data_ev: date | None,
        obs: str | None,
        erros: list[str],
        avisos: list[str],
    ) -> _PlanoPesagem:
        lote = ctx.lotes_por_nome.get(normalizar_texto_chave(lote_nome)) if lote_nome else None
        if not lote_nome:
            erros.append("Informe Brinco/SISBOV/Microchip ou o nome do Lote.")
        elif lote is None:
            erros.append(f"Lote '{lote_nome}' não encontrado na fazenda.")
        elif lote.modo_gestao == "INDIVIDUAL" or ctx.individuais_por_lote.get(lote.id, 0) > 0:
            erros.append(
                f"Lote '{lote.identificacao}' é INDIVIDUAL; informe o brinco do animal na pesagem."
            )

        qtd = self._parse_opcional_int(raw_row, mapeamento, "quantidade_cabecas", "Qtd. Cabeças", erros)
        if qtd is None and lote is not None:
            qtd = int(lote.quantidade_cabecas or 0)
        peso_total = self._parse_nao_neg_float(raw_row, mapeamento, "peso_total_kg", "Peso Total", erros)
        peso_medio_in = self._parse_nao_neg_float(raw_row, mapeamento, "peso_kg", "Peso Médio", erros)

        if peso_total is None or peso_total <= 0:
            if peso_medio_in is not None and peso_medio_in > 0 and qtd and qtd > 0:
                peso_total = round(peso_medio_in * qtd, 2)
            else:
                erros.append("Informe Peso Total do Lote (kg) ou Peso Médio (kg) maior que zero.")
        if qtd is None or qtd <= 0:
            erros.append("Quantidade de cabeças deve ser maior que zero para pesagem coletiva.")

        manejo_existente = None
        if lote and data_ev:
            chave_col = (lote.id, data_ev)
            if chave_col in vistas_col:
                erros.append("Pesagem coletiva duplicada para este lote e data na planilha.")
            vistas_col.add(chave_col)
            manejo_existente = ctx.pesagens_col_existentes.get(chave_col)

        acao = "CRIAR"
        if manejo_existente is not None:
            acao = "IGNORAR" if opcoes.modo_conflito == "IGNORAR" else "ATUALIZAR"
        if erros:
            acao = "ERRO"

        peso_medio_calc = round(peso_total / qtd, 2) if (peso_total and qtd and qtd > 0) else None
        dados_preview = {
            "modo": "COLETIVA",
            "lote": lote_nome,
            "data_evento": data_ev.isoformat() if data_ev else None,
            "quantidade_cabecas": qtd,
            "peso_total_kg": peso_total,
            "peso_medio_kg": peso_medio_calc,
            "observacoes": obs,
        }
        return _PlanoPesagem(
            preview=LinhaImportacaoPreview(
                linha_numero=linha_num,
                acao=acao,  # type: ignore[arg-type]
                identificador=lote_nome or f"Linha {linha_num}",
                dados=dados_preview,
                erros=erros,
                avisos=avisos,
            ),
            modo="COLETIVA",
            lote=lote,
            manejo_existente=manejo_existente,
            dados={**dados_preview, "data_evento_date": data_ev},
        )

    async def _aplicar_planos(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        planos: list[object],
    ) -> tuple[int, int]:
        if opcoes.tipo == "LOTES":
            return await self._aplicar_planos_lote(opcoes, planos)  # type: ignore[arg-type]
        if opcoes.tipo == "ANIMAIS":
            return await self._aplicar_planos_animais(opcoes, ctx, planos)  # type: ignore[arg-type]
        return await self._aplicar_planos_pesagens(ctx, planos)  # type: ignore[arg-type]

    async def _aplicar_planos_lote(
        self,
        opcoes: OpcoesImportacao,
        planos: list[_PlanoLote],
    ) -> tuple[int, int]:
        criados = 0
        atualizados = 0
        for plano in planos:
            if plano.preview.acao in ("ERRO", "IGNORAR"):
                continue
            d = plano.dados
            peso_medio = float(d["peso_medio_kg"] or 0.0)  # type: ignore[arg-type]
            peso_inicial = d["peso_inicial_medio_kg"]
            if plano.existente is not None:
                lote = plano.existente
                lote.modo_gestao = str(d["modo_gestao"])
                lote.categoria = str(d["categoria"])
                lote.raca = str(d["raca"])
                lote.quantidade_cabecas = int(d["quantidade_cabecas"])  # type: ignore[arg-type]
                lote.peso_medio_kg = peso_medio
                if peso_inicial is not None:
                    lote.peso_inicial_medio_kg = float(peso_inicial)  # type: ignore[arg-type]
                lote.rendimento_carcaca_pct = float(d["rendimento_carcaca_pct"])  # type: ignore[arg-type]
                if d["valor_aquisicao_total"] is not None:
                    lote.valor_aquisicao_total = float(d["valor_aquisicao_total"])  # type: ignore[arg-type]
                if d["cotacao_arroba_override"] is not None:
                    lote.cotacao_arroba_override = float(d["cotacao_arroba_override"])  # type: ignore[arg-type]
                if d["area_id_uuid"] is not None:
                    lote.area_id = d["area_id_uuid"]  # type: ignore[assignment]
                if d["observacoes"] is not None:
                    lote.observacoes = str(d["observacoes"])
                self.session.add(lote)
                atualizados += 1
            else:
                if peso_inicial is None and peso_medio > 0:
                    peso_inicial = peso_medio
                lote = LoteAnimal(
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=opcoes.unidade_produtiva_id,
                    area_id=d["area_id_uuid"],
                    identificacao=str(d["identificacao"]),
                    modo_gestao=str(d["modo_gestao"]),
                    categoria=str(d["categoria"]),
                    raca=str(d["raca"]),
                    quantidade_cabecas=int(d["quantidade_cabecas"]),  # type: ignore[arg-type]
                    peso_medio_kg=peso_medio,
                    peso_inicial_medio_kg=float(peso_inicial) if peso_inicial is not None else None,  # type: ignore[arg-type]
                    rendimento_carcaca_pct=float(d["rendimento_carcaca_pct"]),  # type: ignore[arg-type]
                    valor_aquisicao_total=float(d["valor_aquisicao_total"]) if d["valor_aquisicao_total"] is not None else None,  # type: ignore[arg-type]
                    cotacao_arroba_override=float(d["cotacao_arroba_override"]) if d["cotacao_arroba_override"] is not None else None,  # type: ignore[arg-type]
                    data_formacao=d["data_formacao_date"],
                    observacoes=d["observacoes"],
                    ativo=True,
                )
                self.session.add(lote)
                criados += 1
        return criados, atualizados

    async def _aplicar_planos_animais(
        self,
        opcoes: OpcoesImportacao,
        ctx: _ContextoFazenda,
        planos: list[_PlanoAnimal],
    ) -> tuple[int, int]:
        lotes_criados = 0
        lotes_impactados: set[uuid.UUID] = set()
        for plano in planos:
            if plano.preview.acao in ("ERRO", "IGNORAR"):
                continue
            d = plano.dados
            lote_id: uuid.UUID | None = None
            if plano.lote_chave:
                lote = ctx.lotes_por_nome.get(plano.lote_chave)
                if lote is None and opcoes.criar_lotes_automaticamente:
                    lote = LoteAnimal(
                        tenant_id=self.tenant_id,
                        unidade_produtiva_id=opcoes.unidade_produtiva_id,
                        identificacao=plano.lote_nome_original or plano.lote_chave,
                        modo_gestao="INDIVIDUAL",
                        categoria=str(d["categoria"]),
                        raca=str(d["raca"] or "Não informada"),
                        quantidade_cabecas=0,
                        peso_medio_kg=0.0,
                        data_formacao=d["data_entrada_date"],
                        ativo=True,
                    )
                    self.session.add(lote)
                    await self.session.flush()
                    ctx.lotes_por_nome[plano.lote_chave] = lote
                    ctx.lotes_por_id[lote.id] = lote
                    lotes_criados += 1
                if lote is not None:
                    lote_id = lote.id
                    lotes_impactados.add(lote.id)

            peso = float(d["peso_atual_kg"]) if d["peso_atual_kg"] is not None else None  # type: ignore[arg-type]
            valor_aq = float(d["valor_aquisicao"]) if d["valor_aquisicao"] is not None else None  # type: ignore[arg-type]
            if plano.existente is not None:
                animal = plano.existente
                if animal.lote_id:
                    lotes_impactados.add(animal.lote_id)
                if lote_id is not None:
                    animal.lote_id = lote_id
                animal.numero_brinco = d["numero_brinco"]  # type: ignore[assignment]
                if d["numero_sisbov"] is not None:
                    animal.numero_sisbov = str(d["numero_sisbov"])
                if d["microchip"] is not None:
                    animal.microchip = str(d["microchip"])
                if d["nome"] is not None:
                    animal.nome = str(d["nome"])
                animal.especie = str(d["especie"])
                animal.categoria = str(d["categoria"])
                animal.sexo = str(d["sexo"])
                if d["raca"] is not None:
                    animal.raca = str(d["raca"])
                if d["pelagem"] is not None:
                    animal.pelagem = str(d["pelagem"])
                animal.status = str(d["status"])
                if peso is not None:
                    animal.peso_atual_kg = peso
                    if animal.data_ultima_pesagem is None:
                        animal.data_ultima_pesagem = d["data_entrada_date"]  # type: ignore[assignment]
                if valor_aq is not None:
                    animal.valor_aquisicao = valor_aq
                if d["data_nascimento_date"] is not None:
                    animal.data_nascimento = d["data_nascimento_date"]  # type: ignore[assignment]
                if d["observacoes"] is not None:
                    animal.observacoes = str(d["observacoes"])
                self.session.add(animal)
            else:
                animal = Animal(
                    tenant_id=self.tenant_id,
                    unidade_produtiva_id=opcoes.unidade_produtiva_id,
                    lote_id=lote_id,
                    numero_brinco=d["numero_brinco"],
                    numero_sisbov=d["numero_sisbov"],
                    microchip=d["microchip"],
                    nome=d["nome"],
                    especie=str(d["especie"]),
                    categoria=str(d["categoria"]),
                    sexo=str(d["sexo"]),
                    raca=d["raca"],
                    pelagem=d["pelagem"],
                    data_nascimento=d["data_nascimento_date"],
                    data_entrada=d["data_entrada_date"],
                    status=str(d["status"]),
                    peso_atual_kg=peso,
                    data_ultima_pesagem=d["data_entrada_date"] if peso and peso > 0 else None,
                    valor_aquisicao=valor_aq,
                    valor_atual=valor_aq,
                    observacoes=d["observacoes"],
                )
                self.session.add(animal)
                await self.session.flush()
                if peso and peso > 0:
                    self.session.add(
                        EventoAnimal(
                            tenant_id=self.tenant_id,
                            animal_id=animal.id,
                            tipo="PESAGEM",
                            data_evento=d["data_entrada_date"],
                            peso_kg=peso,
                            observacoes="Pesagem inicial via importação",
                        )
                    )

        await self.session.flush()
        lotes_atualizados = await self._materializar_lotes(lotes_impactados)
        return lotes_criados, lotes_atualizados

    async def _aplicar_planos_pesagens(
        self,
        ctx: _ContextoFazenda,
        planos: list[_PlanoPesagem],
    ) -> tuple[int, int]:
        lotes_impactados_ind: set[uuid.UUID] = set()
        lotes_col_impactados: set[uuid.UUID] = set()
        planos_validos = [p for p in planos if p.preview.acao not in ("ERRO", "IGNORAR")]

        for plano in planos_validos:
            d = plano.dados
            data_ev: date = d["data_evento_date"]  # type: ignore[assignment]
            if plano.modo == "INDIVIDUAL" and plano.animal is not None:
                animal = plano.animal
                peso_kg = float(d["peso_kg"])  # type: ignore[arg-type]
                if plano.evento_existente is not None:
                    plano.evento_existente.peso_kg = peso_kg
                    if d["observacoes"] is not None:
                        plano.evento_existente.observacoes = str(d["observacoes"])
                    self.session.add(plano.evento_existente)
                else:
                    self.session.add(
                        EventoAnimal(
                            tenant_id=self.tenant_id,
                            animal_id=animal.id,
                            tipo="PESAGEM",
                            data_evento=data_ev,
                            peso_kg=peso_kg,
                            observacoes=d["observacoes"],
                        )
                    )
                if animal.data_ultima_pesagem is None or data_ev >= animal.data_ultima_pesagem:
                    animal.peso_atual_kg = peso_kg
                    animal.data_ultima_pesagem = data_ev
                    self.session.add(animal)
                if animal.lote_id:
                    lotes_impactados_ind.add(animal.lote_id)
            elif plano.modo == "COLETIVA" and plano.lote is not None:
                lote = plano.lote
                qtd = int(d["quantidade_cabecas"])  # type: ignore[arg-type]
                peso_total = float(d["peso_total_kg"])  # type: ignore[arg-type]
                if plano.manejo_existente is not None:
                    plano.manejo_existente.quantidade_cabecas = qtd
                    plano.manejo_existente.peso_total_kg = peso_total
                    if d["observacoes"] is not None:
                        plano.manejo_existente.observacoes = str(d["observacoes"])
                    self.session.add(plano.manejo_existente)
                else:
                    self.session.add(
                        ManejoLote(
                            tenant_id=self.tenant_id,
                            lote_id=lote.id,
                            tipo_evento="PESAGEM",
                            data_evento=data_ev,
                            quantidade_cabecas=qtd,
                            peso_total_kg=peso_total,
                            observacoes=d["observacoes"],
                        )
                    )
                lotes_col_impactados.add(lote.id)

        await self.session.flush()
        atualizados = await self._materializar_lotes(lotes_impactados_ind)
        atualizados += await self._atualizar_pesos_coletivos(ctx, lotes_col_impactados)
        return 0, atualizados

    async def _materializar_lotes(self, lote_ids: set[uuid.UUID]) -> int:
        if not lote_ids:
            return 0
        atualizados = 0
        for lote_id in lote_ids:
            stmt = select(
                func.count(Animal.id),
                func.coalesce(func.sum(Animal.peso_atual_kg), 0),
                func.count(Animal.peso_atual_kg),
            ).where(
                Animal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
            )
            total, peso_total, qtd_com_peso = (await self.session.execute(stmt)).one()
            lote = await self.session.get(LoteAnimal, lote_id)
            if not lote or lote.tenant_id != self.tenant_id:
                continue
            qtd_ativos = int(total or 0)
            lote.quantidade_cabecas = qtd_ativos
            lote.peso_medio_kg = (
                round(float(peso_total or 0) / int(qtd_com_peso or 0), 2) if qtd_com_peso else 0.0
            )
            if qtd_ativos > 0 and lote.modo_gestao == "POR_LOTE":
                lote.modo_gestao = "INDIVIDUAL"
            self.session.add(lote)
            atualizados += 1
        return atualizados

    async def _atualizar_pesos_coletivos(
        self, ctx: _ContextoFazenda, lote_ids: set[uuid.UUID]
    ) -> int:
        atualizados = 0
        for lote_id in lote_ids:
            lote = ctx.lotes_por_id.get(lote_id)
            if not lote:
                continue
            rows = (
                await self.session.execute(
                    select(
                        ManejoLote.data_evento,
                        ManejoLote.quantidade_cabecas,
                        ManejoLote.peso_total_kg,
                    )
                    .where(
                        ManejoLote.tenant_id == self.tenant_id,
                        ManejoLote.lote_id == lote_id,
                        ManejoLote.tipo_evento == "PESAGEM",
                    )
                    .order_by(ManejoLote.data_evento.asc(), ManejoLote.created_at.asc())
                )
            ).all()
            medias: list[float] = []
            for _, qtd_ev, peso_tot in rows:
                divisor = int(qtd_ev or lote.quantidade_cabecas or 0)
                if divisor > 0 and peso_tot and float(peso_tot) > 0:
                    medias.append(round(float(peso_tot) / divisor, 2))
            if medias:
                if lote.peso_inicial_medio_kg is None:
                    lote.peso_inicial_medio_kg = medias[0]
                lote.peso_medio_kg = medias[-1]
                self.session.add(lote)
                atualizados += 1
        return atualizados

    @staticmethod
    def _campo(raw_row: dict[str, str], mapeamento: dict[str, str | None], chave: str) -> str:
        col = mapeamento.get(chave)
        if not col:
            return ""
        return (raw_row.get(col) or "").strip()

    def _parse_modo_lote(self, raw: str, erros: list[str]) -> str:
        norm = normalizar_texto_chave(raw)
        if not norm or norm in ("por_lote", "coletivo", "lote"):
            return "POR_LOTE"
        if norm in ("individual", "brincado"):
            return "INDIVIDUAL"
        erros.append(f"Modo de gestão inválido: '{raw}' (use POR_LOTE ou INDIVIDUAL).")
        return "POR_LOTE"

    def _parse_opcional_int(
        self,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        chave: str,
        rotulo: str,
        erros: list[str],
    ) -> int | None:
        bruto = self._campo(raw_row, mapeamento, chave)
        if not bruto:
            return None
        try:
            return parse_int_br(bruto)
        except ValueError:
            erros.append(f"{rotulo} inválido: '{bruto}'.")
            return None

    def _parse_nao_neg_float(
        self,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        chave: str,
        rotulo: str,
        erros: list[str],
    ) -> float | None:
        bruto = self._campo(raw_row, mapeamento, chave)
        if not bruto:
            return None
        try:
            valor = parse_float_br(bruto)
        except ValueError:
            erros.append(f"{rotulo} inválido: '{bruto}'.")
            return None
        if valor is not None and valor < 0:
            erros.append(f"{rotulo} não pode ser negativo.")
            return None
        return valor

    def _parse_opcional_date(
        self,
        raw_row: dict[str, str],
        mapeamento: dict[str, str | None],
        chave: str,
        erros: list[str],
    ) -> date | None:
        bruto = self._campo(raw_row, mapeamento, chave)
        if not bruto:
            return None
        try:
            return parse_date_br(bruto)
        except ValueError as exc:
            erros.append(str(exc))
            return None

    @staticmethod
    def _normalizar_enum(
        raw: str,
        mapa: dict[str, str],
        rotulo: str,
        erros: list[str],
    ) -> str:
        norm = normalizar_texto_chave(raw)
        if norm in mapa:
            return mapa[norm]
        erros.append(f"{rotulo} inválida: '{raw}'.")
        return next(iter(mapa.values()))

    @staticmethod
    def _montar_chaves_animal(
        brinco: str | None, sisbov: str | None, microchip: str | None
    ) -> list[tuple[str, str]]:
        chaves: list[tuple[str, str]] = []
        if brinco:
            chaves.append(("BRINCO", brinco.strip().upper()))
        if sisbov:
            chaves.append(("SISBOV", sisbov.strip().upper()))
        if microchip:
            chaves.append(("MICROCHIP", microchip.strip().upper()))
        return chaves

    @staticmethod
    def _montar_resposta_preview(
        opcoes: OpcoesImportacao,
        filename: str,
        avaliacao: _ResultadoAvaliacao,
    ) -> ImportacaoPreviewResponse:
        previews = avaliacao.previews
        erros = [ln for ln in previews if ln.acao == "ERRO"]
        avisos_total = sum(len(ln.avisos) for ln in previews)
        return ImportacaoPreviewResponse(
            tipo=opcoes.tipo,
            nome_arquivo=filename,
            formato=avaliacao.planilha.formato,
            colunas_arquivo=avaliacao.planilha.headers,
            mapeamento_aplicado=avaliacao.mapeamento,
            campos_disponiveis=list(CAMPOS_POR_TIPO[opcoes.tipo]),
            total_linhas=len(previews),
            validas=len(previews) - len(erros),
            a_criar=sum(1 for ln in previews if ln.acao == "CRIAR"),
            a_atualizar=sum(1 for ln in previews if ln.acao == "ATUALIZAR"),
            a_ignorar=sum(1 for ln in previews if ln.acao == "IGNORAR"),
            com_erro=len(erros),
            avisos_total=avisos_total,
            preview_linhas=previews[:MAX_PREVIEW_ROWS],
            linhas_erro=erros[:MAX_ERROR_ROWS],
        )

    @staticmethod
    def _montar_resposta_execucao(
        tipo: TipoImportacaoPecuaria,
        previews: list[LinhaImportacaoPreview],
        lotes_criados: int,
        lotes_atualizados: int,
    ) -> ImportacaoExecucaoResponse:
        erros = [ln for ln in previews if ln.acao == "ERRO"]
        return ImportacaoExecucaoResponse(
            tipo=tipo,
            total_linhas=len(previews),
            criados=sum(1 for ln in previews if ln.acao == "CRIAR"),
            atualizados=sum(1 for ln in previews if ln.acao == "ATUALIZAR"),
            ignorados=sum(1 for ln in previews if ln.acao == "IGNORAR"),
            erros=len(erros),
            lotes_criados_automaticamente=lotes_criados,
            lotes_atualizados=lotes_atualizados,
            avisos_total=sum(len(ln.avisos) for ln in previews),
            linhas_erro=erros[:MAX_ERROR_ROWS],
        )
