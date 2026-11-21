"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Beef,
  CheckCircle2,
  ClipboardList,
  Download,
  FileSpreadsheet,
  FileText,
  Loader2,
  Scale,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  type AcaoLinhaImportacao,
  baixarTemplatePecuaria,
  executarImportacaoPecuaria,
  type ImportacaoExecucaoResponse,
  type ImportacaoPreviewResponse,
  type LinhaImportacaoPreview,
  type ModoConflitoImportacao,
  previsualizarImportacaoPecuaria,
  type TipoImportacaoPecuaria,
} from "@/lib/pecuaria/importacao-api";
import { useAppStore } from "@/lib/stores/app-store";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const UNMAPPED_SENTINEL = "__NONE__";

const TIPOS_INFO: Array<{
  tipo: TipoImportacaoPecuaria;
  titulo: string;
  descricao: string;
  detalhe: string;
  icon: typeof ClipboardList;
}> = [
  {
    tipo: "LOTES",
    titulo: "Lotes Pecuários",
    descricao: "Carga de lotes coletivos ou individuais, pasto, rendimento e aquisição.",
    detalhe: "Colunas principais: identificação, categoria, raça, cabeças, peso médio, piquete.",
    icon: ClipboardList,
  },
  {
    tipo: "ANIMAIS",
    titulo: "Animais Individuais",
    descricao: "Cadastro em massa por brinco, SISBOV ou microchip com peso inicial.",
    detalhe: "Permite criar automaticamente os lotes ausentes e registrar pesagem inicial.",
    icon: Beef,
  },
  {
    tipo: "PESAGENS",
    titulo: "Pesagens de Balança / Curral",
    descricao: "Importe pesagens por brinco individual ou pesagens coletivas por lote.",
    detalhe: "Atualiza peso atual, histórico para cálculo de GMD e média dos lotes.",
    icon: Scale,
  },
];

const ACAO_BADGE: Record<AcaoLinhaImportacao, { label: string; className: string }> = {
  CRIAR: {
    label: "Criar",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300",
  },
  ATUALIZAR: {
    label: "Atualizar",
    className: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300",
  },
  IGNORAR: {
    label: "Ignorar",
    className: "bg-neutral-100 text-neutral-700 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300",
  },
  ERRO: {
    label: "Erro",
    className: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300",
  },
};

function sanitizeCsvField(value: string): string {
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safe.replace(/"/g, '""')}"`;
}

function exportarErrosCsv(linhasErro: LinhaImportacaoPreview[], tipo: TipoImportacaoPecuaria): void {
  const header = ["Linha", "Identificador", "Erros", "Avisos"].map(sanitizeCsvField).join(";");
  const rows = linhasErro.map((ln) =>
    [
      String(ln.linha_numero),
      ln.identificador,
      ln.erros.join(" | "),
      ln.avisos.join(" | "),
    ]
      .map(sanitizeCsvField)
      .join(";")
  );
  const blob = new Blob([`\ufeff${header}\n${rows.join("\n")}`], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `erros-importacao-${tipo.toLowerCase()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function resumirDadosLinha(
  tipo: TipoImportacaoPecuaria,
  dados: Record<string, string | number | boolean | null | undefined>
): string {
  if (tipo === "LOTES") {
    const modo = dados.modo_gestao === "INDIVIDUAL" ? "Individual" : "Por Lote";
    const cab = dados.quantidade_cabecas ?? 0;
    const peso = dados.peso_medio_kg ?? 0;
    return `${dados.categoria ?? "—"} · ${dados.raca ?? "—"} · ${modo} · ${cab} cab. · ${peso} kg`;
  }
  if (tipo === "ANIMAIS") {
    const lote = dados.lote ? `Lote: ${dados.lote}` : "Sem lote";
    const peso = dados.peso_atual_kg != null ? `${dados.peso_atual_kg} kg` : "Sem peso";
    return `${dados.categoria ?? "—"} (${dados.sexo ?? "—"}) · ${lote} · ${peso}`;
  }
  if (dados.modo === "COLETIVA") {
    return `Coletiva · ${dados.data_evento ?? "—"} · ${dados.quantidade_cabecas ?? 0} cab. · ${dados.peso_total_kg ?? 0} kg total`;
  }
  return `Individual · ${dados.data_evento ?? "—"} · ${dados.peso_kg ?? 0} kg`;
}

function resolveInitialTipo(rawParam: string | null): TipoImportacaoPecuaria {
  if (rawParam === "ANIMAIS" || rawParam === "PESAGENS" || rawParam === "LOTES") {
    return rawParam;
  }
  return "LOTES";
}

export function ImportacaoPlanilhaWizard() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { activeFazendaId, isVisaoGrupo } = useAppStore();

  const [etapa, setEtapa] = useState<1 | 2 | 3>(1);
  const [tipo, setTipo] = useState<TipoImportacaoPecuaria>(() =>
    resolveInitialTipo(searchParams.get("tipo"))
  );
  const [modoConflito, setModoConflito] = useState<ModoConflitoImportacao>("ATUALIZAR");
  const [criarLotesAuto, setCriarLotesAuto] = useState(true);
  const [ignorarErros, setIgnorarErros] = useState(false);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [mapeamentoCustom, setMapeamentoCustom] = useState<Record<string, string | null>>({});
  const [mostrarMapeamento, setMostrarMapeamento] = useState(false);
  const [filtroPreview, setFiltroPreview] = useState<"ALL" | "ERRO" | "VALID">("ALL");
  const [preview, setPreview] = useState<ImportacaoPreviewResponse | null>(null);
  const [resultado, setResultado] = useState<ImportacaoExecucaoResponse | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<"xlsx" | "csv" | null>(null);

  const previewMutation = useMutation({
    mutationFn: (overrideMap?: Record<string, string | null>) => {
      if (!activeFazendaId) throw new Error("Selecione uma fazenda ativa antes de importar.");
      if (!arquivo) throw new Error("Selecione um arquivo .xlsx, .xls ou .csv.");
      return previsualizarImportacaoPecuaria({
        tipo,
        unidade_produtiva_id: activeFazendaId,
        modo_conflito: modoConflito,
        criar_lotes_automaticamente: criarLotesAuto,
        mapeamento_colunas: overrideMap,
        arquivo,
      });
    },
    onSuccess: (data) => {
      setPreview(data);
      setMapeamentoCustom(data.mapeamento_aplicado);
      setIgnorarErros(false);
      setFiltroPreview("ALL");
      setEtapa(2);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Erro ao analisar planilha.";
      toast.error(msg);
    },
  });

  const executarMutation = useMutation({
    mutationFn: () => {
      if (!activeFazendaId) throw new Error("Selecione uma fazenda ativa antes de importar.");
      if (!arquivo) throw new Error("Arquivo ausente.");
      return executarImportacaoPecuaria({
        tipo,
        unidade_produtiva_id: activeFazendaId,
        modo_conflito: modoConflito,
        criar_lotes_automaticamente: criarLotesAuto,
        ignorar_linhas_com_erro: ignorarErros,
        mapeamento_colunas: Object.keys(mapeamentoCustom).length > 0 ? mapeamentoCustom : null,
        arquivo,
      });
    },
    onSuccess: (data) => {
      setResultado(data);
      setEtapa(3);
      toast.success("Importação concluída com sucesso!");
      void queryClient.invalidateQueries({ queryKey: ["lotes"] });
      void queryClient.invalidateQueries({ queryKey: ["lotes-bovinos"] });
      void queryClient.invalidateQueries({ queryKey: ["animais"] });
      void queryClient.invalidateQueries({ queryKey: ["pecuaria"] });
      void queryClient.invalidateQueries({ queryKey: ["pecuaria-resumo-economico"] });
      void queryClient.invalidateQueries({ queryKey: ["pecuaria-manejos"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Falha ao executar importação.";
      toast.error(msg);
    },
  });

  const linhasFiltradas = useMemo(() => {
    if (!preview) return [];
    if (filtroPreview === "ERRO") return preview.linhas_erro;
    if (filtroPreview === "VALID") {
      return preview.preview_linhas.filter((ln) => ln.acao !== "ERRO");
    }
    return preview.preview_linhas;
  }, [preview, filtroPreview]);

  const handleDownloadTemplate = async (formato: "xlsx" | "csv") => {
    try {
      setDownloadingFormat(formato);
      await baixarTemplatePecuaria(tipo, formato);
      toast.success(`Modelo .${formato} baixado!`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Falha ao baixar modelo.");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleFileSelected = (selected: File | null) => {
    if (!selected) {
      setArquivo(null);
      return;
    }
    const lowerName = selected.name.toLowerCase();
    if (!lowerName.endsWith(".xlsx") && !lowerName.endsWith(".xls") && !lowerName.endsWith(".csv")) {
      toast.error("Formato inválido. Selecione um arquivo .xlsx, .xls ou .csv.");
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      toast.error("O arquivo excede o limite máximo de 5 MB.");
      return;
    }
    setArquivo(selected);
    setMapeamentoCustom({});
  };

  const handleNovaImportacao = () => {
    setEtapa(1);
    setArquivo(null);
    setPreview(null);
    setResultado(null);
    setMapeamentoCustom({});
    setIgnorarErros(false);
  };

  const semFazendaUnica = !activeFazendaId || isVisaoGrupo;
  const podeConfirmarImportacao =
    Boolean(preview) &&
    (preview?.validas ?? 0) > 0 &&
    ((preview?.com_erro ?? 0) === 0 || ignorarErros) &&
    !executarMutation.isPending;

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-200">
      <PageHeader
        title="Importar Planilhas — Pecuária"
        description="Faça carga rápida de lotes, animais individuais ou pesagens via Excel (.xlsx/.xls) ou CSV."
        icon={<Upload className="size-5 text-primary" />}
        breadcrumbs={[
          { label: "Pecuária", href: "/dashboard/pecuaria" },
          { label: "Importar Planilhas" },
        ]}
        actions={
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/pecuaria/lotes">
              <ArrowLeft className="size-3.5 mr-1.5" />
              Voltar aos Lotes
            </Link>
          </Button>
        }
      />

      {semFazendaUnica && (
        <Card className="rounded-sm border-amber-300 bg-amber-50/70 dark:border-amber-900 dark:bg-amber-950/30">
          <CardContent className="py-3 flex items-center gap-2 text-sm text-amber-900 dark:text-amber-200">
            <AlertTriangle className="size-4 shrink-0" />
            <span>
              Selecione uma fazenda específica no seletor superior (Visão de Grupo não permite importação direta).
            </span>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2 text-xs">
        {[
          { num: 1, label: "1. Modelo e Arquivo" },
          { num: 2, label: "2. Pré-visualização e Mapeamento" },
          { num: 3, label: "3. Resultado" },
        ].map((step) => (
          <Badge
            key={step.num}
            variant={etapa === step.num ? "default" : "outline"}
            className="rounded-sm px-3 py-1"
          >
            {step.label}
          </Badge>
        ))}
      </div>

      {etapa === 1 && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {TIPOS_INFO.map((item) => {
              const Icon = item.icon;
              const ativo = tipo === item.tipo;
              return (
                <button
                  key={item.tipo}
                  type="button"
                  onClick={() => {
                    setTipo(item.tipo);
                    setMapeamentoCustom({});
                  }}
                  className={`text-left border rounded-sm p-4 transition-all ${
                    ativo
                      ? "border-primary bg-primary/5 ring-1 ring-primary/40"
                      : "border-border hover:border-primary/40 bg-card"
                  }`}
                >
                  <div className="flex items-center gap-2.5 mb-2">
                    <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                      <Icon className="size-4" />
                    </div>
                    <span className="font-semibold text-sm">{item.titulo}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{item.descricao}</p>
                  <p className="text-[11px] text-muted-foreground/80 mt-2">{item.detalhe}</p>
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="rounded-sm">
              <CardHeader className="border-b">
                <CardTitle className="text-base">1. Baixar Modelo e Configurar Regras</CardTitle>
                <CardDescription>
                  Use um modelo pronto ou envie sua própria planilha (com remapeamento de colunas na etapa seguinte).
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    disabled={downloadingFormat !== null}
                    onClick={() => void handleDownloadTemplate("xlsx")}
                  >
                    {downloadingFormat === "xlsx" ? (
                      <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <FileSpreadsheet className="size-3.5 mr-1.5" />
                    )}
                    Baixar Modelo Excel (.xlsx)
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    disabled={downloadingFormat !== null}
                    onClick={() => void handleDownloadTemplate("csv")}
                  >
                    {downloadingFormat === "csv" ? (
                      <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <FileText className="size-3.5 mr-1.5" />
                    )}
                    Baixar Modelo CSV (.csv)
                  </Button>
                </div>

                <div className="space-y-1.5 max-w-sm">
                  <label className="text-xs font-semibold uppercase text-muted-foreground">
                    Quando o registro já existir na fazenda
                  </label>
                  <Select
                    value={modoConflito}
                    onValueChange={(value) =>
                      setModoConflito(value === "IGNORAR" ? "IGNORAR" : "ATUALIZAR")
                    }
                  >
                    <SelectTrigger className="h-8 rounded-sm text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ATUALIZAR">Atualizar registros existentes</SelectItem>
                      <SelectItem value="IGNORAR">Ignorar existentes (somente novos)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {tipo === "ANIMAIS" && (
                  <label className="flex items-center gap-2 text-sm cursor-pointer pt-1">
                    <Checkbox
                      checked={criarLotesAuto}
                      onCheckedChange={(checked) => setCriarLotesAuto(Boolean(checked))}
                    />
                    <span>Criar lotes automaticamente caso o nome da coluna Lote ainda não exista</span>
                  </label>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-sm">
              <CardHeader className="border-b">
                <CardTitle className="text-base">2. Enviar Arquivo (.xlsx, .xls ou .csv)</CardTitle>
                <CardDescription>
                  Limite de 5 MB e até 5.000 linhas por importação. Nenhum dado é gravado antes da confirmação.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <label className="flex flex-col items-center justify-center border border-dashed rounded-sm p-6 text-center cursor-pointer hover:border-primary/60 hover:bg-muted/30 transition-colors">
                  <Upload className="size-6 text-primary mb-2" />
                  <span className="text-sm font-medium">
                    {arquivo ? arquivo.name : "Clique para selecionar a planilha do computador"}
                  </span>
                  <span className="text-xs text-muted-foreground mt-1">
                    {arquivo
                      ? `${(arquivo.size / 1024).toFixed(1)} KB · Pronto para análise`
                      : "Formatos aceitos: .xlsx, .xls ou .csv (separado por ; ou ,)"}
                  </span>
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    className="sr-only"
                    onChange={(event) => handleFileSelected(event.target.files?.[0] ?? null)}
                  />
                </label>

                <div className="flex flex-wrap items-center justify-between gap-2">
                  {arquivo ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="rounded-sm"
                      onClick={() => handleFileSelected(null)}
                    >
                      <X className="size-3.5 mr-1.5" />
                      Limpar Arquivo
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">Selecione um arquivo para continuar.</span>
                  )}

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    disabled={semFazendaUnica || !arquivo || previewMutation.isPending}
                    onClick={() => previewMutation.mutate(undefined)}
                  >
                    {previewMutation.isPending ? (
                      <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <Upload className="size-3.5 mr-1.5" />
                    )}
                    {previewMutation.isPending ? "Analisando..." : "Analisar Planilha"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {etapa === 2 && preview && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Total Linhas", valor: preview.total_linhas, cls: "" },
              { label: "Novos", valor: preview.a_criar, cls: "text-emerald-600 dark:text-emerald-400" },
              { label: "Atualizações", valor: preview.a_atualizar, cls: "text-blue-600 dark:text-blue-400" },
              { label: "Ignorados", valor: preview.a_ignorar, cls: "text-muted-foreground" },
              { label: "Com Erro", valor: preview.com_erro, cls: preview.com_erro > 0 ? "text-destructive" : "" },
              { label: "Avisos", valor: preview.avisos_total, cls: "text-amber-600 dark:text-amber-400" },
            ].map((card) => (
              <Card key={card.label} className="rounded-sm">
                <CardContent className="p-3">
                  <div className="text-xs text-muted-foreground">{card.label}</div>
                  <div className={`text-xl font-bold tabular-nums mt-1 ${card.cls}`}>
                    {card.valor}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="rounded-sm">
            <CardHeader className="border-b py-3 flex flex-row items-center justify-between gap-2">
              <div>
                <CardTitle className="text-sm">Mapeamento de Colunas ({preview.nome_arquivo})</CardTitle>
                <CardDescription className="text-xs">
                  Ajuste caso sua planilha utilize nomes de colunas diferentes do modelo.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="rounded-sm"
                onClick={() => setMostrarMapeamento((prev) => !prev)}
              >
                <SlidersHorizontal className="size-3.5 mr-1.5" />
                {mostrarMapeamento ? "Ocultar Mapeamento" : "Ajustar Colunas"}
              </Button>
            </CardHeader>
            {mostrarMapeamento && (
              <CardContent className="pt-4 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {preview.campos_disponiveis.map((campo) => {
                    const selectedCol = mapeamentoCustom[campo.chave] ?? UNMAPPED_SENTINEL;
                    return (
                      <div key={campo.chave} className="space-y-1">
                        <label className="text-xs font-medium flex items-center gap-1">
                          <span>{campo.rotulo}</span>
                          {campo.obrigatorio ? <span className="text-destructive">*</span> : null}
                        </label>
                        <Select
                          value={selectedCol}
                          onValueChange={(value) =>
                            setMapeamentoCustom((prev) => ({
                              ...prev,
                              [campo.chave]: value === UNMAPPED_SENTINEL ? null : value,
                            }))
                          }
                        >
                          <SelectTrigger className="h-8 rounded-sm text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={UNMAPPED_SENTINEL}>— Não mapear —</SelectItem>
                            {preview.colunas_arquivo.map((col) => (
                              <SelectItem key={col} value={col}>
                                {col}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    );
                  })}
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    disabled={previewMutation.isPending}
                    onClick={() => previewMutation.mutate(mapeamentoCustom)}
                  >
                    {previewMutation.isPending ? (
                      <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <SlidersHorizontal className="size-3.5 mr-1.5" />
                    )}
                    Revalidar Mapeamento
                  </Button>
                </div>
              </CardContent>
            )}
          </Card>

          <Card className="rounded-sm">
            <CardHeader className="border-b py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <CardTitle className="text-base">Pré-visualização das Linhas</CardTitle>
                <CardDescription className="text-xs">
                  Exibindo {linhasFiltradas.length} linha(s) no filtro atual (limite de 200 no preview).
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {(["ALL", "VALID", "ERRO"] as const).map((filtro) => (
                  <Button
                    key={filtro}
                    type="button"
                    variant="outline"
                    size="sm"
                    className={`rounded-sm ${filtroPreview === filtro ? "border-primary text-primary" : ""}`}
                    onClick={() => setFiltroPreview(filtro)}
                  >
                    {filtro === "ALL" ? "Todas" : filtro === "VALID" ? "Válidas" : `Com Erro (${preview.com_erro})`}
                  </Button>
                ))}
                {preview.com_erro > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    onClick={() => exportarErrosCsv(preview.linhas_erro, preview.tipo)}
                  >
                    <Download className="size-3.5 mr-1.5" />
                    Exportar Erros (.csv)
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Linha</TableHead>
                    <TableHead className="w-28">Ação</TableHead>
                    <TableHead>Identificador</TableHead>
                    <TableHead>Dados Normalizados</TableHead>
                    <TableHead>Observações / Erros</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {linhasFiltradas.map((linha) => {
                    const badge = ACAO_BADGE[linha.acao];
                    return (
                      <TableRow key={linha.linha_numero}>
                        <TableCell className="tabular-nums text-xs">{linha.linha_numero}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`rounded-sm text-[11px] ${badge.className}`}>
                            {badge.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium text-sm">{linha.identificador}</TableCell>
                        <TableCell className="text-xs text-muted-foreground whitespace-normal">
                          {resumirDadosLinha(preview.tipo, linha.dados)}
                        </TableCell>
                        <TableCell className="text-xs whitespace-normal max-w-md">
                          {linha.erros.map((err, idx) => (
                            <p key={idx} className="text-destructive font-medium">
                              • {err}
                            </p>
                          ))}
                          {linha.avisos.map((aviso, idx) => (
                            <p key={idx} className="text-amber-600 dark:text-amber-400">
                              • {aviso}
                            </p>
                          ))}
                          {linha.erros.length === 0 && linha.avisos.length === 0 ? "OK" : null}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className="rounded-sm">
            <CardContent className="py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                {preview.com_erro > 0 ? (
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <Checkbox
                      checked={ignorarErros}
                      onCheckedChange={(checked) => setIgnorarErros(Boolean(checked))}
                    />
                    <span>
                      Ignorar as {preview.com_erro} linha(s) com erro e importar somente as {preview.validas} válida(s)
                    </span>
                  </label>
                ) : (
                  <p className="text-sm text-emerald-700 dark:text-emerald-400 font-medium">
                    Todas as {preview.total_linhas} linha(s) foram validadas sem erros.
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm"
                  onClick={() => setEtapa(1)}
                >
                  <ArrowLeft className="size-3.5 mr-1.5" />
                  Voltar
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm"
                  disabled={!podeConfirmarImportacao}
                  onClick={() => executarMutation.mutate()}
                >
                  {executarMutation.isPending ? (
                    <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="size-3.5 mr-1.5" />
                  )}
                  {executarMutation.isPending ? "Importando..." : "Confirmar Importação"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {etapa === 3 && resultado && (
        <div className="space-y-5">
          <Card className="rounded-sm border-emerald-300 dark:border-emerald-900">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2 text-base text-emerald-700 dark:text-emerald-400">
                <CheckCircle2 className="size-5" />
                Importação Finalizada ({resultado.tipo})
              </CardTitle>
              <CardDescription>
                Dados gravados na fazenda selecionada com sucesso.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { label: "Criados", valor: resultado.criados },
                  { label: "Atualizados", valor: resultado.atualizados },
                  { label: "Ignorados", valor: resultado.ignorados },
                  { label: "Lotes Criados Auto", valor: resultado.lotes_criados_automaticamente },
                  { label: "Erros Ignorados", valor: resultado.erros },
                ].map((stat) => (
                  <div key={stat.label} className="border rounded-sm p-3">
                    <div className="text-xs text-muted-foreground">{stat.label}</div>
                    <div className="text-xl font-bold tabular-nums mt-1">{stat.valor}</div>
                  </div>
                ))}
              </div>

              {resultado.linhas_erro.length > 0 && (
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="rounded-sm"
                    onClick={() => exportarErrosCsv(resultado.linhas_erro, resultado.tipo)}
                  >
                    <Download className="size-3.5 mr-1.5" />
                    Baixar Relatório de Erros (.csv)
                  </Button>
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                <Button asChild variant="outline" size="sm" className="rounded-sm">
                  <Link href="/dashboard/pecuaria/lotes">
                    <ClipboardList className="size-3.5 mr-1.5" />
                    Ver Lotes
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm" className="rounded-sm">
                  <Link href="/dashboard/pecuaria/animais">
                    <Beef className="size-3.5 mr-1.5" />
                    Ver Animais
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm" className="rounded-sm">
                  <Link href="/dashboard/pecuaria">
                    <Scale className="size-3.5 mr-1.5" />
                    Painel Pecuária
                  </Link>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm"
                  onClick={handleNovaImportacao}
                >
                  <Upload className="size-3.5 mr-1.5" />
                  Nova Importação
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
