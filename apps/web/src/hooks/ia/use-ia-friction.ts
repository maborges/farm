import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";

interface IAFrictionResponse {
  friccao: "BAIXA" | "MEDIA" | "ALTA";
  nudge: string | null;
  acao: "simplificar_ui" | "mostrar_explicacao_extra" | "reforçar_seguranca" | null;
  contexto: {
    aberturas_avancado: number;
    tempo_decorrido_ms: number;
  };
}

export function useIAFriction(enabled: boolean = true) {
  const [sessaoId, setSessaoId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const stored = window.sessionStorage.getItem("ia_ux_sessao_id");
    if (stored) {
      setSessaoId(stored);
      return;
    }

    const newId = Math.random().toString(36).substring(2, 15);
    window.sessionStorage.setItem("ia_ux_sessao_id", newId);
    setSessaoId(newId);
  }, []);

  return useQuery<IAFrictionResponse>({
    queryKey: ["ia-friction", sessaoId],
    queryFn: () => apiFetch(`/ia/ux/friccao?sessao_id=${sessaoId}`),
    retry: false,
    refetchInterval: 10000, // Polling a cada 10s para detectar fricção em tempo real
    enabled: enabled && Boolean(sessaoId),
    placeholderData: {
      friccao: "BAIXA",
      nudge: null,
      acao: null,
      contexto: {
        aberturas_avancado: 0,
        tempo_decorrido_ms: 0,
      },
    },
  });
}
