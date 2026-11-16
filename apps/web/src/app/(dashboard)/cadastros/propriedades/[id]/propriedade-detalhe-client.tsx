"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { toast } from "sonner";
import { Map as MapLibreMap, NavigationControl, Source, Layer, MapRef } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import * as turf from "@turf/turf";
import {
  ArrowLeft, Map as MapIcon, Building2, Plus, Trash2, MapPin, Layers,
  Ruler, MoreVertical, PowerOff, Power, Trees, Sprout, Wheat, FolderTree, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetFooter } from "@/components/ui/sheet";
import { AreaTree, AREA_LABELS } from "@/components/shared/area-tree";
import { AREA_HIERARQUIA } from "@farm/zod-schemas";
import type { AreaRuralTree } from "@farm/zod-schemas";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EstruturaHierarquia } from "@/components/propriedade";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MapVisualizationToggle } from "@/components/shared/map-visualization-toggle";
import { ImoveisVinculadosCard } from "@/components/propriedade/imoveis-vinculados-card";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UnidadeProdutiva {
  id: string;
  nome: string;
  cpf_cnpj?: string;
  inscricao_estadual?: string;
  uf?: string;
  municipio?: string;
  area_total_ha?: string;
  area_total_calculada_ha?: string;
  area_aproveitavel_ha?: string;
  area_app_ha?: string;
  area_rl_ha?: string;
  coordenadas_sede?: string;
  geometria?: Record<string, unknown> | null;
  ativo: boolean;
  territorio?: any;
}

type Fazenda = UnidadeProdutiva;

interface AreaRural {
  id: string;
  tipo: string;
  nome: string;
  codigo?: string;
  parent_id?: string | null;
  area_hectares?: number;
  area_hectares_manual?: number;
  geometria?: any | null;
  tipo_solo_id?: string | null;
  irrigado: boolean;
  tipo_irrigacao_id?: string | null;
  dados_extras?: Record<string, any>;
  descricao?: string | null;
  ativo: boolean;
  cultivo_atual?: {
    id: string;
    cultura: string;
    safra_nome: string;
    data_plantio_real?: string;
    status: string;
  } | null;
}

interface TipoSolo {
  id: string;
  nome: string;
  descricao?: string;
  retencao_agua: string;
  lixiviacao: string;
  ctc_resumo: string;
}

interface TipoIrrigacao {
  id: string;
  nome: string;
  metodo?: string;
  descricao?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const AREA_LABELS_MAP: Record<string, string> = {
  AREA_RURAL: "Área Rural",
  GLEBA: "Gleba", TALHAO: "Talhão", AREA_AMBIENTAL: "Área Ambiental",
  AREA_OPERACIONAL: "Área Operacional", PIQUETE: "Piquete",
  ZONA_MANEJO: "Zona de Manejo", SUBTALHAO: "Subtalhão",
  APP: "APP", RESERVA_LEGAL: "Reserva Legal",
  INFRAESTRUTURA: "Infraestrutura", SEDE: "Sede",
  ARMAZEM: "Armazém", CURRAL: "Curral", OUTROS: "Outros",
};

const SISTEMAS_IRRIGACAO_LABELS: Record<string, string> = {
  SEQUEIRO: "Sequeiro",
  GOTEJAMENTO: "Gotejamento",
  PIVO_CENTRAL: "Pivô Central",
  ASPERSAO: "Aspersão",
  SULCO: "Sulco",
};

// Opções de filho válidas por tipo pai (ou raiz)
function filhosPermitidos(parentTipo: string | null): string[] {
  return [...(AREA_HIERARQUIA[parentTipo ?? "__raiz__"] ?? [])];
}

function fazendaContextHeaders(fazendaId: string): HeadersInit {
  return { "x-fazenda-id": fazendaId };
}

function parseCoordinates(value?: string | null) {
  if (!value) return { lat: "", lng: "" };
  const [lat, lng] = value.split(",").map((part) => part.trim());
  return { lat: lat ?? "", lng: lng ?? "" };
}

function getInitialView(coordenadasSede?: string | null) {
  const { lat, lng } = parseCoordinates(coordenadasSede);
  const latitude = Number(lat);
  const longitude = Number(lng);
  if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
    return { latitude, longitude, zoom: 14 };
  }
  return { latitude: -23.4205, longitude: -51.9253, zoom: 4 };
}

function normalizeGeometry(value?: Record<string, unknown> | string | null): GeoJSON.Feature<GeoJSON.Geometry> | null {
  if (!value) return null;

  let parsedValue = value;
  if (typeof value === "string") {
      try {
          parsedValue = JSON.parse(value);
      } catch {
          return null;
      }
  }

  if (typeof parsedValue !== "object" || parsedValue === null || !("type" in parsedValue)) return null;

  const geo = (parsedValue as unknown) as GeoJSON.Feature<GeoJSON.Geometry> | GeoJSON.Geometry | GeoJSON.FeatureCollection;
  if ((geo as GeoJSON.FeatureCollection).type === "FeatureCollection") {
    const feature = (geo as GeoJSON.FeatureCollection).features?.[0];
    return feature?.geometry ? { type: "Feature", properties: {}, geometry: feature.geometry } : null;
  }
  if ((geo as GeoJSON.Feature).type === "Feature") {
    const feature = geo as GeoJSON.Feature<GeoJSON.Geometry>;
    return feature.geometry ? { type: "Feature", properties: {}, geometry: feature.geometry } : null;
  }
  return { type: "Feature", properties: {}, geometry: geo as GeoJSON.Geometry };
}

function areaHa(feature: GeoJSON.Feature<GeoJSON.Geometry> | null) {
  if (!feature) return 0;
  try {
    return turf.area(feature) / 10000;
  } catch {
    return 0;
  }
}

const DRAW_STYLES: any[] = [
  {
    id: "gl-draw-polygon-fill",
    type: "fill",
    filter: ["all", ["==", "$type", "Polygon"]],
    paint: {
      "fill-color": ["case", ["==", ["get", "active"], "true"], "#f97316", "#2563eb"],
      "fill-opacity": 0.12,
    },
  },
  {
    id: "gl-draw-lines",
    type: "line",
    filter: ["any", ["==", "$type", "LineString"], ["==", "$type", "Polygon"]],
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": ["case", ["==", ["get", "active"], "true"], "#f97316", "#2563eb"],
      "line-dasharray": ["literal", [2, 1]],
      "line-width": 2,
    },
  },
  {
    id: "gl-draw-point-outer",
    type: "circle",
    filter: ["all", ["==", "$type", "Point"], ["==", "meta", "feature"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "active"], "true"], 7, 5],
      "circle-color": "#ffffff",
    },
  },
  {
    id: "gl-draw-point-inner",
    type: "circle",
    filter: ["all", ["==", "$type", "Point"], ["==", "meta", "feature"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "active"], "true"], 5, 3],
      "circle-color": ["case", ["==", ["get", "active"], "true"], "#f97316", "#2563eb"],
    },
  },
  {
    id: "gl-draw-vertex-outer",
    type: "circle",
    filter: ["all", ["==", "$type", "Point"], ["==", "meta", "vertex"], ["!=", "mode", "simple_select"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "active"], "true"], 7, 5],
      "circle-color": "#ffffff",
    },
  },
  {
    id: "gl-draw-vertex-inner",
    type: "circle",
    filter: ["all", ["==", "$type", "Point"], ["==", "meta", "vertex"], ["!=", "mode", "simple_select"]],
    paint: {
      "circle-radius": ["case", ["==", ["get", "active"], "true"], 5, 3],
      "circle-color": "#f97316",
    },
  },
  {
    id: "gl-draw-midpoint",
    type: "circle",
    filter: ["all", ["==", "meta", "midpoint"]],
    paint: {
      "circle-radius": 3,
      "circle-color": "#f97316",
    },
  },
];

// ---------------------------------------------------------------------------
// AreaSheet — painel lateral ciente da hierarquia
// ---------------------------------------------------------------------------

// Tipos que exigem área obrigatória
const TIPOS_AREA_OBRIGATORIA = new Set([
  "TALHAO", "AREA_AMBIENTAL", "SEDE", "ARMAZEM", "CURRAL", "OUTROS", "APP", "RESERVA_LEGAL",
]);

const TIPOS_COM_GEOMETRIA = new Set([
  "TALHAO", "GLEBA", "APP", "RESERVA_LEGAL", "PIQUETE", "AREA_AMBIENTAL", "AREA_OPERACIONAL",
]);

const areaFormSchema = z.object({
  tipo: z.string().min(1, "Selecione o tipo"),
  nome: z.string().min(2, "Mínimo 2 caracteres").max(200),
  codigo: z.string().max(50).optional().or(z.literal("")),
  area_hectares_manual: z.coerce.number().min(0).optional(),
  descricao: z.string().max(500).optional().or(z.literal("")),
  // Dados Agro (Somente Talhão)
  irrigado: z.boolean().default(false),
  tipo_irrigacao_id: z.string().uuid().optional().nullable(),
  tipo_solo_id: z.string().uuid().optional().nullable(),
  cultivo_atual: z.any().optional().nullable(),
}).superRefine((data, ctx) => {
  if (TIPOS_AREA_OBRIGATORIA.has(data.tipo) && !(data.area_hectares_manual && data.area_hectares_manual > 0)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Área em hectares é obrigatória para este tipo",
      path: ["area_hectares_manual"],
    });
  }
});

type AreaFormInput = z.infer<typeof areaFormSchema>;

interface AreaSheetState {
  open: boolean;
  editing: AreaRural | null;
  parentId: string | null;
  parentTipo: string | null;
  parentNome: string | null;
}

function AreaSheet({
  state,
  fazendaId,
  onClose,
  onSuccess,
  }: {
  state: AreaSheetState;
  fazendaId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEdit = !!state.editing;
  const tipos = filhosPermitidos(isEdit ? null : state.parentTipo);

  const { register, handleSubmit, setValue, control, reset, formState: { errors } } = useForm<AreaFormInput>({
    resolver: zodResolver(areaFormSchema) as import("react-hook-form").Resolver<AreaFormInput>,
    defaultValues: {
      tipo: state.editing?.tipo ?? tipos[0] ?? "GLEBA",
      nome: state.editing?.nome ?? "",
      codigo: state.editing?.codigo ?? "",
      area_hectares_manual: state.editing?.area_hectares_manual ?? state.editing?.area_hectares ?? 0,
      descricao: "",
      irrigado: state.editing?.irrigado ?? false,
      tipo_irrigacao_id: state.editing?.tipo_irrigacao_id ?? null,
      tipo_solo_id: state.editing?.tipo_solo_id ?? null,
      cultivo_atual: state.editing?.cultivo_atual ?? null,
    },
  });
  const tipoAtual = useWatch({ control, name: "tipo" }) ?? "";
  const areaHectaresAtual = useWatch({ control, name: "area_hectares_manual" });
  const irrigadoAtual = useWatch({ control, name: "irrigado" });
  const tipoSoloAtual = useWatch({ control, name: "tipo_solo_id" });
  const tipoIrrigacaoAtual = useWatch({ control, name: "tipo_irrigacao_id" });
  const cultivoAtual = useWatch({ control, name: "cultivo_atual" });
  const tipoEdicao = state.editing?.tipo ?? "";
  const tipoEdicaoLabel = AREA_LABELS[tipoEdicao] ?? tipoEdicao;

  const { data: tiposSolo = [] } = useQuery<TipoSolo[]>({
    queryKey: ["seletores", "tipos-solo"],
    queryFn: () => apiFetch("/cadastros/areas-rurais/seletores/tipos-solo"),
    enabled: state.open,
  });

  const { data: tiposIrrigacao = [] } = useQuery<TipoIrrigacao[]>({
    queryKey: ["seletores", "tipos-irrigacao"],
    queryFn: () => apiFetch("/cadastros/areas-rurais/seletores/tipos-irrigacao"),
    enabled: state.open,
  });

  useEffect(() => {
    if (state.open) {
      const tiposDisponiveis = filhosPermitidos(isEdit ? null : state.parentTipo);
      reset({
        tipo: state.editing?.tipo ?? tiposDisponiveis[0] ?? "GLEBA",
        nome: state.editing?.nome ?? "",
        codigo: state.editing?.codigo ?? "",
        area_hectares_manual: state.editing?.area_hectares_manual ?? state.editing?.area_hectares ?? 0,
        descricao: state.editing?.descricao ?? "",
        irrigado: state.editing?.irrigado ?? false,
        tipo_irrigacao_id: state.editing?.tipo_irrigacao_id ?? null,
        tipo_solo_id: state.editing?.tipo_solo_id ?? null,
        cultivo_atual: state.editing?.cultivo_atual ?? null,
      });
    }
  }, [state.open, state.editing, state.parentTipo, isEdit, reset]);

  const mutation = useMutation({
    mutationFn: (data: AreaFormInput) => {
      const payload: Record<string, any> = {
        tipo: data.tipo,
        nome: data.nome,
        ...(data.codigo ? { codigo: data.codigo } : {}),
        ...(data.descricao ? { descricao: data.descricao } : {}),
        ...(data.area_hectares_manual && data.area_hectares_manual > 0
          ? { area_hectares_manual: data.area_hectares_manual }
          : {}),
        irrigado: data.irrigado,
        tipo_irrigacao_id: data.tipo_irrigacao_id,
        tipo_solo_id: data.tipo_solo_id,
      };
      return isEdit
        ? apiFetch(`/cadastros/areas-rurais/${state.editing!.id}`, {
            method: "PATCH",
            headers: fazendaContextHeaders(fazendaId),
            body: JSON.stringify(payload),
          })
        : apiFetch("/cadastros/areas-rurais", {
            method: "POST",
            headers: fazendaContextHeaders(fazendaId),
            body: JSON.stringify({ ...payload, unidade_produtiva_id: fazendaId, parent_id: state.parentId ?? undefined }),
          });
    },
    onSuccess: () => {
      toast.success(isEdit ? "Área atualizada" : "Área criada");
      onSuccess();
      onClose();
    },
    onError: (e: any) => toast.error(e?.detail ?? e?.message ?? "Erro ao salvar"),
  });

  const tiposDisponiveis = filhosPermitidos(isEdit ? null : state.parentTipo);

  return (
    <Sheet open={state.open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>
            {isEdit ? `Editar — ${AREA_LABELS[state.editing!.tipo] ?? state.editing!.tipo}` : "Nova Área"}
          </SheetTitle>
          <SheetDescription>
            {isEdit
              ? "Atualize os dados desta área."
              : state.parentNome
                ? `Adicionando subdivisão em: ${state.parentNome}`
                : "Adicione uma área raiz à propriedade."}
          </SheetDescription>
        </SheetHeader>

        {/* Info do pai */}
        {!isEdit && state.parentNome && (
          <div className="mx-6 mt-2 mb-1 rounded-md border bg-muted/40 px-3 py-2 text-sm">
            <span className="text-muted-foreground">Pai: </span>
            <span className="font-medium">{state.parentNome}</span>
            {state.parentTipo && (
              <span className="ml-1.5 text-xs text-muted-foreground">
                ({AREA_LABELS[state.parentTipo] ?? state.parentTipo})
              </span>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit((d: AreaFormInput) => mutation.mutate(d))} className="space-y-4 px-6 py-4">
          {/* Tipo */}
          <div className="space-y-1.5">
            <Label>Tipo *</Label>
            {isEdit ? (
              <Select value={tipoEdicao} disabled>
                <SelectTrigger
                  render={
                    <Button
                      variant="outline"
                      className="h-8 w-full justify-between rounded-sm border border-primary/20 bg-muted/40 px-3 py-1 text-sm font-normal"
                    />
                  }
                >
                  {tipoEdicaoLabel || "—"}
                </SelectTrigger>
              </Select>
            ) : (
              <Select
                value={tipoAtual}
                onValueChange={(v: string) => setValue("tipo", v as AreaFormInput["tipo"])}
                disabled={mutation.isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o tipo..." />
                </SelectTrigger>
                <SelectContent>
                  {tiposDisponiveis.map((t) => (
                    <SelectItem key={t} value={t}>{AREA_LABELS[t] ?? t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {isEdit && (
              <p className="text-[10px] text-muted-foreground">
                O tipo não pode ser alterado na edição.
              </p>
            )}
            {errors.tipo && <p className="text-xs text-destructive">{errors.tipo.message}</p>}
          </div>

          {/* Info de Geometria (Apenas na Edição) */}
          {isEdit && TIPOS_COM_GEOMETRIA.has(tipoAtual) && (
            <div className="rounded-md border bg-muted/20 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs font-medium uppercase tracking-tight text-muted-foreground/80">
                <div className="flex items-center gap-1.5 font-bold">
                  <MapIcon className="size-3.5 text-primary" /> Geometria / Mapeamento
                </div>
                <Badge
                  variant={state.editing?.geometria ? "default" : "outline"}
                  className={cn(
                    "text-[10px] px-1.5 py-0 h-4 border-none shrink-0",
                    state.editing?.geometria
                      ? "bg-emerald-500/10 text-emerald-600 font-bold"
                      : "bg-amber-500/10 text-amber-600 font-bold"
                  )}
                >
                  {state.editing?.geometria ? "MAPEADO" : "SEM DESENHO"}
                </Badge>
              </div>

              {state.editing?.geometria ? (
                <div className="flex items-center gap-2">
                  <Ruler className="size-3.5 text-emerald-600" />
                  <p className="text-sm font-semibold">
                    {(state.editing?.area_hectares ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })} ha
                    <span className="text-[10px] text-muted-foreground ml-1.5 font-normal normal-case">
                      (Área exata calculada via GPS / Sig)
                    </span>
                  </p>
                </div>
              ) : (
                <p className="text-[11px] text-muted-foreground leading-tight">
                  Este {tipoEdicaoLabel?.toLowerCase() || "item"} ainda não possui um polígono definido no mapa. A área informada abaixo é declaratória.
                </p>
              )}
            </div>
          )}

          {/* Nome */}
          <div className="space-y-1.5">
            <Label>Nome *</Label>
            <Input {...register("nome")} placeholder="Ex: Gleba Norte, Talhão 01..." disabled={mutation.isPending} />
            {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
          </div>

          {/* Área + Código */}
          <div className={TIPOS_AREA_OBRIGATORIA.has(tipoAtual) ? "grid grid-cols-2 gap-4" : "space-y-1.5"}>
            {TIPOS_AREA_OBRIGATORIA.has(tipoAtual) && (
              <div className="space-y-1.5">
                <Label>Área (ha) *</Label>
                <Input
                  type="number" step="0.0001"
                  className="tabular-nums"
                  {...register("area_hectares_manual", { valueAsNumber: true })}
                  placeholder="0.0000"
                  disabled={mutation.isPending}
                />
                {errors.area_hectares_manual && (
                  <p className="text-xs text-destructive">{errors.area_hectares_manual.message}</p>
                )}
              </div>
            )}
            <div className="space-y-1.5">
              <Label>Código / Sigla</Label>
              <Input {...register("codigo")} placeholder="T01, G-A..." disabled={mutation.isPending} />
            </div>
          </div>

          {/* Descrição */}
          <div className="space-y-1.5">
            <Label>Descrição</Label>
            <Input {...register("descricao")} placeholder="Observações opcionais..." disabled={mutation.isPending} />
          </div>

          {/* Dados Agro (Somente Talhão) */}
          {tipoAtual === "TALHAO" && (
            <div className="pt-4 border-t space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold flex items-center gap-2 text-primary">
                  <Sprout className="size-4" /> Detalhes do Talhão
                </h3>
                {isEdit && cultivoAtual && (
                  <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700 font-bold">
                    PLANTADO
                  </Badge>
                )}
              </div>

              {isEdit && cultivoAtual ? (
                <div className="rounded-sm border bg-emerald-50/30 p-3 space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase text-emerald-600/80">
                    Ciclo de Cultura Ativo
                  </div>
                  <div className="flex items-center gap-2">
                    <Wheat className="size-4 text-emerald-600" />
                    <div className="flex-1">
                      <p className="text-sm font-bold text-emerald-900">
                        {cultivoAtual?.cultura} — {cultivoAtual?.safra_nome}
                      </p>
                      <p className="text-[10px] text-emerald-700/80">
                        Plantio: {cultivoAtual?.data_plantio_real ? new Date(cultivoAtual.data_plantio_real).toLocaleDateString() : "Data não informada"}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" className="h-7 text-[10px] bg-white" asChild>
                        <Link href={`/agricola/safras/cultivos/${cultivoAtual?.id}`}>
                        DETALHES
                      </Link>
                    </Button>
                  </div>
                </div>
              ) : isEdit && tipoAtual === "TALHAO" ? (
                 <div className="rounded-sm border border-dashed p-4 flex flex-col items-center justify-center gap-2 bg-muted/5">
                    <p className="text-xs text-muted-foreground text-center">Nenhum cultivo ativo vinculado a este talhão nesta temporada.</p>
                    <Button variant="outline" size="sm" className="h-8 gap-2" asChild>
                       <Link href="/agricola/safras">
                          <Plus className="size-3" /> Iniciar Ciclo
                       </Link>
                    </Button>
                 </div>
              ) : null}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5 col-span-2">
                  <Label>Tipo de Solo</Label>
                  <Select
                      value={tipoSoloAtual || ""}
                      onValueChange={(v: string) => setValue("tipo_solo_id", v || null)}
                  disabled={mutation.isPending}
                >
                  <SelectTrigger>
                      <SelectValue placeholder={tiposSolo.find((s) => s.id === tipoSoloAtual)?.nome || "Selecione o solo..."} />
                  </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">(Nenhum)</SelectItem>
                      {tiposSolo.map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          <div className="flex flex-col text-left">
                            <span className="font-medium">{s.nome}</span>
                            <span className="text-[10px] text-muted-foreground uppercase">{s.retencao_agua} Água | {s.ctc_resumo} CTC</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex flex-col space-y-2 pt-1">
                  <Label className="text-xs font-semibold">Usa Irrigação?</Label>
                  <div className="flex items-center gap-3">
                    <Switch
                      checked={irrigadoAtual}
                      onCheckedChange={(v) => {
                        setValue("irrigado", v);
                        if (!v) setValue("tipo_irrigacao_id", null);
                      }}
                    />
                    <span className="text-xs font-medium">{irrigadoAtual ? "Sim" : "Não (Sequeiro)"}</span>
                  </div>
                </div>

                {irrigadoAtual && (
                  <div className="space-y-1.5">
                    <Label className="text-xs">Sistema de Irrigação</Label>
                    <Select
                      value={tipoIrrigacaoAtual || ""}
                      onValueChange={(v: string) => setValue("tipo_irrigacao_id", v || null)}
                      disabled={mutation.isPending}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={tiposIrrigacao.find((i) => i.id === tipoIrrigacaoAtual)?.nome || "Selecione o sistema..."} />
                      </SelectTrigger>
                      <SelectContent>
                        {tiposIrrigacao.map((i) => (
                          <SelectItem key={i.id} value={i.id}>{i.nome}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </div>
          )}

          <SheetFooter className="pt-4 border-t gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={mutation.isPending}>
              Cancelar
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Salvando..." : isEdit ? "Salvar" : "Adicionar"}
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}

const MAP_STYLE = {
  version: 8,
    sources: {
      sat: {
        type: "raster",
      tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "© Esri",
      },
    },
  layers: [{ id: "sat-layer", type: "raster", source: "sat" }],
};

const MAP_STYLE_STREETS = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

type MapVisualizationMode = "satellite" | "streets";

function GeolocalizacaoDialog({
  open,
  onOpenChange,
  initialGeometry,
  coordenadasSede,
  onSave,
  isSaving,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialGeometry?: Record<string, unknown> | null;
  coordenadasSede?: string | null;
  onSave: (geometry: GeoJSON.Geometry | null) => void;
  isSaving: boolean;
}) {
  const mapRef = useRef<MapRef>(null);
  const drawRef = useRef<any>(null);
  const initialViewState = useMemo(() => getInitialView(coordenadasSede), [coordenadasSede]);
  const [geometry, setGeometry] = useState<GeoJSON.Feature<GeoJSON.Geometry> | null>(normalizeGeometry(initialGeometry));
  const [visualizationMode, setVisualizationMode] = useState<MapVisualizationMode>("satellite");
  const calculatedArea = useMemo(() => areaHa(geometry), [geometry]);

  const syncGeometry = useCallback((feature: GeoJSON.Feature<GeoJSON.Geometry> | null) => {
    setGeometry(feature);
  }, []);

  const clearGeometry = useCallback(() => {
    const draw = drawRef.current;
    if (draw) {
      draw.deleteAll();
      draw.changeMode("draw_polygon");
    }
    syncGeometry(null);
  }, [syncGeometry]);

  useEffect(() => {
    if (!open) return;
    const nextGeometry = normalizeGeometry(initialGeometry);
    setGeometry(nextGeometry);
  }, [initialGeometry, open]);

  useEffect(() => {
    if (!open) return;
    const nextGeometry = normalizeGeometry(initialGeometry);
    let mounted = true;
    let mapInstance: any = null;
    const timer = window.setTimeout(() => {
      void (async () => {
        mapInstance = mapRef.current?.getMap() as any;
        if (!mapInstance || !mounted) return;

        if (drawRef.current) {
          try {
            mapInstance.removeControl(drawRef.current);
          } catch {
            // Control already detached.
          }
          drawRef.current = null;
        }

        const { default: MapboxDraw } = await import("@mapbox/mapbox-gl-draw");
        if (!mounted) return;

        const initDraw = () => {
          if (!mounted || !mapRef.current) return;
          try {
            const draw = new MapboxDraw({
              displayControlsDefault: false,
              controls: { polygon: true, trash: true },
              styles: DRAW_STYLES,
            });

            mapInstance.addControl(draw);
            drawRef.current = draw;

            if (nextGeometry) {
              const ids = draw.add(nextGeometry);
              if (ids?.[0]) {
                draw.changeMode("direct_select", { featureId: ids[0] });
              }
            } else {
              draw.changeMode("draw_polygon");
            }

            const onChange = (event: { features?: Array<GeoJSON.Feature<GeoJSON.Geometry>> }) => {
              const feature = event.features?.[0] ?? null;
              syncGeometry(feature);
            };

            const onDelete = () => syncGeometry(null);
            mapInstance.on("draw.create", onChange);
            mapInstance.on("draw.update", onChange);
            mapInstance.on("draw.delete", onDelete);
          } catch (e) {
            console.error("MapboxDraw init error", e);
          }
        };

        if (mapInstance.isStyleLoaded()) {
          initDraw();
        } else {
          mapInstance.once('load', initDraw);
        }
      })();
    }, 0);

    return () => {
      mounted = false;
      window.clearTimeout(timer);
      const draw = drawRef.current;
      if (mapInstance && draw) {
        try {
          mapInstance.removeControl(draw);
        } catch {
          // Ignorado.
        }
        drawRef.current = null;
      }
    };
  }, [initialGeometry, open, syncGeometry]);

  useEffect(() => {
    const map = mapRef.current?.getMap() as any;
    if (!map || !geometry) return;
    try {
      const bbox = turf.bbox(geometry);
      map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 40, duration: 700 });
    } catch {
      // Geometrias invalidas nao devem bloquear o dialog.
    }
  }, [geometry]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-5xl rounded-sm p-0">
        <DialogHeader className="border-b px-5 pt-5">
          <div className="flex items-center gap-2">
            <MapPin className="size-5 text-primary" />
            <DialogTitle>Geolocalização da Unidade Produtiva</DialogTitle>
          </div>
          <DialogDescription>
            Edite o perímetro da unidade produtiva no mapa. A área calculada é da fazenda inteira e não da área operacional dos talhões.
          </DialogDescription>
        </DialogHeader>

        <div className="relative px-5 pb-5">
          <div className="relative h-[560px] overflow-hidden rounded-sm border bg-background">
            {open && (
              <MapLibreMap
                ref={mapRef}
                mapLib={maplibregl}
                initialViewState={initialViewState}
                mapStyle={visualizationMode === "satellite" ? (MAP_STYLE as any) : (MAP_STYLE_STREETS as any)}
                style={{ width: "100%", height: "100%" }}
              >
                <NavigationControl position="top-right" />
                {geometry && (
                  <Source id="fazenda-geometry" type="geojson" data={geometry}>
                    <Layer
                      id="fazenda-geometry-fill"
                      type="fill"
                      paint={{ "fill-color": "#3b82f6", "fill-opacity": 0.15 }}
                    />
                    <Layer
                      id="fazenda-geometry-line"
                      type="line"
                      paint={{ "line-color": "#2563eb", "line-width": 2.5 }}
                    />
                  </Source>
                )}
              </MapLibreMap>
            )}

            <div className="absolute top-4 right-4 z-10 pointer-events-none">
              <MapVisualizationToggle
                className="pointer-events-auto"
                checked={visualizationMode === "satellite"}
                onCheckedChange={(checked) => setVisualizationMode(checked ? "satellite" : "streets")}
              />
            </div>

            <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
              <div className="pointer-events-auto w-80 rounded-sm border bg-background/95 p-4 shadow-lg backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">Editar Geometria</span>
                  <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => onOpenChange(false)}>
                    <X className="size-4" />
                  </Button>
                </div>
                <div className="mt-3">
                  <p className="text-sm font-medium">Unidade produtiva</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Desenhe o perímetro diretamente no mapa. Clique para criar os pontos e feche o polígono.
                  </p>
                </div>
                <div className="mt-3 rounded-md bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-950/30 dark:text-blue-400">
                  Área calculada: <strong>{calculatedArea > 0 ? `${calculatedArea.toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })} ha` : "não calculada"}</strong>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1" onClick={clearGeometry}>
                    Limpar
                  </Button>
                  <Button size="sm" className="flex-1" onClick={() => onSave(geometry?.geometry ?? null)} disabled={isSaving}>
                    {isSaving ? "Salvando..." : "Salvar"}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800/30 dark:bg-amber-950/20 dark:text-amber-300">
            A área operacional dos talhões continua separada e é tratada na estrutura de áreas.
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

// Constrói árvore a partir de lista plana e propaga área dos filhos para o pai
function buildTree(areas: AreaRural[]): AreaRuralTree[] {
  const map = new Map<string, AreaRuralTree>();
  areas.forEach((a) => map.set(a.id, { ...a, filhos: [] } as unknown as AreaRuralTree));
  const roots: AreaRuralTree[] = [];
  map.forEach((node) => {
    if (node.parent_id) {
      map.get(node.parent_id as string)?.filhos.push(node);
    } else {
      roots.push(node);
    }
  });

  // Pós-ordem: área do pai = soma dos filhos (se houver filhos)
  function computeArea(node: AreaRuralTree): number {
    if (!node.filhos || node.filhos.length === 0) {
      return node.area_hectares_manual ?? node.area_hectares ?? 0;
    }
    const soma = node.filhos.reduce((acc: number, f: AreaRuralTree) => acc + computeArea(f), 0);
    node.area_hectares = soma > 0 ? soma : (node.area_hectares_manual ?? node.area_hectares ?? 0);
    return node.area_hectares;
  }

  function sortByName(nodes: AreaRuralTree[]) {
    nodes.sort((a, b) =>
      (a.nome ?? "").localeCompare(b.nome ?? "", "pt-BR", { numeric: true, sensitivity: "base" }),
    );
    nodes.forEach((n) => {
      if (n.filhos && n.filhos.length > 0) {
        sortByName(n.filhos);
      }
    });
  }

  roots.forEach(computeArea);
  sortByName(roots);
  return roots;
}

export function PropriedadeDetalheClient({ propriedadeId }: { propriedadeId: string }) {
  const id = propriedadeId;
  const queryClient = useQueryClient();

  const [sheet, setSheet] = useState<AreaSheetState>({
    open: false, editing: null, parentId: null, parentTipo: null, parentNome: null,
  });
  const [deleteTarget, setDeleteTarget] = useState<AreaRural | null>(null);
  const [geoDialogOpen, setGeoDialogOpen] = useState(false);

  const { data: fazenda, isLoading } = useQuery<Fazenda>({
    queryKey: ["fazenda", id],
    queryFn: () => apiFetch(`/unidades-produtivas/${id}`, { headers: fazendaContextHeaders(id) }),
    enabled: !!id,
  });

  const { data: allAreas = [] } = useQuery<AreaRural[]>({
    queryKey: ["areas-fazenda", id],
    queryFn: async () => {
      try {
        return await apiFetch(`/cadastros/areas-rurais?unidade_produtiva_id=${id}`, {
          headers: fazendaContextHeaders(id),
        });
      } catch {
        return [];
      }
    },
    enabled: !!id,
    retry: false,
  });

  const tree = buildTree(allAreas);
  const areaTotalInformada = parseFloat(fazenda?.area_total_ha ?? "0");
  const areaTotalCalculada = parseFloat(fazenda?.area_total_calculada_ha ?? "0");

  const updateFazendaMutation = useMutation({
    mutationFn: (payload: { geometria: GeoJSON.Geometry | null }) =>
      apiFetch(`/unidades-produtivas/${id}`, {
        method: "PUT",
        headers: fazendaContextHeaders(id),
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fazenda", id] });
      queryClient.invalidateQueries({ queryKey: ["areas-fazenda", id] });
      toast.success("Geolocalização atualizada");
      setGeoDialogOpen(false);
    },
    onError: () => toast.error("Erro ao atualizar geolocalização"),
  });

  const deleteMutation = useMutation({
    mutationFn: (areaId: string) =>
      apiFetch(`/cadastros/areas-rurais/${areaId}`, {
        method: "DELETE",
        headers: fazendaContextHeaders(id),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["areas-fazenda", id] });
      toast.success("Área removida");
      setDeleteTarget(null);
    },
    onError: () => toast.error("Erro ao remover área"),
  });

  const openCreate = (parentId: string, parentTipo: string) => {
    const parent = allAreas.find((a) => a.id === parentId);
    setSheet({ open: true, editing: null, parentId, parentTipo, parentNome: parent?.nome ?? null });
  };

  const openEdit = (area: AreaRuralTree) =>
    setSheet({ open: true, editing: area as unknown as AreaRural, parentId: area.parent_id as string | null, parentTipo: null, parentNome: null });

  const openRootCreate = () =>
    setSheet({ open: true, editing: null, parentId: null, parentTipo: null, parentNome: null });

  if (isLoading || !fazenda) {
    return (
      <div className="p-6 max-w-7xl space-y-6">
        <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        <div className="h-20 bg-muted rounded-lg animate-pulse" />
        <div className="h-10 bg-muted rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <PageHeader
        title={fazenda.nome}
        description="Resumo operacional da unidade produtiva, com sede, localização e vínculos territoriais."
        icon={<Trees className="size-5" />}
        breadcrumbs={[
          { label: "Cadastros", href: "/cadastros" },
          { label: "Unidades Produtivas", href: "/cadastros/propriedades" },
          { label: fazenda.nome },
        ]}
        actions={
          <div className="flex items-center gap-2">
            {fazenda.ativo ? (
              <Badge className="bg-emerald-600 text-xs rounded-sm">Ativa</Badge>
            ) : (
              <Badge variant="secondary" className="text-xs rounded-sm">Inativa</Badge>
            )}
            <Button size="sm" variant="outline" className="rounded-sm" onClick={() => setGeoDialogOpen(true)}>
              <MapPin className="mr-1.5 size-3.5" />
              Mapa operacional
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="rounded-sm">
                  Ações <MoreVertical className="size-3.5 ml-1" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => toast.info("Funcionalidade em desenvolvimento")}>
                  {fazenda.ativo ? (
                    <><PowerOff className="size-4 mr-2 text-orange-500" /> Desativar</>
                  ) : (
                    <><Power className="size-4 mr-2 text-green-500" /> Reativar</>
                  )}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />


      {/* Tabs */}
      <Tabs defaultValue="estrutura">
        <TabsList className="w-full justify-start h-auto gap-1 bg-transparent p-0 border-b rounded-none">
          <TabsTrigger value="estrutura" className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <Trees className="size-3.5" /> Estrutura de Áreas ({allAreas.length})
          </TabsTrigger>
          <TabsTrigger value="dados" className="rounded-none border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2">
            <MapIcon className="size-3.5" /> Resumo Operacional
          </TabsTrigger>
        </TabsList>

        {/* ── Estrutura de Áreas ── */}
        <TabsContent value="estrutura" className="pt-4">
          <div className="space-y-4">
            {/* KPIs */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
              {[
                { label: "Área Total Informada", value: areaTotalInformada > 0 ? `${areaTotalInformada.toFixed(1)} ha` : "—", icon: <Ruler className="size-5 text-primary" />, bg: "bg-primary/10" },
                { label: "Área Geométrica (Polígono)", value: areaTotalCalculada > 0 ? `${areaTotalCalculada.toFixed(1)} ha` : "—", icon: <MapIcon className="size-5 text-emerald-600" />, bg: "bg-emerald-100" },
                { label: "Glebas", value: allAreas.filter((a) => a.tipo === "GLEBA").length, icon: <Layers className="size-5 text-emerald-600" />, bg: "bg-emerald-100" },
                { label: "Talhões", value: allAreas.filter((a) => a.tipo === "TALHAO").length, icon: <Sprout className="size-5 text-teal-600" />, bg: "bg-teal-100" },
                { label: "Infraestruturas", value: allAreas.filter((a) => ["INFRAESTRUTURA", "SEDE", "ARMAZEM", "CURRAL", "OUTROS"].includes(a.tipo)).length, icon: <Building2 className="size-5 text-blue-600" />, bg: "bg-blue-100" },
                { label: "Áreas Informadas", value: allAreas.length > 0 ? `${allAreas.reduce((acc, a) => acc + ((a.area_hectares_manual ?? a.area_hectares) ?? 0), 0).toFixed(1)} ha` : "—", icon: <MapPin className="size-5 text-amber-600" />, bg: "bg-amber-100" },
              ].map(({ label, value, icon, bg }) => (
                <Card key={label}>
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-3">
                      <div className={`size-10 rounded-lg ${bg} flex items-center justify-center`}>{icon}</div>
                      <div>
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className="font-semibold">{value}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Botão Nova Área + Árvore */}
            <div className="flex justify-end">
              <Button size="sm" onClick={openRootCreate}>
                <Plus className="size-4 mr-1.5" /> Nova Área
              </Button>
            </div>
            <div className="rounded-xl border bg-card p-2">
              <AreaTree
                areas={tree}
                onAdd={(parentId, parentTipo) => openCreate(parentId, parentTipo)}
                onEdit={(area) => openEdit(area)}
                onDelete={(area) => setDeleteTarget(area as unknown as AreaRural)}
              />
            </div>
          </div>
        </TabsContent>

        {/* ── Resumo Operacional ── */}
        <TabsContent value="dados" className="pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Resumo Operacional</CardTitle>
              <CardDescription>Dados operacionais da unidade produtiva. Documentos, áreas oficiais e dados fundiários ficam no cadastro de cada Imóvel Rural.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { label: "Unidade Produtiva", value: fazenda.nome },
                  { label: "CPF / CNPJ", value: fazenda.cpf_cnpj },
                  { label: "Inscrição Estadual", value: fazenda.inscricao_estadual },
                  { label: "Status operacional", value: fazenda.ativo ? "Ativa" : "Inativa" },
                  { label: "Município da sede", value: fazenda.municipio },
                  { label: "UF da sede", value: fazenda.uf },
                  { label: "Área operacional informada", value: fazenda.area_total_ha ? `${parseFloat(fazenda.area_total_ha).toFixed(2)} ha` : undefined },
                  { label: "Área calculada pela geometria", value: fazenda.area_total_calculada_ha ? `${parseFloat(fazenda.area_total_calculada_ha).toFixed(2)} ha` : undefined },
                  { label: "APP de referência", value: fazenda.area_app_ha ? `${parseFloat(fazenda.area_app_ha).toFixed(2)} ha` : undefined },
                  { label: "Reserva Legal de referência", value: fazenda.area_rl_ha ? `${parseFloat(fazenda.area_rl_ha).toFixed(2)} ha` : undefined },
                  { label: "Coordenadas da sede", value: fazenda.coordenadas_sede },
                ].map(({ label, value }) => (
                  <div key={label} className="space-y-1.5">
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
                    <p className="text-sm font-medium">{value ?? <span className="text-muted-foreground/50">—</span>}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {fazenda.territorio?.avisos && fazenda.territorio.avisos.length > 0 && (
            <div className="mt-4 space-y-2">
              {fazenda.territorio.avisos.map((aviso, idx) => (
                <div key={idx} className="p-3 bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-md text-sm">
                  {aviso}
                </div>
              ))}
            </div>
          )}

          <ImoveisVinculadosCard
            unidadeProdutivaId={fazenda.id}
            territory={fazenda.territorio ?? null}
            className="mt-4"
          />
        </TabsContent>
      </Tabs>

      {/* Estrutura Hierárquica */}
      <Card className="border-border/50 shadow-sm overflow-hidden mt-12 rounded-sm">
        <Accordion type="single" collapsible>
          <AccordionItem value="estrutura" className="border-none">
            <CardHeader className="p-0">
              <AccordionTrigger className="px-6 py-4 hover:no-underline hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                    <FolderTree className="size-4 text-primary" />
                  </div>
                  <div className="text-left">
                    <CardTitle className="text-sm font-black uppercase tracking-widest leading-none">
                      Estrutura de Áreas
                    </CardTitle>
                    <CardDescription className="text-[10px] mt-1 uppercase tracking-wider font-semibold opacity-50">
                      Organize glebas, talhões e infraestrutura rurais
                    </CardDescription>
                  </div>
                </div>
              </AccordionTrigger>
            </CardHeader>
            <AccordionContent>
              <CardContent className="pt-0 pb-6">
                <Separator className="mb-6 opacity-40" />
                <EstruturaHierarquia propriedadeNome={fazenda.nome} />
              </CardContent>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </Card>

      {/* Area Sheet */}
      <AreaSheet
        state={sheet}
        fazendaId={id}
        onClose={() => setSheet((s) => ({ ...s, open: false }))}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["areas-fazenda", id] })}
      />

      {/* Delete confirm */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover área?</AlertDialogTitle>
            <AlertDialogDescription>
              &quot;{deleteTarget?.nome}&quot; e todos os seus filhos serão removidos permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <GeolocalizacaoDialog
        open={geoDialogOpen}
        onOpenChange={setGeoDialogOpen}
        initialGeometry={fazenda?.geometria ?? null}
        coordenadasSede={fazenda?.coordenadas_sede}
        onSave={(geometry) => updateFazendaMutation.mutate({ geometria: geometry })}
        isSaving={updateFazendaMutation.isPending}
      />
    </div>
  );
}
