import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  atualizarStatusPassaporte,
  atualizarStatusRelatorioESG,
  criarPassaporte,
  criarRelatorioESG,
  listarPassaportes,
  listarRelatoriosESG,
  adicionarIndicadorRelatorioESG,
  adicionarEventoPassaporte,
  listarIndicadoresRelatorioESG,
  listarEventosPassaporte,
  listarEvidenciasRelatorioESG,
  vincularEvidenciaRelatorioESG,
  listarEvidenciasPassaporte,
  vincularEvidenciaPassaporte,
  CreateRelatorioESGPayload,
  UpdateRelatorioStatusPayload,
  CreatePassaporteRastreabilidadePayload,
  UpdatePassaporteStatusPayload,
  CreateRelatorioESGIndicadorPayload,
  CreatePassaporteRastreabilidadeEventoPayload,
  LinkEvidenciaPayload,
} from "@/services/certificacoes-esg/service";

// -- Relatórios ESG Hooks --

export function useRelatoriosESG() {
  return useQuery({
    queryKey: ["esg-relatorios"],
    queryFn: listarRelatoriosESG,
  });
}

export function useCreateRelatorioESG() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarRelatorioESG,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-relatorios"] });
    },
  });
}

export function useUpdateRelatorioESGStatus(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateRelatorioStatusPayload) => atualizarStatusRelatorioESG(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-relatorios"] });
    },
  });
}

export function useIndicadoresRelatorioESG(relatorioId: string) {
  return useQuery({
    queryKey: ["esg-relatorios-indicadores", relatorioId],
    queryFn: () => listarIndicadoresRelatorioESG(relatorioId),
    enabled: !!relatorioId,
  });
}

export function useAddIndicadorRelatorioESG(relatorioId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRelatorioESGIndicadorPayload) => adicionarIndicadorRelatorioESG(relatorioId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-relatorios-indicadores", relatorioId] });
    },
  });
}

export function useEvidenciasRelatorioESG(relatorioId: string) {
  return useQuery({
    queryKey: ["esg-relatorios-evidencias", relatorioId],
    queryFn: () => listarEvidenciasRelatorioESG(relatorioId),
    enabled: !!relatorioId,
  });
}

export function useLinkEvidenciaRelatorioESG(relatorioId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LinkEvidenciaPayload) => vincularEvidenciaRelatorioESG(relatorioId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-relatorios-evidencias", relatorioId] });
    },
  });
}

// -- Passaportes Rastreabilidade Hooks --

export function usePassaportes() {
  return useQuery({
    queryKey: ["esg-passaportes"],
    queryFn: listarPassaportes,
  });
}

export function useCreatePassaporte() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarPassaporte,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-passaportes"] });
    },
  });
}

export function useUpdatePassaporteStatus(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdatePassaporteStatusPayload) => atualizarStatusPassaporte(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-passaportes"] });
    },
  });
}

export function useEventosPassaporte(passaporteId: string) {
  return useQuery({
    queryKey: ["esg-passaportes-eventos", passaporteId],
    queryFn: () => listarEventosPassaporte(passaporteId),
    enabled: !!passaporteId,
  });
}

export function useAddEventoPassaporte(passaporteId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreatePassaporteRastreabilidadeEventoPayload) => adicionarEventoPassaporte(passaporteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-passaportes-eventos", passaporteId] });
    },
  });
}

export function useEvidenciasPassaporte(passaporteId: string) {
  return useQuery({
    queryKey: ["esg-passaportes-evidencias", passaporteId],
    queryFn: () => listarEvidenciasPassaporte(passaporteId),
    enabled: !!passaporteId,
  });
}

export function useLinkEvidenciaPassaporte(passaporteId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LinkEvidenciaPayload) => vincularEvidenciaPassaporte(passaporteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["esg-passaportes-evidencias", passaporteId] });
    },
  });
}
