"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Filter } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import {
  ErpAssociationStatus,
  ExternalAssociationPendingItem,
  ExternalAssociationSummaryResponse,
} from "./types";
import { buildErpAssociationViewModel, buildErpAssociationSummaryViewModel } from "./association-center-view-model";
import { AssociationDetailsSheet } from "./association-details-sheet";

export interface AssociationCenterProps {
  configured?: boolean;
}

export function AssociationCenter({ configured = true }: AssociationCenterProps) {
  const { toast } = useToast();
  const [items, setItems] = useState<ExternalAssociationPendingItem[]>([]);
  const [summary, setSummary] = useState<ExternalAssociationSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAssociation, setSelectedAssociation] = useState<ExternalAssociationPendingItem | null>(null);

  const [draftFilters, setDraftFilters] = useState({
    status: "",
    feature_code: "",
    search: "",
  });
  const [appliedFilters, setAppliedFilters] = useState({
    status: "",
    feature_code: "",
    search: "",
  });

  const loadAssociations = useCallback(async () => {
    if (!configured) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (appliedFilters.status) params.set("status", appliedFilters.status);
      if (appliedFilters.feature_code) params.set("feature_code", appliedFilters.feature_code);
      if (appliedFilters.search) params.set("search", appliedFilters.search);
      params.set("limit", "50");

      const suffix = params.toString() ? `?${params.toString()}` : "";
      
      const [listData, summaryData] = await Promise.all([
        apiFetch<{ items: ExternalAssociationPendingItem[] }>(`/integracoes/erp/associacoes${suffix}`),
        apiFetch<ExternalAssociationSummaryResponse>(`/integracoes/erp/associacoes/resumo`),
      ]);

      setItems(listData?.items || []);
      setSummary(summaryData);
    } catch {
      toast({
        title: "Erro",
        description: "Não foi possível carregar as associações.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [appliedFilters, configured, toast]);

  useEffect(() => {
    void loadAssociations();
  }, [loadAssociations]);

  function applyFilters() {
    setAppliedFilters(draftFilters);
  }

  const viewModels = items.map(buildErpAssociationViewModel);
  const summaryViewModel = summary ? buildErpAssociationSummaryViewModel(summary) : null;

  if (!configured) {
    return null;
  }

  return (
    <Card id="erp-associations" tabIndex={-1}>
      <CardHeader>
        <CardTitle>Centro de Associações</CardTitle>
        <CardDescription>
          Gerencie e reconcilie todos os vínculos (de-para) entre registros locais e o ERP.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {summaryViewModel && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="rounded-sm border bg-muted/20 p-4">
              <p className="text-sm font-medium text-muted-foreground">Pendentes</p>
              <p className="text-2xl font-bold">{summaryViewModel.pendingCount}</p>
            </div>
            <div className="rounded-sm border bg-destructive/10 p-4">
              <p className="text-sm font-medium text-destructive">Conflitos</p>
              <p className="text-2xl font-bold text-destructive">{summaryViewModel.conflictCount}</p>
            </div>
            <div className="rounded-sm border bg-primary/10 p-4">
              <p className="text-sm font-medium text-primary">Ativos</p>
              <p className="text-2xl font-bold text-primary">{summaryViewModel.activeCount}</p>
            </div>
            <div className="rounded-sm border bg-muted/20 p-4">
              <p className="text-sm font-medium text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{summaryViewModel.totalCount}</p>
            </div>
          </div>
        )}

        <div className="flex flex-col md:flex-row gap-3">
          <Input
            className="h-8 md:w-64"
            placeholder="Buscar por ID..."
            value={draftFilters.search}
            onChange={(e) => setDraftFilters({ ...draftFilters, search: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && applyFilters()}
          />
          <Select
            value={draftFilters.status}
            onValueChange={(val) => setDraftFilters({ ...draftFilters, status: val === "ALL" ? "" : val })}
          >
            <SelectTrigger className="h-8 md:w-[180px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">Todos os status</SelectItem>
              <SelectItem value="PENDING">Pendentes</SelectItem>
              <SelectItem value="CONFLICT">Conflitos</SelectItem>
              <SelectItem value="ACTIVE">Ativos</SelectItem>
              <SelectItem value="SUPERSEDED">Superados</SelectItem>
              <SelectItem value="INACTIVE">Inativos</SelectItem>
            </SelectContent>
          </Select>
          <Input
            className="h-8 md:w-64"
            placeholder="Filtrar por capability (ex: pessoas)"
            value={draftFilters.feature_code}
            onChange={(e) => setDraftFilters({ ...draftFilters, feature_code: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && applyFilters()}
          />
          <Button size="sm" variant="outline" onClick={applyFilters}>
            <Filter className="mr-2 h-4 w-4" />
            Filtrar
          </Button>
        </div>

        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : viewModels.length === 0 ? (
          <div className="flex h-32 items-center justify-center rounded-sm border border-dashed">
            <p className="text-sm text-muted-foreground">Nenhuma associação encontrada.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {viewModels.map((vm) => (
              <div
                key={vm.id}
                className="flex items-center justify-between rounded-sm border p-3 hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => setSelectedAssociation(items.find(i => i.id === vm.id) || null)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") return
                  const target = event.target as HTMLElement
                  if (target.closest("button, a, input, select, textarea")) return
                  event.preventDefault()
                  setSelectedAssociation(items.find(i => i.id === vm.id) || null)
                }}
                role="button"
                tabIndex={0}
                aria-label={`Ver detalhes da associação ${vm.externalId}`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={vm.status === "ACTIVE" ? "default" : vm.status === "CONFLICT" ? "destructive" : "secondary"}>
                      {vm.status}
                    </Badge>
                    <span className="text-sm font-medium">{vm.externalId}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {vm.localEntityType} {vm.localEntityId ? `(${vm.localEntityId})` : ""} ⇄ {vm.externalEntityType}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    Capability: {vm.featureCode || "n/d"}
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2 h-7 rounded-sm px-2 text-xs"
                    onClick={(event) => {
                      event.stopPropagation()
                      setSelectedAssociation(items.find(i => i.id === vm.id) || null)
                    }}
                  >
                    Detalhes
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <AssociationDetailsSheet
        association={selectedAssociation}
        onOpenChange={(open) => !open && setSelectedAssociation(null)}
        onReconciled={() => {
          setSelectedAssociation(null);
          loadAssociations();
        }}
      />
    </Card>
  );
}
