"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";

export type RecommendationDomain =
  | "AGRICULTURE"
  | "LIVESTOCK"
  | "FINANCE"
  | "OPERATIONS"
  | "FIELD"
  | "INTEGRATIONS"
  | "SYSTEM";

export type RecommendationStatus =
  | "CREATED"
  | "VIEWED"
  | "ACCEPTED"
  | "DISMISSED"
  | "POSTPONED"
  | "EXECUTED"
  | "EXPIRED"
  | "AUTO_EXPIRED"
  | "SUPERSEDED"
  | "REOPENED";

export type RecommendationPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export type RecommendationSourceType = "SIGNAL" | "EVENT" | "INDICATOR" | "ANALYTICS" | "MANUAL" | "SYSTEM";

export type RecommendationActionType = "NONE" | "OPEN_ROUTE" | "OPEN_URL" | "REVIEW" | "EXECUTE_ASSISTED";

export interface RecommendationListItem {
  id: string;
  tenant_id: string;
  unidade_produtiva_id: string | null;
  domain: RecommendationDomain;
  status: RecommendationStatus;
  priority: RecommendationPriority;
  source_type: RecommendationSourceType;
  action_type: RecommendationActionType;
  provider_name: string;
  rule_code: string;
  scope_type: string;
  scope_id: string;
  title: string;
  summary: string;
  rationale: string;
  dedupe_key: string;
  source_signal_ids: string[];
  confidence: number | string | null;
  action_label: string | null;
  action_target: string | null;
  context: Record<string, unknown> | null;
  expires_at: string | null;
  viewed_at: string | null;
  accepted_at: string | null;
  dismissed_at: string | null;
  postponed_until: string | null;
  executed_at: string | null;
  expired_at: string | null;
  superseded_at: string | null;
  superseded_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecommendationPageResponse {
  items: RecommendationListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface RecommendationMetricsFilters {
  start_date?: string;
  end_date?: string;
  domain?: RecommendationDomain | string;
  unidade_produtiva_id?: string;
}

export interface RecommendationMetricsSummaryResponse {
  filters: {
    start_date: string | null;
    end_date: string | null;
    domain: RecommendationDomain | null;
    unidade_produtiva_id: string | null;
  };
  generated_at: string;
  tenant_id: string;
  total_recommendations: number;
  by_domain: Record<string, number>;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  viewed_total: number;
  accepted_total: number;
  dismissed_total: number;
  executed_total: number;
  expired_total: number;
  superseded_total: number;
  reopened_total: number;
  view_rate: number;
  accept_rate: number;
  dismiss_rate: number;
  execute_rate: number;
  avg_time_to_view_seconds: number | null;
  avg_time_to_accept_seconds: number | null;
  avg_time_to_execute_seconds: number | null;
  lifecycle_events_total: number;
  timeline: Array<{
    period: string;
    total_recommendations: number;
    viewed_total: number;
    accepted_total: number;
    dismissed_total: number;
    executed_total: number;
    accept_rate: number;
    dismissed_rate: number;
    executed_rate: number;
  }>;
}

export interface RecommendationDomainMetricsItem {
  domain: RecommendationDomain;
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  viewed_total: number;
  accepted_total: number;
  dismissed_total: number;
  executed_total: number;
  view_rate: number;
  accept_rate: number;
  dismiss_rate: number;
  execute_rate: number;
  avg_time_to_view_seconds: number | null;
  avg_time_to_accept_seconds: number | null;
  avg_time_to_execute_seconds: number | null;
}

export interface RecommendationDomainMetricsResponse {
  filters: RecommendationMetricsSummaryResponse["filters"];
  generated_at: string;
  items: RecommendationDomainMetricsItem[];
}

export interface RecommendationRuleMetricsItem {
  rule_code: string;
  provider_name: string;
  domain: RecommendationDomain;
  total: number;
  accepted_total: number;
  dismissed_total: number;
  executed_total: number;
  view_rate: number;
  accept_rate: number;
  dismiss_rate: number;
  execute_rate: number;
}

export interface RecommendationRuleMetricsResponse {
  filters: RecommendationMetricsSummaryResponse["filters"];
  generated_at: string;
  top_by_volume: RecommendationRuleMetricsItem[];
  top_by_acceptance: RecommendationRuleMetricsItem[];
  top_by_dismissal: RecommendationRuleMetricsItem[];
}

export interface RecommendationLifecycleMetricsResponse {
  filters: RecommendationMetricsSummaryResponse["filters"];
  generated_at: string;
  tenant_id: string;
  total_events: number;
  by_action: Record<string, number>;
  by_transition: Record<string, number>;
  created_total: number;
  viewed_total: number;
  accepted_total: number;
  dismissed_total: number;
  executed_total: number;
  expired_total: number;
  superseded_total: number;
  reopened_total: number;
  timeline: Array<{
    period: string;
    total_events: number;
    by_action: Record<string, number>;
    by_transition: Record<string, number>;
  }>;
}

export interface RecommendationMetricsBundle {
  summary: RecommendationMetricsSummaryResponse;
  byDomain: RecommendationDomainMetricsResponse;
  byRule: RecommendationRuleMetricsResponse;
  lifecycle: RecommendationLifecycleMetricsResponse;
}

export interface RecommendationListFilters extends RecommendationMetricsFilters {
  status?: RecommendationStatus | string;
  priority?: RecommendationPriority | string;
  scope_type?: string;
  scope_id?: string;
  limit?: number;
  offset?: number;
}

export type RecommendationLifecycleAction =
  | "view"
  | "accept"
  | "dismiss"
  | "postpone"
  | "execute"
  | "reopen";

export interface RecommendationLifecycleActionPayload {
  reason?: string;
  until?: string;
  execution_note?: string;
}

export interface RecommendationLifecycleActionInput {
  recommendationId: string;
  action: RecommendationLifecycleAction;
  payload?: RecommendationLifecycleActionPayload;
}

const RECOMMENDATIONS_KEY = ["recommendations"] as const;

function buildParams(filters: RecommendationListFilters | RecommendationMetricsFilters) {
  const params: Record<string, string | number | undefined> = {};

  if ("domain" in filters && filters.domain) params.domain = filters.domain;
  if ("status" in filters && filters.status) params.status = filters.status;
  if ("priority" in filters && filters.priority) params.priority = filters.priority;
  if ("scope_type" in filters && filters.scope_type) params.scope_type = filters.scope_type;
  if ("scope_id" in filters && filters.scope_id) params.scope_id = filters.scope_id;
  if (filters.unidade_produtiva_id) params.unidade_produtiva_id = filters.unidade_produtiva_id;
  if (filters.start_date) params.start_date = filters.start_date;
  if (filters.end_date) params.end_date = filters.end_date;
  if ("limit" in filters && filters.limit !== undefined) params.limit = filters.limit;
  if ("offset" in filters && filters.offset !== undefined) params.offset = filters.offset;

  return params;
}

function lifecycleEndpoint(action: RecommendationLifecycleAction) {
  return action === "view"
    ? "view"
    : action === "accept"
      ? "accept"
      : action === "dismiss"
        ? "dismiss"
        : action === "postpone"
          ? "postpone"
          : action === "execute"
            ? "execute"
            : "reopen";
}

function lifecycleSuccessMessage(action: RecommendationLifecycleAction) {
  return action === "view"
    ? "Visualização registrada."
    : action === "accept"
      ? "Recomendação aceita."
      : action === "dismiss"
        ? "Recomendação descartada."
        : action === "postpone"
          ? "Recomendação adiada."
          : action === "execute"
            ? "Execução registrada."
            : "Recomendação reaberta.";
}

export function useRecommendations(filters: RecommendationListFilters) {
  return useQuery({
    queryKey: [...RECOMMENDATIONS_KEY, "list", filters],
    queryFn: () => apiFetch<RecommendationPageResponse>("/recommendations", { params: buildParams(filters) }),
    staleTime: 30_000,
  });
}

export function useRecommendationMetrics(filters: RecommendationMetricsFilters) {
  return useQuery({
    queryKey: [...RECOMMENDATIONS_KEY, "metrics", filters],
    queryFn: async (): Promise<RecommendationMetricsBundle> => {
      const params = buildParams(filters);
      const [summary, byDomain, byRule, lifecycle] = await Promise.all([
        apiFetch<RecommendationMetricsSummaryResponse>("/recommendations/metrics/summary", { params }),
        apiFetch<RecommendationDomainMetricsResponse>("/recommendations/metrics/by-domain", { params }),
        apiFetch<RecommendationRuleMetricsResponse>("/recommendations/metrics/by-rule", { params }),
        apiFetch<RecommendationLifecycleMetricsResponse>("/recommendations/metrics/lifecycle", { params }),
      ]);

      return { summary, byDomain, byRule, lifecycle };
    },
    staleTime: 30_000,
  });
}

export function useRecommendationLifecycleAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ recommendationId, action, payload }: RecommendationLifecycleActionInput) =>
      apiFetch(`/recommendations/${recommendationId}/${lifecycleEndpoint(action)}`, {
        method: "POST",
        body: payload ?? undefined,
      }),
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: RECOMMENDATIONS_KEY });
      toast.success(lifecycleSuccessMessage(variables.action));
    },
    onError: (error, variables) => {
      const fallback = `Falha ao ${variables.action} a recomendação.`;
      const message = error instanceof Error ? error.message : fallback;
      toast.error(message);
    },
  });
}
