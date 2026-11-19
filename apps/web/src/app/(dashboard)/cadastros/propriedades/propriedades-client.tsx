"use client";

import React, { useState, useRef, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller, useWatch, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { type CreateCadastroCompletoInput, type UpdateCadastroCompletoInput } from "@farm/zod-schemas";
import Map, { NavigationControl, Source, Layer, MapRef } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import * as turf from "@turf/turf";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useAppStore } from "@/lib/stores/app-store";
import {
    Plus, Pencil, Landmark, Ruler, MapPinned, Undo2,
    AlertTriangle, Layers, TreePine, HelpCircle, Eye,
    Trees, Trash2, Save, X
} from "lucide-react";
import { PlanUsageBanner } from "@/components/shared/plan-usage-banner";
import { PageHeader } from "@/components/shared/page-header";
import { cn } from "@/lib/utils";
import { resolveAssetUrl } from "@/lib/runtime-config";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PermissionGuard } from "@/components/auth/permission-guard";
import { Switch } from "@/components/ui/switch";
import Link from "next/link";
import type { UnidadeProdutiva as UnidadeProdutivaBase } from "@/types/global";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { MapVisualizationToggle } from "@/components/shared/map-visualization-toggle";
import { ImoveisVinculadosCard } from "@/components/propriedade/imoveis-vinculados-card";
import { buildOperationalCadastroPayload } from "./propriedades-operational-payload";

type UnidadeProdutiva = UnidadeProdutivaBase;

const propriedadeFormSchema = z.object({
    grupo_id: z.string().uuid("Grupo inválido").optional().nullable().or(z.literal("")),
    nome: z.string()
        .trim()
        .min(2, "Mínimo de 2 caracteres")
        .max(150, "Máximo de 150 caracteres"),
    tipo_propriedade: z.enum(["fazenda", "sitio", "chacara", "arrendamento", "parceria"], {
        error: () => "Selecione o tipo",
    }),
    cpf_cnpj: z.string().max(18, "Máximo de 18 caracteres").optional().or(z.literal("")),
    inscricao_estadual: z.string().max(50, "Máximo de 50 caracteres").optional().or(z.literal("")),
    area_total_ha: z.coerce.number().optional().or(z.literal(0)),
    area_app_ha: z.coerce.number().optional().or(z.literal(0)),
    area_rl_ha: z.coerce.number().optional().or(z.literal(0)),
    cep: z.string().max(9, "Máximo de 9 caracteres").optional().or(z.literal("")),
    logradouro: z.string().max(255, "Máximo de 255 caracteres").optional().or(z.literal("")),
    numero: z.string().max(20, "Máximo de 20 caracteres").optional().or(z.literal("")),
    complemento: z.string().max(100, "Máximo de 100 caracteres").optional().or(z.literal("")),
    bairro: z.string().max(100, "Máximo de 100 caracteres").optional().or(z.literal("")),
    municipio: z.string().max(100, "Máximo de 100 caracteres").optional().or(z.literal("")),
    uf: z.string().max(2, "Máximo de 2 caracteres").optional().or(z.literal("")),
    ibge_municipio_codigo: z.string().max(7, "Máximo de 7 caracteres").optional().or(z.literal("")),
    coordenadas_sede: z.string().max(100, "Máximo de 100 caracteres").optional().or(z.literal("")),
    ativo: z.boolean().default(true),
});

type CreateUnidadeProdutivaValues = z.input<typeof propriedadeFormSchema>;
type TipoPropriedade = CreateUnidadeProdutivaValues["tipo_propriedade"];

const TIPO_LABEL: Record<string, string> = {
    fazenda: "Fazenda",
    sitio: "Sítio",
    chacara: "Chácara",
    arrendamento: "Arrendamento",
    parceria: "Parceria",
};

function normalizeTipo(t?: string | null): TipoPropriedade {
    if (!t) return "fazenda";
    const normalized = t.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    if (["fazenda", "sitio", "chacara", "arrendamento", "parceria"].includes(normalized)) {
        return normalized as TipoPropriedade;
    }
    return "fazenda";
}

function resolveLogo(url: string | null) {
    return resolveAssetUrl(url);
}

function toAreaNumber(value: unknown) {
    if (value === null || value === undefined || value === "") return 0;
    const parsed = typeof value === "number" ? value : Number(String(value).replace(",", "."));
    return Number.isFinite(parsed) ? parsed : 0;
}

function formatOptionalArea(value: unknown, fractionDigits = 4) {
    if (value === null || value === undefined || value === "") return "";
    const parsed = typeof value === "number" ? value : Number(String(value).replace(",", "."));
    if (!Number.isFinite(parsed)) return "";
    return parsed.toLocaleString("pt-BR", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits });
}

function parseCoordenadasSede(value?: string | null) {
    if (!value) return { lat: "", lng: "" };
    const [rawLat, rawLng] = value.split(",").map((part) => part.trim());
    return {
        lat: rawLat ?? "",
        lng: rawLng ?? "",
    };
}

function normalizeCoordinate(value: string) {
    return value.trim().replace(",", ".");
}

function isCoordinateInRange(value: string, min: number, max: number) {
    if (!value) return false;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= min && parsed <= max;
}

function getMapInitialView(coordenadasSede?: string | null) {
    const coords = parseCoordenadasSede(coordenadasSede);
    const latitude = Number(coords.lat);
    const longitude = Number(coords.lng);

    if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
        return { longitude, latitude, zoom: 14 };
    }

    return {
        longitude: -51.9253,
        latitude: -23.4205,
        zoom: 4,
    };
}

function normalizeGeometry(
    value?: Record<string, unknown> | string | null
): GeoJSON.Feature<GeoJSON.Geometry> | null {
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

function geometryAreaHa(geometry: GeoJSON.Feature<GeoJSON.Geometry> | null) {
    if (!geometry) return 0;
    try {
        return turf.area(geometry) / 10000;
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

export function PropriedadesClient() {
    const queryClient = useQueryClient();
    const [sheetOpen, setSheetOpen] = useState(false);
    const [editTarget, setEditTarget] = useState<UnidadeProdutiva | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<UnidadeProdutiva | null>(null);

    const hasHydrated = useAppStore((s) => s._hasHydrated);
    const token = useAppStore((s) => s.token);
    const activeFazendaId = useAppStore((s) => s.activeFazendaId);
    const unidadesProdutivasAutorizadas = useAppStore((s) => s.unidadesProdutivasAutorizadas);
    const isReady = hasHydrated;

    const { data: fazendas = [], isLoading, error } = useQuery<UnidadeProdutiva[]>({
        queryKey: ["unidades-produtivas"],
        queryFn: async () => {
            if (!token) {
                return unidadesProdutivasAutorizadas;
            }
            try {
                return await apiFetch("/unidades-produtivas", { suppressErrorLog: true });
            } catch (err) {
                if (unidadesProdutivasAutorizadas.length > 0) {
                    return unidadesProdutivasAutorizadas;
                }
                throw err;
            }
        },
        enabled: isReady && (!!token || unidadesProdutivasAutorizadas.length > 0),
        retry: false,
    });

    const { data: fazendaAtivaDetalhe } = useQuery<UnidadeProdutiva | null>({
        queryKey: ["unidades-produtivas", activeFazendaId],
        queryFn: async () => {
            if (!activeFazendaId) return null;
            if (!token) return unidadesProdutivasAutorizadas.find((f) => f.id === activeFazendaId) ?? null;
            try {
                return await apiFetch(`/unidades-produtivas/${activeFazendaId}`, { suppressErrorLog: true });
            } catch {
                return null;
            }
        },
        enabled: isReady && !!activeFazendaId && (!!token || unidadesProdutivasAutorizadas.some((f) => f.id === activeFazendaId)),
        retry: false,
    });

    const { data: areasRurais = [] } = useQuery<Array<{
        id: string;
        nome?: string | null;
        tipo: string;
        parent_id: string | null;
        area_hectares: number | null;
        area_hectares_manual: number | null;
    }>>({
        queryKey: ["areas-rurais-all"],
        queryFn: () => apiFetch(`/cadastros/areas-rurais?unidade_produtiva_id=${activeFazendaId}`),
        enabled: isReady && !!token && !!activeFazendaId,
    });

    const areaCalculada = areasRurais
        .filter(a => a.parent_id === null || a.parent_id === undefined)
        .reduce((acc, a) => acc + toAreaNumber(a.area_hectares_manual ?? a.area_hectares), 0);
    const areaRuralRaiz = areasRurais.find((a) => a.tipo === "AREA_RURAL");

    const grupos: { id: string; nome: string }[] = [];

        const { data: limitesTenant } = useQuery<{
            max_fazendas: { atual: number; limite: number | null; atingido: boolean };
            limite_hectares?: { atual: number; limite: number | null; atingido: boolean };
        }>({
            queryKey: ["fazendas-limite"],
            queryFn: async () => {
                return await apiFetch<{
                    max_fazendas: { atual: number; limite: number | null; atingido: boolean };
                    limite_hectares?: { atual: number; limite: number | null; atingido: boolean };
                }>("/billing/limits");
            },
            retry: false,
            enabled: isReady && !!token,
        });
        const limiteInfo = limitesTenant?.max_fazendas;
        const limiteHectaresInfo = limitesTenant?.limite_hectares;

        const createMutation = useMutation({
            mutationFn: (data: CreateCadastroCompletoInput) =>
                apiFetch("/unidades-produtivas/cadastro-completo", { method: "POST", body: JSON.stringify(data) }),
            onSuccess: async (created: UnidadeProdutiva) => {
                toast.success("Unidade produtiva cadastrada com sucesso!");
                const hydrated = await queryClient.fetchQuery<UnidadeProdutiva>({
                    queryKey: ["unidades-produtivas", created.id],
                    queryFn: () => apiFetch(`/unidades-produtivas/${created.id}`),
                    staleTime: 0,
                }).catch(() => created);
                queryClient.setQueryData<UnidadeProdutiva[]>(["unidades-produtivas"], (current = []) => {
                    const next = current.filter((item) => item.id !== created.id);
                    return [hydrated, ...next];
                });
                queryClient.setQueryData(["unidades-produtivas", created.id], hydrated);
                queryClient.invalidateQueries({ queryKey: ["unidades-produtivas"] });
                queryClient.invalidateQueries({ queryKey: ["imoveis-rurais"] });
                queryClient.invalidateQueries({ queryKey: ["visao-territorial"] });
                queryClient.invalidateQueries({ queryKey: ["visao-fundiaria"] });
                queryClient.invalidateQueries({ queryKey: ["fazendas-limite"] });
                queryClient.invalidateQueries({ queryKey: ["areas-rurais-all"] });
                setSheetOpen(false);
            },
            onError: (err: Error) => {
                    const msg = err.message || "Erro ao criar unidade produtiva";
                    if (msg.toLowerCase().includes("limite") || msg.toLowerCase().includes("pacote") || msg.toLowerCase().includes("upgrade")) {
                        toast.error(msg, {
                            action: {
                                label: "Fazer Upgrade",
                                onClick: () => { window.location.href = "/dashboard/settings/billing"; },
                            },
                        });
                    } else {
                        toast.error(msg);
                    }
                },
            });

        const updateMutation = useMutation({
            mutationFn: ({ id, data }: { id: string; data: UpdateCadastroCompletoInput }) =>
                apiFetch(`/unidades-produtivas/${id}/cadastro-completo`, { method: "PUT", body: JSON.stringify(data) }),
            onSuccess: async (updated: UnidadeProdutiva) => {
                toast.success("Unidade produtiva atualizada!");
                const hydrated = await queryClient.fetchQuery<UnidadeProdutiva>({
                    queryKey: ["unidades-produtivas", updated.id],
                    queryFn: () => apiFetch(`/unidades-produtivas/${updated.id}`),
                    staleTime: 0,
                }).catch(() => updated);
                queryClient.setQueryData<UnidadeProdutiva[]>(["unidades-produtivas"], (current = []) =>
                    current.map((item) => (item.id === updated.id ? hydrated : item))
                );
                queryClient.setQueryData(["unidades-produtivas", updated.id], hydrated);
                queryClient.invalidateQueries({ queryKey: ["unidades-produtivas"] });
                queryClient.invalidateQueries({ queryKey: ["imoveis-rurais"] });
                queryClient.invalidateQueries({ queryKey: ["visao-territorial"] });
                queryClient.invalidateQueries({ queryKey: ["visao-fundiaria"] });
                queryClient.invalidateQueries({ queryKey: ["fazendas-limite"] });
                queryClient.invalidateQueries({ queryKey: ["areas-rurais-all"] });
                setEditTarget(null);
                setSheetOpen(false);
            },
            onError: (err: Error) => {
                const msg = err.message || "Erro ao atualizar";
                if (msg.toLowerCase().includes("limite") || msg.toLowerCase().includes("pacote") || msg.toLowerCase().includes("upgrade")) {
                    toast.error(msg, {
                        action: {
                            label: "Fazer Upgrade",
                            onClick: () => { window.location.href = "/dashboard/settings/billing"; },
                        },
                    });
                } else {
                    toast.error(msg);
                }
            },
        });

        const deleteMutation = useMutation({
            mutationFn: (id: string) => apiFetch(`/unidades-produtivas/${id}`, { method: "DELETE" }),
            onSuccess: () => {
                toast.success("Unidade produtiva removida.");
                queryClient.invalidateQueries({ queryKey: ["unidades-produtivas"] });
                queryClient.invalidateQueries({ queryKey: ["fazendas-limite"] });
                queryClient.invalidateQueries({ queryKey: ["areas-rurais-all"] });
                setDeleteTarget(null);
            },
            onError: (err: Error) => toast.error(err.message || "Erro ao remover"),
        });

        const fazendaAtivaDoStore = unidadesProdutivasAutorizadas.find((f) => f.id === activeFazendaId);

        function mergeFazenda(base ?: Partial<UnidadeProdutiva> | null, extra ?: Partial<UnidadeProdutiva> | null): UnidadeProdutiva | null {
        const source = { ...(base ?? {}) } as Partial<UnidadeProdutiva>;
        if(extra) {
            for (const k in extra) {
                const key = k as keyof UnidadeProdutiva;
                if (extra[key] !== undefined && extra[key] !== null) {
                    (source as any)[key] = extra[key];
                }
            }
        }
        
        if(!source.id) return null;

    return {
        id: source.id,
        tenant_id: source.tenant_id ?? "",
        nome: source.nome ?? areaRuralRaiz?.nome ?? "Propriedade ativa",
        tipo_propriedade: source.tipo_propriedade ?? "fazenda",
        cpf_cnpj: source.cpf_cnpj ?? null,
        inscricao_estadual: source.inscricao_estadual ?? null,
        cep: source.cep ?? null,
        logradouro: source.logradouro ?? null,
        numero: source.numero ?? null,
        complemento: source.complemento ?? null,
        bairro: source.bairro ?? null,
        municipio: source.municipio ?? null,
        uf: source.uf ?? null,
        ibge_municipio_codigo: source.ibge_municipio_codigo ?? null,
        area_total_ha: source.area_total_ha ?? areaRuralRaiz?.area_hectares_manual ?? areaRuralRaiz?.area_hectares ?? null,
        area_total_calculada_ha: source.area_total_calculada_ha ?? areaRuralRaiz?.area_hectares ?? areaRuralRaiz?.area_hectares_manual ?? null,
        area_app_ha: source.area_app_ha ?? null,
        area_rl_ha: source.area_rl_ha ?? null,
        coordenadas_sede: source.coordenadas_sede ?? null,
        geometria: source.geometria ?? null,
        logo_url: source.logo_url ?? null,
        ativo: source.ativo ?? true,
        created_at: source.created_at ?? "",
        updated_at: source.updated_at ?? "",
    };
}

const fazendaFallback = mergeFazenda(
    activeFazendaId ? { id: activeFazendaId } : null,
    fazendaAtivaDetalhe ?? fazendaAtivaDoStore ?? null
);

const fazendasBase =
    fazendas.length > 0
        ? fazendas
        : unidadesProdutivasAutorizadas.length > 0
            ? unidadesProdutivasAutorizadas
            : fazendaFallback
                ? [fazendaFallback]
                : [];

const fazendasDisponiveis = fazendasBase.map((fazenda) =>
    fazenda.id === activeFazendaId
        ? (mergeFazenda(fazenda, fazendaAtivaDetalhe ?? fazendaAtivaDoStore ?? null) ?? fazenda)
        : fazenda
);
const showLoadError = !!error && fazendasDisponiveis.length === 0;
const limiteAtingido = limiteInfo?.atingido ?? false;

function openCreate() {
    if (limiteAtingido) {
        toast.error("Limite de unidades produtivas do plano atingido. Faça upgrade.");
        return;
    }
    setEditTarget(null);
    setSheetOpen(true);
}
function openEdit(f: UnidadeProdutiva) { setEditTarget(f); setSheetOpen(true); }

function handleInvalidSubmit(formErrors: FieldErrors<CreateUnidadeProdutivaValues>) {
    const firstError = Object.values(formErrors)[0];
    const message = firstError?.message;
    toast.error(typeof message === "string" && message.trim() ? message : "Preencha os campos obrigatórios.");
}

const columns = useMemo<ColumnDef<UnidadeProdutiva>[]>(() => [
    {
        id: "nome",
        header: "Nome",
        accessorKey: "nome",
        cell: (value, row) => (
            <div className="flex items-center gap-3">
                <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                    {row.logo_url ? <img src={resolveLogo(row.logo_url) ?? ""} className="size-8 object-cover rounded-sm" alt="Logo" /> : <Landmark className="size-4 text-primary" />}
                </div>
                <div className="flex flex-col">
                    <span className="font-medium">{value}</span>
                    <span className="text-[10px] text-muted-foreground">{[row.municipio, row.uf].filter(Boolean).join(" - ")}</span>
                </div>
            </div>
        )
    },
    {
        id: "tipo",
        header: "Tipo",
        accessorFn: (row) => TIPO_LABEL[normalizeTipo(row.tipo_propriedade)] ?? row.tipo_propriedade,
    },
    {
        id: "area",
        header: "Área Total",
        accessorKey: "area_total_ha",
        cell: (value) => value ? `${Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ha` : "-",
    },
    {
        id: "area_real",
        header: "Área Útil",
        accessorFn: (row) => Math.max(
            0,
            toAreaNumber(row.area_total_ha) - toAreaNumber(row.area_app_ha) - toAreaNumber(row.area_rl_ha)
        ),
        cell: (value) => value ? `${Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ha` : "-",
    },
    {
        id: "imoveis",
        header: "Imóveis vinculados",
        accessorFn: (row) => {
            const principal = row.territorio?.imovel_principal?.id ? 1 : 0;
            const secundarios = row.territorio?.imoveis_secundarios?.length ?? 0;
            return principal + secundarios;
        },
        cell: (value) => `${value ?? 0}`,
    },
    {
        id: "status",
        header: "Status",
        accessorKey: "ativo",
        cell: (value, row) => (
            <div className="flex items-center gap-2">
                <Badge variant={value ? "default" : "secondary"} className="text-[10px] rounded-sm">
                    {value ? "Ativa" : "Inativa"}
                </Badge>
                {row.territorio?.estado_de_convergencia && row.territorio.estado_de_convergencia !== "CANONICAL" && (
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger>
                                <AlertTriangle className="size-3.5 text-amber-500" />
                            </TooltipTrigger>
                            <TooltipContent>
                                <p>Esta propriedade possui pendências de migração territorial.</p>
                                <p className="text-xs text-muted-foreground">Estado: {row.territorio.estado_de_convergencia}</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                )}
            </div>
        )
    },
    {
        id: "acoes",
        header: "",
        exportable: false,
        sortable: false,
        filterable: false,
        cell: (_, row) => (
            <div className="flex items-center gap-0 justify-end">
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary rounded-sm" asChild>
                                <Link href={`/cadastros/propriedades/${row.id}/visao-territorial`}>
                                    <Eye className="size-3.5" />
                                </Link>
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Visão territorial</TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary rounded-sm" asChild>
                                <Link href={`/cadastros/propriedades/${row.id}`}>
                                    <TreePine className="size-3.5" />
                                </Link>
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Estrutura de Áreas</TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary rounded-sm" onClick={() => openEdit(row)}>
                                <Pencil className="size-3.5" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Editar</TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive rounded-sm" onClick={() => setDeleteTarget(row)}>
                                <Trash2 className="size-3.5" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>Remover</TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            </div>
        )
    }
], []);

const totalArea = fazendasDisponiveis.reduce((acc, f) => acc + toAreaNumber(f.area_total_ha), 0);
const totalAreaCalculada = fazendasDisponiveis.reduce((acc, f) => acc + toAreaNumber(f.area_total_calculada_ha), 0);
const areaGeometriaExibida = totalAreaCalculada > 0 ? totalAreaCalculada : areaCalculada;
const totalAreaReal = fazendasDisponiveis.reduce((acc, f) => {
    const total = toAreaNumber(f.area_total_ha);
    const app = toAreaNumber(f.area_app_ha);
    const rl = toAreaNumber(f.area_rl_ha);
    return acc + Math.max(0, total - app - rl);
}, 0);
const totalAtivas = fazendasDisponiveis.filter((f) => f.ativo).length;

if (!isReady || isLoading) {
    return (
        <div className="p-6 space-y-6">
            <Skeleton className="h-10 w-64" />
            <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-sm shadow-sm" />)}
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40 rounded-sm shadow-sm" />)}
            </div>
        </div>
    );
}

return (
    <div className="p-6 space-y-6">
        <PageHeader
            title="Unidades Produtivas"
            description="Gerencie as operações, sedes e localizações operacionais da sua conta."
            icon={<Trees className="text-primary" size={22} />}
            breadcrumbs={[
                { label: "Cadastros", href: "/cadastros" },
                { label: "Unidades Produtivas" },
            ]}
            actions={
                <PermissionGuard permission="tenant:fazendas:create">
                    <Button size="sm" onClick={openCreate} disabled={limiteAtingido} variant="outline" className="rounded-sm">
                        <Plus className="size-3.5 mr-1.5" /> Nova Unidade Produtiva
                    </Button>
                </PermissionGuard>
            }
        />

        <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
            <PropertyMetricCard icon={Landmark} label="Total" value={fazendasDisponiveis.length} tone="primary" />
            <PropertyMetricCard icon={TreePine} label="Ativas" value={totalAtivas} tone="success" />
            <PropertyMetricCard
                icon={Ruler}
                label="Área operacional informada"
                value={`${totalArea.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha`}
                subtitle="Soma das áreas declaradas"
            />
            <PropertyMetricCard
                icon={Trees}
                label="Área útil estimada"
                value={`${totalAreaReal.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha`}
                subtitle="Área informada - APP/RL de referência"
                tone="success"
            />
            <PropertyMetricCard
                icon={Layers}
                label="Área geométrica (polígono)"
                value={`${areaGeometriaExibida.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha`}
                subtitle={`Var. ${((areaGeometriaExibida / (totalArea || 1) - 1) * 100).toFixed(1)}% vs informada`}
            />
        </div>

        {limiteHectaresInfo && limiteHectaresInfo.limite !== null && (
            <PlanUsageBanner
                label="ha equivalentes em operação (talhões/cultivos) no limite do pacote"
                atual={limiteHectaresInfo.atual}
                limite={limiteHectaresInfo.limite}
                atingido={limiteHectaresInfo.atingido}
                hint="Considera a área produtiva em uso nos talhões (APP/RL isentas). A inclusão ou edição de áreas respeita o limite total do pacote."
            />
        )}

        {limiteInfo && (
            <PlanUsageBanner
                label="unidade(s) produtiva(s) cadastrada(s) (cota de fazendas do plano)"
                atual={limiteInfo.atual}
                limite={limiteInfo.limite}
                atingido={limiteInfo.atingido}
                hint={
                    limiteInfo.atingido
                        ? "As unidades já cadastradas permanecem ativas. Faça upgrade apenas se precisar incluir uma nova unidade."
                        : undefined
                }
            />
        )}

        {showLoadError && (
            <Alert variant="destructive" className="rounded-sm">
                <AlertTriangle className="size-4" />
                <AlertDescription>Não foi possível carregar as unidades produtivas.</AlertDescription>
            </Alert>
        )}

        <Card className="shadow-sm">
            <CardHeader className="border-b">
                <CardTitle>Lista de Unidades Produtivas</CardTitle>
                <CardDescription>
                    Consulte, edite e exporte as unidades produtivas cadastradas para o tenant ativo.
                </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
                <DataTable
                    data={fazendasDisponiveis}
                    columns={columns}
                    searchable={true}
                    searchPlaceholder="Buscar unidade produtiva..."
                    exportable={true}
                    exportFileName="unidades_produtivas_export"
                    emptyMessage="Nenhuma unidade produtiva cadastrada ou encontrada."
                />

                {fazendasDisponiveis.length > 0 && (
                    <div className="mt-4 flex justify-end border-t pt-4">
                        <div className="flex flex-col gap-3 rounded-sm border bg-muted/30 p-3 text-sm sm:flex-row sm:items-center sm:gap-6">
                            <div className="flex flex-col sm:items-end">
                                <span className="text-[10px] font-bold uppercase text-muted-foreground">Total Operacional Informado</span>
                                <span className="font-mono text-lg font-semibold text-foreground">
                                    {totalArea.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha
                                </span>
                            </div>
                            <div className="hidden w-px bg-border sm:block" />
                            <div className="flex flex-col sm:items-end">
                                <span className="text-[10px] font-bold uppercase text-muted-foreground">Total Útil Estimado</span>
                                <span className="font-mono text-lg font-semibold text-primary">
                                    {totalAreaReal.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>

        {/* Dialog de criação/edição */}
        <PropriedadeDialog
            key={`${sheetOpen ? "open" : "closed"}-${editTarget?.id ?? "new"}`}
            open={sheetOpen}
            onOpenChange={(v) => { setSheetOpen(v); if (!v) setEditTarget(null); }}
            fazenda={editTarget ?? undefined}
            grupos={grupos}
            isPending={createMutation.isPending || updateMutation.isPending}
            onSubmit={(data) => {
                if (editTarget) {
                    updateMutation.mutate({ id: editTarget.id, data: data as UpdateCadastroCompletoInput });
                } else {
                    createMutation.mutate(data as CreateCadastroCompletoInput);
                }
            }}
            onInvalidSubmit={handleInvalidSubmit}
        />

        {/* Dialog de exclusão */}
        {deleteTarget && (
            <AlertDialog open onOpenChange={() => setDeleteTarget(null)}>
                <AlertDialogContent className="rounded-sm">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remover unidade produtiva?</AlertDialogTitle>
                        <AlertDialogDescription>
                            A unidade produtiva <strong>{deleteTarget.nome}</strong> e os dados operacionais vinculados serão removidos permanentemente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleteMutation.isPending} className="rounded-sm">Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => deleteMutation.mutate(deleteTarget.id)}
                            disabled={deleteMutation.isPending}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-sm"
                        >
                            {deleteMutation.isPending ? "Removendo..." : "Remover"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        )}
    </div>
);
}

type MetricTone = "default" | "primary" | "success";

function PropertyMetricCard({
    icon: Icon,
    label,
    value,
    subtitle,
    tone = "default",
}: {
    icon: React.ElementType<{ className?: string }>;
    label: string;
    value: React.ReactNode;
    subtitle?: string;
    tone?: MetricTone;
}) {
    const toneClass: Record<MetricTone, string> = {
        default: "bg-muted text-muted-foreground",
        primary: "bg-primary/10 text-primary",
        success: "bg-accent text-accent-foreground",
    };

    return (
        <Card size="sm" className="shadow-sm">
            <CardContent className="flex items-start gap-3">
                <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-sm", toneClass[tone])}>
                    <Icon className="size-4" />
                </div>
                <div className="flex min-w-0 flex-col gap-1">
                    <p className="truncate text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
                    <p className="truncate text-lg font-semibold leading-none text-foreground">{value}</p>
                    {subtitle && <p className="truncate text-[10px] text-muted-foreground">{subtitle}</p>}
                </div>
            </CardContent>
        </Card>
    );
}

function FieldHelp({ text }: { text: string }) {
    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger tabIndex={-1} className="outline-none">
                    <HelpCircle className="size-3.5 text-muted-foreground cursor-help shrink-0" aria-hidden />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs">
                    {text}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}

function FieldLabel({ htmlFor, label, help }: { htmlFor?: string; label: string; help: string }) {
    return (
        <Label htmlFor={htmlFor} className="gap-1.5">
            {label}
            <FieldHelp text={help} />
        </Label>
    );
}

function FieldGroup({ children, className }: { children: React.ReactNode; className?: string }) {
    return <div className={cn("space-y-2", className)}>{children}</div>;
}

function getFieldErrorClass(hasError: boolean) {
    return hasError
        ? "border-destructive ring-1 ring-destructive/20 focus-visible:ring-destructive/30"
        : "";
}

function FieldErrorMessage({ message }: { message?: string }) {
    if (!message) return null;
    return <p className="text-xs text-destructive">{message}</p>;
}

const FIRST_INVALID_FIELD_IDS: Partial<Record<keyof CreateUnidadeProdutivaValues, string>> = {
    nome: "nome",
    tipo_propriedade: "tipo",
    cpf_cnpj: "cpf_cnpj",
    inscricao_estadual: "ie",
    cep: "cep",
    logradouro: "logradouro",
    numero: "numero",
    complemento: "complemento",
    bairro: "bairro",
    municipio: "municipio",
    uf: "uf",
    ibge_municipio_codigo: "ibge",
    area_total_ha: "area_total",
    area_app_ha: "area_app",
    area_rl_ha: "area_rl",
};

function focusFieldById(id: string) {
    const field = document.getElementById(id);
    if (!field) return;
    field.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => {
        if ("focus" in field && typeof field.focus === "function") {
            field.focus();
        }
    }, 120);
}

const PROPERTY_MAP_STYLE = {
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
} as const;

const PROPERTY_MAP_STYLE_STREETS = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

type PropertyMapVisualizationMode = "satellite" | "streets";

const CEP_LOOKUP_DEDUP_MS = 2000;
const cepLookupTimestamps = new globalThis.Map<string, number>();

function PropertyGeolocationDialog({
    open,
    onOpenChange,
    initialGeometry,
    coordenadasSede,
    onGeometryChange,
    onAreaChange,
}: {
    open: boolean;
    onOpenChange: (value: boolean) => void;
    initialGeometry: Record<string, unknown> | null;
    coordenadasSede?: string | null;
    onGeometryChange: (geometry: GeoJSON.Geometry | null) => void;
    onAreaChange: (areaHa: number) => void;
}) {
    const mapRef = useRef<MapRef>(null);
    const drawRef = useRef<any>(null);
    const initialViewState = useMemo(() => getMapInitialView(coordenadasSede), [coordenadasSede]);
    const [visualizationMode, setVisualizationMode] = useState<PropertyMapVisualizationMode>("satellite");
    const [geometry, setGeometry] = useState<GeoJSON.Feature<GeoJSON.Geometry> | null>(
        normalizeGeometry(initialGeometry)
    );
    const [calculatedArea, setCalculatedArea] = useState(() => geometryAreaHa(normalizeGeometry(initialGeometry)));

    const updateLocalGeometry = useCallback((geom: any) => {
        if (!geom) {
            setGeometry(null);
            setCalculatedArea(0);
            return;
        }
        const feature = { type: "Feature", properties: {}, geometry: geom };
        setGeometry(feature as any);
        setCalculatedArea(geometryAreaHa(feature as any));
    }, []);

    const handleConfirm = useCallback(() => {
        onGeometryChange(geometry?.geometry ?? null);
        onAreaChange(calculatedArea);
        onOpenChange(false);
    }, [geometry, calculatedArea, onGeometryChange, onAreaChange, onOpenChange]);

    const clearGeometry = useCallback(() => {
        const map = mapRef.current?.getMap() as any;
        if (drawRef.current && map) {
            drawRef.current.deleteAll();
            drawRef.current.changeMode("draw_polygon");
        }
        updateLocalGeometry(null);
    }, [updateLocalGeometry]);

    useEffect(() => {
        if (!open) return;
        const nextGeometry = normalizeGeometry(initialGeometry);
        setGeometry(nextGeometry);
        setCalculatedArea(geometryAreaHa(nextGeometry));
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
                        // O controle pode já ter sido removido pelo ciclo do mapa.
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
                            draw.deleteAll();
                            draw.add(nextGeometry);
                        } else {
                            draw.changeMode("draw_polygon");
                        }

                        const onChange = (event: { features?: Array<GeoJSON.Feature<GeoJSON.Geometry>> }) => {
                            const feature = event.features?.[0] ?? null;
                            updateLocalGeometry(feature?.geometry ?? null);
                        };

                        const onDelete = () => updateLocalGeometry(null);
                        mapInstance.on("draw.create", onChange);
                        mapInstance.on("draw.update", onChange);
                        mapInstance.on("draw.delete", onDelete);

                        if (!mounted) {
                            mapInstance.off("draw.create", onChange);
                            mapInstance.off("draw.update", onChange);
                            mapInstance.off("draw.delete", onDelete);
                        }
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
                    // Ignorado: o mapa já pode ter desmontado.
                }
                drawRef.current = null;
            }
        };
    }, [initialGeometry, open, updateLocalGeometry]);

    useEffect(() => {
        const map = mapRef.current?.getMap() as any;
        if (!map || !geometry) return;

        try {
            const bbox = turf.bbox(geometry);
            map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 40, duration: 800 });
        } catch {
            // Geometrias invalidadas nao devem impedir o cadastro.
        }
    }, [geometry]);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-5xl rounded-sm p-0 overflow-hidden">
                <DialogHeader className="hidden">
                    <DialogTitle>Geolocalização da Unidade Produtiva</DialogTitle>
                </DialogHeader>
                <div className="relative h-[600px] w-full">
                    {open && (
                        <Map
                            ref={mapRef}
                            mapLib={maplibregl}
                            initialViewState={initialViewState}
                            mapStyle={(visualizationMode === "satellite" ? PROPERTY_MAP_STYLE : PROPERTY_MAP_STYLE_STREETS) as any}
                            style={{ width: "100%", height: "100%" }}
                        >
                            <NavigationControl position="top-right" />
                            {geometry && (
                                <Source id="property-geometry" type="geojson" data={geometry}>
                                    <Layer
                                        id="property-geometry-fill"
                                        type="fill"
                                        paint={{
                                            "fill-color": "#22c55e",
                                            "fill-opacity": 0.14,
                                        }}
                                    />
                                    <Layer
                                        id="property-geometry-line"
                                        type="line"
                                        paint={{
                                            "line-color": "#16a34a",
                                            "line-width": 2,
                                        }}
                                    />
                                </Source>
                            )}
                        </Map>
                    )}

                    <div className="absolute top-4 right-4 z-10 pointer-events-none">
                        <MapVisualizationToggle
                            className="pointer-events-auto"
                            checked={visualizationMode === "satellite"}
                            onCheckedChange={(checked) => setVisualizationMode(checked ? "satellite" : "streets")}
                        />
                    </div>

                    <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
                        <div className="bg-background/95 backdrop-blur-sm border rounded-sm shadow-lg p-4 w-72 pointer-events-auto">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="font-semibold text-sm">Editar Geometria</span>
                                    <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => onOpenChange(false)}>
                                        <X className="size-4" />
                                    </Button>
                                </div>
                                <div>
                                    <p className="text-sm font-medium">Perímetro Operacional</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Arraste os vértices para editar. Clique em um vértice e pressione <kbd className="bg-muted px-1 rounded">⌫</kbd> para remover.
                                    </p>
                                </div>
                                {calculatedArea > 0 && (
                                    <div className="bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-400 text-sm rounded-md p-3">
                                        Área calculada: <strong>{formatOptionalArea(calculatedArea)} ha</strong>
                                    </div>
                                )}
                                <div className="flex gap-2">
                                    <Button variant="outline" size="sm" className="flex-1" onClick={() => onOpenChange(false)}>
                                        Cancelar
                                    </Button>
                                    <Button
                                        size="sm"
                                        className="flex-1"
                                        onClick={handleConfirm}
                                        disabled={!geometry && !initialGeometry}
                                    >
                                        <Save className="h-4 w-4 mr-2" />
                                        Confirmar
                                    </Button>
                                </div>
                                <Button type="button" variant="ghost" size="sm" className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive mt-2" onClick={clearGeometry}>
                                    <Trash2 className="size-3 mr-2" />
                                    Limpar desenho
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}

function PropriedadeDialog({
    open, onOpenChange, onSubmit, onInvalidSubmit, fazenda, grupos, isPending,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    onSubmit: (data: CreateCadastroCompletoInput | UpdateCadastroCompletoInput) => void;
    onInvalidSubmit?: (errors: FieldErrors<CreateUnidadeProdutivaValues>) => void;
    fazenda?: UnidadeProdutiva;
    grupos: { id: string; nome: string }[];
    isPending: boolean;
}) {
    const isEdit = !!fazenda;
    const token = useAppStore((s) => s.token);
    const toNullableText = (value: string | null | undefined) => {
        const normalized = value?.trim() ?? "";
        return normalized.length > 0 ? normalized : null;
    };
    const initialCoords = parseCoordenadasSede(fazenda?.coordenadas_sede);
    const [lat, setLat] = useState(initialCoords.lat);
    const [lng, setLng] = useState(initialCoords.lng);
    const [logoUrl, setLogoUrl] = useState<string | null>(fazenda?.logo_url ?? null);
    const [uploadingLogo, setUploadingLogo] = useState(false);
    const [geoDialogOpen, setGeoDialogOpen] = useState(false);
    const [coordinateErrors, setCoordinateErrors] = useState<{ lat?: string; lng?: string }>({});
    const [geometry, setGeometry] = useState<GeoJSON.Geometry | null>(
        normalizeGeometry(fazenda?.geometria ?? null)?.geometry ?? null
    );
    const [calculatedArea, setCalculatedArea] = useState<number>(
        geometryAreaHa(normalizeGeometry(fazenda?.geometria ?? null))
    );
    const logoInputRef = useRef<HTMLInputElement>(null);
    const resolvedLogoUrl = resolveLogo(logoUrl);

    useEffect(() => {
        const nextGeometry = normalizeGeometry(fazenda?.geometria ?? null)?.geometry ?? null;
        setGeometry(nextGeometry);
        setCalculatedArea(geometryAreaHa(normalizeGeometry(fazenda?.geometria ?? null)));
    }, [fazenda?.geometria]);

    const emptyValues = {
        nome: "",
        tipo_propriedade: "fazenda" as const,
        cpf_cnpj: "",
        inscricao_estadual: "",
        area_total_ha: 0,
        area_app_ha: 0,
        area_rl_ha: 0,
        cep: "",
        logradouro: "",
        numero: "",
        complemento: "",
        bairro: "",
        municipio: "",
        uf: "",
        ibge_municipio_codigo: "",
        coordenadas_sede: "",
        ativo: true,
    };

    const editValues = fazenda ? {
        nome: fazenda.nome,
        tipo_propriedade: normalizeTipo(fazenda.tipo_propriedade),
        cpf_cnpj: fazenda.cpf_cnpj ?? "",
        inscricao_estadual: fazenda.inscricao_estadual ?? "",
        area_total_ha: fazenda.area_total_ha ?? 0,
        area_app_ha: fazenda.area_app_ha ?? 0,
        area_rl_ha: fazenda.area_rl_ha ?? 0,
        cep: fazenda.cep ?? "",
        logradouro: fazenda.logradouro ?? "",
        numero: fazenda.numero ?? "",
        complemento: fazenda.complemento ?? "",
        bairro: fazenda.bairro ?? "",
        municipio: fazenda.municipio ?? "",
        uf: fazenda.uf ?? "",
        ibge_municipio_codigo: fazenda.ibge_municipio_codigo ?? "",
        coordenadas_sede: fazenda.coordenadas_sede ?? "",
        ativo: fazenda.ativo ?? true,
    } : emptyValues;

    const { register, handleSubmit, setValue, control, formState: { errors } } = useForm<CreateUnidadeProdutivaValues>({
        resolver: zodResolver(propriedadeFormSchema),
        defaultValues: editValues,
    });
    const cepValue = useWatch({ control, name: "cep" });
    const areaTotalValue = useWatch({ control, name: "area_total_ha" });
    const areaAppValue = useWatch({ control, name: "area_app_ha" });
    const areaRlValue = useWatch({ control, name: "area_rl_ha" });

    useEffect(() => {
        const firstInvalidFieldName = Object.keys(errors)[0] as keyof CreateUnidadeProdutivaValues | undefined;
        if (!firstInvalidFieldName) return;
        const fieldId = FIRST_INVALID_FIELD_IDS[firstInvalidFieldName];
        if (fieldId) {
            focusFieldById(fieldId);
        }
    }, [errors]);

    function handleFormSubmit(data: CreateUnidadeProdutivaValues) {
        const normalizedLat = normalizeCoordinate(lat);
        const normalizedLng = normalizeCoordinate(lng);
        setCoordinateErrors({});

        if ((normalizedLat && !normalizedLng) || (!normalizedLat && normalizedLng)) {
            if (!normalizedLat) {
                setCoordinateErrors({ lat: "Latitude obrigatória" });
                focusFieldById("lat");
            } else {
                setCoordinateErrors({ lng: "Longitude obrigatória" });
                focusFieldById("lng");
            }
            toast.error("Informe latitude e longitude, ou deixe ambos em branco.");
            return;
        }

        if (
            (normalizedLat && !isCoordinateInRange(normalizedLat, -90, 90)) ||
            (normalizedLng && !isCoordinateInRange(normalizedLng, -180, 180))
        ) {
            const nextCoordinateErrors: { lat?: string; lng?: string } = {};
            if (normalizedLat && !isCoordinateInRange(normalizedLat, -90, 90)) {
                nextCoordinateErrors.lat = "Valor inválido";
            }
            if (normalizedLng && !isCoordinateInRange(normalizedLng, -180, 180)) {
                nextCoordinateErrors.lng = "Valor inválido";
            }
            setCoordinateErrors(nextCoordinateErrors);
            focusFieldById(nextCoordinateErrors.lat ? "lat" : "lng");
            toast.error("Coordenadas inválidas. Verifique latitude e longitude.");
            return;
        }

        const coords = normalizedLat && normalizedLng ? `${normalizedLat},${normalizedLng}` : "";
        const payload = buildOperationalCadastroPayload({
            id: fazenda?.id,
            nome: data.nome,
            tipo_propriedade: data.tipo_propriedade,
            cpf_cnpj: toNullableText(data.cpf_cnpj),
            inscricao_estadual: toNullableText(data.inscricao_estadual),
            area_total_ha: typeof data.area_total_ha === "number" ? data.area_total_ha : undefined,
            area_app_ha: typeof data.area_app_ha === "number" ? data.area_app_ha : undefined,
            area_rl_ha: typeof data.area_rl_ha === "number" ? data.area_rl_ha : undefined,
            cep: toNullableText(data.cep),
            logradouro: toNullableText(data.logradouro),
            numero: toNullableText(data.numero),
            complemento: toNullableText(data.complemento),
            bairro: toNullableText(data.bairro),
            municipio: toNullableText(data.municipio),
            uf: toNullableText(data.uf),
            ibge_municipio_codigo: toNullableText(data.ibge_municipio_codigo),
            coordenadas_sede: coords || null,
            geometria: geometry,
            ativo: data.ativo ?? true,
        });

        onSubmit(payload);
    }

    async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file || !fazenda?.id) return;
        setUploadingLogo(true);
        try {
            const form = new FormData();
            form.append("arquivo", file);
            const res = await apiFetch<{ logo_url: string }>(
                `/unidades-produtivas/${fazenda.id}/logo`,
                { method: "POST", body: form }
            );
            setLogoUrl(res.logo_url);
            toast.success("Logo atualizado com sucesso.");
        } catch {
            toast.error("Erro ao enviar o logo.");
        } finally {
            setUploadingLogo(false);
            if (logoInputRef.current) logoInputRef.current.value = "";
        }
    }

    async function buscarCep() {
        const cepVal = cepValue?.replace(/\D/g, "");
        if (!cepVal || cepVal.length < 8) { toast.error("CEP inválido"); return; }
        const now = Date.now();
        const lastLookupAt = cepLookupTimestamps.get(cepVal) ?? 0;
        if (now - lastLookupAt < CEP_LOOKUP_DEDUP_MS) return;
        cepLookupTimestamps.set(cepVal, now);
        try {
            const dados = await apiFetch<Record<string, string>>(
                `/integracoes/regulatorias/cep/${cepVal}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const hasEndereco = Boolean(
                dados?.logradouro || dados?.bairro || dados?.municipio || dados?.uf || dados?.ibge_municipio_codigo
            );
            const enderecoFields = ["logradouro", "numero", "complemento", "bairro", "municipio", "uf", "ibge_municipio_codigo"] as const;
            const applyField = (field: (typeof enderecoFields)[number], value: string) =>
                setValue(field, value, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
            if (!hasEndereco) {
                enderecoFields.forEach((field) => applyField(field, ""));
                toast.error("CEP não encontrado.");
                return;
            }
            enderecoFields.forEach((field) => {
                applyField(field, typeof dados?.[field] === "string" ? dados[field] : "");
            });
            toast.success("Endereço preenchido automaticamente.");
        } catch {
            ["logradouro", "numero", "complemento", "bairro", "municipio", "uf", "ibge_municipio_codigo"].forEach((field) =>
                setValue(field as keyof CreateUnidadeProdutivaValues, "", { shouldDirty: true, shouldTouch: true, shouldValidate: true })
            );
            toast.error("CEP não encontrado.");
        }
    }

    const cepField = register("cep");

    return (
        <>
            <Dialog open={open} onOpenChange={(value) => {
                if (!value) setGeoDialogOpen(false);
                onOpenChange(value);
            }}>
                <DialogContent className="flex max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-5xl flex-col gap-0 overflow-hidden rounded-sm p-0">
                    <DialogHeader className="shrink-0">
                        <div className="flex items-center gap-2 px-5 pt-5">
                            <Landmark className="size-5 text-primary" />
                            <DialogTitle>{isEdit ? "Editar Unidade Produtiva" : "Nova Unidade Produtiva"}</DialogTitle>
                        </div>
                        <DialogDescription className="px-5 pb-4">
                            {isEdit
                                ? "Atualize os dados operacionais da unidade produtiva."
                                : "Cadastre a operação, a sede e a localização da unidade produtiva."}
                        </DialogDescription>
                    </DialogHeader>

                    <form onSubmit={handleSubmit(handleFormSubmit, onInvalidSubmit)} className="flex min-h-0 flex-1 flex-col overflow-hidden">
                        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
                            <div className="grid gap-4 lg:grid-cols-2">
                            {(Object.keys(errors).length > 0 || coordinateErrors.lat || coordinateErrors.lng) && (
                                <Alert variant="destructive" className="rounded-sm lg:col-span-2">
                                    <AlertTriangle className="size-4" />
                                    <AlertDescription>
                                        Preencha os campos obrigatórios.
                                    </AlertDescription>
                                </Alert>
                            )}

                            {/* Identificação operacional */}
                            <div className="grid gap-3 rounded-sm border bg-muted/20 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Identificação operacional</p>
                                <FieldGroup>
                                    <FieldLabel htmlFor="nome" label="Nome *" help="Nome pelo qual a propriedade é conhecida." />
                                    <Input
                                        id="nome"
                                        placeholder="Ex: Fazenda Santa Maria"
                                        {...register("nome")}
                                        disabled={isPending}
                                        aria-invalid={Boolean(errors.nome)}
                                        className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.nome)))}
                                    />
                                    <FieldErrorMessage message={errors.nome?.message} />
                                </FieldGroup>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <FieldGroup>
                                        <FieldLabel htmlFor="tipo" label="Tipo *" help="Classificação da propriedade." />
                                        <Controller
                                            control={control}
                                            name="tipo_propriedade"
                                            render={({ field, fieldState }) => (
                                                <Select
                                                    key={field.value || "empty"}
                                                    value={normalizeTipo(field.value)}
                                                    onValueChange={field.onChange}
                                                    disabled={isPending}
                                                >
                                                    <SelectTrigger
                                                        id="tipo"
                                                        aria-invalid={fieldState.invalid}
                                                        className={cn("rounded-sm", getFieldErrorClass(fieldState.invalid))}
                                                    >
                                                        {TIPO_LABEL[normalizeTipo(field.value)] ?? "Selecione o tipo..."}
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {Object.entries(TIPO_LABEL).map(([value, label]) => (
                                                            <SelectItem key={value} value={value}>{label}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        />
                                        <FieldErrorMessage message={errors.tipo_propriedade?.message} />
                                    </FieldGroup>
                                    <FieldGroup>
                                        <FieldLabel htmlFor="cpf_cnpj" label="CPF / CNPJ" help="Documento do proprietário ou pessoa jurídica." />
                                        <Input
                                            id="cpf_cnpj"
                                            placeholder="000.000.000-00"
                                            {...register("cpf_cnpj")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.cpf_cnpj)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.cpf_cnpj)))}
                                        />
                                        <FieldErrorMessage message={errors.cpf_cnpj?.message} />
                                    </FieldGroup>
                                </div>

                                <FieldGroup>
                                    <FieldLabel htmlFor="ie" label="Inscrição Estadual" help="Registro junto à Secretaria de Fazenda do estado." />
                                    <Input
                                        id="ie"
                                        placeholder="Ex: 123.456.789.000"
                                        {...register("inscricao_estadual")}
                                        disabled={isPending}
                                        aria-invalid={Boolean(errors.inscricao_estadual)}
                                        className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.inscricao_estadual)))}
                                    />
                                    <FieldErrorMessage message={errors.inscricao_estadual?.message} />
                                </FieldGroup>
                            </div>

                            {/* Endereço da sede */}
                            <div className="grid gap-3 rounded-sm border bg-muted/20 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Endereço da sede</p>
                                {/* CEP com botão de busca */}
                                <FieldGroup>
                                    <FieldLabel htmlFor="cep" label="CEP" help="CEP da sede operacional." />
                                    <div className="flex gap-1">
                                        <Input
                                            id="cep"
                                            placeholder="00000-000"
                                            {...cepField}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.cep)}
                                            className={cn("h-8 flex-1 rounded-sm", getFieldErrorClass(Boolean(errors.cep)))}
                                        />
                                        <Button type="button" variant="outline" size="sm" onClick={buscarCep} disabled={isPending} className="rounded-sm">Buscar</Button>
                                    </div>
                                    <FieldErrorMessage message={errors.cep?.message} />
                                </FieldGroup>

                                <div className="grid gap-3 sm:grid-cols-4">
                                    {/* Logradouro (maior espaço) */}
                                    <FieldGroup className="sm:col-span-3">
                                        <FieldLabel htmlFor="logradouro" label="Logradouro" help="Rua, estrada ou rodovia." />
                                        <Input
                                            id="logradouro"
                                            placeholder="Ex: Estrada Rural Km 12, s/n"
                                            {...register("logradouro")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.logradouro)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.logradouro)))}
                                        />
                                        <FieldErrorMessage message={errors.logradouro?.message} />
                                    </FieldGroup>
                                    {/* Número */}
                                    <FieldGroup className="sm:col-span-1">
                                        <FieldLabel htmlFor="numero" label="Número" help="Número do endereço." />
                                        <Input
                                            id="numero"
                                            placeholder="Ex: 123, s/n"
                                            {...register("numero")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.numero)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.numero)))}
                                        />
                                        <FieldErrorMessage message={errors.numero?.message} />
                                    </FieldGroup>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <FieldGroup>
                                        <FieldLabel htmlFor="complemento" label="Complemento" help="Complemento do endereço." />
                                        <Input
                                            id="complemento"
                                            placeholder="Ex: Apto 12"
                                            {...register("complemento")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.complemento)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.complemento)))}
                                        />
                                        <FieldErrorMessage message={errors.complemento?.message} />
                                    </FieldGroup>

                                    <FieldGroup>
                                        <FieldLabel htmlFor="bairro" label="Bairro / Distrito" help="Bairro ou comunidade rural." />
                                        <Input
                                            id="bairro"
                                            placeholder="Zona Rural"
                                            {...register("bairro")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.bairro)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.bairro)))}
                                        />
                                        <FieldErrorMessage message={errors.bairro?.message} />
                                    </FieldGroup>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_96px_140px]">
                                    <FieldGroup>
                                        <FieldLabel htmlFor="municipio" label="Município da sede" help="Município da sede operacional." />
                                        <Input
                                            id="municipio"
                                            placeholder="São Paulo"
                                            {...register("municipio")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.municipio)}
                                            className={cn("h-8 rounded-sm", getFieldErrorClass(Boolean(errors.municipio)))}
                                        />
                                        <FieldErrorMessage message={errors.municipio?.message} />
                                    </FieldGroup>

                                    <FieldGroup>
                                        <FieldLabel htmlFor="uf" label="UF da sede" help="Sigla do estado da sede operacional." />
                                        <Input
                                            id="uf"
                                            placeholder="SP"
                                            maxLength={2}
                                            {...register("uf")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.uf)}
                                            className={cn("h-8 rounded-sm uppercase", getFieldErrorClass(Boolean(errors.uf)))}
                                        />
                                        <FieldErrorMessage message={errors.uf?.message} />
                                    </FieldGroup>

                                    <FieldGroup>
                                        <FieldLabel htmlFor="ibge" label="Código IBGE" help="Código de 7 dígitos do município da sede operacional." />
                                        <Input
                                            id="ibge"
                                            placeholder="3550308"
                                            maxLength={7}
                                            {...register("ibge_municipio_codigo")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.ibge_municipio_codigo)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(errors.ibge_municipio_codigo)))}
                                        />
                                        <FieldErrorMessage message={errors.ibge_municipio_codigo?.message} />
                                    </FieldGroup>
                                </div>
                            </div>

                            {/* Indicadores operacionais */}
                            <div className="grid gap-3 rounded-sm border bg-muted/20 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Indicadores operacionais</p>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="area_total" label="Área informada" help="Área declarada para referência operacional." />
                                        <Input
                                            id="area_total"
                                            type="number"
                                            step="0.0001"
                                            placeholder="0,0000"
                                            {...register("area_total_ha")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.area_total_ha)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(errors.area_total_ha)))}
                                        />
                                        <FieldErrorMessage message={errors.area_total_ha?.message} />
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="area_total_calculada" label="Área geométrica" help="Área calculada automaticamente pela geometria operacional." />
                                        <Input
                                            id="area_total_calculada"
                                            type="text"
                                            placeholder="Calculada pela geometria operacional"
                                            value={calculatedArea > 0 ? formatOptionalArea(calculatedArea) : ""}
                                            disabled
                                            readOnly
                                            className="h-8 rounded-sm tabular-nums"
                                        />
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="area_app" label="APP ref." help="Valor referencial da operação. Não representa o dado oficial do imóvel rural." />
                                        <Input
                                            id="area_app"
                                            type="number"
                                            step="0.0001"
                                            placeholder="0,0000"
                                            {...register("area_app_ha")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.area_app_ha)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(errors.area_app_ha)))}
                                        />
                                        <FieldErrorMessage message={errors.area_app_ha?.message} />
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="area_rl" label="Reserva Legal ref." help="Valor referencial da operação. Não representa o dado oficial do imóvel rural." />
                                        <Input
                                            id="area_rl"
                                            type="number"
                                            step="0.0001"
                                            placeholder="0,0000"
                                            {...register("area_rl_ha")}
                                            disabled={isPending}
                                            aria-invalid={Boolean(errors.area_rl_ha)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(errors.area_rl_ha)))}
                                        />
                                        <FieldErrorMessage message={errors.area_rl_ha?.message} />
                                    </div>
                                </div>

                                <div className="mt-1 flex items-center justify-between rounded-sm border border-emerald-100 bg-emerald-50 p-3 dark:border-emerald-900/30 dark:bg-emerald-950/20">
                                    <span className="text-[10px] font-bold uppercase leading-none text-emerald-800 dark:text-emerald-400">Área Útil Estimada (Real)</span>
                                    <span className="font-mono text-xs font-bold text-emerald-700 dark:text-emerald-300">
                                        {Math.max(
                                            0,
                                            toAreaNumber(areaTotalValue) - toAreaNumber(areaAppValue) - toAreaNumber(areaRlValue)
                                        ).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} ha
                                    </span>
                                </div>
                                <p className="flex items-start gap-1.5 rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800/30 dark:bg-amber-950/20 dark:text-amber-300">
                                    <span className="mt-0.5 shrink-0">⚠️</span>
                                    <span>Os valores desta seção são referenciais da operação. Os dados ambientais e fundiários oficiais devem ser mantidos no cadastro do Imóvel Rural.</span>
                                </p>
                            </div>

                            {/* Localização operacional */}
                            <div className="grid gap-3 rounded-sm border bg-muted/20 p-4">
                                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Localização operacional</p>

                                <div className="grid gap-3 sm:grid-cols-2">
                                    {/* GPS */}
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="lat" label="Latitude da sede" help="Ex: -23.5505" />
                                        <Input
                                            id="lat"
                                            placeholder="-23.5505"
                                            value={lat}
                                            onChange={(e) => {
                                                setLat(e.target.value);
                                                if (coordinateErrors.lat) {
                                                    setCoordinateErrors((current) => ({ ...current, lat: undefined }));
                                                }
                                            }}
                                            disabled={isPending}
                                            aria-invalid={Boolean(coordinateErrors.lat)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(coordinateErrors.lat)))}
                                        />
                                        <FieldErrorMessage message={coordinateErrors.lat} />
                                    </div>
                                    <div className="grid gap-1.5">
                                        <FieldLabel htmlFor="lng" label="Longitude da sede" help="Ex: -46.6333" />
                                        <Input
                                            id="lng"
                                            placeholder="-46.6333"
                                            value={lng}
                                            onChange={(e) => {
                                                setLng(e.target.value);
                                                if (coordinateErrors.lng) {
                                                    setCoordinateErrors((current) => ({ ...current, lng: undefined }));
                                                }
                                            }}
                                            disabled={isPending}
                                            aria-invalid={Boolean(coordinateErrors.lng)}
                                            className={cn("h-8 rounded-sm tabular-nums", getFieldErrorClass(Boolean(coordinateErrors.lng)))}
                                        />
                                        <FieldErrorMessage message={coordinateErrors.lng} />
                                    </div>

                                    {/* Logo */}
                                    <div className="grid gap-1.5 sm:col-span-2">
                                        <Label>Logo</Label>
                                        <div className="mt-1.5 flex items-center gap-3">
                                            <div className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-sm bg-muted ring-1 ring-foreground/10">
                                                {resolvedLogoUrl
                                                    ? <img src={resolvedLogoUrl} alt="Logo" className="size-12 object-cover" />
                                                    : <Trees className="size-6 text-muted-foreground/40" />}
                                            </div>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="sm"
                                                onClick={() => logoInputRef.current?.click()}
                                                disabled={uploadingLogo || !fazenda?.id}
                                                className="h-8 rounded-sm"
                                            >
                                                {uploadingLogo ? "..." : "Alterar"}
                                            </Button>
                                            <input type="file" hidden ref={logoInputRef} accept="image/*" onChange={handleLogoUpload} />
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-2 flex items-center justify-between rounded-sm border bg-background p-3">
                                    <div className="space-y-0.5">
                                        <Label htmlFor="ativo" className="text-xs font-bold uppercase">Status operacional</Label>
                                        <p className="text-[10px] text-muted-foreground">Define se a unidade produtiva está em uso operacional.</p>
                                    </div>
                                    <Controller
                                        control={control}
                                        name="ativo"
                                        render={({ field }) => (
                                            <Switch
                                                id="ativo"
                                                checked={field.value}
                                                onCheckedChange={field.onChange}
                                                disabled={isPending}
                                            />
                                        )}
                                    />
                                </div>

                                <div className="rounded-sm border bg-background p-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Geolocalização da Unidade Produtiva</p>
                                            <p className="text-xs text-muted-foreground">Abra o mapa para desenhar a geometria operacional da unidade produtiva.</p>
                                        </div>
                                        <Button type="button" size="sm" variant="outline" className="shrink-0 rounded-sm" onClick={() => setGeoDialogOpen(true)}>
                                            <MapPinned className="mr-1.5 size-3.5" />
                                            Abrir mapa da unidade produtiva
                                        </Button>
                                    </div>
                                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                                        <div>
                                            <p className="text-[10px] font-semibold uppercase text-muted-foreground">Geometria operacional</p>
                                            <p className="text-sm">{geometry ? "Desenhada" : "Não informada"}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-semibold uppercase text-muted-foreground">Área calculada pela geometria operacional</p>
                                            <p className="text-sm">{calculatedArea > 0 ? `${formatOptionalArea(calculatedArea)} ha` : "—"}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {isEdit ? (
                                <ImoveisVinculadosCard
                                    unidadeProdutivaId={fazenda?.id}
                                    territory={fazenda?.territorio ?? null}
                                    className="lg:col-span-2"
                                />
                            ) : (
                                <div className="grid gap-2 rounded-sm border border-dashed bg-muted/10 p-4 lg:col-span-2">
                                    <p className="text-sm font-semibold">Imóveis Rurais Vinculados</p>
                                    <p className="text-xs text-muted-foreground">
                                        Após salvar a unidade produtiva, você poderá cadastrar ou vincular um Imóvel Rural sem misturar documentos fundiários à edição operacional.
                                    </p>
                                </div>
                            )}
                            </div>
                        </div>

                        <DialogFooter className="shrink-0 border-t px-5 py-3">
                            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending} className="rounded-sm" size="sm">
                                Cancelar
                            </Button>
                            <Button type="submit" disabled={isPending} className="rounded-sm" size="sm">
                                {isPending ? "Salvando..." : isEdit ? "Salvar Alterações" : "Cadastrar Unidade Produtiva"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
            <PropertyGeolocationDialog
                open={geoDialogOpen}
                onOpenChange={setGeoDialogOpen}
                initialGeometry={geometry ? { type: "Feature", properties: {}, geometry } : null}
                coordenadasSede={fazenda?.coordenadas_sede}
                onGeometryChange={setGeometry}
                onAreaChange={setCalculatedArea}
            />
        </>
    );
}
