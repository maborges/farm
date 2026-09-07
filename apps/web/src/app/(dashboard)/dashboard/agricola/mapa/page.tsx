"use client";

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import Map, { NavigationControl, Source, Layer, GeolocateControl, ScaleControl, MapRef } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import * as turf from "@turf/turf";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Plus, Save, Undo2, MousePointerClick, Satellite as SatelliteIcon,
    Map as MapIcon, Crosshair, Layers as LayersIcon, Activity,
    TrendingUp, Info, Tractor, ArrowUpRight, Hexagon, Maximize2,
    Trash2, Edit3, MapPin, Box, FileUp
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";

// -- Configs
const INITIAL_VIEW_STATE = {
    longitude: -51.9253,
    latitude: -23.4205,
    zoom: 4
};

const MAP_STYLES = {
    STREETS: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        SATELLITE: {
            version: 8,
            sources: {
                "satellite-tiles": {
                    type: "raster",
                    tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                    tileSize: 256,
                    attribution: "© Esri"
                }
            },
        layers: [{ id: "satellite-layer", type: "raster", source: "satellite-tiles" }]
    }
};

type DrawingType = "TALHAO" | "PERIMETRO_FAZENDA";

export default function MapaGeoprocessamentoPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const mapRef = useRef<MapRef>(null);

    // State
    const [mapStyle, setMapStyle] = useState<any>(MAP_STYLES.SATELLITE);
    const [overlay, setOverlay] = useState<"none" | "ndvi" | "productivity">("none");
    const [drawingMode, setDrawingMode] = useState(false);
    const [drawingType, setDrawingType] = useState<DrawingType>("TALHAO");
    const [drawnFeatures, setDrawnFeatures] = useState<GeoJSON.Feature[]>([]);
    const [nomeTalhao, setNomeTalhao] = useState("");
    const [selectedTalhao, setSelectedTalhao] = useState<any>(null);
    const [hoveredTalhao, setHoveredTalhao] = useState<any>(null);
    const [mapCursor, setMapCursor] = useState<string>("grab");
    const [view3d, setView3d] = useState(false);

    // --- DATA FETCHING ---
    const { data: configs } = useQuery({
        queryKey: ["tenant-configs", "mapas"],
        queryFn: () => apiFetch<any[]>("/config/tenant?categoria=mapas")
    });

    const is3dEnabled = useMemo(() => configs?.find(c => c.chave === "enable_3d_terrain")?.valor?.enabled, [configs]);
    const isTrailEnabled = useMemo(() => configs?.find(c => c.chave === "telemetry_trail")?.valor?.enabled, [configs]);
    const isKmlEnabled = useMemo(() => configs?.find(c => c.chave === "kml_import")?.valor?.enabled, [configs]);

    const { data: fazenda } = useQuery({
        queryKey: ["fazenda", activeFazendaId],
        queryFn: () => apiFetch<any>(`/fazendas/${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: talhoes = [], isLoading: loadingTalhoes } = useQuery({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch<any[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    // --- MUTATIONS ---
    const updateFazendaMutation = useMutation({
        mutationFn: (payload: any) => apiFetch(`/fazendas/${activeFazendaId}`, { method: "PUT", body: JSON.stringify(payload) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fazenda", activeFazendaId] });
            toast.success("Perímetro da fazenda atualizado!");
            setDrawingMode(false);
            setDrawnFeatures([]);
        }
    });

    const createTalhaoMutation = useMutation({
        mutationFn: (payload: any) => apiFetch("/cadastros/areas-rurais/", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["talhoes", activeFazendaId] });
            toast.success("Talhão registrado com sucesso!");
            setDrawingMode(false);
            setDrawnFeatures([]);
            setNomeTalhao("");
        }
    });

    // --- LOGIC ---
    useEffect(() => {
        if (!loadingTalhoes && talhoes?.length > 0 && mapRef.current) {
            const features = talhoes.filter((t: any) => t.geometria_geojson);
            if (features.length > 0) {
                const collection = turf.featureCollection(features.map(t => ({ type: "Feature", geometry: t.geometria_geojson, properties: {} })));
                const bbox = turf.bbox(collection);
                mapRef.current.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 100, duration: 1000 });
            }
        } else if (fazenda?.geometria && mapRef.current) {
            const bbox = turf.bbox(fazenda.geometria);
            mapRef.current.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], { padding: 100, duration: 1000 });
        }
    }, [talhoes?.length, fazenda?.geometria, loadingTalhoes]);

    const onHover = useCallback((event: any) => {
        if (drawingMode) return;

        const features = event.target.queryRenderedFeatures(event.point, { layers: ["talhoes-fill"] });
        if (features.length > 0) {
            setMapCursor("pointer");
            const t = talhoes.find((t: any) => t.id === features[0].properties?.id);
            setHoveredTalhao(t);
        } else {
            setMapCursor("grab");
            setHoveredTalhao(null);
        }
    }, [drawingMode, talhoes]);

    const onMapClick = useCallback((event: maplibregl.MapMouseEvent) => {
        if (drawingMode) {
            const { lng, lat } = event.lngLat;
            const coord = [lng, lat];

            setDrawnFeatures(prev => {
                if (prev.length === 0) {
                    return [{
                        type: "Feature",
                        properties: {},
                        geometry: { type: "Polygon", coordinates: [[coord, coord, coord, coord]] }
                    }];
                } else {
                    const poly = prev[0] as GeoJSON.Feature<GeoJSON.Polygon>;
                    const coords = [...poly.geometry.coordinates[0]];
                    coords.splice(coords.length - 1, 0, coord);
                    return [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [coords] } }];
                }
            });
        } else {
            const features = event.target.queryRenderedFeatures(event.point, { layers: ["talhoes-fill"] });
            if (features.length > 0) {
                const t = talhoes.find((t: any) => t.id === features[0].properties?.id);
                setSelectedTalhao(t);
            } else {
                setSelectedTalhao(null);
            }
        }
    }, [drawingMode, talhoes]);

    const calculatedArea = useMemo(() => {
        if (drawnFeatures.length > 0) {
            const poly = drawnFeatures[0] as any;
            if (poly.geometry.coordinates[0].length >= 4) {
                const areaM2 = turf.area(poly);
                return areaM2 / 10000;
            }
        }
        return 0;
    }, [drawnFeatures]);

    const handleSave = () => {
        if (calculatedArea === 0) return toast.error("Desenhe um polígono válido.");

        if (drawingType === "PERIMETRO_FAZENDA") {
            updateFazendaMutation.mutate({ geometria: drawnFeatures[0].geometry, area_total_ha: calculatedArea });
        } else {
            if (!nomeTalhao) return toast.error("Informe o nome do talhão.");
            createTalhaoMutation.mutate({ nome: nomeTalhao, unidade_produtiva_id: activeFazendaId, geometria_geojson: drawnFeatures[0].geometry, area_ha_manual: calculatedArea });
        }
    };

    return (
        <div className="p-6 space-y-6 h-[calc(100vh-90px)] flex flex-col">
            <PageHeader
                title={`Geoprocessamento | ${fazenda?.nome || "Fazenda"}`}
                description="Cartografia Digital • Satélite Ativo"
                icon={<MapPin className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Mapas" }]}
                actions={
                    <div className="flex agro-glass p-1 rounded-sm ring-1 ring-black/5 shadow-2xl gap-1">
                        <Button variant={mapStyle === MAP_STYLES.STREETS ? "secondary" : "ghost"} size="sm" className="rounded-sm" onClick={() => setMapStyle(MAP_STYLES.STREETS)}>
                            <MapIcon className="size-4 mr-2" /> Mapa
                        </Button>
                        <Button variant={mapStyle === MAP_STYLES.SATELLITE ? "secondary" : "ghost"} size="sm" className="rounded-sm" onClick={() => setMapStyle(MAP_STYLES.SATELLITE)}>
                            <SatelliteIcon className="size-4 mr-2" /> Satélite
                        </Button>
                        <div className="w-px bg-border mx-1" />
                        {!drawingMode ? (
                            <DropdownMenu>
                                <DropdownMenuTrigger 
                                    render={
                                        <Button variant="outline" size="sm" className="gap-2">
                                            <Plus className="size-4" /> Mapear Área
                                        </Button>
                                    }
                                />
                                <DropdownMenuContent align="end" className="w-56 agro-glass p-2">
                                    <DropdownMenuItem className="gap-2 rounded-sm" onClick={() => { setDrawingMode(true); setDrawingType("TALHAO"); }}>
                                        <Hexagon className="size-4 text-primary" /> Novo Talhão
                                    </DropdownMenuItem>
                                    <DropdownMenuItem className="gap-2 rounded-sm font-bold" onClick={() => { setDrawingMode(true); setDrawingType("PERIMETRO_FAZENDA"); }}>
                                        <Maximize2 className="size-4 text-orange-500" /> Perímetro da Fazenda
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        ) : (
                            <div className="flex gap-1 animate-in zoom-in duration-300">
                                <Badge variant="secondary" className="bg-orange-500/10 text-orange-600 border-none px-4 flex items-center gap-2 rounded-sm">
                                    <span className="animate-pulse w-2 h-2 rounded-full bg-orange-600" />
                                    {drawingType === "TALHAO" ? "Novo Talhão" : "Limite Fazenda"}
                                </Badge>
                                <Button variant="ghost" size="sm" className="rounded-sm" onClick={() => { setDrawingMode(false); setDrawnFeatures([]); }}>Cancelar</Button>
                            </div>
                        )}
                    </div>
                }
            />

            <div className="relative flex-1 rounded-sm overflow-hidden shadow-2xl border border-border flex flex-col lg:flex-row bg-muted/50 backdrop-blur-3xl">
                {/* Drawing Sidebar */}
                {drawingMode && (
                    <div className="w-full lg:w-80 agro-glass border-b lg:border-b-0 lg:border-r border-primary/10 p-8 flex flex-col gap-8 z-10 animate-in fade-in duration-200">
                        <div>
                            <h3 className="text-xl font-black uppercase italic">Editor Vetorial</h3>
                            <p className="text-[10px] text-muted-foreground font-bold tracking-widest mt-1">Marque os pontos no mapa conforme o limite físico.</p>
                        </div>

                        <div className="space-y-6">
                            {isKmlEnabled && (
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase text-primary tracking-widest px-1">Interoperabilidade</label>
                                    <Button variant="outline" className="w-full h-12 rounded-sm border-primary/20 text-primary font-bold gap-2 bg-primary/5 hover:bg-primary/10 transition-all shadow-sm" onClick={() => toast.info("Módulo de parsing KML/Shapefile: Aguardando upload...")}>
                                        <FileUp size={16} /> Importar KML / SHP
                                    </Button>
                                </div>
                            )}

                            {drawingType === "TALHAO" && (
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase text-primary tracking-widest px-1">Nome do Talhão</label>
                                    <Input placeholder="Ex: G-04 Soja Safrinha" value={nomeTalhao} onChange={(e) => setNomeTalhao(e.target.value)} className="h-12 rounded-sm bg-background/50 border-primary/20 focus-visible:ring-primary/20" />
                                </div>
                            )}

                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-primary tracking-widest px-1">Superfície Cartográfica</label>
                                <div className="p-6 bg-primary/5 rounded-sm border border-primary/10 flex justify-between items-baseline shadow-inner">
                                    <span className="text-4xl font-black text-primary font-mono tabular-nums leading-none">{calculatedArea.toFixed(2)}</span>
                                    <span className="text-[10px] font-black text-primary/40 uppercase">hectares</span>
                                </div>
                            </div>
                        </div>

                        <div className="mt-auto space-y-3">
                            <Button variant="outline" className="w-full h-12 rounded-sm border-orange-200 text-orange-600 hover:bg-orange-50 font-bold" onClick={() => setDrawnFeatures([])}>
                                <Undo2 className="size-4 mr-2" /> Limpar Esboço
                            </Button>
                            <Button className="w-full h-14 rounded-sm font-black shadow-xl shadow-primary/20 text-lg hover:scale-[1.02] transition-transform" onClick={handleSave} disabled={calculatedArea === 0}>
                                <Save className="w-5 h-5 mr-3" /> Finalizar Mapa
                            </Button>
                        </div>
                    </div>
                )}

                {/* Map Interface */}
                <div className="flex-1 relative">
                    <div className="absolute top-4 left-4 z-10 w-64 agro-glass p-2 rounded-sm shadow-xl flex gap-2 ring-1 ring-black/5">
                        <Input
                            placeholder="Buscar coordenada..."
                            className="h-9 rounded-sm text-[11px] bg-background/50 border-none focus-visible:ring-primary/20"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    const val = (e.target as HTMLInputElement).value;
                                    const coords = val.split(',').map(n => Number(n.trim()));
                                    if (coords.length === 2 && !isNaN(coords[0]) && !isNaN(coords[1])) {
                                        mapRef.current?.flyTo({ center: [coords[1], coords[0]], zoom: 16 });
                                        toast.success("Navegando para coordenada");
                                    } else {
                                        toast.error("Formato: lat, lng");
                                    }
                                }
                            }}
                        />
                        <Button size="icon" variant="ghost" className="h-9 w-9 rounded-sm hover:bg-primary/10">
                            <MapPin size={16} className="text-primary" />
                        </Button>
                    </div>

                    <Map
                        ref={mapRef}
                        mapLib={maplibregl}
                        initialViewState={INITIAL_VIEW_STATE}
                        mapStyle={mapStyle}
                        style={{ width: "100%", height: "100%" }}
                        onClick={onMapClick}
                        onMouseMove={onHover}
                        cursor={drawingMode ? "crosshair" : mapCursor}
                        terrain={is3dEnabled && view3d ? { source: "terrain-source", exaggeration: 1.5 } : undefined}
                    >
                        <NavigationControl position="top-right" showCompass={view3d} />
                        <GeolocateControl position="top-right" />
                        <ScaleControl position="bottom-right" />

                        {is3dEnabled && (
                            <Source
                                id="terrain-source"
                                type="raster-dem"
                                url="https://demotiles.maplibre.org/terrain-tiles/tiles.json"
                                tileSize={256}
                            />
                        )}

                        {/* Top Perspective Toggle */}
                        {is3dEnabled && (
                            <div className="absolute top-4 right-14 z-10">
                                <Button
                                    size="sm"
                                    variant={view3d ? "secondary" : "outline"}
                                    className={`rounded-sm agro-glass border-none shadow-xl transition-all ${view3d ? 'text-primary font-black' : 'text-muted-foreground opacity-70'}`}
                                    onClick={() => {
                                        const next = !view3d;
                                        setView3d(next);
                                        if (next) {
                                            mapRef.current?.easeTo({ pitch: 60, bearing: -20, duration: 1000 });
                                        } else {
                                            mapRef.current?.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
                                        }
                                    }}
                                >
                                    <Box className="size-4 mr-2" /> 3D View
                                </Button>
                            </div>
                        )}

                        {/* Farm Boundary Layer */}
                        {fazenda?.geometria && (
                            <Source id="fazenda-boundary" type="geojson" data={fazenda.geometria}>
                                <Layer id="fazenda-line" type="line" paint={{ "line-color": "#ffffff", "line-width": 3, "line-dasharray": ["literal", [2, 1]], "line-opacity": 0.5 }} />
                                <Layer id="fazenda-glow" type="line" paint={{ "line-color": "#ffffff", "line-width": 8, "line-blur": 10, "line-opacity": 0.2 }} />
                            </Source>
                        )}

                        {/* Machine Trail Layer (Simulated) */}
                        {isTrailEnabled && (
                            <Source id="trail-source" type="geojson" data={{
                                type: "FeatureCollection",
                                features: [{
                                    type: "Feature",
                                    geometry: {
                                        type: "LineString",
                                        coordinates: [
                                            [-51.9253, -23.4205], [-51.926, -23.421], [-51.927, -23.420], [-51.928, -23.422]
                                        ]
                                    },
                                    properties: {}
                                }]
                            }}>
                                <Layer id="trail-glow" type="line" paint={{ "line-color": "#fbbf24", "line-width": 8, "line-blur": 6, "line-opacity": 0.3 }} />
                                <Layer id="trail-line" type="line" paint={{ "line-color": "#fbbf24", "line-width": 2.5, "line-opacity": 0.9 }} />
                            </Source>
                        )}

                        {/* Talhões Layer */}
                        <Source id="talhoes-source" type="geojson" data={{
                            type: "FeatureCollection",
                            features: [
                                ...(talhoes || []).filter((t: any) => t.geometria_geojson).map((t: any) => ({
                                    type: "Feature",
                                    geometry: t.geometria_geojson,
                                    properties: { id: t.id, nome: t.nome, area: t.area_efetiva_ha }
                                })),
                                ...drawnFeatures
                            ] as any
                        }}>
                            <Layer id="talhoes-fill" type="fill" paint={{
                                "fill-color": ["case",
                                    ["==", ["get", "id"], hoveredTalhao?.id || ""], "#81C784",
                                    ["has", "id"], "#4CAF50",
                                    "#FFC107"
                                ],
                                "fill-opacity": ["case", ["has", "id"], 0.4, 0.6]
                            }} />
                            <Layer id="talhoes-border" type="line" paint={{
                                "line-color": "#ffffff",
                                "line-width": ["case", ["==", ["get", "id"], hoveredTalhao?.id || ""], 3, 1.5],
                                "line-opacity": ["case", ["==", ["get", "id"], hoveredTalhao?.id || ""], 1, 0.7]
                            }} />
                            <Layer id="talhoes-label" type="symbol" layout={{ "text-field": ["get", "nome"], "text-size": 11 }} paint={{ "text-color": "#fff", "text-halo-color": "#000", "text-halo-width": 1 }} />
                        </Source>
                    </Map>

                    {/* Quick Info Tooltip (Floating) */}
                    {hoveredTalhao && !selectedTalhao && (
                        <div className="absolute agro-glass px-3 py-1.5 rounded-sm shadow-xl pointer-events-none z-50 animate-in fade-in zoom-in duration-200" style={{ left: '50%', top: '50%', transform: 'translate(-50%, -120%)' }}>
                            <p className="text-[10px] font-black uppercase text-primary leading-none">{hoveredTalhao.nome}</p>
                            <p className="text-[9px] font-bold opacity-60">{Number(hoveredTalhao.area_efetiva_ha).toFixed(1)} ha</p>
                        </div>
                    )}

                    {/* Right Panel: Data Analysis */}
                    {selectedTalhao && (
                        <div className="absolute top-4 right-4 bottom-4 w-80 agro-glass rounded-sm shadow-2xl flex flex-col z-50 animate-in fade-in duration-200 ring-1 ring-black/5 overflow-hidden">
                            <div className="p-8 border-b border-primary/10">
                                <div className="flex items-center justify-between mb-8">
                                    <Badge className="bg-primary/20 text-primary border-none text-[10px] font-black uppercase py-1 px-3 italic">Digital Twin 4.0</Badge>
                                    <Button variant="ghost" size="icon" onClick={() => setSelectedTalhao(null)} className="rounded-full h-8 w-8 hover:bg-destructive/10 hover:text-destructive"><Plus className="rotate-45" /></Button>
                                </div>
                                <h2 className="text-4xl font-black text-foreground leading-tight drop-shadow-sm">{selectedTalhao.nome}</h2>
                                <div className="flex items-center gap-2 mt-3">
                                    <Badge variant="outline" className="text-[9px] font-bold border-primary/20 text-muted-foreground uppercase">{selectedTalhao.cultura_atual || "Soja"}</Badge>
                                    <Badge variant="outline" className="text-[9px] font-bold border-primary/20 text-muted-foreground uppercase">Safra 24/25</Badge>
                                </div>
                            </div>

                            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                                <div className="grid grid-cols-1 gap-4">
                                    <div className="p-6 bg-background/40 rounded-sm shadow-sm border border-border/50 group hover:border-primary/30 transition-all">
                                        <div className="flex justify-between items-start mb-2">
                                            <p className="text-[10px] font-black uppercase text-muted-foreground/60 tracking-widest leading-none">Superfície Efetiva</p>
                                            <div className="h-6 w-6 rounded-full bg-green-500/10 flex items-center justify-center text-green-600"><TrendingUp size={12} /></div>
                                        </div>
                                        <p className="text-4xl font-black leading-none tabular-nums text-foreground">{Number(selectedTalhao.area_efetiva_ha).toFixed(1)} <span className="text-sm font-medium opacity-40 uppercase ml-1">ha</span></p>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="p-5 bg-blue-500/5 rounded-sm border border-blue-200/20">
                                            <p className="text-[9px] font-black uppercase text-blue-600 tracking-widest mb-2 opacity-70">Umidade Solo</p>
                                            <p className="text-2xl font-black text-blue-700 leading-none">24<span className="text-xs font-bold">%</span></p>
                                        </div>
                                        <div className="p-5 bg-orange-500/5 rounded-sm border border-orange-200/20">
                                            <p className="text-[9px] font-black uppercase text-orange-600 tracking-widest mb-2 opacity-70">Temp. Solo</p>
                                            <p className="text-2xl font-black text-orange-700 leading-none">22.5<span className="text-xs font-bold">°C</span></p>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <h4 className="text-[10px] font-black uppercase text-primary tracking-[0.2em] flex items-center gap-2">
                                        <Activity size={14} /> Telemetria de Vigor
                                    </h4>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between px-1">
                                            <span className="text-[10px] font-bold text-muted-foreground uppercase opacity-60">NDVI Médio</span>
                                            <span className="text-xs font-black text-green-600">0.82 (Ótimo)</span>
                                        </div>
                                        <div className="h-2 w-full bg-muted rounded-full overflow-hidden flex ring-1 ring-black/5">
                                            <div className="h-full bg-green-500 w-[82%]" />
                                            <div className="h-full bg-muted w-[18%]" />
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-4 pt-2">
                                    <h4 className="text-[10px] font-black uppercase text-primary tracking-[0.2em]">Último Manejo</h4>
                                    <div className="p-4 bg-background border border-border/40 rounded-sm flex items-center gap-4 group hover:bg-primary/5 transition-colors cursor-pointer">
                                        <div className="h-10 w-10 rounded-sm bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform"><Tractor size={18} /></div>
                                        <div className="flex-1">
                                            <p className="text-[11px] font-black uppercase text-foreground leading-none">Fertirrigação V3</p>
                                            <p className="text-[9px] text-muted-foreground font-bold uppercase">14/08/2025 • Operador: Silva</p>
                                        </div>
                                        <ArrowUpRight size={14} className="text-muted-foreground/30 group-hover:text-primary transition-colors" />
                                    </div>
                                </div>
                            </div>

                            <div className="p-8 bg-primary/5 border-t border-primary/10">
                                <Button variant="outline" size="sm" className="w-full h-14 font-black text-lg gap-3 shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all bg-primary text-primary-foreground border-none">
                                    BI Power Analytics <ArrowUpRight size={20} className="stroke-[3px]" />
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
