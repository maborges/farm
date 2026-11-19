"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import Map, {
    Layer,
    NavigationControl,
    Source,
    type MapLayerMouseEvent,
    type MapRef,
} from "react-map-gl/maplibre";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import * as turf from "@turf/turf";
import { MapPin } from "lucide-react";

import { MapVisualizationToggle } from "@/components/shared/map-visualization-toggle";
import { Button } from "@/components/ui/button";

import {
    buildNdviGeoJsonCollection,
    type AreaProdutivaGeo,
    type NDVITalhaoResumo,
} from "./ndvi-view-model";

const SATELLITE_STYLE: StyleSpecification = {
    version: 8,
    sources: {
        satellite: {
            type: "raster",
            tiles: [
                "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            maxzoom: 17,
            attribution: "© Esri",
        },
    },
    layers: [{ id: "satellite-layer", type: "raster", source: "satellite" }],
};

const STREETS_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

const INITIAL_VIEW_STATE = {
    longitude: -55.72,
    latitude: -12.54,
    zoom: 12,
};

interface NdviMapViewProps {
    areas: readonly AreaProdutivaGeo[];
    resumoPorTalhao: ReadonlyMap<string, NDVITalhaoResumo>;
    selectedTalhaoId: string | null;
    onSelectTalhao: (talhaoId: string) => void;
}

export function NdviMapView({
    areas,
    resumoPorTalhao,
    selectedTalhaoId,
    onSelectTalhao,
}: NdviMapViewProps) {
    const mapRef = useRef<MapRef>(null);
    const [satellite, setSatellite] = useState(true);
    const [mapLoaded, setMapLoaded] = useState(false);

    const featureCollection = useMemo(
        () => buildNdviGeoJsonCollection(areas, resumoPorTalhao, selectedTalhaoId),
        [areas, resumoPorTalhao, selectedTalhaoId],
    );

    useEffect(() => {
        if (!mapLoaded || featureCollection.features.length === 0) {
            return;
        }
        const [minLng, minLat, maxLng, maxLat] = turf.bbox(featureCollection);
        if ([minLng, minLat, maxLng, maxLat].every(Number.isFinite)) {
            mapRef.current?.fitBounds(
                [
                    [minLng, minLat],
                    [maxLng, maxLat],
                ],
                { padding: 48, maxZoom: 16, duration: 500 },
            );
        }
    }, [mapLoaded, featureCollection]);

    const handleMapClick = (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        const clickedId = feature?.properties?.id;
        if (typeof clickedId === "string" && clickedId) {
            onSelectTalhao(clickedId);
        }
    };

    const selectedFeature = featureCollection.features.find(
        (f) => f.properties.id === selectedTalhaoId,
    );

    if (featureCollection.features.length === 0) {
        return (
            <div className="flex h-[450px] flex-col items-center justify-center gap-3 bg-muted/15 p-8 text-center">
                <MapPin className="size-10 text-muted-foreground/50" />
                <div className="space-y-1">
                    <p className="text-sm font-medium">
                        Nenhuma área produtiva com polígono georreferenciado
                    </p>
                    <p className="mx-auto max-w-md text-xs text-muted-foreground">
                        Desenhe ou importe os polígonos dos talhões e piquetes para visualizar o
                        mapa espacial colorido pelo índice NDVI real.
                    </p>
                </div>
                <Button variant="outline" size="sm" className="rounded-sm" asChild>
                    <Link href="/cadastros/propriedades/talhoes">Georreferenciar talhões</Link>
                </Button>
            </div>
        );
    }

    return (
        <div className="relative h-[450px] w-full overflow-hidden">
            <Map
                ref={mapRef}
                mapLib={maplibregl}
                initialViewState={INITIAL_VIEW_STATE}
                mapStyle={satellite ? SATELLITE_STYLE : STREETS_STYLE}
                style={{ width: "100%", height: "100%" }}
                interactiveLayerIds={["ndvi-areas-fill"]}
                onLoad={() => setMapLoaded(true)}
                onClick={handleMapClick}
                cursor="pointer"
            >
                <NavigationControl position="top-left" />
                <Source id="ndvi-areas" type="geojson" data={featureCollection}>
                    <Layer
                        id="ndvi-areas-fill"
                        type="fill"
                        paint={{
                            "fill-color": ["get", "ndvi_color"],
                            "fill-opacity": ["case", ["get", "selected"], 0.72, 0.52],
                        }}
                    />
                    <Layer
                        id="ndvi-areas-outline"
                        type="line"
                        paint={{
                            "line-color": ["case", ["get", "selected"], "#ffffff", "#0f172a"],
                            "line-width": ["case", ["get", "selected"], 3, 1.5],
                        }}
                    />
                </Source>
            </Map>

            <div className="pointer-events-none absolute left-14 top-3 z-10">
                <MapVisualizationToggle checked={satellite} onCheckedChange={setSatellite} />
            </div>

            {selectedFeature && (
                <div className="absolute bottom-3 left-3 z-10 rounded-sm border bg-background/95 px-3 py-2 text-xs shadow-lg backdrop-blur-sm">
                    <p className="font-semibold">{selectedFeature.properties.nome}</p>
                    <p className="text-muted-foreground">
                        NDVI:{" "}
                        <span className="font-mono font-semibold text-foreground">
                            {selectedFeature.properties.indice_atual != null
                                ? selectedFeature.properties.indice_atual.toFixed(3)
                                : "Sem dados"}
                        </span>{" "}
                        · {selectedFeature.properties.classificacao}
                    </p>
                </div>
            )}

            <div className="absolute right-3 top-3 z-10 flex flex-col gap-2 rounded-sm border bg-background/95 p-3 text-[11px] shadow-lg backdrop-blur-sm">
                <span className="border-b pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Legenda NDVI
                </span>
                <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-[#059669]" />
                    <span>≥ 0,60 (Excelente)</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-[#22c55e]" />
                    <span>0,40 – 0,59 (Moderado)</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-[#f59e0b]" />
                    <span>0,20 – 0,39 (Atenção)</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-[#ef4444]" />
                    <span>&lt; 0,20 (Crítico)</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-[#94a3b8]" />
                    <span>Sem registros</span>
                </div>
            </div>
        </div>
    );
}
