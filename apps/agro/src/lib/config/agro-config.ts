/**
 * Integração do DeepFarms Agro (PWA) com as configurações e mensagens institucionais públicas (AGRO-ADMIN-01E5).
 *
 * Características:
 * - Cache resiliente com offline fallback (localStorage + fallback seguro)
 * - Zero Layout Shift
 * - Tipagem rigorosa (sem any)
 * - Revalidação periódica em background
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { agroApiUrl } from "@/lib/api-url";

export interface AgroFeatureFlags {
  clima_enabled: boolean;
  mercado_enabled: boolean;
  byok_enabled: boolean;
  ibge_enabled: boolean;
  calculadoras_enabled: boolean;
}

export type AgroMensagemFinalidade =
  | "REGULATORIO"
  | "URGENTE"
  | "MANUTENCAO"
  | "COMUNICADO"
  | "NOVIDADE";

export interface AgroMensagemItem {
  id: string;
  titulo: string;
  conteudo: string;
  finalidade: AgroMensagemFinalidade;
  ativo: boolean;
  prioridade: number;
  vigencia_inicio?: string | null;
  vigencia_fim?: string | null;
  link_externo?: string | null;
  criado_em: string;
}

export interface AgroPublicConfig {
  sucesso: boolean;
  versao: string;
  consultado_em: string;
  feature_flags: AgroFeatureFlags;
  banner_urgente?: string | null;
  mensagens_vigentes: AgroMensagemItem[];
  avisos_legais: Record<string, string>;
}

export const DEFAULT_AGRO_CONFIG: AgroPublicConfig = {
  sucesso: true,
  versao: "1.0",
  consultado_em: new Date().toISOString(),
  feature_flags: {
    clima_enabled: true,
    mercado_enabled: true,
    byok_enabled: true,
    ibge_enabled: true,
    calculadoras_enabled: true,
  },
  banner_urgente: null,
  mensagens_vigentes: [],
  avisos_legais: {
    aviso_precos_deral:
      "Preço médio semanal recebido pelo produtor, publicado pelo DERAL/SEAB-PR. Não constitui cotação em tempo real nem contrato futuro.",
    aviso_ptax:
      "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.",
    aviso_macro_bcb:
      "Dados públicos oficiais divulgados pelo Banco Central do Brasil (BCB) e IBGE. Não constituem recomendação de investimento.",
    aviso_ibge:
      "Estatística oficial de produção divulgada pelo IBGE (SIDRA). Não é cotação nem preço de comercialização.",
  },
};

const STORAGE_KEY = "deepfarms_agro_public_config_v1";

export async function fetchAgroConfig(): Promise<AgroPublicConfig> {
  try {
    const res = await fetch(agroApiUrl("/api/v1/public/agro/config"), {
      headers: { Accept: "application/json" },
      cache: "no-cache",
    });

    if (!res.ok) {
      throw new Error(`Falha ao obter configuração pública (${res.status})`);
    }

    const data: AgroPublicConfig = await res.json();
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch {
        // Ignora quota storage excedida
      }
    }
    return data;
  } catch {
    // Fallback offline via localStorage ou defaults
    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem(STORAGE_KEY);
        if (cached) {
          const parsed = JSON.parse(cached) as AgroPublicConfig;
          if (parsed && parsed.feature_flags) {
            return parsed;
          }
        }
      } catch {
        // parse error fallback
      }
    }
    return DEFAULT_AGRO_CONFIG;
  }
}

export function useAgroConfig(): {
  config: AgroPublicConfig;
  isLoading: boolean;
  refresh: () => Promise<void>;
} {
  const [config, setConfig] = useState<AgroPublicConfig>(() => {
    if (typeof window !== "undefined") {
      try {
        const cached = localStorage.getItem(STORAGE_KEY);
        if (cached) {
          const parsed = JSON.parse(cached) as AgroPublicConfig;
          if (parsed && parsed.feature_flags) return parsed;
        }
      } catch {
        // fallback
      }
    }
    return DEFAULT_AGRO_CONFIG;
  });
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    const data = await fetchAgroConfig();
    setConfig(data);
    setIsLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    await load();
  }, [load]);

  useEffect(() => {
    const initialLoad = setTimeout(() => void load(), 0);
    const interval = setInterval(() => void load(), 5 * 60 * 1000); // 5 minutos de revalidação
    return () => {
      clearTimeout(initialLoad);
      clearInterval(interval);
    };
  }, [load]);

  return { config, isLoading, refresh };
}
