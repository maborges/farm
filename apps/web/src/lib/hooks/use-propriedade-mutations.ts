"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import type { CreatePropriedadeInput } from "@farm/zod-schemas";

export function usePropriedadeMutations(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  const criarMutation = useMutation({
    mutationFn: (data: CreatePropriedadeInput) =>
      apiFetch("/cadastros/propriedades", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      toast.success("Propriedade criada com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["propriedades-economicas"] });
      onSuccess?.();
    },
    onError: (error: any) => {
      toast.error(error.message || "Erro ao criar propriedade");
    },
  });

  const atualizarMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreatePropriedadeInput> }) =>
      apiFetch(`/cadastros/propriedades/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      toast.success("Propriedade atualizada com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["propriedades-economicas"] });
      onSuccess?.();
    },
    onError: (error: any) => {
      toast.error(error.message || "Erro ao atualizar propriedade");
    },
  });

  const removerMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/cadastros/propriedades/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      toast.success("Propriedade removida com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["propriedades-economicas"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Erro ao remover propriedade");
    },
  });

  return {
    criar: criarMutation,
    atualizar: atualizarMutation,
    remover: removerMutation,
    isPending: criarMutation.isPending || atualizarMutation.isPending || removerMutation.isPending,
  };
}
