"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Leaf,
  Plus,
  ChevronDown,
  ChevronUp,
  MapPin,
  Layers,
  Search,
  Calendar,
  AlertTriangle,
  Clock,
  LayoutGrid,
  TableProperties,
  X,
  Check,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogBody,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { useState, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { format, differenceInDays, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface Escala {
  id: string;
  codigo: string;
  nome: string;
  ordem: number;
}

interface FenologiaRegistro {
  id: string;
  talhao_id: string;
  grupo_id: string | null;
  escala_codigo: string;
  escala_nome: string;
  escala_ordem: number;
  data_observacao: string;
  observacao: string | null;
}

interface GrupoItem {
  id: string;
  talhao_id: string;
}

interface Grupo {
  id: string;
  nome: string;
  cor: string | null;
  itens: GrupoItem[];
}

interface Talhao {
  id: string;
  nome: string;
  area_ha?: number | null;
  codigo?: string | null;
}

interface SafraFenologiaProps {
  safraId: string;
  cultura: string | null;
  grupos: Grupo[];
  talhoes: Talhao[];
}

interface TalhaoTableRow {
  id: string;
  talhao_id: string;
  talhao_nome: string;
  area_ha?: number | null;
  grupo_nome?: string | null;
  grupo_cor?: string | null;
  escala_codigo?: string | null;
  escala_nome?: string | null;
  data_observacao?: string | null;
  diasDesdeObservacao: number;
  requerAtencao: boolean;
  monitorado: boolean;
  observacao?: string | null;
  totalHistorico: number;
  registros: FenologiaRegistro[];
}

function fmt(d: string) {
  try {
    return format(parseISO(d), "dd/MM/yyyy", { locale: ptBR });
  } catch {
    return d;
  }
}

function fmtRelativo(d: string) {
  try {
    const dias = differenceInDays(new Date(), parseISO(d));
    if (dias <= 0) return "Hoje";
    if (dias === 1) return "Ontem";
    return `há ${dias} dias`;
  } catch {
    return "";
  }
}

export function SafraFenologia({
  safraId,
  cultura,
  grupos = [],
  talhoes = [],
}: SafraFenologiaProps) {
  const queryClient = useQueryClient();
  const queryKey = ["fenologia", safraId];

  // View state
  const [viewMode, setViewMode] = useState<"cards" | "tabela">("cards");
  const [subViewTabela, setSubViewTabela] = useState<"talhoes" | "historico">("talhoes");
  const [searchTerm, setSearchTerm] = useState("");
  const [filtroStatus, setFiltroStatus] = useState<"todos" | "monitorados" | "atencao" | "sem_registro">("todos");
  const [filtroGrupo, setFiltroGrupo] = useState<string>("all");
  const [filtroEstagio, setFiltroEstagio] = useState<string | null>(null);

  // Modal de registro
  const [isOpen, setIsOpen] = useState(false);
  const [alvoTipo, setAlvoTipo] = useState<"talhao" | "grupo">("talhao");
  const [alvoId, setAlvoId] = useState<string>("");

  // Modal de histórico individual do talhão (usado na tabela)
  const [talhaoHistoricoModal, setTalhaoHistoricoModal] = useState<TalhaoTableRow | null>(null);

  // Expandir histórico por talhão nos cards
  const [historicoAberto, setHistoricoAberto] = useState<Record<string, boolean>>({});

  const toggleHistorico = (talhaoId: string) => {
    setHistoricoAberto((prev) => ({ ...prev, [talhaoId]: !prev[talhaoId] }));
  };

  const { data: registros = [], isLoading: loadingRegistros } = useQuery<FenologiaRegistro[]>({
    queryKey,
    queryFn: () => apiFetch(`/safras/${safraId}/fenologia`),
  });

  const { data: escalas = [], isLoading: loadingEscalas } = useQuery<Escala[]>({
    queryKey: ["fenologia-escalas", cultura],
    queryFn: () => apiFetch(`/fenologia/escalas?cultura=${encodeURIComponent(cultura ?? "")}`),
  });

  const mutation = useMutation({
    mutationFn: (data: { escala_id: string; data_observacao: string; observacao?: string }) => {
      const url =
        alvoTipo === "grupo"
          ? `/safras/${safraId}/grupos-talhoes/${alvoId}/fenologia`
          : `/safras/${safraId}/talhoes/${alvoId}/fenologia`;
      return apiFetch(url, { method: "POST", body: JSON.stringify(data) });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      toast.success(alvoTipo === "grupo" ? "Estágio registrado para o grupo com sucesso!" : "Estágio registrado com sucesso!");
      setIsOpen(false);
      reset();
    },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao registrar estágio"),
  });

  const { register, handleSubmit, control, reset } = useForm({
    defaultValues: {
      data_observacao: new Date().toISOString().split("T")[0],
      escala_id: "",
      observacao: "",
    },
  });

  const abrirModalParaTalhao = (talhaoId: string) => {
    setAlvoTipo("talhao");
    setAlvoId(talhaoId);
    setIsOpen(true);
  };

  // Mapeamento enriquecido dos talhões com seus respectivos registros
  const talhoesComStatus = useMemo(() => {
    return talhoes.map((t) => {
      const registrosDoTalhao = [...registros]
        .filter((r) => r.talhao_id === t.id)
        .sort((a, b) => new Date(a.data_observacao).getTime() - new Date(b.data_observacao).getTime());

      const ultimo = registrosDoTalhao[registrosDoTalhao.length - 1] || null;
      const grupoDoTalhao = grupos.find((g) => g.itens?.some((i) => i.talhao_id === t.id)) || null;

      let diasDesdeObservacao = 0;
      let requerAtencao = false;

      if (ultimo) {
        try {
          diasDesdeObservacao = differenceInDays(new Date(), parseISO(ultimo.data_observacao));
          requerAtencao = diasDesdeObservacao > 15;
        } catch {
          diasDesdeObservacao = 0;
        }
      }

      return {
        talhao: t,
        registros: registrosDoTalhao,
        ultimo,
        grupo: grupoDoTalhao,
        diasDesdeObservacao,
        requerAtencao,
        monitorado: !!ultimo,
      };
    });
  }, [talhoes, registros, grupos]);

  // Cálculos de KPIs / Resumo Geral
  const stats = useMemo(() => {
    const totalTalhoes = talhoesComStatus.length;
    const totalAreaHa = talhoes.reduce((acc, t) => acc + (t.area_ha || 0), 0);
    const monitorados = talhoesComStatus.filter((t) => t.monitorado).length;
    const requeremAtencao = talhoesComStatus.filter((t) => t.requerAtencao || !t.monitorado).length;
    const percentualMonitorado = totalTalhoes > 0 ? Math.round((monitorados / totalTalhoes) * 100) : 0;

    // Frequência de estágios atuais para achar o predominante
    const contagemPorEstagio: Record<string, { codigo: string; nome: string; count: number }> = {};
    talhoesComStatus.forEach((t) => {
      if (t.ultimo) {
        const key = t.ultimo.escala_codigo;
        if (!contagemPorEstagio[key]) {
          contagemPorEstagio[key] = {
            codigo: t.ultimo.escala_codigo,
            nome: t.ultimo.escala_nome,
            count: 0,
          };
        }
        contagemPorEstagio[key].count += 1;
      }
    });

    const maisFrequente = Object.values(contagemPorEstagio).sort((a, b) => b.count - a.count)[0] || null;

    return {
      totalTalhoes,
      totalAreaHa,
      monitorados,
      requeremAtencao,
      percentualMonitorado,
      predominante: maisFrequente,
      contagemPorEstagio,
    };
  }, [talhoesComStatus, talhoes]);

  // Filtros aplicados na lista de talhões (fonte da verdade tanto para Cards quanto para Tabela por Talhão)
  const talhoesFiltrados = useMemo(() => {
    return talhoesComStatus.filter((item) => {
      // Busca por nome
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const nomeMatch = item.talhao.nome.toLowerCase().includes(term);
        const grupoMatch = item.grupo?.nome.toLowerCase().includes(term);
        const codigoMatch = item.ultimo?.escala_codigo.toLowerCase().includes(term);
        const faseMatch = item.ultimo?.escala_nome.toLowerCase().includes(term);
        if (!nomeMatch && !grupoMatch && !codigoMatch && !faseMatch) return false;
      }

      // Filtro por grupo
      if (filtroGrupo !== "all") {
        if (filtroGrupo === "sem_grupo" && item.grupo) return false;
        if (filtroGrupo !== "sem_grupo" && item.grupo?.id !== filtroGrupo) return false;
      }

      // Filtro por status
      if (filtroStatus === "monitorados" && !item.monitorado) return false;
      if (filtroStatus === "sem_registro" && item.monitorado) return false;
      if (filtroStatus === "atencao" && !item.requerAtencao && item.monitorado) return false;

      // Filtro pelo pipeline de estágio
      if (filtroEstagio) {
        if (!item.ultimo || item.ultimo.escala_codigo !== filtroEstagio) return false;
      }

      return true;
    });
  }, [talhoesComStatus, searchTerm, filtroGrupo, filtroStatus, filtroEstagio]);

  // Linhas da tabela de talhões (situação atual de cada talhão - 1 linha por talhão, correspondência 1:1 com os cards)
  const talhoesTableData: TalhaoTableRow[] = useMemo(() => {
    return talhoesFiltrados.map((item) => ({
      id: item.talhao.id,
      talhao_id: item.talhao.id,
      talhao_nome: item.talhao.nome,
      area_ha: item.talhao.area_ha,
      grupo_nome: item.grupo?.nome,
      grupo_cor: item.grupo?.cor,
      escala_codigo: item.ultimo?.escala_codigo || null,
      escala_nome: item.ultimo?.escala_nome || null,
      data_observacao: item.ultimo?.data_observacao || null,
      diasDesdeObservacao: item.diasDesdeObservacao,
      requerAtencao: item.requerAtencao,
      monitorado: item.monitorado,
      observacao: item.ultimo?.observacao || null,
      totalHistorico: item.registros.length,
      registros: item.registros,
    }));
  }, [talhoesFiltrados]);

  // Colunas do DataTable na visualização de Talhões
  const talhoesColumns: ColumnDef<TalhaoTableRow>[] = [
    {
      id: "talhao",
      header: "Talhão",
      accessorKey: "talhao_nome",
      sortable: true,
      cell: (val: string, row) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5">
            <MapPin className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span className="font-semibold text-xs text-foreground">{val}</span>
          </div>
          {row.area_ha ? (
            <span className="text-[11px] text-muted-foreground pl-5 block">
              {row.area_ha.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha
            </span>
          ) : null}
        </div>
      ),
    },
    {
      id: "grupo",
      header: "Grupo",
      accessorKey: "grupo_nome",
      sortable: true,
      cell: (val: string | null | undefined, row) => (
        val ? (
          <div className="flex items-center gap-1.5">
            {row.grupo_cor && (
              <span className="size-2 rounded-full inline-block" style={{ backgroundColor: row.grupo_cor }} />
            )}
            <span className="text-xs font-medium text-foreground">{val}</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )
      ),
    },
    {
      id: "codigo",
      header: "Código (BBCH)",
      accessorKey: "escala_codigo",
      sortable: true,
      cell: (val: string | null | undefined) => (
        val ? (
          <Badge
            variant="outline"
            className="font-mono text-xs px-2 py-0.5 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10"
          >
            {val}
          </Badge>
        ) : (
          <Badge variant="outline" className="text-[10px] text-muted-foreground border-border">
            Sem registro
          </Badge>
        )
      ),
    },
    {
      id: "fase",
      header: "Estágio Atual",
      accessorKey: "escala_nome",
      sortable: true,
      cell: (val: string | null | undefined) => (
        val ? (
          <span className="text-xs font-medium text-foreground">{val}</span>
        ) : (
          <span className="text-xs text-muted-foreground italic">Sem acompanhamento</span>
        )
      ),
    },
    {
      id: "data_observacao",
      header: "Última Observação",
      accessorKey: "data_observacao",
      sortable: true,
      exportFormat: (val) => (val ? fmt(val) : "—"),
      cell: (val: string | null | undefined) => (
        val ? (
          <div className="space-y-0.5">
            <span className="text-xs font-medium text-foreground whitespace-nowrap block">
              {fmt(val)}
            </span>
            <span className="text-[11px] text-muted-foreground block">
              {fmtRelativo(val)}
            </span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )
      ),
    },
    {
      id: "situacao",
      header: "Situação",
      accessorFn: (row) => (
        !row.monitorado ? "Pendente" : row.requerAtencao ? "Requer visita (> 15 dias)" : "Atualizado"
      ),
      sortable: true,
      cell: (_, row) => (
        !row.monitorado ? (
          <Badge variant="outline" className="text-[10px] text-muted-foreground border-border">
            Sem registro
          </Badge>
        ) : row.requerAtencao ? (
          <Badge
            variant="outline"
            className="text-[10px] py-0 px-1.5 border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300 gap-1 font-medium whitespace-nowrap"
          >
            <AlertTriangle className="size-2.5" />
            &gt; 15 dias
          </Badge>
        ) : (
          <Badge
            variant="outline"
            className="text-[10px] py-0 px-1.5 border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 gap-1 font-medium whitespace-nowrap"
          >
            <CheckCircle2 className="size-2.5" />
            Atualizado
          </Badge>
        )
      ),
    },
    {
      id: "observacao",
      header: "Observações",
      accessorKey: "observacao",
      cell: (val: string | null | undefined) => (
        <span className="text-xs text-muted-foreground truncate max-w-[200px] block" title={val || undefined}>
          {val || "—"}
        </span>
      ),
    },
    {
      id: "acoes",
      header: "",
      isActionColumn: true,
      cell: (_, row) => (
        <div className="flex items-center gap-1.5 justify-end">
          {row.totalHistorico > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="rounded-sm h-7 text-xs text-muted-foreground hover:text-foreground gap-1 px-2"
              onClick={() => setTalhaoHistoricoModal(row)}
              title="Ver histórico de estágios deste talhão"
            >
              <Clock className="size-3" />
              Histórico ({row.totalHistorico})
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="rounded-sm h-7 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/5"
            onClick={() => abrirModalParaTalhao(row.talhao_id)}
          >
            <Plus className="size-3" />
            Registrar
          </Button>
        </div>
      ),
    },
  ];

  // Registros formatados para o DataTable da visão de histórico completo
  const registrosTableData = useMemo(() => {
    return registros.map((r) => {
      const talhao = talhoes.find((t) => t.id === r.talhao_id);
      const grupo = grupos.find((g) => g.itens?.some((i) => i.talhao_id === r.talhao_id));
      return {
        ...r,
        talhao_nome: talhao?.nome || "Talhão desconhecido",
        grupo_nome: grupo?.nome,
        grupo_cor: grupo?.cor,
      };
    });
  }, [registros, talhoes, grupos]);

  // Filtros aplicados no histórico completo quando essa sub-visão for ativada
  const registrosFiltrados = useMemo(() => {
    return registrosTableData.filter((r) => {
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const nomeMatch = r.talhao_nome.toLowerCase().includes(term);
        const grupoMatch = r.grupo_nome?.toLowerCase().includes(term);
        const codigoMatch = r.escala_codigo.toLowerCase().includes(term);
        const faseMatch = r.escala_nome.toLowerCase().includes(term);
        const obsMatch = r.observacao?.toLowerCase().includes(term);
        if (!nomeMatch && !grupoMatch && !codigoMatch && !faseMatch && !obsMatch) return false;
      }
      if (filtroGrupo !== "all") {
        const talhao = talhoesComStatus.find((t) => t.talhao.id === r.talhao_id);
        if (filtroGrupo === "sem_grupo" && talhao?.grupo) return false;
        if (filtroGrupo !== "sem_grupo" && talhao?.grupo?.id !== filtroGrupo) return false;
      }
      if (filtroEstagio) {
        if (r.escala_codigo !== filtroEstagio) return false;
      }
      return true;
    });
  }, [registrosTableData, searchTerm, filtroGrupo, filtroEstagio, talhoesComStatus]);

  // Colunas do DataTable na visualização de Histórico Completo
  const historicoColumns: ColumnDef<typeof registrosTableData[0]>[] = [
    {
      id: "data",
      header: "Data Observação",
      accessorKey: "data_observacao",
      sortable: true,
      exportFormat: (val) => fmt(val),
      cell: (val: string) => (
        <span className="font-medium whitespace-nowrap text-xs">
          {fmt(val)}
        </span>
      ),
    },
    {
      id: "talhao",
      header: "Talhão",
      accessorKey: "talhao_nome",
      sortable: true,
      filterable: true,
      cell: (val: string, row) => (
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-xs">{val}</span>
          {row.grupo_nome && (
            <Badge variant="outline" className="text-[10px] py-0 px-1 font-normal bg-muted">
              {row.grupo_nome}
            </Badge>
          )}
        </div>
      ),
    },
    {
      id: "codigo",
      header: "Código (BBCH)",
      accessorKey: "escala_codigo",
      sortable: true,
      cell: (val: string) => (
        <Badge
          variant="outline"
          className="font-mono text-xs px-2 py-0.5 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10"
        >
          {val}
        </Badge>
      ),
    },
    {
      id: "fase",
      header: "Estágio Fenológico",
      accessorKey: "escala_nome",
      sortable: true,
      cell: (val: string) => (
        <span className="text-xs font-medium text-foreground">{val}</span>
      ),
    },
    {
      id: "observacao",
      header: "Observações",
      accessorKey: "observacao",
      cell: (val: string | null) => (
        <span className="text-xs text-muted-foreground truncate max-w-[280px] block" title={val || undefined}>
          {val || "—"}
        </span>
      ),
    },
    {
      id: "acoes",
      header: "",
      isActionColumn: true,
      cell: (_, row) => (
        <Button
          variant="outline"
          size="sm"
          className="rounded-sm h-7 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/5"
          onClick={() => abrirModalParaTalhao(row.talhao_id)}
        >
          <Plus className="size-3" />
          Novo Registro
        </Button>
      ),
    },
  ];

  if (loadingRegistros || loadingEscalas) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-sm" />
          ))}
        </div>
        <Skeleton className="h-12 w-full rounded-sm" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-44 w-full rounded-sm" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. KPIs / RESUMO DA SAFRA */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <Card className="rounded-sm border shadow-xs bg-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Total de Talhões
              </p>
              <h3 className="text-2xl font-bold text-foreground tracking-tight">
                {stats.totalTalhoes}
              </h3>
              {stats.totalAreaHa > 0 && (
                <p className="text-[11px] text-muted-foreground">
                  {stats.totalAreaHa.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha totais
                </p>
              )}
            </div>
            <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center text-primary">
              <MapPin className="size-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-sm border shadow-xs bg-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Talhões Monitorados
              </p>
              <div className="flex items-baseline gap-2">
                <h3 className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tracking-tight">
                  {stats.monitorados}
                </h3>
                <span className="text-xs text-muted-foreground">
                  / {stats.totalTalhoes} ({stats.percentualMonitorado}%)
                </span>
              </div>
              <div className="w-full bg-muted h-1.5 rounded-full overflow-hidden mt-1 max-w-[130px]">
                <div
                  className="bg-emerald-600 dark:bg-emerald-500 h-full transition-all duration-300"
                  style={{ width: `${stats.percentualMonitorado}%` }}
                />
              </div>
            </div>
            <div className="size-10 rounded-sm bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="size-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-sm border shadow-xs bg-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1 max-w-[calc(100%-3rem)]">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Estágio Predominante
              </p>
              {stats.predominante ? (
                <div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="outline" className="font-mono text-xs px-1.5 py-0 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                      {stats.predominante.codigo}
                    </Badge>
                    <span className="text-sm font-bold text-foreground truncate">
                      {stats.predominante.nome}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {stats.predominante.count} {stats.predominante.count === 1 ? "talhão" : "talhões"} nesta fase
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Nenhuma fase registrada</p>
              )}
            </div>
            <div className="size-10 rounded-sm bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <Leaf className="size-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-sm border shadow-xs bg-card">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Requerem Atenção
              </p>
              <h3 className={cn(
                "text-2xl font-bold tracking-tight",
                stats.requeremAtencao > 0 ? "text-amber-600 dark:text-amber-400" : "text-foreground"
              )}>
                {stats.requeremAtencao}
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Sem registro ou &gt; 15 dias
              </p>
            </div>
            <div className={cn(
              "size-10 rounded-sm flex items-center justify-center",
              stats.requeremAtencao > 0 ? "bg-amber-500/10 text-amber-600 dark:text-amber-400" : "bg-muted text-muted-foreground"
            )}>
              <AlertTriangle className="size-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 2. PIPELINE DE ESTÁGIOS DA CULTURA */}
      {escalas.length > 0 && (
        <Card className="rounded-sm border shadow-xs bg-card overflow-hidden">
          <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-semibold text-foreground uppercase tracking-wide">
                Linha de Desenvolvimento da Cultura {cultura ? `(${cultura})` : ""}
              </span>
            </div>
            {filtroEstagio && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground hover:text-foreground gap-1"
                onClick={() => setFiltroEstagio(null)}
              >
                <X className="size-3" />
                Limpar filtro ({filtroEstagio})
              </Button>
            )}
          </div>
          <div className="p-3 overflow-x-auto scrollbar-thin">
            <div className="flex items-center gap-2 min-w-max pb-1">
              {escalas.map((esc) => {
                const count = stats.contagemPorEstagio[esc.codigo]?.count || 0;
                const isSelected = filtroEstagio === esc.codigo;
                return (
                  <button
                    key={esc.id}
                    type="button"
                    onClick={() => setFiltroEstagio(isSelected ? null : esc.codigo)}
                    className={cn(
                      "group flex flex-col items-start gap-1 p-2.5 rounded-sm border transition-all text-left min-w-[130px] max-w-[170px]",
                      isSelected
                        ? "border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500"
                        : count > 0
                        ? "border-emerald-500/40 bg-card hover:border-emerald-500 hover:bg-muted/40"
                        : "border-border/60 bg-muted/20 opacity-70 hover:opacity-100 hover:bg-muted/50"
                    )}
                  >
                    <div className="flex items-center justify-between w-full gap-2">
                      <span className="font-mono text-xs font-bold text-foreground">
                        {esc.codigo}
                      </span>
                      {count > 0 && (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-600 text-white">
                          {count}
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-medium text-muted-foreground line-clamp-1 group-hover:text-foreground">
                      {esc.nome}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* 3. TOOLBAR DE CONTROLES E FILTROS */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Busca e Filtros */}
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar talhão ou fase..."
              className="pl-8 h-8 text-xs rounded-sm"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            )}
          </div>

          {/* Filtro Status Tabs/Pills */}
          <div className="flex items-center border rounded-sm p-0.5 bg-muted/40 text-xs">
            <button
              type="button"
              onClick={() => setFiltroStatus("todos")}
              className={cn(
                "px-2.5 py-1 rounded-sm font-medium transition-colors",
                filtroStatus === "todos" ? "bg-background text-foreground shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Todos ({talhoesComStatus.length})
            </button>
            <button
              type="button"
              onClick={() => setFiltroStatus("monitorados")}
              className={cn(
                "px-2.5 py-1 rounded-sm font-medium transition-colors",
                filtroStatus === "monitorados" ? "bg-background text-foreground shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Monitorados ({stats.monitorados})
            </button>
            <button
              type="button"
              onClick={() => setFiltroStatus("atencao")}
              className={cn(
                "px-2.5 py-1 rounded-sm font-medium transition-colors",
                filtroStatus === "atencao" ? "bg-background text-amber-600 dark:text-amber-400 shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Atenção ({stats.requeremAtencao})
            </button>
          </div>

          {/* Filtro por Grupo */}
          {grupos.length > 0 && (
            <Select value={filtroGrupo} onValueChange={setFiltroGrupo}>
              <SelectTrigger className="h-8 text-xs rounded-sm w-[150px]">
                <SelectValue placeholder="Filtrar Grupo" />
              </SelectTrigger>
              <SelectContent className="rounded-sm">
                <SelectItem value="all" className="text-xs">Todos os Grupos</SelectItem>
                {grupos.map((g) => (
                  <SelectItem key={g.id} value={g.id} className="text-xs">
                    <span className="flex items-center gap-1.5">
                      {g.cor && <span className="size-2 rounded-full inline-block" style={{ backgroundColor: g.cor }} />}
                      {g.nome}
                    </span>
                  </SelectItem>
                ))}
                <SelectItem value="sem_grupo" className="text-xs">Sem Grupo</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Alternância de Modo (Cards / Tabela) & Ação Global */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center border rounded-sm p-0.5 bg-muted/40">
            <Button
              type="button"
              variant={viewMode === "cards" ? "outline" : "ghost"}
              size="sm"
              className={cn(
                "h-7 px-2.5 rounded-sm text-xs gap-1.5",
                viewMode === "cards" ? "bg-background shadow-xs font-semibold" : "border-transparent"
              )}
              onClick={() => setViewMode("cards")}
            >
              <LayoutGrid className="size-3.5" />
              Cards ({talhoesFiltrados.length})
            </Button>
            <Button
              type="button"
              variant={viewMode === "tabela" ? "outline" : "ghost"}
              size="sm"
              className={cn(
                "h-7 px-2.5 rounded-sm text-xs gap-1.5",
                viewMode === "tabela" ? "bg-background shadow-xs font-semibold" : "border-transparent"
              )}
              onClick={() => setViewMode("tabela")}
            >
              <TableProperties className="size-3.5" />
              Tabela ({talhoesFiltrados.length})
            </Button>
          </div>

          <Button
            size="sm"
            variant="outline"
            className="rounded-sm gap-1.5 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/10"
            onClick={() => {
              setAlvoTipo("talhao");
              setAlvoId(talhoes[0]?.id || "");
              setIsOpen(true);
            }}
          >
            <Plus className="size-3.5" />
            Registrar Estágio
          </Button>
        </div>
      </div>

      {/* 4. CONTEÚDO PRINCIPAL: CARDS OU TABELA */}
      {viewMode === "cards" ? (
        talhoesFiltrados.length === 0 ? (
          <Card className="rounded-sm border-dashed p-8 text-center bg-muted/10">
            <Leaf className="size-8 text-muted-foreground/50 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-foreground">Nenhum talhão encontrado</h4>
            <p className="text-xs text-muted-foreground mt-1">
              Tente ajustar os filtros ou a busca acima para encontrar os talhões da safra.
            </p>
            {(searchTerm || filtroStatus !== "todos" || filtroGrupo !== "all" || filtroEstagio) && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm mt-3 gap-1.5 text-xs"
                onClick={() => {
                  setSearchTerm("");
                  setFiltroStatus("todos");
                  setFiltroGrupo("all");
                  setFiltroEstagio(null);
                }}
              >
                <X className="size-3" />
                Limpar todos os filtros
              </Button>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {talhoesFiltrados.map(({ talhao, registros: hist, ultimo, grupo, requerAtencao }) => {
              const expandido = !!historicoAberto[talhao.id];
              return (
                <Card
                  key={talhao.id}
                  className={cn(
                    "rounded-sm border transition-all duration-200 shadow-xs flex flex-col justify-between overflow-hidden",
                    ultimo ? "border-l-[3px] border-l-emerald-500" : "border-l-[3px] border-l-muted-foreground/30"
                  )}
                >
                  <div className="p-4 space-y-3">
                    {/* Topo do Card */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                          <h4 className="font-semibold text-sm text-foreground">
                            {talhao.nome}
                          </h4>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground pl-5">
                          {talhao.area_ha ? (
                            <span>{talhao.area_ha.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha</span>
                          ) : null}
                          {grupo && (
                            <span className="flex items-center gap-1">
                              •
                              {grupo.cor && (
                                <span className="size-2 rounded-full" style={{ backgroundColor: grupo.cor }} />
                              )}
                              {grupo.nome}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Badge da Fase Atual */}
                      {ultimo ? (
                        <Badge
                          variant="outline"
                          className="font-mono text-xs px-2 py-0.5 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 shrink-0"
                        >
                          {ultimo.escala_codigo}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground border-border shrink-0">
                          Sem registro
                        </Badge>
                      )}
                    </div>

                    {/* Conteúdo / Status de Observação */}
                    {ultimo ? (
                      <div className="space-y-2 bg-muted/20 p-2.5 rounded-sm border border-border/40">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-foreground truncate pr-2">
                            {ultimo.escala_nome}
                          </span>
                          <span className="text-[11px] text-muted-foreground whitespace-nowrap">
                            {fmtRelativo(ultimo.data_observacao)}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/30">
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3" />
                            {fmt(ultimo.data_observacao)}
                          </span>
                          {requerAtencao && (
                            <Badge
                              variant="outline"
                              className="text-[10px] py-0 px-1.5 border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300 gap-1 font-medium"
                            >
                              <AlertTriangle className="size-2.5" />
                              &gt; 15 dias
                            </Badge>
                          )}
                        </div>

                        {ultimo.observacao && (
                          <p className="text-[11px] text-muted-foreground/90 italic line-clamp-2 pt-1 border-t border-border/20">
                            &quot;{ultimo.observacao}&quot;
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="bg-muted/15 p-3 rounded-sm border border-dashed border-border/60 text-center space-y-1">
                        <p className="text-xs text-muted-foreground">
                          Nenhuma fase registrada ainda
                        </p>
                        <p className="text-[11px] text-muted-foreground/70">
                          Acompanhe a emergência ou estágio inicial clicando abaixo.
                        </p>
                      </div>
                    )}

                    {/* Histórico linear expandido */}
                    {expandido && hist.length > 0 && (
                      <div className="pt-2 border-t space-y-2">
                        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                          Histórico de Estágios ({hist.length})
                        </p>
                        <div className="relative pl-4 space-y-3 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-border/60">
                          {[...hist].reverse().map((reg) => (
                            <div key={reg.id} className="relative text-xs space-y-0.5">
                              <span className="absolute -left-[14px] top-1.5 size-2 rounded-full bg-emerald-600 ring-2 ring-background" />
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-foreground">
                                  {reg.escala_codigo} — {reg.escala_nome}
                                </span>
                                <span className="text-[10px] text-muted-foreground">
                                  {fmt(reg.data_observacao)}
                                </span>
                              </div>
                              {reg.observacao && (
                                <p className="text-[11px] text-muted-foreground italic">
                                  {reg.observacao}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Ações do Card */}
                  <div className="p-3 bg-muted/30 border-t flex items-center justify-between gap-2">
                    {hist.length > 0 ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="rounded-sm h-7 text-xs text-muted-foreground hover:text-foreground gap-1 px-2"
                        onClick={() => toggleHistorico(talhao.id)}
                      >
                        <Clock className="size-3" />
                        Histórico ({hist.length})
                        {expandido ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
                      </Button>
                    ) : (
                      <span className="text-[11px] text-muted-foreground px-2">Sem histórico</span>
                    )}

                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-sm h-7 text-xs gap-1 border-primary/30 text-primary hover:bg-primary/5"
                      onClick={() => abrirModalParaTalhao(talhao.id)}
                    >
                      <Plus className="size-3" />
                      Registrar
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )
      ) : (
        /* VISÃO EM TABELA */
        <Card className="rounded-sm border shadow-xs bg-card p-4 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground uppercase tracking-wide">
                Exibição:
              </span>
              <div className="flex items-center border rounded-sm p-0.5 bg-muted/40 text-xs">
                <button
                  type="button"
                  onClick={() => setSubViewTabela("talhoes")}
                  className={cn(
                    "px-2.5 py-1 rounded-sm font-medium transition-colors",
                    subViewTabela === "talhoes" ? "bg-background text-foreground shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  Situação por Talhão ({talhoesFiltrados.length})
                </button>
                <button
                  type="button"
                  onClick={() => setSubViewTabela("historico")}
                  className={cn(
                    "px-2.5 py-1 rounded-sm font-medium transition-colors",
                    subViewTabela === "historico" ? "bg-background text-foreground shadow-xs font-semibold" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  Todos os Registros Históricos ({registrosFiltrados.length})
                </button>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {subViewTabela === "talhoes"
                ? `Mostrando os ${talhoesFiltrados.length} talhões da safra e seus estágios atuais (mesma lista dos cards)`
                : `Mostrando todas as ${registrosFiltrados.length} observações já registradas nesta safra`}
            </p>
          </div>

          {subViewTabela === "talhoes" ? (
            <DataTable
              data={talhoesTableData}
              columns={talhoesColumns}
              searchable={false}
              exportable
              exportFileName={`fenologia_talhoes_safra_${safraId}`}
              emptyMessage="Nenhum talhão encontrado para os filtros selecionados."
            />
          ) : (
            <DataTable
              data={registrosFiltrados}
              columns={historicoColumns}
              searchable={false}
              exportable
              exportFileName={`fenologia_historico_safra_${safraId}`}
              emptyMessage="Nenhum registro histórico encontrado para os filtros selecionados."
            />
          )}
        </Card>
      )}

      {/* 5. MODAL DE HISTÓRICO COMPLETO DO TALHÃO (ACESSADO PELA TABELA) */}
      <Dialog open={!!talhaoHistoricoModal} onOpenChange={(open) => !open && setTalhaoHistoricoModal(null)}>
        <DialogContent className="sm:max-w-[480px] p-0 gap-0 rounded-sm">
          <DialogHeader className="px-6 py-4 border-b">
            <div className="flex items-center gap-2">
              <Clock className="size-4 text-emerald-600 dark:text-emerald-400" />
              <DialogTitle className="text-base font-semibold">
                Histórico Fenológico — {talhaoHistoricoModal?.talhao_nome}
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground">
              {talhaoHistoricoModal?.totalHistorico} {talhaoHistoricoModal?.totalHistorico === 1 ? "registro observado" : "registros observados"} nesta safra.
            </DialogDescription>
          </DialogHeader>

          <DialogBody className="p-6 max-h-[60vh] overflow-y-auto">
            {talhaoHistoricoModal && talhaoHistoricoModal.registros.length > 0 ? (
              <div className="relative pl-4 space-y-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-border/60">
                {[...talhaoHistoricoModal.registros].reverse().map((reg) => (
                  <div key={reg.id} className="relative text-xs space-y-1">
                    <span className="absolute -left-[14px] top-1.5 size-2 rounded-full bg-emerald-600 ring-2 ring-background" />
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="font-mono text-[11px] px-1.5 py-0 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 bg-emerald-500/10">
                          {reg.escala_codigo}
                        </Badge>
                        <span className="font-semibold text-foreground">
                          {reg.escala_nome}
                        </span>
                      </div>
                      <span className="text-[11px] text-muted-foreground whitespace-nowrap">
                        {fmt(reg.data_observacao)}
                      </span>
                    </div>
                    {reg.observacao && (
                      <p className="text-[11px] text-muted-foreground italic pl-0.5">
                        &quot;{reg.observacao}&quot;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground text-center py-4">
                Nenhum registro fenológico encontrado para este talhão.
              </p>
            )}
          </DialogBody>

          <DialogFooter className="px-6 py-3 border-t bg-muted/50 flex items-center justify-end">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm gap-1.5"
              onClick={() => setTalhaoHistoricoModal(null)}
            >
              <X className="size-3.5" />
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 6. MODAL DE REGISTRO DE ESTÁGIO FENOLÓGICO */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[480px] p-0 gap-0 rounded-sm">
          <form onSubmit={handleSubmit((d) => mutation.mutate(d))}>
            <DialogHeader className="px-6 py-4 border-b">
              <div className="flex items-center gap-2">
                <Leaf className="size-4 text-emerald-600 dark:text-emerald-400" />
                <DialogTitle className="text-base font-semibold">
                  Registrar Estágio Fenológico
                </DialogTitle>
              </div>
              <DialogDescription className="text-xs text-muted-foreground">
                Informe o estágio de desenvolvimento observado em campo.
              </DialogDescription>
            </DialogHeader>

            <DialogBody className="p-6 space-y-4">
              {/* Alvo: Talhão Individual ou Grupo (Lote) */}
              {grupos.length > 0 && (
                <div className="space-y-1.5">
                  <Label className="text-xs">Aplicar observação em</Label>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant={alvoTipo === "talhao" ? "default" : "outline"}
                      className="flex-1 rounded-sm text-xs gap-1.5"
                      onClick={() => {
                        setAlvoTipo("talhao");
                        setAlvoId(talhoes[0]?.id || "");
                      }}
                    >
                      <MapPin className="size-3.5" />
                      Por Talhão
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={alvoTipo === "grupo" ? "default" : "outline"}
                      className="flex-1 rounded-sm text-xs gap-1.5"
                      onClick={() => {
                        setAlvoTipo("grupo");
                        setAlvoId(grupos[0]?.id || "");
                      }}
                    >
                      <Layers className="size-3.5" />
                      Por Grupo ({grupos.length})
                    </Button>
                  </div>
                </div>
              )}

              {/* Seletor de Talhão ou Grupo */}
              <div className="space-y-1.5">
                <Label className="text-xs">
                  {alvoTipo === "grupo" ? "Grupo de Talhões *" : "Talhão *"}
                </Label>
                <Select value={alvoId} onValueChange={setAlvoId}>
                  <SelectTrigger className="h-8 text-xs rounded-sm">
                    <SelectValue
                      placeholder={
                        alvoTipo === "talhao"
                          ? talhoes.find((t) => t.id === alvoId)?.nome || "Selecione o talhão..."
                          : grupos.find((g) => g.id === alvoId)?.nome || "Selecione o grupo..."
                      }
                    />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {alvoTipo === "talhao"
                      ? talhoes.map((t) => (
                          <SelectItem key={t.id} value={t.id} className="text-xs">
                            {t.nome} {t.area_ha ? `(${t.area_ha} ha)` : ""}
                          </SelectItem>
                        ))
                      : grupos.map((g) => (
                          <SelectItem key={g.id} value={g.id} className="text-xs">
                            <span className="flex items-center gap-2">
                              {g.cor && (
                                <span
                                  className="size-2 rounded-full inline-block"
                                  style={{ backgroundColor: g.cor }}
                                />
                              )}
                              {g.nome} ({g.itens?.length || 0} talhões)
                            </span>
                          </SelectItem>
                        ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Estágio (Escala BBCH da cultura) */}
              <div className="space-y-1.5">
                <Label className="text-xs">Estágio Fenológico (Escala BBCH) *</Label>
                <Controller
                  name="escala_id"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue
                          placeholder={(() => {
                            const esc = escalas.find((e) => e.id === field.value);
                            return esc ? `${esc.codigo} — ${esc.nome}` : "Selecione o estágio...";
                          })()}
                        />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm max-h-60">
                        {escalas.map((e) => (
                          <SelectItem key={e.id} value={e.id} className="text-xs">
                            <span className="font-mono font-bold text-emerald-700 dark:text-emerald-300 mr-2">
                              {e.codigo}
                            </span>
                            {e.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              {/* Data da Observação */}
              <div className="space-y-1.5">
                <Label className="text-xs">Data da Observação em Campo *</Label>
                <Input
                  type="date"
                  className="h-8 text-xs rounded-sm"
                  {...register("data_observacao", { required: true })}
                />
              </div>

              {/* Observações de Campo */}
              <div className="space-y-1.5">
                <Label className="text-xs">Anotações e Condições Foliares (Opcional)</Label>
                <Textarea
                  placeholder="Ex: 85% das plantas com botão floral visível, boa uniformidade, sem estresse hídrico..."
                  rows={3}
                  className="text-xs rounded-sm resize-none"
                  {...register("observacao")}
                />
              </div>
            </DialogBody>

            <DialogFooter className="px-6 py-3 border-t bg-muted/50 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                type="button"
                className="rounded-sm gap-1.5"
                onClick={() => setIsOpen(false)}
              >
                <X className="size-3.5" />
                Cancelar
              </Button>
              <Button
                variant="outline"
                size="sm"
                type="submit"
                disabled={mutation.isPending || !alvoId}
                className="rounded-sm gap-1.5 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/10 font-semibold"
              >
                <Check className="size-3.5" />
                {mutation.isPending ? "Salvando..." : "Salvar Registro"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
