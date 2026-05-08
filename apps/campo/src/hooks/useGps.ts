"use client";

import { useState, useEffect } from "react";

export interface GpsResult {
  latitude: number | null;
  longitude: number | null;
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}

export function useGps(autoCapture = true): GpsResult & { capture: () => void } {
  const [result, setResult] = useState<GpsResult>({
    latitude: null,
    longitude: null,
    status: "AGUARDANDO",
  });

  const capture = () => {
    if (!navigator.geolocation) {
      setResult({ latitude: null, longitude: null, status: "INDISPONIVEL" });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setResult({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          status: "DISPONIVEL",
        });
      },
      () => {
        setResult({ latitude: null, longitude: null, status: "INDISPONIVEL" });
      },
      { timeout: 8000, maximumAge: 30000, enableHighAccuracy: true }
    );
  };

  useEffect(() => {
    if (autoCapture) capture();
  }, []);

  return { ...result, capture };
}
