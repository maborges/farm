"use client";

import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import MapLibre, { MapRef, Marker, NavigationControl } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { AlertTriangle, Info, Map, Leaf, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MapVisualizationToggle } from "@/components/shared/map-visualization-toggle";

const SATELLITE_STYLE: StyleSpecification = {
    version: 8,
    sources: {
        satellite: {
            type: "raster",
            tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
            tileSize: 256,
            maxzoom: 17,
            attribution: "© Esri",
        },
    },
    layers: [{ id: "satellite-layer", type: "raster", source: "satellite" }],
};

const STREETS_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

interface Alerta {
    id: string;
    fazenda_nome?: string;
    tipo: string;
    severidade: string;
    status: string;
    area_ha?: number;
    latitude?: number;
    longitude?: number;
    coordenadas_aproximadas?: boolean;
    data_deteccao: string;
}

const SEV_DOT: Record<string, string> = {
    BAIXA:  "bg-green-500",
    MEDIA:  "bg-yellow-500",
    ALTA:   "bg-orange-500",
    CRITICA:"bg-red-500",
};

export default function MapaMonitoramentoPage() {
    const mapRef = useRef<MapRef>(null);
    const [satellite, setSatellite] = useState(true);
    const [alertaSelecionado, setAlertaSelecionado] = useState<string | null>(null);
    const { data: alertas = [] } = useQuery<Alerta[]>({
        queryKey: ["ambiental", "alertas", "mapa"],
        queryFn: () => apiFetch("/ambiental/alertas?status=NOVO&status=EM_ANALISE"),
    });

    const comCoordenadas = useMemo(() => alertas.filter(a => typeof a.latitude === "number" && typeof a.longitude === "number"), [alertas]);
    const semCoordenadas = useMemo(() => alertas.filter(a => typeof a.latitude !== "number" || typeof a.longitude !== "number"), [alertas]);
    const alertaAtivo = comCoordenadas.find(a => a.id === alertaSelecionado);

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Mapa de Monitoramento"
                description="Visualização geoespacial de alertas ambientais ativos."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "Monitoramento" },
                    { label: "Mapa" },
                ]}
                icon={<Map />}
                actions={(
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/ambiental/monitoramento/alertas">
                            <AlertTriangle data-icon="inline-start" />
                            Ver alertas
                        </Link>
                    </Button>
                )}
            />

            <Card className="overflow-hidden">
                <div className="relative h-[28rem] border-b">
                    <MapLibre
                        ref={mapRef}
                        initialViewState={{ latitude: -15.8, longitude: -47.9, zoom: 4 }}
                        mapStyle={satellite ? SATELLITE_STYLE : STREETS_STYLE}
                        style={{ width: "100%", height: "100%" }}
                        onLoad={() => {
                            if (comCoordenadas.length === 0) return;
                            if (comCoordenadas.length === 1) {
                                const alerta = comCoordenadas[0];
                                mapRef.current?.flyTo({
                                    center: [alerta.longitude as number, alerta.latitude as number],
                                    zoom: 14,
                                    duration: 500,
                                });
                                return;
                            }
                            const latitudes = comCoordenadas.map(a => a.latitude as number);
                            const longitudes = comCoordenadas.map(a => a.longitude as number);
                            mapRef.current?.fitBounds(
                                [[Math.min(...longitudes), Math.min(...latitudes)], [Math.max(...longitudes), Math.max(...latitudes)]],
                                { padding: 60, maxZoom: 14, duration: 500 },
                            );
                        }}
                    >
                        <NavigationControl position="top-right" />
                        {comCoordenadas.map(alerta => (
                            <Marker key={alerta.id} latitude={alerta.latitude as number} longitude={alerta.longitude as number} anchor="bottom">
                                <button type="button" title={`Ver alerta ${alerta.tipo}`} onClick={() => setAlertaSelecionado(alerta.id)} className="group">
                                    <MapPin className={`size-8 drop-shadow-md ${SEV_DOT[alerta.severidade]?.replace("bg-", "text-") ?? "text-slate-500"}`} fill="currentColor" />
                                </button>
                            </Marker>
                        ))}
                    </MapLibre>
                    <div className="absolute top-4 left-4 z-10">
                        <MapVisualizationToggle checked={satellite} onCheckedChange={setSatellite} />
                    </div>
                    {alertaAtivo && (
                        <div className="absolute bottom-4 left-4 z-10 max-w-xs rounded-sm border bg-background/95 p-3 shadow-lg backdrop-blur-sm">
                            <p className="text-xs font-semibold">{alertaAtivo.tipo}</p>
                            <p className="text-xs text-muted-foreground">{alertaAtivo.fazenda_nome ?? "Unidade não informada"} · {alertaAtivo.area_ha ?? "—"} ha</p>
                            {alertaAtivo.coordenadas_aproximadas && <p className="text-xs text-amber-600">Localização aproximada pelo centroide do talhão.</p>}
                            <button type="button" className="mt-2 text-xs text-primary underline" onClick={() => setAlertaSelecionado(null)}>Fechar</button>
                        </div>
                    )}
                </div>
                <CardContent className="pt-3 pb-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Info />
                        <span>Mapa interativo com alertas ativos. Sentinel-2/NDVI via GEE permanece pendente de integração e credenciais.</span>
                    </div>
                </CardContent>
            </Card>

            {/* Alertas com coordenadas */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm">
                            <AlertTriangle className="text-red-500" />
                            Alertas com Localização ({comCoordenadas.length})
                        </CardTitle>
                        <CardDescription className="text-xs">Eventos com coordenadas GPS registradas</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {comCoordenadas.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-4">Nenhum alerta com coordenadas.</p>
                        ) : (
                            <div className="flex flex-col gap-2">
                                {comCoordenadas.map(a => (
                                    <div key={a.id} className="flex items-center gap-2 p-2 rounded bg-muted/30">
                                        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${SEV_DOT[a.severidade] ?? "bg-muted"}`} />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-medium truncate">{a.fazenda_nome ?? "Fazenda não informada"}</p>
                                            <p className="text-xs text-muted-foreground">{a.tipo} — {a.area_ha ?? "?"} ha</p>
                                        </div>
                                        <p className="text-xs text-muted-foreground font-mono shrink-0">
                                            {a.latitude?.toFixed(4)}, {a.longitude?.toFixed(4)}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-sm">
                            <Leaf className="text-green-500" />
                            Alertas sem Localização ({semCoordenadas.length})
                        </CardTitle>
                        <CardDescription className="text-xs">Edite os alertas para adicionar coordenadas GPS</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {semCoordenadas.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-4">Todos os alertas têm coordenadas.</p>
                        ) : (
                            <div className="flex flex-col gap-2">
                                {semCoordenadas.slice(0, 5).map(a => (
                                    <div key={a.id} className="flex items-center gap-2 p-2 rounded bg-muted/30">
                                        <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${SEV_DOT[a.severidade] ?? "bg-muted"}`} />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-medium truncate">{a.fazenda_nome ?? "Fazenda não informada"}</p>
                                            <p className="text-xs text-muted-foreground">{a.tipo} — {new Date(a.data_deteccao).toLocaleDateString("pt-BR")}</p>
                                        </div>
                                    </div>
                                ))}
                                {semCoordenadas.length > 5 && (
                                    <p className="text-xs text-muted-foreground text-center">+{semCoordenadas.length - 5} mais</p>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Legenda */}
            <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">Legenda</CardTitle></CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        {[
                            { label: "Baixa severidade", dot: "bg-green-500" },
                            { label: "Média severidade", dot: "bg-yellow-500" },
                            { label: "Alta severidade", dot: "bg-orange-500" },
                            { label: "Crítica", dot: "bg-red-500" },
                        ].map(item => (
                            <div key={item.label} className="flex items-center gap-2">
                                <div className={`w-3 h-3 rounded-full ${item.dot}`} />
                                <span className="text-xs text-muted-foreground">{item.label}</span>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
