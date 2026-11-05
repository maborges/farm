"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  TrendingUp,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Activity,
  Server,
  Layers,
  ArrowRightLeft,
  AlertOctagon,
  FileCheck,
  Upload,
  Eye,
  Download,
  FileText,
  ExternalLink,
  Copy,
  Check,
  Database,
  Building2,
  Calendar,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// ── Tipos TypeScript Estritos ──────────────────────────────────────────────────

interface MarketSourceStatusItem {
  fonte_id: "BCB_PTAX" | "BCB_SGS" | "IBGE_SIDRA" | "DERAL_SEAB";
  nome: string;
  orgao: string;
  tipo_dado: string;
  url_origem: string;
  status: "ONLINE" | "DEFASADO" | "OFFLINE" | "DEGRADADO";
  cache_ttl_seconds: number;
  last_success_at?: string | null;
  last_error?: string | null;
  defasagem_dias?: number | null;
  detalhes_operacionais: Record<string, unknown>;
}

interface AgroMercadoConfig {
  ptax_cache_ttl_seconds: number;
  macro_cache_ttl_seconds: number;
  sidra_cache_ttl_seconds: number;
  precos_cache_ttl_seconds: number;
  max_defasagem_dias: number;
  deral_active_snapshot: string;
  active_snapshot_id: string;
  deral_source_url: string;
  ptax_enabled: boolean;
  sgs_enabled: boolean;
  sidra_enabled: boolean;
  deral_enabled: boolean;
}

interface MarketSourcesStatusResponse {
  sources: MarketSourceStatusItem[];
  config: AgroMercadoConfig;
  revision: number;
  updated_at: string;
}

interface DeralSnapshotMetadata {
  id: string;
  filename: string;
  sha256: string;
  data_referencia: string;
  data_publicacao?: string | null;
  data_obtencao?: string | null;
  fonte_oficial: string;
  origem_declarada?: string;
  origem_verificada?: boolean;
  estado_verificacao?: "PENDENTE" | "VERIFICADO" | "FALHA_VERIFICACAO";
  estado_aprovacao?: "PENDENTE" | "APROVADO" | "REJEITADO";
  aprovado_por?: string | null;
  aprovado_em?: string | null;
  motivo_rejeicao?: string | null;
  documento_oficial: string;
  total_itens: number;
  status: "VALIDADO" | "APROVADO" | "ATIVO" | "ANTERIOR" | "ARQUIVADO" | "REJEITADO";
  is_active: boolean;
  uploaded_at: string;
  uploaded_by: string;
  activated_at?: string | null;
  activated_by?: string | null;
  transformacao_aplicada: string;
  tamanho_bytes: number;
}

interface DeralSnapshotIntegrityResponse {
  snapshot_id: string;
  sha256_registrado: string;
  sha256_recalculado: string;
  tamanho_bytes_registrado: number;
  tamanho_bytes_armazenado: number;
  integro: boolean;
  verificado_em: string;
  origem_verificada: boolean;
  estado_verificacao: string;
  mensagem: string;
}

interface DeralSnapshotsListResponse {
  active_snapshot_id?: string | null;
  snapshots: DeralSnapshotMetadata[];
  total: number;
}

interface DeralSnapshotItem {
  id: string;
  commodityNome: string;
  produtoOriginal: string;
  classificacao: string;
  valor: number;
  valorOriginal: number;
  unidade: string;
  unidadeOriginal: string;
  registroOriginal: string;
}

interface DeralSnapshotDetailResponse {
  metadata: DeralSnapshotMetadata;
  itens: DeralSnapshotItem[];
  raw_document_preview?: Record<string, unknown> | null;
}

interface DeralSnapshotUploadResponse {
  sucesso: boolean;
  mensagem: string;
  metadata: DeralSnapshotMetadata;
  validacoes: string[];
  itens_preview: DeralSnapshotItem[];
}

export default function BackofficeMercadoPage() {
  const queryClient = useQueryClient();

  const canView =
    usePermission("backoffice:agro:market:view") ||
    usePermission("backoffice:agro:config:view") ||
    usePermission("backoffice:agro:*");

  const canUpdate =
    usePermission("backoffice:agro:market:update") ||
    usePermission("backoffice:agro:config:edit") ||
    usePermission("backoffice:agro:*");

  // Estados de modais e preview
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFeedback, setUploadFeedback] = useState<DeralSnapshotUploadResponse | null>(null);
  const [copiedSha, setCopiedSha] = useState<string | null>(null);

  // Estados de formulário de configuração
  const [formData, setFormData] = useState<{
    ptax_cache_ttl_seconds: number;
    macro_cache_ttl_seconds: number;
    sidra_cache_ttl_seconds: number;
    precos_cache_ttl_seconds: number;
    max_defasagem_dias: number;
    deral_source_url: string;
    ptax_enabled: boolean;
    sgs_enabled: boolean;
    sidra_enabled: boolean;
    deral_enabled: boolean;
  }>({
    ptax_cache_ttl_seconds: 1800,
    macro_cache_ttl_seconds: 1800,
    sidra_cache_ttl_seconds: 3600,
    precos_cache_ttl_seconds: 1800,
    max_defasagem_dias: 14,
    deral_source_url: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    ptax_enabled: true,
    sgs_enabled: true,
    sidra_enabled: true,
    deral_enabled: true,
  });

  // Queries
  const {
    data: statusData,
    isLoading: isLoadingStatus,
    isRefetching: isRefetchingStatus,
    refetch: refetchStatus,
  } = useQuery<MarketSourcesStatusResponse>({
    queryKey: ["backoffice-market-status"],
    queryFn: () => apiFetch("/api/v1/backoffice/agro/mercado/status"),
  });

  const {
    data: snapshotsData,
    isLoading: isLoadingSnapshots,
    refetch: refetchSnapshots,
  } = useQuery<DeralSnapshotsListResponse>({
    queryKey: ["backoffice-deral-snapshots"],
    queryFn: () => apiFetch("/api/v1/backoffice/agro/mercado/deral/snapshots"),
  });

  const {
    data: previewData,
    isLoading: isLoadingPreview,
  } = useQuery<DeralSnapshotDetailResponse>({
    queryKey: ["backoffice-deral-snapshot-preview", selectedSnapshotId],
    queryFn: () =>
      apiFetch(`/api/v1/backoffice/agro/mercado/deral/snapshots/${selectedSnapshotId}`),
    enabled: !!selectedSnapshotId,
  });

  // Preenche formulário quando statusData carrega
  React.useEffect(() => {
    if (statusData?.config) {
      setFormData({
        ptax_cache_ttl_seconds: statusData.config.ptax_cache_ttl_seconds,
        macro_cache_ttl_seconds: statusData.config.macro_cache_ttl_seconds,
        sidra_cache_ttl_seconds: statusData.config.sidra_cache_ttl_seconds,
        precos_cache_ttl_seconds: statusData.config.precos_cache_ttl_seconds,
        max_defasagem_dias: statusData.config.max_defasagem_dias,
        deral_source_url: statusData.config.deral_source_url,
        ptax_enabled: statusData.config.ptax_enabled,
        sgs_enabled: statusData.config.sgs_enabled,
        sidra_enabled: statusData.config.sidra_enabled,
        deral_enabled: statusData.config.deral_enabled,
      });
    }
  }, [statusData]);

  // Mutations
  const updateConfigMutation = useMutation({
    mutationFn: async () => {
      return apiFetch("/api/v1/backoffice/agro/mercado/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          expected_revision: statusData?.revision,
        }),
      });
    },
    onSuccess: () => {
      toast.success("Parâmetros operacionais e TTLs de cache atualizados com sucesso!");
      setIsConfigModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["backoffice-market-status"] });
    },
    onError: (error: Error) => {
      toast.error(`Falha ao salvar configuração: ${error.message}`);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (fileToUpload: File) => {
      const data = new FormData();
      data.append("file", fileToUpload);
      return apiFetch("/api/v1/backoffice/agro/mercado/deral/upload", {
        method: "POST",
        body: data,
      });
    },
    onSuccess: (res: DeralSnapshotUploadResponse) => {
      setUploadFeedback(res);
      toast.success("Snapshot validado e salvo com sucesso!");
      queryClient.invalidateQueries({ queryKey: ["backoffice-deral-snapshots"] });
    },
    onError: (error: Error) => {
      toast.error(`Falha na validação do snapshot: ${error.message}`);
    },
  });

  const activateMutation = useMutation({
    mutationFn: async (id: string) => {
      return apiFetch(`/api/v1/backoffice/agro/mercado/deral/snapshots/${id}/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expected_revision: statusData?.revision,
          justificativa: "Ativação administrativa de snapshot semanal homologado",
        }),
      });
    },
    onSuccess: () => {
      toast.success("Snapshot ativado com sucesso! Cache de preços atualizado.");
      setSelectedSnapshotId(null);
      queryClient.invalidateQueries({ queryKey: ["backoffice-market-status"] });
      queryClient.invalidateQueries({ queryKey: ["backoffice-deral-snapshots"] });
    },
    onError: (error: Error) => {
      toast.error(`Falha na ativação do snapshot: ${error.message}`);
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: async (targetId: string) => {
      return apiFetch(`/api/v1/backoffice/agro/mercado/deral/snapshots/${targetId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_snapshot_id: targetId,
          expected_revision: statusData?.revision,
          justificativa: "Rollback operacional preventivo homologado pelo Backoffice",
        }),
      });
    },
    onSuccess: () => {
      toast.success("Rollback concluído com sucesso! Versão anterior restaurada.");
      setSelectedSnapshotId(null);
      queryClient.invalidateQueries({ queryKey: ["backoffice-market-status"] });
      queryClient.invalidateQueries({ queryKey: ["backoffice-deral-snapshots"] });
    },
    onError: (error: Error) => {
      toast.error(`Falha no rollback: ${error.message}`);
    },
  });

  const approveMutation = useMutation({
    mutationFn: async ({
      snapshotId,
      aprovado,
      justificativa,
    }: {
      snapshotId: string;
      aprovado: boolean;
      justificativa: string;
    }) => {
      return apiFetch(`/api/v1/backoffice/agro/mercado/deral/snapshots/${snapshotId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aprovado, justificativa }),
      });
    },
    onSuccess: (_, vars) => {
      toast.success(
        vars.aprovado
          ? "Proveniência do snapshot DERAL aprovada com sucesso!"
          : "Snapshot DERAL formalmente rejeitado."
      );
      queryClient.invalidateQueries({ queryKey: ["backoffice-deral-snapshots"] });
    },
    onError: (error: Error) => {
      toast.error(`Falha ao aprovar/rejeitar: ${error.message}`);
    },
  });

  const [integrityData, setIntegrityData] = useState<DeralSnapshotIntegrityResponse | null>(null);
  const [isIntegrityModalOpen, setIsIntegrityModalOpen] = useState(false);

  const checkIntegrity = async (snapshotId: string) => {
    try {
      const res: DeralSnapshotIntegrityResponse = await apiFetch(
        `/api/v1/backoffice/agro/mercado/deral/snapshots/${snapshotId}/verify-integrity`
      );
      setIntegrityData(res);
      setIsIntegrityModalOpen(true);
      if (res.integro) {
        toast.success("Integridade dos bytes verificada com sucesso!");
      } else {
        toast.error("Alerta: Falha de integridade criptográfica no snapshot!");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Erro ao verificar integridade: ${msg}`);
    }
  };

  const downloadRaw = (snapshotId: string) => {
    window.open(`/api/v1/backoffice/agro/mercado/deral/snapshots/${snapshotId}/download-raw`, "_blank");
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(sha);
    toast.success("SHA-256 copiado para a área de transferência!");
    setTimeout(() => setCopiedSha(null), 2000);
  };

  if (!canView) {
    return (
      <div className="p-6">
        <Alert variant="destructive" className="rounded-sm">
          <AlertOctagon className="h-4 w-4" />
          <AlertTitle>Acesso Negado</AlertTitle>
          <AlertDescription>
            Você não possui permissão (backoffice:agro:market:view) para acessar a governança de
            mercado e fontes oficiais.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Mercado & Fontes Oficiais"
        description="Governança de integridade, parâmetros de cache, rastreabilidade e versionamento atômico das fontes públicas do Agro."
        icon={<TrendingUp className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />}
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Configurações Agro", href: "/dashboard/backoffice/agro" },
          { label: "Mercado & Fontes" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => {
                refetchStatus();
                refetchSnapshots();
                toast.info("Status das fontes atualizado.");
              }}
              disabled={isRefetchingStatus}
            >
              <RefreshCw
                className={`mr-2 h-3.5 w-3.5 ${isRefetchingStatus ? "animate-spin" : ""}`}
              />
              Atualizar Status
            </Button>
            {canUpdate && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-sm border-emerald-600/30 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/30"
                  onClick={() => setIsConfigModalOpen(true)}
                >
                  <Server className="mr-2 h-3.5 w-3.5" />
                  Parâmetros Operacionais
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-sm bg-emerald-600 text-white hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-700"
                  onClick={() => {
                    setUploadFeedback(null);
                    setUploadFile(null);
                    setIsUploadModalOpen(true);
                  }}
                >
                  <Upload className="mr-2 h-3.5 w-3.5" />
                  Ingerir Snapshot DERAL
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* Alerta de Segurança e Imutabilidade */}
      <Alert className="rounded-sm border-emerald-500/20 bg-emerald-50/50 text-emerald-900 dark:bg-emerald-950/20 dark:text-emerald-200">
        <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        <AlertTitle className="text-xs font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">
          Autenticidade e Governança Pública Estrita
        </AlertTitle>
        <AlertDescription className="text-xs text-emerald-700/90 dark:text-emerald-300/80">
          As cotações de preços (DERAL), taxas cambiais (PTAX), séries temporais (SGS) e estatísticas
          (SIDRA) são dados oficiais homologados e imutáveis. Esta interface administra
          exclusivamente parâmetros de observabilidade, TTLs de cache e ciclo de vida de snapshots. É
          estritamente vedada a adulteração manual de cotações governamentais.
        </AlertDescription>
      </Alert>

      {/* Grid de Situação das Fontes Oficiais */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoadingStatus ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="rounded-sm">
              <CardHeader className="p-4">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-3 w-40 mt-1" />
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))
        ) : (
          statusData?.sources.map((source) => {
            const isOnline = source.status === "ONLINE";
            const isDefasado = source.status === "DEFASADO";

            return (
              <Card
                key={source.fonte_id}
                className={`rounded-sm transition-all hover:border-emerald-500/30 ${
                  isDefasado
                    ? "border-amber-500/30 bg-amber-50/10"
                    : isOnline
                    ? "border-emerald-500/20"
                    : "border-red-500/20 bg-red-50/10"
                }`}
              >
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-sm font-medium">{source.nome}</CardTitle>
                      <CardDescription className="text-xs truncate max-w-[200px]">
                        {source.orgao}
                      </CardDescription>
                    </div>
                    <Badge
                      variant="outline"
                      className={`rounded-sm text-[10px] font-medium ${
                        isOnline
                          ? "border-emerald-600/30 text-emerald-700 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/40"
                          : isDefasado
                          ? "border-amber-600/30 text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-950/40"
                          : "border-red-600/30 text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-950/40"
                      }`}
                    >
                      {source.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2 space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Cache TTL:</span>
                    <span className="font-mono font-medium text-foreground">
                      {Math.round(source.cache_ttl_seconds / 60)} min ({source.cache_ttl_seconds}s)
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Defasagem Estimada:</span>
                    <span
                      className={`font-medium ${
                        (source.defasagem_dias ?? 0) > 14
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-foreground"
                      }`}
                    >
                      {source.defasagem_dias !== null && source.defasagem_dias !== undefined
                        ? `${source.defasagem_dias} dia(s)`
                        : "Tempo real"}
                    </span>
                  </div>

                  <div className="pt-2 border-t border-border/50 text-[11px] text-muted-foreground flex items-center justify-between">
                    <span className="truncate max-w-[170px]" title={source.tipo_dado}>
                      {source.tipo_dado}
                    </span>
                    <a
                      href={source.url_origem}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-600 hover:underline flex items-center gap-0.5 shrink-0"
                    >
                      Fonte <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Seção Principal: Gerenciamento e Versionamento de Snapshots DERAL */}
      <Card className="rounded-sm">
        <CardHeader className="p-4 pb-3 border-b border-border/50">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Database className="h-4 w-4 text-emerald-600" />
                Catálogo e Histórico de Snapshots DERAL
              </CardTitle>
              <CardDescription className="text-xs">
                Pipeline de validação de esquemas das 21 commodities oficiais, integridade SHA-256 e
                ativação atômica sem downtime.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="rounded-sm font-mono text-[11px]">
                Ativo: {statusData?.config?.active_snapshot_id ?? "2026-10-16"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingSnapshots ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : snapshotsData?.snapshots && snapshotsData.snapshots.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/40 border-b border-border text-muted-foreground font-medium">
                  <tr>
                    <th className="p-3 pl-4">Data Ref.</th>
                    <th className="p-3">Arquivo & Documento</th>
                    <th className="p-3">SHA-256 (Integridade)</th>
                    <th className="p-3">Itens</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Ingestão</th>
                    <th className="p-3 pr-4 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {snapshotsData.snapshots.map((snap) => {
                    const isActive = snap.is_active;
                    const canActivate = !isActive && snap.status === "VALIDADO";
                    const canRollback = !isActive && (snap.status === "ANTERIOR" || snap.status === "VALIDADO");

                    return (
                      <tr
                        key={snap.id}
                        className={`hover:bg-muted/20 transition-colors ${
                          isActive ? "bg-emerald-50/20 dark:bg-emerald-950/10 font-medium" : ""
                        }`}
                      >
                        <td className="p-3 pl-4 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 font-mono">
                            <Calendar className="h-3 w-3 text-muted-foreground" />
                            {snap.data_referencia}
                          </div>
                        </td>

                        <td className="p-3 whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="font-medium text-foreground">{snap.filename}</span>
                            <span className="text-[11px] text-muted-foreground truncate max-w-[200px]" title={snap.documento_oficial}>
                              {snap.documento_oficial}
                            </span>
                          </div>
                        </td>

                        <td className="p-3 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                            <span>{snap.sha256.substring(0, 16)}...</span>
                            <button
                              type="button"
                              onClick={() => handleCopySha(snap.sha256)}
                              className="text-muted-foreground hover:text-foreground transition-colors"
                              title="Copiar hash SHA-256 completo"
                            >
                              {copiedSha === snap.sha256 ? (
                                <Check className="h-3 w-3 text-emerald-600" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </button>
                          </div>
                        </td>

                        <td className="p-3 whitespace-nowrap">
                          <Badge variant="outline" className="rounded-sm font-mono text-[10px]">
                            {snap.total_itens} commodities
                          </Badge>
                        </td>

                        <td className="p-3 whitespace-nowrap">
                          <Badge
                            variant="outline"
                            className={`rounded-sm text-[10px] uppercase font-semibold ${
                              isActive
                                ? "border-emerald-600 text-emerald-700 bg-emerald-100/60 dark:text-emerald-400 dark:bg-emerald-950/60"
                                : snap.status === "VALIDADO"
                                ? "border-blue-500/40 text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-950/40"
                                : "border-muted-foreground/30 text-muted-foreground"
                            }`}
                          >
                            {isActive ? "ATIVO" : snap.status}
                          </Badge>
                        </td>

                        <td className="p-3 whitespace-nowrap text-[11px] text-muted-foreground">
                          <div>
                            {snap.uploaded_at ? format(new Date(snap.uploaded_at), "dd/MM/yyyy HH:mm", { locale: ptBR }) : "—"}
                          </div>
                          <div className="text-[10px] truncate max-w-[130px]">{snap.uploaded_by}</div>
                        </td>

                        <td className="p-3 pr-4 whitespace-nowrap text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-sm h-7 px-2 text-xs"
                              onClick={() => setSelectedSnapshotId(snap.id)}
                              title="Pré-visualizar dados e proveniência"
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              Preview
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-sm h-7 px-2 text-xs"
                              onClick={() => checkIntegrity(snap.id)}
                              title="Auditar e recalcular hash SHA-256 dos bytes persistidos"
                            >
                              <ShieldCheck className="h-3 w-3 mr-1 text-emerald-600" />
                              Integridade
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-sm h-7 px-2 text-xs"
                              onClick={() => downloadRaw(snap.id)}
                              title="Baixar arquivo original bruto imutável"
                            >
                              <Download className="h-3 w-3" />
                            </Button>

                            {canUpdate && !isActive && snap.status === "VALIDADO" && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="rounded-sm h-7 px-2 text-xs border-blue-600 text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-950/50"
                                onClick={() =>
                                  approveMutation.mutate({
                                    snapshotId: snap.id,
                                    aprovado: true,
                                    justificativa: "Aprovação formal de proveniência governamental",
                                  })
                                }
                                disabled={approveMutation.isPending}
                                title="Aprovar proveniência governamental"
                              >
                                <Check className="h-3 w-3 mr-1" />
                                Aprovar
                              </Button>
                            )}

                            {canUpdate && canActivate && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="rounded-sm h-7 px-2 text-xs border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/50"
                                onClick={() => activateMutation.mutate(snap.id)}
                                disabled={activateMutation.isPending}
                              >
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                Ativar
                              </Button>
                            )}

                            {canUpdate && canRollback && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="rounded-sm h-7 px-2 text-xs border-amber-600/40 text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950/50"
                                onClick={() => rollbackMutation.mutate(snap.id)}
                                disabled={rollbackMutation.isPending}
                                title="Reverter ponteiro ativo para esta versão homologada"
                              >
                                <RotateCcw className="h-3 w-3 mr-1" />
                                Rollback
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground text-xs">
              Nenhum snapshot DERAL catalogado no momento.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal de Pré-Visualização do Snapshot */}
      <Dialog
        open={!!selectedSnapshotId}
        onOpenChange={(open) => {
          if (!open) setSelectedSnapshotId(null);
        }}
      >
        <DialogContent className="w-[calc(100vw-1rem)] sm:w-[calc(100vw-2rem)] max-w-3xl max-h-[calc(100dvh-2rem)] overflow-hidden rounded-sm p-4 sm:p-6 gap-4">
          <DialogHeader>
            <DialogTitle className="min-w-0 pr-8 text-base font-semibold flex items-start gap-2">
              <FileCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <span className="min-w-0 break-words">
                Auditoria e Pré-Visualização
                {previewData?.metadata.id && <> — Snapshot {previewData.metadata.id}</>}
              </span>
            </DialogTitle>
            <DialogDescription className="text-xs">
              Validação das 21 commodities homologadas, hash criptográfico de bytes e documento oficial de origem.
            </DialogDescription>
          </DialogHeader>

          {isLoadingPreview ? (
            <div className="min-h-0 flex-1 overflow-y-auto py-2 pr-1 space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : previewData ? (
            <div className="min-h-0 flex-1 overflow-y-auto pr-1 space-y-4 text-xs">
              {/* Metadados Técnicos */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2 p-3 bg-muted/40 rounded-sm">
                <div>
                  <span className="text-muted-foreground block text-[10px]">Data de Referência</span>
                  <span className="font-mono font-medium">{previewData.metadata.data_referencia}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px]">Total de Cotações</span>
                  <span className="font-mono font-medium">{previewData.metadata.total_itens} commodities</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px]">Tamanho do Arquivo</span>
                  <span className="font-mono font-medium">{previewData.metadata.tamanho_bytes} bytes</span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px]">Situação</span>
                  <Badge variant="outline" className="rounded-sm text-[10px]">
                    {previewData.metadata.is_active ? "ATIVO EM PRODUÇÃO" : previewData.metadata.status}
                  </Badge>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground block text-[10px]">Hash SHA-256 (Integridade de Bytes)</span>
                <div className="p-2 bg-muted/60 rounded-sm font-mono text-[11px] break-all select-all flex items-start justify-between gap-2">
                  <span className="min-w-0">{previewData.metadata.sha256}</span>
                  <button
                    type="button"
                    onClick={() => handleCopySha(previewData.metadata.sha256)}
                    className="shrink-0 hover:text-emerald-600"
                    aria-label="Copiar hash SHA-256"
                    title="Copiar hash"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <div>
                <span className="text-muted-foreground block text-[10px]">Documento Oficial de Proveniência</span>
                <span className="font-mono text-[11px] break-all">{previewData.metadata.documento_oficial}</span>
              </div>

              {/* Tabela dos 21 Itens */}
              <div className="border border-border rounded-sm overflow-hidden mt-3">
                <div className="bg-muted/60 p-2 font-medium text-xs border-b border-border">
                  Cotações Auditadas (21 Itens Oficiais)
                </div>
                <div className="max-h-[min(40vh,300px)] divide-y divide-border/50 overflow-y-auto md:hidden">
                  {previewData.itens.map((item) => (
                    <div key={item.id} className="space-y-2 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <span className="min-w-0 break-words font-medium text-foreground">
                          {item.commodityNome}
                        </span>
                        <span className="shrink-0 text-right font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                          R$ {item.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                        <span className="truncate" title={item.classificacao}>{item.classificacao}</span>
                        <span>{item.unidade}</span>
                        <span className="col-span-2 break-all font-mono">{item.registroOriginal}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="hidden max-h-[min(40vh,300px)] overflow-auto md:block">
                  <table className="w-full min-w-[680px] text-left text-xs">
                    <thead className="bg-muted/30 border-b border-border text-muted-foreground text-[11px]">
                      <tr>
                        <th className="p-2 pl-3">Commodity</th>
                        <th className="p-2">Classificação</th>
                        <th className="p-2 text-right">Preço Médio (R$)</th>
                        <th className="p-2">Unidade</th>
                        <th className="p-2 pr-3">Célula / Registro</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {previewData.itens.map((item) => (
                        <tr key={item.id} className="hover:bg-muted/20">
                          <td className="p-2 pl-3 font-medium text-foreground">{item.commodityNome}</td>
                          <td className="p-2 text-muted-foreground truncate max-w-[200px]" title={item.classificacao}>
                            {item.classificacao}
                          </td>
                          <td className="p-2 text-right font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                            {item.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="p-2 text-muted-foreground">{item.unidade}</td>
                          <td className="p-2 pr-3 font-mono text-[11px] text-muted-foreground">{item.registroOriginal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}

          <DialogFooter className="mt-0 flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setSelectedSnapshotId(null)}
            >
              Fechar
            </Button>
            {canUpdate && previewData && !previewData.metadata.is_active && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm bg-emerald-600 text-white hover:bg-emerald-700"
                onClick={() => activateMutation.mutate(previewData.metadata.id)}
                disabled={activateMutation.isPending}
              >
                <CheckCircle2 className="mr-2 h-3.5 w-3.5" />
                Ativar este Snapshot
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de Ingestão e Upload de Snapshot */}
      <Dialog open={isUploadModalOpen} onOpenChange={setIsUploadModalOpen}>
        <DialogContent className="max-w-lg rounded-sm">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Upload className="h-4 w-4 text-emerald-600" />
              Ingestão de Snapshot DERAL/SEAB-PR
            </DialogTitle>
            <DialogDescription className="text-xs">
              Envie o documento estruturado oficial (.json) para validação de integridade antes da ativação em produção.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="border-2 border-dashed border-border rounded-sm p-6 text-center hover:border-emerald-500/50 transition-colors">
              <Input
                type="file"
                accept=".json,.xlsx,.xls"
                className="hidden"
                id="file-upload"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setUploadFile(file);
                }}
              />
              <Label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center justify-center space-y-2"
              >
                <FileText className="h-8 w-8 text-muted-foreground" />
                <span className="font-medium text-foreground">
                  {uploadFile ? uploadFile.name : "Clique para selecionar o arquivo DERAL (.json)"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {uploadFile ? `${(uploadFile.size / 1024).toFixed(1)} KB` : "Máximo de 5 MB. Formato JSON oficial homologado."}
                </span>
              </Label>
            </div>

            {uploadFeedback && (
              <Alert className="rounded-sm border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-950/20">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <AlertTitle className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
                  Validação Concluída com Sucesso!
                </AlertTitle>
                <AlertDescription className="text-xs text-emerald-700/90 dark:text-emerald-300/90 space-y-1 mt-1">
                  <div>Snapshot: <strong>{uploadFeedback.metadata.id}</strong> ({uploadFeedback.metadata.filename})</div>
                  <div>SHA-256: <code className="text-[10px] font-mono">{uploadFeedback.metadata.sha256.substring(0, 24)}...</code></div>
                  <div>Itens válidos: <strong>{uploadFeedback.metadata.total_itens} commodities</strong></div>
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setIsUploadModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm bg-emerald-600 text-white hover:bg-emerald-700"
              onClick={() => {
                if (uploadFile) {
                  uploadMutation.mutate(uploadFile);
                } else {
                  toast.error("Por favor, selecione um arquivo primeiro.");
                }
              }}
              disabled={!uploadFile || uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Validando..." : "Validar e Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de Parâmetros Operacionais e TTLs de Cache */}
      <Dialog open={isConfigModalOpen} onOpenChange={setIsConfigModalOpen}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Server className="h-4 w-4 text-emerald-600" />
              Parâmetros Operacionais de Mercado
            </DialogTitle>
            <DialogDescription className="text-xs">
              Ajuste as políticas de TTL de cache e tolerâncias de defasagem para resiliência dos serviços públicos.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <Label className="text-xs font-medium">TTL Cache PTAX — Banco Central (segundos)</Label>
              <Input
                type="number"
                min={300}
                max={14400}
                className="h-8 text-xs rounded-sm"
                value={formData.ptax_cache_ttl_seconds}
                onChange={(e) =>
                  setFormData({ ...formData, ptax_cache_ttl_seconds: parseInt(e.target.value) || 1800 })
                }
              />
              <span className="text-[10px] text-muted-foreground">Mínimo 300s (5m), máximo 14400s (4h).</span>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">TTL Cache Indicadores SGS — Banco Central (segundos)</Label>
              <Input
                type="number"
                min={300}
                max={86400}
                className="h-8 text-xs rounded-sm"
                value={formData.macro_cache_ttl_seconds}
                onChange={(e) =>
                  setFormData({ ...formData, macro_cache_ttl_seconds: parseInt(e.target.value) || 1800 })
                }
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">TTL Cache Estatísticas SIDRA — IBGE (segundos)</Label>
              <Input
                type="number"
                min={300}
                max={604800}
                className="h-8 text-xs rounded-sm"
                value={formData.sidra_cache_ttl_seconds}
                onChange={(e) =>
                  setFormData({ ...formData, sidra_cache_ttl_seconds: parseInt(e.target.value) || 3600 })
                }
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">TTL Cache Preços Públicos — DERAL (segundos)</Label>
              <Input
                type="number"
                min={300}
                max={86400}
                className="h-8 text-xs rounded-sm"
                value={formData.precos_cache_ttl_seconds}
                onChange={(e) =>
                  setFormData({ ...formData, precos_cache_ttl_seconds: parseInt(e.target.value) || 1800 })
                }
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Tolerância Máxima de Defasagem (dias corridos)</Label>
              <Input
                type="number"
                min={1}
                max={60}
                className="h-8 text-xs rounded-sm"
                value={formData.max_defasagem_dias}
                onChange={(e) =>
                  setFormData({ ...formData, max_defasagem_dias: parseInt(e.target.value) || 14 })
                }
              />
              <span className="text-[10px] text-muted-foreground">
                Período antes de marcar a cotação com a flag &apos;DEFASADO&apos; nos alertas.
              </span>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setIsConfigModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm bg-emerald-600 text-white hover:bg-emerald-700"
              onClick={() => updateConfigMutation.mutate()}
              disabled={updateConfigMutation.isPending}
            >
              {updateConfigMutation.isPending ? "Salvando..." : "Salvar Parâmetros"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal de Auditoria e Recálculo de Integridade */}
      <Dialog open={isIntegrityModalOpen} onOpenChange={setIsIntegrityModalOpen}>
        <DialogContent className="rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              Auditoria Criptográfica de Bytes
            </DialogTitle>
            <DialogDescription className="text-xs">
              Recálculo forense de hash SHA-256 executado diretamente sobre os bytes binários armazenados.
            </DialogDescription>
          </DialogHeader>

          {integrityData && (
            <div className="space-y-3 py-2 text-xs">
              <div
                className={`p-3 rounded-sm border ${
                  integrityData.integro
                    ? "border-emerald-500/30 bg-emerald-50/50 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"
                    : "border-red-500/30 bg-red-50/50 text-red-900 dark:bg-red-950/30 dark:text-red-300"
                }`}
              >
                <div className="font-semibold flex items-center gap-1.5 mb-1">
                  {integrityData.integro ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      Documento Íntegro e Não Adulterado
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      Falha de Integridade Detectada
                    </>
                  )}
                </div>
                <p className="text-[11px] opacity-90">{integrityData.mensagem}</p>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Hash SHA-256 Registrado (Upload):</Label>
                <div className="font-mono text-[11px] p-2 bg-muted rounded-sm break-all">
                  {integrityData.sha256_registrado}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Hash SHA-256 Recalculado (Storage):</Label>
                <div className="font-mono text-[11px] p-2 bg-muted rounded-sm break-all">
                  {integrityData.sha256_recalculado}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-muted-foreground">
                <div className="p-2 border rounded-sm">
                  <div className="text-[10px]">Tamanho Gravado:</div>
                  <div className="font-mono text-foreground font-semibold">
                    {integrityData.tamanho_bytes_armazenado} bytes
                  </div>
                </div>
                <div className="p-2 border rounded-sm">
                  <div className="text-[10px]">Proveniência:</div>
                  <div className="font-mono text-foreground font-semibold">
                    {integrityData.estado_verificacao}
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setIsIntegrityModalOpen(false)}
            >
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
