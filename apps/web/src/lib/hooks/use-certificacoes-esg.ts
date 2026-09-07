import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  criarEvidencia,
  criarNaoConformidade,
  criarPlanoAcao,
  atualizarStatusNaoConformidade,
  atualizarStatusPlanoAcao,
  listarEvidencias,
  listarNaoConformidades,
  listarPlanosAcao,
  listarProgramas,
  criarPrograma,
  atualizarPrograma,
} from "@/services/certificacoes-esg/service";

const CERTIFICACOES_ESG_KEY = ["certificacoes-esg"] as const;

export function useCertificacoesEsgProgramas() {
  return useQuery({
    queryKey: [...CERTIFICACOES_ESG_KEY, "programas"],
    queryFn: listarProgramas,
    retry: false,
  });
}

export function useCriarPrograma() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarPrograma,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Programa criado com sucesso.");
    },
  });
}

export function useAtualizarPrograma() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof atualizarPrograma>[1] }) => atualizarPrograma(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Programa atualizado com sucesso.");
    },
  });
}

export function useCertificacoesEsgEvidencias() {
  return useQuery({
    queryKey: [...CERTIFICACOES_ESG_KEY, "evidencias"],
    queryFn: listarEvidencias,
    retry: false,
  });
}

export function useCertificacoesEsgNaoConformidades() {
  return useQuery({
    queryKey: [...CERTIFICACOES_ESG_KEY, "nao-conformidades"],
    queryFn: listarNaoConformidades,
    retry: false,
  });
}

export function useCertificacoesEsgPlanosAcao() {
  return useQuery({
    queryKey: [...CERTIFICACOES_ESG_KEY, "planos-acao"],
    queryFn: listarPlanosAcao,
    retry: false,
  });
}

export function useAtualizarNaoConformidadeStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof atualizarStatusNaoConformidade>[1] }) =>
      atualizarStatusNaoConformidade(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Status da não conformidade atualizado.");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Falha ao atualizar a não conformidade.";
      toast.error(message);
    },
  });
}

export function useAtualizarPlanoAcaoStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof atualizarStatusPlanoAcao>[1] }) =>
      atualizarStatusPlanoAcao(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Status do plano de ação atualizado.");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Falha ao atualizar o plano de ação.";
      toast.error(message);
    },
  });
}

export function useCriarEvidencia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarEvidencia,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Evidência criada com sucesso.");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Falha ao criar a evidência.";
      toast.error(message);
    },
  });
}

export function useCriarNaoConformidade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarNaoConformidade,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Não conformidade criada com sucesso.");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Falha ao criar a não conformidade.";
      toast.error(message);
    },
  });
}

export function useCriarPlanoAcao() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: criarPlanoAcao,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CERTIFICACOES_ESG_KEY });
      toast.success("Plano de ação criado com sucesso.");
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : "Falha ao criar o plano de ação.";
      toast.error(message);
    },
  });
}
