"use client";

import * as React from "react";
import {
  AlertCircle,
  BarChart3,
  Calendar,
  ExternalLink,
  Layers,
  MapPin,
  RefreshCw,
  Sprout,
  WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchIbgeCatalogo,
  fetchIbgeEstatisticas,
  markIbgeUnavailable,
  fetchIbgeMunicipios,
  formatarPeriodoIbge,
  formatarValorIbge,
  gerarQueryKey,
  readSavedCatalogo,
  readSavedIbge,
  saveCatalogo,
  saveIbge,
  type CatalogoIbgeResponse,
  type EstatisticasIbgeResponse,
  type MunicipioIbge,
  type NivelTerritorialIbge,
  type ProdutoCatalogoIbge,
  type UfIbge,
} from "@/lib/mercado/ibge";

const PRODUTOS_PADRAO: ProdutoCatalogoIbge[] = [
  { id: "soja", nome: "Soja (em grão)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "milho", nome: "Milho (em grão)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "cafe", nome: "Café (em grão) — total", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "pimenta-do-reino", nome: "Pimenta-do-reino", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: false },
  { id: "cacau", nome: "Cacau (em amêndoa)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "cana-de-acucar", nome: "Cana-de-açúcar", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "trigo", nome: "Trigo (em grão)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "arroz", nome: "Arroz (em casca)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
  { id: "bovinos", nome: "Bovinos", tipo: "REBANHO", pesquisa: "PPM", indicadores: [], suportaLspa: false },
  { id: "leite", nome: "Leite", tipo: "PRODUCAO_ANIMAL", pesquisa: "PPM", indicadores: [], suportaLspa: false },
];

const UFS_PADRAO: UfIbge[] = [
  { codigo: "51", sigla: "MT", nome: "Mato Grosso" },
  { codigo: "41", sigla: "PR", nome: "Paraná" },
  { codigo: "35", sigla: "SP", nome: "São Paulo" },
  { codigo: "31", sigla: "MG", nome: "Minas Gerais" },
  { codigo: "43", sigla: "RS", nome: "Rio Grande do Sul" },
  { codigo: "52", sigla: "GO", nome: "Goiás" },
  { codigo: "50", sigla: "MS", nome: "Mato Grosso do Sul" },
  { codigo: "29", sigla: "BA", nome: "Bahia" },
];

export function IbgeProducaoCard() {
  const [catalogo, setCatalogo] = React.useState<CatalogoIbgeResponse | null>(null);
  const [produtoId, setProdutoId] = React.useState<string>("soja");
  const [nivel, setNivel] = React.useState<NivelTerritorialIbge>("BRASIL");
  const [uf, setUf] = React.useState<string>("51");
  const [municipio, setMunicipio] = React.useState<string>("");
  const [municipiosLista, setMunicipiosLista] = React.useState<MunicipioIbge[]>([]);
  const [carregandoMunicipios, setCarregandoMunicipios] = React.useState<boolean>(false);
  const [fonteLspa, setFonteLspa] = React.useState<boolean>(false);

  const [estatisticas, setEstatisticas] = React.useState<EstatisticasIbgeResponse | null>(null);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [refreshing, setRefreshing] = React.useState<boolean>(false);
  const [isOffline, setIsOffline] = React.useState<boolean>(false);
  const [erro, setErro] = React.useState<string | null>(null);

  // 1. Carrega catálogo inicial
  React.useEffect(() => {
    const savedCat = readSavedCatalogo(window.localStorage);
    if (savedCat) {
      setCatalogo(savedCat);
    }

    let active = true;
    const controller = new AbortController();

    async function carregarCat() {
      try {
        const cat = await fetchIbgeCatalogo(window.location, controller.signal);
        if (active && cat) {
          setCatalogo(cat);
          saveCatalogo(window.localStorage, cat);
        }
      } catch {
        // Mantém catálogo salvo ou lista padrão
      }
    }

    carregarCat();
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const produtosDisponiveis = catalogo?.produtos ?? PRODUTOS_PADRAO;
  const ufsDisponiveis = catalogo?.ufs ?? UFS_PADRAO;
  const produtoAtual = produtosDisponiveis.find((p) => p.id === produtoId) ?? produtosDisponiveis[0];
  const suportaLspa = Boolean(produtoAtual?.suportaLspa);

  // Se o usuário selecionou município mas LSPA estava ativo, desativa LSPA
  React.useEffect(() => {
    if (nivel === "MUNICIPIO" && fonteLspa) {
      setFonteLspa(false);
    }
  }, [nivel, fonteLspa]);

  // Se o produto não suporta LSPA, desativa LSPA
  React.useEffect(() => {
    if (!suportaLspa && fonteLspa) {
      setFonteLspa(false);
    }
  }, [suportaLspa, fonteLspa]);

  // 2. Carrega municípios quando nível for MUNICIPIO e UF mudar
  React.useEffect(() => {
    if (nivel !== "MUNICIPIO" || !uf) return;

    let active = true;
    const controller = new AbortController();
    setCarregandoMunicipios(true);

    async function carregarMun() {
      try {
        const res = await fetchIbgeMunicipios(window.location, uf, controller.signal);
        if (active && res && res.itens.length > 0) {
          setMunicipiosLista(res.itens);
          setMunicipio(res.itens[0].codigo);
        }
      } catch {
        if (active) {
          setMunicipiosLista([]);
          setMunicipio("");
        }
      } finally {
        if (active) {
          setCarregandoMunicipios(false);
        }
      }
    }

    carregarMun();
    return () => {
      active = false;
      controller.abort();
    };
  }, [nivel, uf]);

  // 3. Consulta de estatísticas
  const carregarDados = React.useCallback(
    async (isManualRefresh = false) => {
      if (nivel === "MUNICIPIO" && !municipio) {
        return;
      }

      const params = {
        produto: produtoId,
        nivel,
        uf: nivel !== "BRASIL" ? uf : undefined,
        municipio: nivel === "MUNICIPIO" ? municipio : undefined,
        anos: 5,
        fonte: fonteLspa ? ("LSPA" as const) : undefined,
      };

      const queryKey = gerarQueryKey(params);
      const saved = readSavedIbge(window.localStorage, queryKey);
      if (saved && !isManualRefresh) {
        setEstatisticas(saved);
      }

      if (!navigator.onLine) {
        setIsOffline(true);
        setLoading(false);
        setRefreshing(false);
        return;
      }

      if (isManualRefresh) setRefreshing(true);
      else if (!saved) setLoading(true);

      setErro(null);

      try {
        const res = await fetchIbgeEstatisticas(window.location, params);
        if (res && res.sucesso) {
          setEstatisticas(res);
          saveIbge(window.localStorage, queryKey, res);
          setIsOffline(false);
        } else if (saved) {
          setEstatisticas(markIbgeUnavailable(saved));
        }
      } catch (e) {
        if (saved) {
          setEstatisticas(markIbgeUnavailable(saved));
        } else {
          setErro(e instanceof Error ? e.message : "Falha ao consultar IBGE/SIDRA");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [produtoId, nivel, uf, municipio, fonteLspa]
  );

  React.useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  return (
    <Card className="rounded-sm border border-border bg-card shadow-sm">
      <CardHeader className="p-4 pb-3 border-b border-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                Inteligência e Estatísticas Oficiais de Produção (IBGE/SIDRA)
              </CardTitle>
              <Badge variant="outline" className="text-[10px] rounded-sm border-emerald-600/30 text-emerald-700 dark:text-emerald-300">
                Dados Públicos Gratuitos
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Séries históricas e estimativas da Produção Agrícola Municipal (PAM), Pecuária (PPM) e Levantamento Sistemático (LSPA).
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isOffline && (
              <Badge variant="outline" className="text-[10px] rounded-sm text-amber-600 border-amber-600/30 flex items-center gap-1">
                <WifiOff className="w-3 h-3" />
                Offline
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => carregarDados(true)}
              disabled={refreshing || loading}
              className="h-7 text-xs rounded-sm gap-1 px-2.5"
              aria-label="Atualizar estatísticas do IBGE"
            >
              <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Atualizar</span>
            </Button>
          </div>
        </div>

        {/* Barra de Filtros e Controles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-3">
          {/* 1. Cultura / Atividade */}
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
              <Sprout className="w-3 h-3" /> Cultura / Atividade
            </label>
            <select
              value={produtoId}
              onChange={(e) => setProdutoId(e.target.value)}
              className="w-full h-8 text-xs rounded-sm border border-input bg-background px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              aria-label="Selecionar produto ou rebanho agropecuário"
            >
              <optgroup label="Lavouras">
                {produtosDisponiveis
                  .filter((p) => p.tipo === "LAVOURA")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Pecuária e Rebanhos">
                {produtosDisponiveis
                  .filter((p) => p.tipo === "REBANHO")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Origem Animal">
                {produtosDisponiveis
                  .filter((p) => p.tipo === "PRODUCAO_ANIMAL")
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nome}
                    </option>
                  ))}
              </optgroup>
            </select>
          </div>

          {/* 2. Nível Territorial */}
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
              <MapPin className="w-3 h-3" /> Abrangência
            </label>
            <select
              value={nivel}
              onChange={(e) => setNivel(e.target.value as NivelTerritorialIbge)}
              className="w-full h-8 text-xs rounded-sm border border-input bg-background px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              aria-label="Selecionar nível territorial"
            >
              <option value="BRASIL">Brasil (Nacional)</option>
              <option value="UF">Estado (UF)</option>
              <option value="MUNICIPIO" disabled={fonteLspa}>
                Município {fonteLspa ? "(indisp. no LSPA)" : ""}
              </option>
            </select>
          </div>

          {/* 3. UF ou Município dependendo do Nível */}
          {nivel !== "BRASIL" ? (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                Estado (UF)
              </label>
              <select
                value={uf}
                onChange={(e) => setUf(e.target.value)}
                className="w-full h-8 text-xs rounded-sm border border-input bg-background px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                aria-label="Selecionar estado"
              >
                {ufsDisponiveis.map((u) => (
                  <option key={u.codigo} value={u.codigo}>
                    {u.sigla} — {u.nome}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Layers className="w-3 h-3" /> Pesquisa Primária
              </label>
              <div className="h-8 px-2.5 py-1 text-xs rounded-sm border border-border/80 bg-muted/40 text-muted-foreground flex items-center">
                {fonteLspa ? "LSPA (Estimativa Mensal)" : produtoAtual.tipo === "LAVOURA" ? "PAM (Consolidado Anual)" : "PPM (Consolidado Anual)"}
              </div>
            </div>
          )}

          {/* 4. Município (se selecionado nível MUNICIPIO) ou Alternador LSPA */}
          {nivel === "MUNICIPIO" ? (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                Município
              </label>
              <select
                value={municipio}
                onChange={(e) => setMunicipio(e.target.value)}
                disabled={carregandoMunicipios || municipiosLista.length === 0}
                className="w-full h-8 text-xs rounded-sm border border-input bg-background px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-60"
                aria-label="Selecionar município"
              >
                {carregandoMunicipios ? (
                  <option value="">Carregando...</option>
                ) : (
                  municipiosLista.map((m) => (
                    <option key={m.codigo} value={m.codigo}>
                      {m.nome}
                    </option>
                  ))
                )}
              </select>
            </div>
          ) : suportaLspa ? (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3 h-3" /> Série / Regime
              </label>
              <div className="flex gap-1 h-8 items-center">
                <Button
                  variant={!fonteLspa ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => setFonteLspa(false)}
                  className="flex-1 h-7 text-[11px] rounded-sm px-2"
                >
                  PAM Anual
                </Button>
                <Button
                  variant={fonteLspa ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => setFonteLspa(true)}
                  className="flex-1 h-7 text-[11px] rounded-sm px-2"
                >
                  LSPA Mensal
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3 h-3" /> Periodicidade
              </label>
              <div className="h-8 px-2.5 py-1 text-xs rounded-sm border border-border/80 bg-muted/40 text-muted-foreground flex items-center">
                Anual (Censo / Pesquisa PPM)
              </div>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-4">
        {loading && !estatisticas ? (
          /* Skeletons para Zero Layout Shift */
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-sm border border-border/60 bg-muted/30 animate-pulse p-3 space-y-2">
                <div className="h-3 w-2/3 bg-muted rounded-sm" />
                <div className="h-6 w-1/2 bg-muted rounded-sm" />
                <div className="h-2 w-1/3 bg-muted rounded-sm" />
              </div>
            ))}
          </div>
        ) : erro ? (
          <div className="p-4 rounded-sm border border-red-500/30 bg-red-500/10 text-xs text-foreground flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold">Não foi possível carregar as estatísticas do IBGE</p>
              <p className="text-muted-foreground mt-0.5">{erro}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => carregarDados(true)}
                className="mt-2 h-7 text-xs rounded-sm gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Tentar novamente
              </Button>
            </div>
          </div>
        ) : estatisticas ? (
          <>
            {/* Metadados e Localidade */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs border-b border-border/40 pb-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground">
                  {estatisticas.localidade.nome || "Brasil"}
                </span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">
                  {estatisticas.pesquisa} (Tabela {estatisticas.tabelaSidra})
                </span>
                {(estatisticas.estadoDisponibilidade === "DEFASADO" || estatisticas.estadoDisponibilidade === "FONTE_INDISPONIVEL") && (
                  <Badge variant="outline" className="text-[10px] rounded-sm text-amber-600 border-amber-600/30">
                    {estatisticas.estadoDisponibilidade === "FONTE_INDISPONIVEL" ? "Fonte indisponível — dado salvo" : "Defasado"}
                  </Badge>
                )}
                {estatisticas.estadoDisponibilidade === "SEM_DADOS" && (
                  <Badge variant="outline" className="text-[10px] rounded-sm text-muted-foreground border-border">
                    Sem registros para a localidade
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                <span>
                  Último período:{" "}
                  <strong className="text-foreground">
                    {formatarPeriodoIbge(estatisticas.ultimoPeriodoDisponivel, estatisticas.periodicidade)}
                  </strong>
                </span>
                <a
                  href={estatisticas.urlTabela}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  SIDRA #{estatisticas.tabelaSidra}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>

            {/* Grid de Indicadores */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {estatisticas.indicadores.map((ind) => (
                <div
                  key={`${ind.id}_${ind.recorte ?? ""}`}
                  className="rounded-sm border border-border/80 bg-background/50 p-3 space-y-1.5 transition-colors hover:border-emerald-600/30"
                >
                  <div className="text-[11px] font-medium text-muted-foreground truncate" title={ind.nomeOficial}>
                    {ind.recorte ? `${ind.nomeOficial} (${ind.recorte})` : ind.nomeOficial}
                  </div>
                  <div className="text-lg sm:text-xl font-bold tracking-tight text-foreground">
                    {formatarValorIbge(ind.ultimoValor, ind.unidade)}
                  </div>
                  <div className="text-[10px] text-muted-foreground flex items-center justify-between">
                    <span>Ref: {formatarPeriodoIbge(ind.ultimoPeriodo, estatisticas.periodicidade)}</span>
                    <span className="font-mono text-[9px] uppercase tracking-wider">{ind.id}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Aviso Legal Estrito e Isenção Regulatória */}
            <div className="rounded-sm border border-emerald-600/20 bg-emerald-600/5 p-2.5 text-[11px] text-muted-foreground space-y-1">
              <div className="font-medium text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                Aviso Legal e Semântica de Dados Agropecuários
              </div>
              <p>{estatisticas.avisoLegal}</p>
              {estatisticas.avisoDefasagem && (
                <p className="text-amber-700 dark:text-amber-400 text-[10px]">
                  {estatisticas.avisoDefasagem}
                </p>
              )}
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
