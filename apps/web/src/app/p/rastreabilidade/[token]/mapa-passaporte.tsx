"use client";

import { useEffect, useRef, useState } from "react";
import Map, { Source, Layer, MapRef, Marker } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapPin } from "lucide-react";
import * as turf from "@turf/turf";

const MAP_STYLE: any = {
  version: 8,
  sources: {
    "sat": {
      type: "raster",
      tiles: ["https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "© Esri"
    }
  },
  layers: [{ id: "sat-layer", type: "raster", source: "sat" }]
};

const fillLayer: any = {
  id: "polygon-fill",
  type: "fill",
  paint: {
    "fill-color": "#10b981", // Emerald 500
    "fill-opacity": 0.18,
  },
};

const lineLayer: any = {
  id: "polygon-outline",
  type: "line",
  paint: {
    "line-color": "#059669", // Emerald 600
    "line-width": 2.5,
  },
};

interface MapaPassaporteProps {
  geometria?: any;
  centroide_lat?: number | null;
  centroide_lng?: number | null;
  talhao_nome?: string;
  fazenda_nome?: string;
}

export default function MapaPassaporte({
  geometria,
  centroide_lat,
  centroide_lng,
  talhao_nome = "Talhão",
  fazenda_nome = "Fazenda"
}: MapaPassaporteProps) {
  const mapRef = useRef<MapRef>(null);
  const [hasError, setHasError] = useState(false);

  // Setup default viewport coordinates (Brazil center if not present)
  let initialLat = centroide_lat || -23.42;
  let initialLng = centroide_lng || -51.92;
  let initialZoom = 14;

  // Compute a center from the geometry to avoid pointing elsewhere initially
  if (geometria) {
    try {
      const feature = geometria.type === "Feature"
        ? geometria
        : geometria.type === "FeatureCollection"
          ? geometria.features[0]
          : { type: "Feature", properties: {}, geometry: geometria };

      if (feature && feature.geometry) {
        const center = turf.center(feature);
        initialLng = center.geometry.coordinates[0];
        initialLat = center.geometry.coordinates[1];
        initialZoom = 15;
      }
    } catch (err) {
      console.warn("Falha ao calcular centroide inicial da geometria:", err);
    }
  }

  // Adjust view state to fit the geometry bounds automatically once loaded
  useEffect(() => {
    if (geometria && mapRef.current) {
      try {
        const feature = geometria.type === "Feature"
          ? geometria
          : geometria.type === "FeatureCollection"
            ? geometria
            : { type: "Feature", properties: {}, geometry: geometria };

        const bbox = turf.bbox(feature);
        if (bbox && bbox.length === 4 && bbox.every(isFinite)) {
          mapRef.current.fitBounds(
            [bbox[0], bbox[1], bbox[2], bbox[3]],
            { padding: 35, duration: 600 }
          );
        }
      } catch (err) {
        console.warn("Erro ao fazer fitBounds no mapa:", err);
      }
    }
  }, [geometria]);

  if (hasError) {
    return (
      <div className="h-64 bg-stone-100 rounded-sm flex flex-col items-center justify-center text-xs text-stone-500 p-4 text-center border border-stone-200">
        <MapPin className="size-8 text-stone-400 mb-2" />
        <p className="font-semibold text-stone-700">Visualização de Mapa Indisponível</p>
        <p className="text-[10px] text-stone-400 mt-1 max-w-[200px]">
          Verifique se o seu dispositivo suporta aceleração gráfica WebGL.
        </p>
      </div>
    );
  }

  // Normalize GeoJSON source
  const geojsonSource = geometria ? (
    geometria.type === "FeatureCollection" || geometria.type === "Feature"
      ? geometria
      : { type: "Feature", properties: {}, geometry: geometria }
  ) : null;

  return (
    <div className="relative w-full h-64 rounded-sm overflow-hidden border border-stone-200 shadow-inner">
      <Map
        ref={mapRef}
        initialViewState={{
          latitude: initialLat,
          longitude: initialLng,
          zoom: initialZoom
        }}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        onError={(e) => {
          console.error("Erro no MapLibre:", e);
          setHasError(true);
        }}
        attributionControl={false}
      >
        {geojsonSource && (
          <Source id="talhao-source" type="geojson" data={geojsonSource}>
            <Layer {...fillLayer} />
            <Layer {...lineLayer} />
          </Source>
        )}

        {/* Highlight centroid with a styled premium Pin Marker */}
        {centroide_lat && centroide_lng && (
          <Marker latitude={centroide_lat} longitude={centroide_lng} anchor="bottom">
            <div className="flex flex-col items-center">
              <div className="bg-emerald-950 text-white text-[10px] font-bold px-2 py-0.5 rounded-sm shadow-md border border-emerald-600 mb-1 max-w-[120px] truncate">
                {talhao_nome}
              </div>
              <div className="bg-emerald-600 p-1.5 rounded-full border border-white shadow-lg animate-bounce">
                <MapPin className="size-4 text-white fill-emerald-100" />
              </div>
            </div>
          </Marker>
        )}
      </Map>
    </div>
  );
}
