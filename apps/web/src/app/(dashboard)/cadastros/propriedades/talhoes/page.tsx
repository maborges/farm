"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Map, { NavigationControl, Source, Layer, MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import * as turf from "@turf/turf";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import type { UnidadeProdutiva } from "@/types/global";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription
} from "@/components/ui/sheet";
import { toast } from "sonner";
import {
    Save, Pencil, MapPin, Layers,
    CheckCircle2, XCircle, Square, X, Trash2, RotateCcw
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { MapVisualizationToggle } from "@/components/shared/map-visualization-toggle";
import { TalhaoFormDialog } from "@/components/cadastros/talhao-form-dialog";
import { StatusBadge } from "@/components/ui/status-badge";

// Satellite base style (no token required)
const MAP_STYLE: any = {
    version: 8,
    sources: {
        "sat": {
            type: "raster",
            tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
            tileSize: 256,
            // A cobertura de alta resolução do Esri World_Imagery varia por região e,
            // em áreas rurais, costuma parar por volta do zoom 17. Acima disso o Esri
            // responde com um tile de erro ("Map data not yet available"). Fixando o
            // maxzoom da fonte, o MapLibre para de pedir tiles inexistentes e faz
            // overzoom (amplia o último tile válido) — o usuário ainda pode aproximar
            // a câmera livremente para desenhar com precisão.
            maxzoom: 17,
            attribution: "© Esri"
        }
    },
    layers: [{ id: "sat-layer", type: "raster", source: "sat" }]
};

const MAP_STYLE_STREETS = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

type MapVisualizationMode = "satellite" | "streets";

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

type Mode = "view" | "editing_geom";

interface Talhao {
    id: string;
    nome: string;
    tipo?: string;
    codigo?: string;
    descricao?: string;
    parent_id?: string;
    area_hectares?: number;
    area_hectares_manual?: number;
    centroide_lat?: number;
    centroide_lng?: number;
    dados_extras?: {
        tipo_solo?: string;
        textura_solo?: string;
        relevo?: string;
        irrigado?: boolean;
        sistema_irrigacao?: string;
        [key: string]: any;
    };
    ativo: boolean;
    geometria?: any;
    created_at: string;
    updated_at: string;
}

const defaultCenter = { longitude: -51.92, latitude: -23.42, zoom: 5 };

function parseCoordenadasSede(value?: string | null) {
    if (!value) return null;

    const parts = value.split(",");
    if (parts.length !== 2) return null;

    const latitude = Number(parts[0].trim());
    const longitude = Number(parts[1].trim());

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
    if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;

    return { longitude, latitude, zoom: 13 };
}


export default function TalhoesPage() {
    const { activeFazendaId, unidadesProdutivasAutorizadas } = useAppStore();
    const queryClient = useQueryClient();
    const mapRef = useRef<MapRef>(null);
    const drawRef = useRef<any>(null);

    const [mode, setMode] = useState<Mode>("view");
    const [visualizationMode, setVisualizationMode] = useState<MapVisualizationMode>("satellite");
    const [selectedTalhao, setSelectedTalhao] = useState<Talhao | null>(null);
    const [sheetOpen, setSheetOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [drawnGeometry, setDrawnGeometry] = useState<any>(null);
    const [drawnAreaHa, setDrawnAreaHa] = useState<number | null>(null);

    // ── Queries ──────────────────────────────────────────────────────────────
    const { data: fazendaDetalhe } = useQuery<UnidadeProdutiva | null>({
        queryKey: ["unidades-produtivas", activeFazendaId, "georreferenciamento"],
        queryFn: () => activeFazendaId
            ? apiFetch<UnidadeProdutiva>(`/unidades-produtivas/${activeFazendaId}`)
            : Promise.resolve(null),
        enabled: !!activeFazendaId,
        staleTime: 60_000,
    });

    const fazendaAtualResumo = unidadesProdutivasAutorizadas.find((f) => f.id === activeFazendaId);
    const fazendaAtual = fazendaDetalhe ?? fazendaAtualResumo;
    const propriedadeCenter = parseCoordenadasSede(fazendaAtual?.coordenadas_sede);
    const fazendaCenter = propriedadeCenter ?? defaultCenter;

    const { data: allAreas = [], isLoading } = useQuery<Talhao[]>({
        queryKey: ["areas-rurais", activeFazendaId],
        queryFn: async () => {
            const res = await apiFetch<Talhao[]>(`/cadastros/areas-rurais?unidade_produtiva_id=${activeFazendaId}`);
            return res.map(t => {
                if (typeof t.geometria === "string") {
                    try { t.geometria = JSON.parse(t.geometria); } catch { t.geometria = null; }
                }
                return t;
            });
        },
        enabled: !!activeFazendaId
    });

    // Separar por tipos para lógica de georeferenciamento e UI
    const glebas = allAreas.filter(a => a.tipo === "GLEBA");
    const raizes = allAreas.filter(a => a.tipo === "AREA_RURAL");
    
    // Filtrar áreas produtivas (Talhões, Piquetes, Subtalhões, Zonas de Manejo e Áreas Operacionais)
    const TIPOS_PRODUTIVOS = new Set(["TALHAO", "PIQUETE", "SUBTALHAO", "ZONA_MANEJO", "AREA_OPERACIONAL"]);
    const displayAreas = allAreas.filter(a => TIPOS_PRODUTIVOS.has(a.tipo)).sort((a, b) => a.nome.localeCompare(b.nome));

    // Mapa de gleba_id → gleba
    const glebaMap = glebas.reduce<Record<string, Talhao>>((acc, g) => {
        acc[g.id] = g;
        return acc;
    }, {});

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: any }) =>
            apiFetch(`/cadastros/areas-rurais/${id}`, { method: "PATCH", body: data }),
        onSuccess: (_result, variables) => {
            queryClient.invalidateQueries({ queryKey: ["areas-rurais", activeFazendaId] });
            const cleared = variables.data?.geometria === null;
            toast.success(cleared ? "Região desmarcada com sucesso" : "Geometria salva");
            cancelMode();
            setSheetOpen(false);
            if (cleared) setSelectedTalhao(null);
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao salvar geometria")
    });

    // ── MapboxDraw setup ──────────────────────────────────────────────────────
    const initDraw = useCallback(async () => {
        const map = mapRef.current?.getMap() as any;
        if (!map) return;
        if (drawRef.current) return;

        const { default: MapboxDraw } = await import("@mapbox/mapbox-gl-draw");

        await new Promise<void>((resolve) => {
            const doInit = () => {
                if (drawRef.current) {
                    resolve();
                    return;
                }
                try {
                    const draw = new MapboxDraw({
                        displayControlsDefault: false,
                        controls: { polygon: true, trash: true },
                        styles: DRAW_STYLES,
                    });

                    map.addControl(draw);
                    drawRef.current = draw;

                    const onChange = (e: any) => {
                        const feature = e.features?.[0];
                        if (feature) {
                            const areaM2 = turf.area(feature);
                            setDrawnAreaHa(Math.round(areaM2 / 10000 * 100) / 100);
                            setDrawnGeometry(feature.geometry);
                        } else {
                            setDrawnAreaHa(null);
                            setDrawnGeometry(null);
                        }
                    };

                    const onDelete = () => {
                        const remaining = draw.getAll()?.features?.[0];
                        if (remaining) {
                            const areaM2 = turf.area(remaining);
                            setDrawnAreaHa(Math.round(areaM2 / 10000 * 100) / 100);
                            setDrawnGeometry(remaining.geometry);
                        } else {
                            setDrawnAreaHa(null);
                            setDrawnGeometry(null);
                        }
                    };

                    map.on("draw.create", onChange);
                    map.on("draw.update", onChange);
                    map.on("draw.delete", onDelete);
                } catch (e) {
                    console.error("MapboxDraw init error", e);
                }
                resolve();
            };

            if (map.isStyleLoaded()) {
                doInit();
            } else {
                // 'load' só dispara uma vez, na primeira carga do mapa — se o mapa já
                // foi carregado antes (ex.: usuário trocando de talhão ou de estilo),
                // esse evento nunca mais ocorre e doInit ficaria pendente para sempre.
                // 'idle' dispara sempre que o mapa termina de carregar/renderizar, e
                // esperamos essa Promise antes de prosseguir (sem corrida com timeouts).
                map.once('idle', doInit);
            }
        });
    }, []);

    const removeDraw = useCallback(() => {
        const map = mapRef.current?.getMap() as any;
        if (drawRef.current && map) {
            try {
                map.removeControl(drawRef.current);
            } catch {
                // O controle pode ja ter sido removido pelo MapLibre.
            }
            drawRef.current = null;
        }
    }, []);

    // ── Mode transitions ──────────────────────────────────────────────────────
    const startEditingGeom = useCallback(async (talhao: Talhao) => {
        setSheetOpen(false);
        setDrawnGeometry(null);
        setDrawnAreaHa(null);
        setSelectedTalhao(talhao);
        setMode("editing_geom");
        await initDraw();

        const draw = drawRef.current;
        if (!draw) return;
        draw.deleteAll();
        if (talhao.geometria) {
            let geom = talhao.geometria;
            if (typeof geom === "string") {
                try { geom = JSON.parse(geom); } catch { geom = null; }
            }
            if (geom) {
                const ids = draw.add({
                    type: "Feature",
                    geometry: geom,
                    properties: {}
                });
                if (ids?.[0]) draw.changeMode("direct_select", { featureId: ids[0] });
                // Calculate area from existing geometry
                const areaM2 = turf.area(geom);
                setDrawnAreaHa(Math.round(areaM2 / 10000 * 100) / 100);
                setDrawnGeometry(geom);
            } else {
                draw.changeMode("draw_polygon");
            }
        } else {
            draw.changeMode("draw_polygon");
        }
    }, [initDraw]);

    const cancelMode = useCallback(() => {
        removeDraw();
        setMode("view");
        setDrawnGeometry(null);
        setDrawnAreaHa(null);
    }, [removeDraw]);

    const clearDrawnPolygon = useCallback(() => {
        const draw = drawRef.current;
        if (draw) {
            draw.deleteAll();
            draw.changeMode("draw_polygon");
        }
        setDrawnGeometry(null);
        setDrawnAreaHa(null);
    }, []);

    const unmarkTalhaoRegion = useCallback((talhao: Talhao) => {
        const draw = drawRef.current;
        if (draw) {
            draw.deleteAll();
        }
        setDrawnGeometry(null);
        setDrawnAreaHa(null);
        updateMutation.mutate({
            id: talhao.id,
            data: {
                geometria: null,
                area_hectares: null,
                centroide_lat: null,
                centroide_lng: null,
            }
        });
    }, [updateMutation]);

    // ── Save actions ──────────────────────────────────────────────────────────
    const saveEditGeom = useCallback(() => {
        if (!drawnGeometry || !selectedTalhao) return;
 
        // Calcular nova área e centroide
        const feature: any = { type: "Feature", geometry: drawnGeometry, properties: {} };
        const areaM2 = turf.area(feature);
        const areaHa = Math.round(areaM2 / 10000 * 100) / 100;
        const centroid = turf.centroid(feature);

        updateMutation.mutate({
            id: selectedTalhao.id,
            data: {
                geometria: drawnGeometry,
                area_hectares: areaHa,
                centroide_lat: centroid.geometry.coordinates[1],
                centroide_lng: centroid.geometry.coordinates[0],
            }
        });
    }, [drawnGeometry, selectedTalhao, updateMutation]);

    // ── Map helpers ───────────────────────────────────────────────────────────
    const flyToTalhao = useCallback((t: Talhao) => {
        if (t.geometria) {
            try {
                const bbox = turf.bbox(t.geometria);
                mapRef.current?.fitBounds(
                    [[bbox[0], bbox[1]], [bbox[2], bbox[3]]],
                    { padding: 80, duration: 900 }
                );
                return;
            } catch {
                // Geometrias invalidas nao devem impedir a navegacao por centroide.
            }
        }
        if (t.centroide_lat && t.centroide_lng) {
            mapRef.current?.flyTo({ center: [t.centroide_lng, t.centroide_lat], zoom: 14, duration: 900 });
        }
    }, []);

    const handleSelectTalhao = useCallback((t: Talhao) => {
        if (mode !== "view") return;
        setSelectedTalhao(t);
        setSheetOpen(true);
        flyToTalhao(t);
    }, [mode, flyToTalhao]);

    // Clean up draw on unmount
    useEffect(() => () => removeDraw(), [removeDraw]);

    useEffect(() => {
        if (mode !== "view") return;

        const center = parseCoordenadasSede(fazendaAtual?.coordenadas_sede);
        if (!center) return;

        mapRef.current?.flyTo({
            center: [center.longitude, center.latitude],
            zoom: center.zoom,
            duration: 900,
        });
    }, [mode, fazendaAtual?.coordenadas_sede]);

    // ── GeoJSON for map layers ────────────────────────────────────────────────
    const geojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: allAreas
            .filter(t => TIPOS_PRODUTIVOS.has(t.tipo) && t.geometria && !(mode === "editing_geom" && t.id === selectedTalhao?.id))
            .map(t => ({
                type: "Feature",
                geometry: t.geometria,
                properties: { 
                    id: t.id, 
                    nome: t.nome, 
                    area: t.area_hectares ?? 0, 
                    tipo: t.tipo,
                    selected: t.id === selectedTalhao?.id 
                }
            }))
    };

    const totalArea = displayAreas.reduce((s, t) => s + (t.area_hectares ?? t.area_hectares_manual ?? 0), 0);
    const mappedCount = displayAreas.filter(t => t.geometria).length;

    return (
        <div className="p-6 space-y-6 h-full flex flex-col">
            <PageHeader
                title="Georreferenciamento"
                description="Visualize e edite a geometria de talhões, piquetes e áreas produtivas no mapa"
                icon={<MapPin className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Cadastros", href: "/cadastros" }, { label: "Propriedades", href: "/cadastros/propriedades" }, { label: "Georreferenciamento" }]}
            />

            <div className="flex-1 flex overflow-hidden border rounded-sm">

            {/* ── Left panel ── */}
            <div className="w-80 flex-shrink-0 border-r flex flex-col overflow-hidden">
                <div className="p-4 border-b space-y-3">
                    <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Estatísticas</h2>
                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="bg-muted rounded-sm p-2">
                            <div className="font-bold text-base">{displayAreas.length}</div>
                            <div className="text-muted-foreground uppercase text-[9px]">Total</div>
                        </div>
                        <div className="bg-muted rounded-sm p-2">
                            <div className="font-bold text-base">{totalArea.toFixed(0)}</div>
                            <div className="text-muted-foreground uppercase text-[9px]">Hectares</div>
                        </div>
                        <div className="bg-muted rounded-sm p-2 border border-primary/20">
                            <div className="font-bold text-base text-primary">{mappedCount}</div>
                            <div className="text-muted-foreground uppercase text-[9px]">Mapeados</div>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {isLoading ? (
                        <div className="p-6 text-center text-sm text-muted-foreground">Carregando...</div>
                    ) : displayAreas.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                            <Square className="h-8 w-8 mx-auto mb-2 opacity-40" />
                            <p className="text-sm font-medium">Nenhuma área</p>
                            <p className="text-xs mt-1">Clique em &quot;Novo&quot; para desenhar no mapa</p>
                        </div>
                    ) : (
                        <div className="p-2 space-y-1">
                            {displayAreas.map(t => (
                                <button
                                    key={t.id}
                                    disabled={mode !== "view"}
                                    onClick={() => handleSelectTalhao(t)}
                                    className={`w-full text-left p-3 rounded-sm border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                                        selectedTalhao?.id === t.id
                                            ? "bg-primary/5 border-primary/20 ring-1 ring-primary/20"
                                            : "border-transparent hover:bg-muted"
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center gap-1.5 mb-0.5">
                                               {t.tipo === "GLEBA" && <Layers size={12} className="text-amber-500" />}
                                               {t.tipo === "TALHAO" && <Square size={12} className="text-green-500" />}
                                               {t.tipo === "PIQUETE" && <Square size={12} className="text-amber-600" />}
                                               {t.tipo === "AREA_RURAL" && <MapPin size={12} className="text-blue-500" />}
                                               <span className="text-[9px] font-bold uppercase text-muted-foreground">
                                                  {t.tipo?.replace("_", " ")}
                                               </span>
                                            </div>
                                            <span className="font-semibold text-sm truncate block">{t.nome}</span>
                                            {t.parent_id && glebaMap[t.parent_id]?.nome && (
                                                <span className="text-[10px] text-muted-foreground">
                                                    Pai: {glebaMap[t.parent_id].nome}
                                                </span>
                                            )}
                                        </div>
                                        <div className="shrink-0">
                                            {t.area_hectares && t.geometria ? (
                                                <Badge className="text-[10px] py-0 h-4 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-sm">
                                                    {t.area_hectares.toFixed(1)} ha
                                                </Badge>
                                            ) : t.area_hectares_manual ? (
                                                <Badge variant="secondary" className="text-[10px] py-0 h-4 rounded-sm">
                                                    {t.area_hectares_manual.toFixed(1)} ha*
                                                </Badge>
                                            ) : null}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                                        {t.geometria ? (
                                            <span className="flex items-center gap-0.5 text-[9px] font-bold text-green-600 uppercase">
                                                <div className="size-1 bg-green-600 rounded-full" />
                                                Mapeado
                                            </span>
                                        ) : (
                                            <span className="flex items-center gap-0.5 text-[9px] font-bold text-amber-600 uppercase">
                                                <div className="size-1 bg-amber-600 rounded-full" />
                                                Sem mapa
                                            </span>
                                        )}
                                        {t.dados_extras?.irrigado && (
                                            <span className="flex items-center gap-0.5 text-[9px] font-bold text-blue-600 uppercase whitespace-nowrap">
                                                <CheckCircle2 className="size-2.5 shrink-0" />
                                                {t.dados_extras?.sistema_irrigacao
                                                    ? t.dados_extras.sistema_irrigacao.replace(/_/g, " ")
                                                    : "Irrigado"}
                                            </span>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Map area ── */}
            <div className="flex-1 relative overflow-hidden">
                <Map
                    ref={mapRef}
                    initialViewState={fazendaCenter}
                    style={{ width: "100%", height: "100%" }}
                    mapStyle={visualizationMode === "satellite" ? MAP_STYLE : MAP_STYLE_STREETS}
                >
                    <NavigationControl position="top-right" />

                    {geojson.features.length > 0 && (
                        <Source id="talhoes-src" type="geojson" data={geojson}>
                            <Layer
                                id="talhoes-fill"
                                type="fill"
                                paint={{
                                    "fill-color": ["case", ["==", ["get", "selected"], true], "#22c55e", "#3b82f6"],
                                    "fill-opacity": ["case", ["==", ["get", "selected"], true], 0.3, 0.15]
                                }}
                            />
                            <Layer
                                id="talhoes-outline"
                                type="line"
                                paint={{
                                    "line-color": ["case", ["==", ["get", "selected"], true], "#16a34a", "#2563eb"],
                                    "line-width": ["case", ["==", ["get", "selected"], true], 2.5, 1.5]
                                }}
                            />
                            <Layer
                                id="talhoes-label"
                                type="symbol"
                                layout={{
                                    "text-field": ["concat",
                                        ["get", "nome"], "\n",
                                        ["number-format", ["get", "area"], { "min-fraction-digits": 1, "max-fraction-digits": 1 }], " ha"
                                    ],
                                    "text-size": 12,
                                    "text-anchor": "center",
                                    "text-allow-overlap": false
                                }}
                                paint={{
                                    "text-color": "#ffffff",
                                    "text-halo-color": "#000000",
                                    "text-halo-width": 1.5
                                }}
                            />
                        </Source>
                    )}
                </Map>

                <div className="absolute top-4 right-4 z-10 pointer-events-none">
                    <MapVisualizationToggle
                        className="pointer-events-auto"
                        checked={visualizationMode === "satellite"}
                        onCheckedChange={(checked) => setVisualizationMode(checked ? "satellite" : "streets")}
                    />
                </div>

                {/* Draw mode panel — somente edição de geometria */}
                {mode !== "view" && (
                    <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
                        <div className="bg-background/95 backdrop-blur-sm border rounded-sm shadow-lg p-4 w-72 pointer-events-auto">
                            {mode === "editing_geom" && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <span className="font-semibold text-sm">Editar Geometria</span>
                                        <Button size="icon" variant="ghost" className="h-6 w-6 rounded-sm" onClick={cancelMode}>
                                            <X className="size-4" />
                                        </Button>
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium">{selectedTalhao?.nome}</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            Arraste os vértices para editar. Clique em um vértice e pressione <kbd className="bg-muted px-1 rounded">⌫</kbd> para remover.
                                        </p>
                                    </div>
                                    {drawnAreaHa !== null && (
                                        <div className="bg-blue-500/10 border border-blue-500/20 text-blue-700 dark:text-blue-300 text-sm rounded-sm p-3">
                                            Área calculada: <strong>{drawnAreaHa} ha</strong>
                                        </div>
                                    )}
                                    {(drawnGeometry || selectedTalhao?.geometria) && (
                                        <div className="space-y-2">
                                            {drawnGeometry && (
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="w-full rounded-sm"
                                                    disabled={updateMutation.isPending}
                                                    onClick={clearDrawnPolygon}
                                                >
                                                    <RotateCcw className="h-4 w-4 mr-2" />
                                                    Limpar Desenho
                                                </Button>
                                            )}
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="w-full rounded-sm text-destructive hover:text-destructive"
                                                disabled={updateMutation.isPending}
                                                onClick={() => {
                                                    if (selectedTalhao?.geometria) {
                                                        unmarkTalhaoRegion(selectedTalhao);
                                                    } else {
                                                        clearDrawnPolygon();
                                                    }
                                                }}
                                            >
                                                <Trash2 className="h-4 w-4 mr-2" />
                                                Desmarcar Região
                                            </Button>
                                        </div>
                                    )}
                                    <div className="flex gap-2">
                                        <Button variant="outline" size="sm" className="flex-1 rounded-sm" onClick={cancelMode}>
                                            Cancelar
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1 rounded-sm"
                                            onClick={saveEditGeom}
                                            disabled={!drawnGeometry || updateMutation.isPending}
                                        >
                                            <Save className="h-4 w-4 mr-2" />
                                            Salvar
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* ── Detail Sheet ── */}
            <Sheet open={sheetOpen} onOpenChange={open => { setSheetOpen(open); if (!open) setSelectedTalhao(null); }}>
                <SheetContent className="w-full sm:max-w-md overflow-y-auto">
                    <SheetHeader>
                        <SheetTitle className="flex items-center gap-2">
                            <Square className="h-4 w-4" />
                            {selectedTalhao?.nome}
                            {selectedTalhao?.codigo && (
                                <Badge variant="outline" className="text-xs font-normal ml-1">
                                    {selectedTalhao.codigo}
                                </Badge>
                            )}
                        </SheetTitle>
                        <SheetDescription>
                            {selectedTalhao?.area_hectares
                                ? `${selectedTalhao.area_hectares.toFixed(1)} ha (calculado)`
                                : selectedTalhao?.area_hectares_manual
                                    ? `${selectedTalhao.area_hectares_manual.toFixed(1)} ha (informado)`
                                    : "Área não informada"}
                        </SheetDescription>
                    </SheetHeader>

                    {selectedTalhao && (
                        <>
                            {/* Details */}
                            <div className="space-y-3 px-4">
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">Status</span>
                                    <StatusBadge status={selectedTalhao.ativo ? "ativo" : "inativo"} />
                                </div>
                                {selectedTalhao.area_hectares && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Área calculada</span>
                                        <span className="font-bold text-green-600">{selectedTalhao.area_hectares.toFixed(2)} ha</span>
                                    </div>
                                )}
                                {selectedTalhao.area_hectares_manual && selectedTalhao.area_hectares_manual !== selectedTalhao.area_hectares && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Área informada</span>
                                        <span className="font-medium">{selectedTalhao.area_hectares_manual.toFixed(2)} ha</span>
                                    </div>
                                )}
                                {selectedTalhao.descricao && (
                                    <div className="text-sm">
                                        <span className="text-muted-foreground">Descrição</span>
                                        <p className="mt-1 text-sm">{selectedTalhao.descricao}</p>
                                    </div>
                                )}
                                {selectedTalhao.dados_extras?.tipo_solo && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Tipo de solo</span>
                                        <span className="font-medium">{selectedTalhao.dados_extras.tipo_solo}</span>
                                    </div>
                                )}
                                {selectedTalhao.dados_extras?.textura_solo && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Textura</span>
                                        <span className="font-medium">{selectedTalhao.dados_extras.textura_solo}</span>
                                    </div>
                                )}
                                {selectedTalhao.dados_extras?.relevo && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Relevo</span>
                                        <span className="font-medium capitalize">{selectedTalhao.dados_extras.relevo}</span>
                                    </div>
                                )}
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">Irrigado</span>
                                    <span className="font-medium flex items-center gap-1">
                                        {selectedTalhao.dados_extras?.irrigado ? (
                                            <><CheckCircle2 className="h-4 w-4 text-blue-500" /> Sim</>
                                        ) : (
                                            <><XCircle className="h-4 w-4 text-muted-foreground" /> Não</>
                                        )}
                                    </span>
                                </div>
                                {selectedTalhao.dados_extras?.sistema_irrigacao && (
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-muted-foreground">Sistema</span>
                                        <span className="font-medium">{selectedTalhao.dados_extras.sistema_irrigacao}</span>
                                    </div>
                                )}
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">Geometria</span>
                                    {selectedTalhao.geometria ? (
                                        <span className="text-green-600 font-medium flex items-center gap-1">
                                            <MapPin className="h-3.5 w-3.5" /> Mapeado
                                        </span>
                                    ) : (
                                        <span className="text-amber-600 font-medium">Sem mapa</span>
                                    )}
                                </div>
                                {(selectedTalhao.centroide_lat && selectedTalhao.centroide_lng) && (
                                    <div className="text-sm">
                                        <span className="text-muted-foreground">Centroide</span>
                                        <p className="font-mono text-xs mt-0.5">
                                            {selectedTalhao.centroide_lat.toFixed(6)}, {selectedTalhao.centroide_lng.toFixed(6)}
                                        </p>
                                    </div>
                                )}
                            </div>

                            {/* Actions */}
                            <div className="mt-auto space-y-2 p-4">
                                <Button
                                    className="w-full rounded-sm"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setEditDialogOpen(true)}
                                >
                                    <Pencil className="h-4 w-4 mr-2" />
                                    Editar Dados do Talhão
                                </Button>
                                <Button
                                    className="w-full rounded-sm"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => startEditingGeom(selectedTalhao)}
                                >
                                    <MapPin className="h-4 w-4 mr-2" />
                                    {selectedTalhao.geometria ? "Editar Geometria no Mapa" : "Desenhar Geometria no Mapa"}
                                </Button>
                                {selectedTalhao.geometria && (
                                    <Button
                                        className="w-full rounded-sm text-destructive hover:text-destructive"
                                        variant="outline"
                                        size="sm"
                                        disabled={updateMutation.isPending}
                                        onClick={() => unmarkTalhaoRegion(selectedTalhao)}
                                    >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Desmarcar Região
                                    </Button>
                                )}
                            </div>
                        </>
                    )}
                </SheetContent>
            </Sheet>

            {/* Edit dialog */}
            {selectedTalhao && (
                <TalhaoFormDialog
                    open={editDialogOpen}
                    onOpenChange={setEditDialogOpen}
                    talhao={selectedTalhao}
                    parentOptions={[...glebas, ...raizes]}
                    fazendaId={activeFazendaId ?? ""}
                />
            )}
            </div>
        </div>
    );
}
