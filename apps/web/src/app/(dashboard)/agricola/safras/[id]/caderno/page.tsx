"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Plus, Download, BookOpen, Calendar, Camera, PenTool, ClipboardList, HardHat, ListTodo, Lock } from "lucide-react";
import { CadernoTimeline, type TimelineItem } from "@/components/agricola/caderno/CadernoTimeline";
import { EntradaDrawer } from "@/components/agricola/caderno/EntradaDrawer";
import { NovaEntradaForm } from "@/components/agricola/caderno/NovaEntradaForm";
import { DeleteEntradaDialog } from "@/components/agricola/caderno/DeleteEntradaDialog";
import { AssinarRTDialog } from "@/components/agricola/caderno/AssinarRTDialog";
import { VisitaTecnicaForm } from "@/components/agricola/caderno/VisitaTecnicaForm";
import { EPIEntregaForm } from "@/components/agricola/caderno/EPIEntregaForm";
import Link from "next/link";
import { useHasTier } from "@/hooks/use-has-tier";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";
import { getSafraLabel } from "@/lib/safra-label";

interface Safra {
  id: string;
  cultura: string | null;
  ano_safra: string;
  status: string;
}

interface SafraTalhao {
  id: string;
  safra_id: string;
  area_id: string;
  principal: boolean;
  area_ha: number | null;
}

interface AreaRural {
  id: string;
  nome: string;
  codigo: string | null;
  unidade_produtiva_id: string;
}

interface CadernoExportacao {
  id: string;
  url_pdf: string;
  data_geracao: string;
  modo_exportacao: string;
  hash_documental?: string | null;
  assinatura_hash?: string | null;
  assinado_em?: string | null;
  responsavel_tecnico_nome?: string | null;
  assinado_por?: string;
  crea_rt?: string;
}

const TIPOS_FILTRO = [
  { value: "", label: "Todos os tipos" },
  { value: "OPERACAO_AUTO", label: "Operações" },
  { value: "MONITORAMENTO", label: "Monitoramento" },
  { value: "VISITA_TECNICA", label: "Visitas Técnicas" },
  { value: "EPI_ENTREGA", label: "Entrega EPI" },
  { value: "OBSERVACAO", label: "Observações" },
  { value: "CLIMA", label: "Clima" },
  { value: "SOLO", label: "Solo" },
];

export default function CadernoCampoPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);
  const hasEnterpriseTier = useHasTier("ENTERPRISE");
  useMonetizationPromptTracking(!hasEnterpriseTier, {
    feature: "agricola.caderno.safra",
    surface: "agricola.caderno.safra.page",
    requiredTier: "ENTERPRISE",
    ctaLabel: "Ver planos",
  });

  const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);
  const [isNovaEntradaOpen, setIsNovaEntradaOpen] = useState(false);
  const [deleteEntradaId, setDeleteEntradaId] = useState<string | null>(null);
  const [assinarOpen, setAssinarOpen] = useState(false);
  const [visitaOpen, setVisitaOpen] = useState(false);
  const [epiOpen, setEpiOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("timeline");
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroTalhao, setFiltroTalhao] = useState("");
  const [filtroDataInicio, setFiltroDataInicio] = useState("");
  const [filtroDataFim, setFiltroDataFim] = useState("");
  const canManageStatus = Boolean(user?.is_superuser || (user?.tenant_role && ["owner", "admin", "gerente", "agronomo"].includes(user.tenant_role)));

  const { data: safra } = useQuery<Safra>({
    queryKey: ["safra", id],
    queryFn: () => apiFetch(`/safras/${id}`),
  });
  const safraLabel = safra ? getSafraLabel(safra) : "";

  // Talhões vinculados à safra (mapping table)
  const { data: talhoesSafra = [] } = useQuery<SafraTalhao[]>({
    queryKey: ["safra-talhoes", id],
    queryFn: () => apiFetch(`/safras/${id}/talhoes`),
  });

  // Todas as áreas rurais tipo TALHAO (para resolver nomes)
  const { data: todasAreas = [] } = useQuery<AreaRural[]>({
    queryKey: ["areas-rurais-talhoes-caderno"],
    queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
  });

  // Join: talhões da safra com nomes das áreas
  const talhoes = talhoesSafra
    .map((ts) => {
      const area = todasAreas.find((a) => a.id === ts.area_id);
      return area
        ? {
            id: area.id,
            nome: area.nome,
            codigo: area.codigo,
            area_ha: ts.area_ha,
            principal: ts.principal,
            unidade_produtiva_id: area.unidade_produtiva_id,
          }
        : null;
    })
    .filter(Boolean) as { id: string; nome: string; codigo: string | null; area_ha: number | null; principal: boolean; unidade_produtiva_id?: string }[];

  const params_timeline = new URLSearchParams();
  if (filtroTipo) params_timeline.set("tipo", filtroTipo);
  if (filtroTalhao) params_timeline.set("talhao_id", filtroTalhao);
  if (filtroDataInicio) params_timeline.set("data_inicio", filtroDataInicio);
  if (filtroDataFim) params_timeline.set("data_fim", filtroDataFim);

  const { data: timeline = [], isLoading } = useQuery<TimelineItem[]>({
    queryKey: ["caderno-timeline", id, filtroTipo, filtroTalhao, filtroDataInicio, filtroDataFim],
    queryFn: () => apiFetch(`/caderno/safra/${id}/timeline?${params_timeline.toString()}`),
  });

  const criarEntradaMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiFetch("/caderno/entradas", {
      method: "POST",
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      toast.success("Registro adicionado ao caderno!");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao registrar entrada"),
  });

  const deletarMutation = useMutation({
    mutationFn: ({ entradaId, motivo }: { entradaId: string; motivo: string }) =>
      apiFetch(`/caderno/entradas/${entradaId}`, {
        method: "DELETE",
        body: JSON.stringify({ motivo_exclusao: motivo }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      setSelectedItem(null);
      setDeleteEntradaId(null);
      toast.success("Registro excluído (mantido em auditoria)");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao excluir registro"),
  });

  const atualizarStatusMutation = useMutation({
    mutationFn: ({ entradaId, statusEvento, justificativa }: { entradaId: string; statusEvento: string; justificativa?: string }) =>
      apiFetch(`/caderno/${entradaId}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status_evento: statusEvento,
          justificativa,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      setSelectedItem(null);
      toast.success("Status atualizado com sucesso");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao atualizar status"),
  });

  const retificarMutation = useMutation({
    mutationFn: ({ entradaId, motivo, dadosCorrigidos }: { entradaId: string; motivo: string; dadosCorrigidos?: Record<string, unknown> }) =>
      apiFetch(`/caderno/entradas/${entradaId}/reprocessar`, {
        method: "POST",
        body: JSON.stringify({
          motivo,
          dados_corrigidos: dadosCorrigidos ?? {},
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      setSelectedItem(null);
      toast.success("Evento retificado com sucesso");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao retificar registro"),
  });

  const exportarMutation = useMutation({
    mutationFn: ({ modo }: { modo: "OFICIAL" | "AUDITORIA" }) => {
      if (!hasEnterpriseTier) {
        trackMonetizationEvent("monetization_blocked", {
          feature: "agricola.caderno.exportar",
          surface: "agricola.caderno.safra.page",
          requiredTier: "ENTERPRISE",
          ctaLabel: "Exportar PDF",
          reason: "mutation_guard",
        });
        throw new Error("Recurso disponível no plano ENTERPRISE.");
      }
      return apiFetch("/caderno/exportar", {
        method: "POST",
        body: JSON.stringify({
          safra_id: id,
          modo_exportacao: modo,
          modelo_certificacao: "INTERNO",
        }),
      });
    },
    onSuccess: (data: { id?: string }) => {
      toast.success("Caderno exportado! PDF disponível.");
      if (data.id) {
        window.open(`/api/v1/caderno/exportacoes/${data.id}/download`, "_blank");
      }
      queryClient.invalidateQueries({ queryKey: ["caderno-exportacoes", id] });
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao exportar"),
  });

  const assinarMutation = useMutation({
    mutationFn: ({ nome, crea, creaValidade }: { nome: string; crea: string; creaValidade?: string }) => {
      if (!hasEnterpriseTier) {
        trackMonetizationEvent("monetization_blocked", {
          feature: "agricola.caderno.assinar",
          surface: "agricola.caderno.safra.page",
          requiredTier: "ENTERPRISE",
          ctaLabel: "Assinar",
          reason: "mutation_guard",
        });
        throw new Error("Recurso disponível no plano ENTERPRISE.");
      }
      // Busca a última exportação para assinar
      return apiFetch(`/caderno/exportacoes/assinar-ultima`, {
        method: "POST",
        body: JSON.stringify({
          safra_id: id,
          responsavel_tecnico_id: user?.id,
          responsavel_tecnico_nome: nome || user?.name || user?.username,
          crea_rt: crea,
          crea_validade: creaValidade || undefined,
        }),
      });
    },
    onSuccess: () => {
      toast.success("Caderno assinado com sucesso!");
      setAssinarOpen(false);
      queryClient.invalidateQueries({ queryKey: ["caderno-exportacoes", id] });
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao assinar"),
  });

  const handleSubmitVisita = async (data: Parameters<typeof visitaMutation.mutateAsync>[0]): Promise<void> => {
    await visitaMutation.mutateAsync(data);
  };

  const handleSubmitEPI = async (data: Parameters<typeof epiMutation.mutateAsync>[0]): Promise<void> => {
    await epiMutation.mutateAsync(data);
  };

  const handleSubmitNovaEntrada = async (data: Parameters<typeof criarEntradaMutation.mutateAsync>[0]): Promise<void> => {
    await criarEntradaMutation.mutateAsync(data);
  };

  const handleUpdateStatus = async (entradaId: string, statusEvento: string, justificativa?: string): Promise<void> => {
    await atualizarStatusMutation.mutateAsync({ entradaId, statusEvento, justificativa });
  };

  const handleRetificar = async (entradaId: string, motivo: string, dadosCorrigidos?: Record<string, unknown>): Promise<void> => {
    await retificarMutation.mutateAsync({ entradaId, motivo, dadosCorrigidos });
  };

  // Busca exportações existentes
  const { data: exportacoes = [] } = useQuery<CadernoExportacao[]>({
    queryKey: ["caderno-exportacoes", id],
    queryFn: () => apiFetch(`/caderno/exportacoes/safra/${id}`),
    enabled: hasEnterpriseTier,
  });

  // Mutations para Visita Técnica e EPI
  const visitaMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiFetch("/caderno/visitas", {
      method: "POST",
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      toast.success("Visita técnica registrada!");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao registrar visita"),
  });

  const epiMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => apiFetch("/caderno/epis", {
      method: "POST",
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caderno-timeline", id] });
      toast.success("Entrega de EPI registrada!");
    },
    onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao registrar entrega de EPI"),
  });

  const totalRegistros = timeline.length;
  const comFotos = timeline.filter(i => i.fotos_count > 0).length;
  const alertas = timeline.filter(i => i.nivel_severidade === "ALTO" || i.nivel_severidade === "CRITICO").length;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={safraLabel ? `Caderno de Campo — ${safraLabel}` : "Caderno de Campo"}
        icon={<BookOpen className="text-slate-600" size={22} />}
        description={safraLabel}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAssinarOpen(true)}
              disabled={!hasEnterpriseTier || (exportacoes.length === 0 && !exportarMutation.isPending)}
            >
              <PenTool className="size-3.5 mr-1.5" />
              Assinar
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportarMutation.mutate({ modo: "OFICIAL" })}
              disabled={!hasEnterpriseTier || exportarMutation.isPending}
            >
              <Download className="size-3.5 mr-1.5" />
              Exportar oficial
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportarMutation.mutate({ modo: "AUDITORIA" })}
              disabled={!hasEnterpriseTier || exportarMutation.isPending}
            >
              <Download className="size-3.5 mr-1.5" />
              Exportar auditoria
            </Button>
            <Button size="sm" onClick={() => setIsNovaEntradaOpen(true)}>
              <Plus className="size-3.5 mr-1.5" />
              Novo Registro
            </Button>
          </div>
        }
      />

      {!hasEnterpriseTier && (
        <Alert className="rounded-sm">
          <Lock className="size-4" />
          <AlertTitle>Exportação e assinatura do caderno disponíveis no ENTERPRISE</AlertTitle>
          <AlertDescription className="space-y-3">
              <p>O registro operacional permanece liberado. Exportar o PDF oficial/auditoria e assinar a última versão exigem tier ENTERPRISE.</p>
              <Button
                asChild
                size="sm"
                className="rounded-sm"
                onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                  feature: "agricola.caderno.safra",
                  surface: "agricola.caderno.safra.page",
                  requiredTier: "ENTERPRISE",
                  ctaLabel: "Ver planos",
                })}
              >
              <Link href="/dashboard/settings/billing">Ver planos</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="shadow-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <BookOpen className="size-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Total Registros</p>
              <p className="font-bold text-lg">{totalRegistros}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <Camera className="size-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Com Fotos</p>
              <p className="font-bold text-lg">{comFotos}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm">
          <CardContent className="p-4 flex items-center gap-3">
            <Calendar className="size-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Alertas</p>
              <p className="font-bold text-lg">
                {alertas > 0
                  ? <Badge variant="destructive" className="text-sm">{alertas}</Badge>
                  : 0
                }
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="timeline" className="gap-1.5">
            <ListTodo className="size-3.5" />
            <span className="hidden sm:inline">Timeline</span>
          </TabsTrigger>
          <TabsTrigger value="visitas" className="gap-1.5">
            <ClipboardList className="size-3.5" />
            <span className="hidden sm:inline">Visitas</span>
          </TabsTrigger>
          <TabsTrigger value="epis" className="gap-1.5">
            <HardHat className="size-3.5" />
            <span className="hidden sm:inline">EPIs</span>
          </TabsTrigger>
          <TabsTrigger value="exportacoes" className="gap-1.5">
            <Download className="size-3.5" />
            <span className="hidden sm:inline">Exportações</span>
          </TabsTrigger>
        </TabsList>

        {/* ── Tab: Timeline ── */}
        <TabsContent value="timeline" className="space-y-4">
          {/* Filtros */}
          <Card className="shadow-sm">
            <CardContent className="p-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <Select value={filtroTipo} onValueChange={setFiltroTipo}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    {TIPOS_FILTRO.map(t => (
                      <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filtroTalhao} onValueChange={setFiltroTalhao}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Talhão" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos os talhões</SelectItem>
                    {talhoes.map((t) => (
                      <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Input
                  type="date"
                  className="h-9"
                  value={filtroDataInicio}
                  onChange={e => setFiltroDataInicio(e.target.value)}
                />

                <Input
                  type="date"
                  className="h-9"
                  value={filtroDataFim}
                  onChange={e => setFiltroDataFim(e.target.value)}
                />

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9"
                  onClick={() => {
                    setFiltroTipo("");
                    setFiltroTalhao("");
                    setFiltroDataInicio("");
                    setFiltroDataFim("");
                  }}
                >
                  Limpar filtros
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card className="shadow-sm">
            <CardContent className="p-6">
              <CadernoTimeline
                items={timeline}
                isLoading={isLoading}
                onSelect={setSelectedItem}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Tab: Visitas Técnicas ── */}
        <TabsContent value="visitas" className="space-y-4">
          <Card className="shadow-sm">
            <CardContent className="p-6 flex flex-col items-center justify-center gap-4 min-h-[200px]">
              <ClipboardList className="size-10 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">Visitas Técnicas</p>
                <p className="text-sm text-muted-foreground">Registre visitas do responsável técnico</p>
              </div>
              <Button onClick={() => setVisitaOpen(true)}>
                <Plus className="size-3.5 mr-1.5" />
                Registrar Visita
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Tab: EPIs ── */}
        <TabsContent value="epis" className="space-y-4">
          <Card className="shadow-sm">
            <CardContent className="p-6 flex flex-col items-center justify-center gap-4 min-h-[200px]">
              <HardHat className="size-10 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">Entregas de EPI</p>
                <p className="text-sm text-muted-foreground">Registre entregas de equipamentos de proteção</p>
              </div>
              <Button onClick={() => setEpiOpen(true)}>
                <Plus className="size-3.5 mr-1.5" />
                Registrar Entrega
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Tab: Exportações ── */}
        <TabsContent value="exportacoes" className="space-y-4">
          {exportacoes.length > 0 ? (
            <Card className="shadow-sm">
              <CardContent className="p-4">
                <h3 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                  <PenTool className="size-3.5" />
                  Histórico de Exportações
                </h3>
                <div className="space-y-1.5">
                  {exportacoes.map((exp) => (
                    <div key={exp.id} className="flex items-center justify-between text-sm py-1.5 border-b last:border-0">
                      <div className="flex items-center gap-2">
                        <Badge variant={exp.assinado_em ? "default" : "secondary"} className="text-xs">
                          {exp.assinado_em ? "Assinado" : "Pendente"}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {exp.modo_exportacao}
                        </Badge>
                        <span className="text-muted-foreground">
                          {new Date(exp.data_geracao).toLocaleDateString("pt-BR")}
                        </span>
                        {(exp.responsavel_tecnico_nome || exp.assinado_por) && (
                          <span className="text-xs text-muted-foreground">
                            — {exp.responsavel_tecnico_nome || exp.assinado_por} {exp.crea_rt ? `(CREA ${exp.crea_rt})` : ""}
                          </span>
                        )}
                        {exp.hash_documental && (
                          <span className="text-[10px] text-muted-foreground font-mono">
                            #{exp.hash_documental.slice(0, 12)}
                          </span>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs"
                        onClick={() => window.open(`/api/v1/caderno/exportacoes/${exp.id}/download`, "_blank")}
                      >
                        <Download className="size-3 mr-1" />
                        PDF
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="shadow-sm">
              <CardContent className="p-6 flex flex-col items-center justify-center gap-4 min-h-[200px]">
                <Download className="size-10 text-muted-foreground" />
                <div className="text-center">
                  <p className="font-medium">Nenhuma exportação</p>
                  <p className="text-sm text-muted-foreground">Exporte o caderno em PDF para auditoria</p>
                </div>
                <Button onClick={() => exportarMutation.mutate({ modo: "OFICIAL" })} disabled={exportarMutation.isPending}>
                  <Download className="size-3.5 mr-1.5" />
                  Exportar oficial
                </Button>
                <Button variant="outline" onClick={() => exportarMutation.mutate({ modo: "AUDITORIA" })} disabled={exportarMutation.isPending}>
                  <Download className="size-3.5 mr-1.5" />
                  Exportar auditoria
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Drawer de detalhe */}
      <EntradaDrawer
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onDelete={(entradaId) => setDeleteEntradaId(entradaId)}
        canManageStatus={canManageStatus}
        onUpdateStatus={handleUpdateStatus}
        onRetificar={handleRetificar}
      />

      {/* Dialog de exclusão */}
      <DeleteEntradaDialog
        open={!!deleteEntradaId}
        onClose={() => setDeleteEntradaId(null)}
        onConfirm={(motivo) => {
          if (deleteEntradaId) {
            deletarMutation.mutate({ entradaId: deleteEntradaId, motivo });
          }
        }}
        isPending={deletarMutation.isPending}
      />

      {/* Dialog de assinatura RT */}
      <AssinarRTDialog
        open={assinarOpen}
        onClose={() => setAssinarOpen(false)}
        onConfirm={(nome, crea, creaValidade) => assinarMutation.mutate({ nome, crea, creaValidade })}
        isPending={assinarMutation.isPending}
      />

      {/* Form de Visita Técnica */}
      <VisitaTecnicaForm
        open={visitaOpen}
        onClose={() => setVisitaOpen(false)}
        safraId={id}
        talhoes={talhoes}
        onSubmit={handleSubmitVisita}
        isLoading={visitaMutation.isPending}
      />

      {/* Form de Entrega de EPI */}
      <EPIEntregaForm
        open={epiOpen}
        onClose={() => setEpiOpen(false)}
        onSubmit={handleSubmitEPI}
        isLoading={epiMutation.isPending}
      />

      {/* Form nova entrada */}
      <NovaEntradaForm
        open={isNovaEntradaOpen}
        onClose={() => setIsNovaEntradaOpen(false)}
        safraId={id}
        talhoes={talhoes}
        talhaoIdSelecionado={filtroTalhao}
        onSubmit={handleSubmitNovaEntrada}
        isLoading={criarEntradaMutation.isPending}
      />
    </div>
  );
}
