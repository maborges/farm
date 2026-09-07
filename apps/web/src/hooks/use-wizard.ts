"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import type {
  WizardActionPayload,
  WizardChecklist,
  WizardEtapa,
  WizardIniciarPayload,
  WizardPendencia,
  WizardResumo,
} from "@/types/wizard";

const WIZARD_QUERY_KEYS = {
  status: ["wizard", "status"] as const,
  etapas: ["wizard", "etapas"] as const,
  checklist: ["wizard", "checklist"] as const,
  pendencias: ["wizard", "pendencias"] as const,
};

const WIZARD_NOT_STARTED_MESSAGES = [
  "Implantacao ativa nao encontrada para o tenant.",
  "Implantação ativa não encontrada para o tenant.",
];

interface WizardActionMutationInput {
  endpoint: string;
  successMessage: string;
  payload?: WizardActionPayload;
}

interface WizardConfigurarCargaPayload {
  modo_implantacao: string;
  origem: string;
  escopo_modulos?: Record<string, unknown> | null;
  diagnostico_inicial_snapshot?: Record<string, unknown> | null;
}

function isWizardNotStartedError(error: Error | null): boolean {
  if (!error) return false;
  return WIZARD_NOT_STARTED_MESSAGES.some((message) => error.message.includes(message));
}

async function invalidateWizardQueries(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: WIZARD_QUERY_KEYS.status }),
    queryClient.invalidateQueries({ queryKey: WIZARD_QUERY_KEYS.etapas }),
    queryClient.invalidateQueries({ queryKey: WIZARD_QUERY_KEYS.checklist }),
    queryClient.invalidateQueries({ queryKey: WIZARD_QUERY_KEYS.pendencias }),
  ]);
}

export function useWizard() {
  const queryClient = useQueryClient();
  const {
    _hasHydrated,
    token,
    tenant,
    activeFazendaId,
    isVisaoGrupo,
    unidadesProdutivasAutorizadas,
  } = useAppStore();

  const hasSingleActiveContext =
    unidadesProdutivasAutorizadas.filter((unidade) => unidade.ativo).length === 1;
  const wizardContextReady =
    _hasHydrated &&
    Boolean(token) &&
    Boolean(tenant);
  const contextKey = isVisaoGrupo ? "grupo" : activeFazendaId ?? "auto";

  const statusQuery = useQuery<WizardResumo, Error>({
    queryKey: [...WIZARD_QUERY_KEYS.status, tenant?.id ?? "tenant", contextKey],
    queryFn: () =>
      apiFetch("/wizard/status", {
        suppressErrorLog: true,
      }),
    enabled: wizardContextReady,
    retry: false,
  });

  const hasActiveWizard = Boolean(statusQuery.data);
  const wizardNotStarted = isWizardNotStartedError(statusQuery.error);

  const etapasQuery = useQuery<WizardEtapa[], Error>({
    queryKey: [...WIZARD_QUERY_KEYS.etapas, tenant?.id ?? "tenant", contextKey],
    queryFn: () => apiFetch("/wizard/etapas"),
    enabled: wizardContextReady && hasActiveWizard,
  });

  const checklistQuery = useQuery<WizardChecklist, Error>({
    queryKey: [...WIZARD_QUERY_KEYS.checklist, tenant?.id ?? "tenant", contextKey],
    queryFn: () => apiFetch("/wizard/checklist"),
    enabled: wizardContextReady && hasActiveWizard,
  });

  const pendenciasQuery = useQuery<WizardPendencia[], Error>({
    queryKey: [...WIZARD_QUERY_KEYS.pendencias, tenant?.id ?? "tenant", contextKey],
    queryFn: () => apiFetch("/wizard/pendencias"),
    enabled: wizardContextReady && hasActiveWizard,
  });

  const iniciarMutation = useMutation({
    mutationFn: (payload?: WizardIniciarPayload) =>
      apiFetch<WizardResumo>("/wizard/iniciar", {
        method: "POST",
        body: payload ?? {},
      }),
    onSuccess: async () => {
      toast.success("Implantação pronta para uso.");
      await invalidateWizardQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const reavaliarChecklistMutation = useMutation({
    mutationFn: () =>
      apiFetch<WizardChecklist>("/wizard/checklist/reavaliar", {
        method: "POST",
        body: {},
      }),
    onSuccess: async () => {
      toast.success("Checklist reavaliado.");
      await invalidateWizardQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const configurarCargaMutation = useMutation({
    mutationFn: (payload: WizardConfigurarCargaPayload) =>
      apiFetch<WizardResumo>("/wizard/configurar-carga", {
        method: "POST",
        body: payload,
      }),
    onSuccess: async () => {
      toast.success("Estratégia de carga atualizada.");
      await invalidateWizardQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({ endpoint, payload }: WizardActionMutationInput) =>
      apiFetch<WizardResumo>(endpoint, {
        method: "POST",
        body: payload ?? {},
      }),
    onSuccess: async (_data, variables) => {
      toast.success(variables.successMessage);
      await invalidateWizardQueries(queryClient);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const refetchAll = async () => {
    await invalidateWizardQueries(queryClient);
  };

  return {
    statusQuery,
    etapasQuery,
    checklistQuery,
    pendenciasQuery,
    iniciarMutation,
    configurarCargaMutation,
    reavaliarChecklistMutation,
    actionMutation,
    wizardContextReady,
    hasActiveWizard,
    wizardNotStarted,
    refetchAll,
  };
}
