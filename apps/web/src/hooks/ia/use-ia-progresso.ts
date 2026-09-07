import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAProgressoResponse {
  progresso: {
    tempo_decisao: {
      atual: string;
      melhoria: number;
      status: string;
    };
    taxa_execucao: {
      atual: string;
      melhoria: number;
      status: string;
    };
    roi: {
      total: string;
      melhoria: number;
      status: string;
    };
    perfil: {
      atual: string;
      anterior: string;
      evoluiu: boolean;
    };
  };
  mensagem_destaque: string;
  periodo: string;
}

export function useIAProgresso() {
  return useQuery<IAProgressoResponse>({
    queryKey: ["ia-progresso"],
    queryFn: () => apiFetch("/ia/progresso"),
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutos
    placeholderData: {
      progresso: {
        tempo_decisao: {
          atual: "0,0s",
          melhoria: 0,
          status: "ESTÁVEL",
        },
        taxa_execucao: {
          atual: "0%",
          melhoria: 0,
          status: "ESTÁVEL",
        },
        roi: {
          total: "R$ 0,00",
          melhoria: 0,
          status: "ESTÁVEL",
        },
        perfil: {
          atual: "NEUTRO",
          anterior: "NEUTRO",
          evoluiu: false,
        },
      },
      mensagem_destaque: "Ainda não há histórico suficiente para medir evolução da IA.",
      periodo: "Últimos 7 dias vs período anterior",
    },
  });
}
