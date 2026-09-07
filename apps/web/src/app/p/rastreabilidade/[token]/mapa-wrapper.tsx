"use client";

import dynamic from "next/dynamic";

const MapaPassaporte = dynamic(
  () => import("./mapa-passaporte"),
  { 
    ssr: false, 
    loading: () => (
      <div className="h-64 bg-stone-100 rounded-sm flex items-center justify-center text-xs text-stone-400 border border-stone-200 animate-pulse">
        Carregando mapa interativo...
      </div>
    ) 
  }
);

interface MapaWrapperProps {
  geometria?: any;
  centroide_lat?: number | null;
  centroide_lng?: number | null;
  talhao_nome?: string;
  fazenda_nome?: string;
}

export default function MapaWrapper(props: MapaWrapperProps) {
  return <MapaPassaporte {...props} />;
}
