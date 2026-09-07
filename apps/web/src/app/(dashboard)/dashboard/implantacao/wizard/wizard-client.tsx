"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Flag,
  Loader2,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Target,
  Pencil,
  Wrench,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/shared";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useWizard } from "@/hooks/use-wizard";
import { WizardFlow } from "./wizard-flow";
import { type Edge, MarkerType, type Node } from "@xyflow/react";
import type {
  WizardActionPayload,
  WizardChecklistSeverity,
  WizardChecklistStatus,
  WizardEtapa,
  WizardPendencia,
  WizardResumo,
  WizardStatus,
} from "@/types/wizard";

type ActionButton = {
  label: string;
  endpoint: string;
  successMessage: string;
  variant?: "default" | "outline" | "destructive" | "secondary";
  icon: typeof PlayCircle;
  payload?: WizardActionPayload;
};

type LoadStrategy = "MANUAL" | "ERP" | "LATER";



function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getLoadStrategy(status: WizardResumo | undefined): LoadStrategy | null {
  const diagnostico = isObject(status?.diagnostico_inicial_snapshot)
    ? status.diagnostico_inicial_snapshot
    : null;
  
  if (diagnostico?.configurar_erp_depois === true) return "LATER";
  if (diagnostico?.utiliza_erp === true) return "ERP";
  if (diagnostico?.utiliza_erp === false) return "MANUAL";

  const escopo = isObject(status?.escopo_modulos) ? status.escopo_modulos : null;
  const estrategia = diagnostico?.estrategia_carga;

  if (estrategia === "ERP" || escopo?.integracao_erp === true) return "ERP";
  if (estrategia === "MANUAL") return "MANUAL";
  if (estrategia === "LATER") return "LATER";
  return null;
}

function getErpName(status: WizardResumo | undefined): string {
  const diagnostico = isObject(status?.diagnostico_inicial_snapshot)
    ? status.diagnostico_inicial_snapshot
    : null;
  const escopo = isObject(status?.escopo_modulos) ? status.escopo_modulos : null;
  if (typeof diagnostico?.erp_nome === "string") return diagnostico.erp_nome;
  if (typeof escopo?.erp_nome === "string") return escopo.erp_nome;
  return "";
}



function getWizardMode(strategy: LoadStrategy): string {
  return strategy === "ERP" ? "ASSISTIDA" : "MANUAL_ASSISTIDA";
}

function getStrategyLabel(strategy: LoadStrategy | null) {
  if (strategy === "ERP") return "Carga via ERP";
  if (strategy === "MANUAL") return "Carga manual assistida";
  if (strategy === "LATER") return "Configurarei depois";
  return "Estratégia pendente";
}

const STAGE_STATUS_META: Record<WizardEtapa["status"], string> = {
  NOT_STARTED: "Não iniciada",
  IN_PROGRESS: "Em andamento",
  COMPLETED: "Concluída",
  SKIPPED: "Dispensada",
  BLOCKED: "Bloqueada",
};

const STATUS_META: Record<
  WizardStatus,
  { label: string; className: string; description: string }
> = {
  NOT_STARTED: {
    label: "Não iniciado",
    className: "border-slate-300 bg-slate-100 text-slate-700",
    description: "A implantação ainda não foi aberta para este tenant.",
  },
  IN_PROGRESS: {
    label: "Em progresso",
    className: "border-blue-200 bg-blue-500/10 text-blue-700",
    description: "A implantação está em execução e pode avançar por etapas.",
  },
  PAUSED: {
    label: "Pausado",
    className: "border-amber-200 bg-amber-500/10 text-amber-700",
    description: "A implantação foi pausada operacionalmente e pode ser retomada.",
  },
  BLOCKED: {
    label: "Bloqueado",
    className: "border-red-200 bg-red-500/10 text-red-700",
    description: "Existe um impedimento estrutural ativo antes do go-live.",
  },
  READY_FOR_GO_LIVE: {
    label: "Pronto para go-live",
    className: "border-emerald-200 bg-emerald-500/10 text-emerald-700",
    description: "Os requisitos mínimos foram atendidos para avançar ao go-live.",
  },
  GO_LIVE: {
    label: "Go-live",
    className: "border-emerald-200 bg-emerald-600/15 text-emerald-700",
    description: "A implantação entrou em go-live assistido.",
  },
  STABILIZATION: {
    label: "Estabilização",
    className: "border-violet-200 bg-violet-500/10 text-violet-700",
    description: "A operação está em estabilização pós go-live.",
  },
  COMPLETED: {
    label: "Concluído",
    className: "border-emerald-200 bg-emerald-500/10 text-emerald-700",
    description: "A implantação operacional foi concluída.",
  },
  CANCELLED: {
    label: "Cancelado",
    className: "border-slate-300 bg-slate-100 text-slate-700",
    description: "A implantação foi encerrada sem continuar o fluxo.",
  },
};

const CHECKLIST_STATUS_META: Record<
  WizardChecklistStatus,
  { label: string; className: string }
> = {
  PENDENTE: {
    label: "Pendente",
    className: "border-amber-200 bg-amber-500/10 text-amber-700",
  },
  ATENDIDO: {
    label: "Atendido",
    className: "border-emerald-200 bg-emerald-500/10 text-emerald-700",
  },
  DISPENSADO: {
    label: "Dispensado",
    className: "border-slate-300 bg-slate-100 text-slate-700",
  },
  FALHOU: {
    label: "Falhou",
    className: "border-red-200 bg-red-500/10 text-red-700",
  },
};

const SEVERITY_META: Record<WizardChecklistSeverity, string> = {
  INFO: "border-sky-200 bg-sky-500/10 text-sky-700",
  ATENCAO: "border-amber-200 bg-amber-500/10 text-amber-700",
  CRITICO: "border-red-200 bg-red-500/10 text-red-700",
};

const CHECKLIST_SEVERITY_LABEL: Record<WizardChecklistSeverity, string> = {
  INFO: "Informativo",
  ATENCAO: "Atenção",
  CRITICO: "Crítico",
};

const PENDENCIA_SEVERITY_LABEL: Record<WizardPendencia["severidade"], string> = {
  BAIXA: "Baixa",
  MEDIA: "Média",
  ALTA: "Alta",
  CRITICA: "Crítica",
};

const PENDENCIA_STATUS_LABEL: Record<WizardPendencia["status"], string> = {
  ABERTA: "Aberta",
  EM_TRATAMENTO: "Em tratamento",
  RESOLVIDA: "Resolvida",
  DESCARTADA: "Descartada",
};

const EVIDENCIA_TIPO_LABEL: Record<string, string> = {
  AUTOMATICA: "Validação automática",
  MANUAL: "Validação manual",
  DOCUMENTAL: "Documento anexado",
  REFERENCIAL: "Referência de cadastro",
};

function formatInternalCode(value: string) {
  return value
    .replace(/^WIZARD::/, "")
    .split(/[_:\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(" ");
}

const WIZARD_INTERNAL_TITLES: Record<string, string> = {
  "CHECK_UNIDADE_PRODUTIVA": "Validação de Unidade Produtiva",
  "CHECK_ESTRUTURA_TERRITORIAL": "Validação de Estrutura Territorial",
  "CHECK_AGRICULTURA_TALHAO": "Validação de Talhões Agrícolas",
  "CHECK_PECUARIA_PIQUETE": "Validação de Piquetes",
  "CHECK_ESTOQUE_DEPOSITO": "Validação de Depósito de Estoque",
  "CHECK_FINANCEIRO_PLANO_CONTA": "Validação de Plano de Contas",
  "CHECK_PRODUTO_CATALOGO": "Validação de Catálogo de Produtos",
  "CHECK_MAQUINA_EQUIPAMENTO": "Validação de Máquinas e Equipamentos",
  "CHECK_CULTURA": "Validação de Culturas",
  "CHECK_INTEGRACAO_ERP": "Validação de Integração de ERP",
};

function formatPendenciaTitulo(titulo: string) {
  if (titulo.startsWith("WIZARD::")) {
    const code = titulo.replace("WIZARD::", "");
    return WIZARD_INTERNAL_TITLES[code] ?? formatInternalCode(code);
  }
  return titulo;
}

function formatDateTime(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function getReadyBadge(status: WizardResumo) {
  if (
    status.status === "READY_FOR_GO_LIVE" ||
    status.status === "GO_LIVE" ||
    status.status === "STABILIZATION" ||
    status.status === "COMPLETED"
  ) {
    return {
      label: "Pronto para operar",
      className: "border-emerald-200 bg-emerald-500/10 text-emerald-700",
    };
  }

  if (status.elegivel_para_pronto_go_live) {
    return {
      label: "Elegível para go-live",
      className: "border-emerald-200 bg-emerald-500/10 text-emerald-700",
    };
  }

  if (status.pendencias_criticas_abertas > 0) {
    return {
      label: `${status.pendencias_criticas_abertas} bloqueio(s) crítico(s)`,
      className: "border-red-200 bg-red-500/10 text-red-700",
    };
  }

  return {
    label: "Preparação em andamento",
    className: "border-amber-200 bg-amber-500/10 text-amber-700",
  };
}

function getPrimaryAction(status: WizardResumo | undefined) {
  if (!status) {
    return {
      label: "Iniciar implantação",
      icon: PlayCircle,
    };
  }

  if (status.status === "PAUSED" || status.status === "BLOCKED") {
    return {
      label: "Retomar implantação",
      icon: PlayCircle,
    };
  }

  return {
    label: "Implantação em andamento",
    icon: RefreshCw,
  };
}

function getStatusActions(status: WizardResumo): ActionButton[] {
  switch (status.status) {
    case "IN_PROGRESS":
      return [
        {
          label: "Pausar",
          endpoint: "/wizard/pausar",
          successMessage: "Implantação pausada.",
          variant: "outline",
          icon: PauseCircle,
        },
        {
          label: "Bloquear",
          endpoint: "/wizard/bloquear",
          successMessage: "Implantação bloqueada.",
          variant: "outline",
          icon: ShieldAlert,
          payload: { motivo: "Bloqueio operacional registrado no Wizard." },
        },
        {
          label: "Marcar pronto para go-live",
          endpoint: "/wizard/pronto-go-live",
          successMessage: "Implantação marcada como pronta para go-live.",
          icon: Target,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    case "PAUSED":
      return [
        {
          label: "Retomar",
          endpoint: "/wizard/retomar",
          successMessage: "Implantação retomada.",
          icon: PlayCircle,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    case "BLOCKED":
      return [
        {
          label: "Desbloquear",
          endpoint: "/wizard/desbloquear",
          successMessage: "Implantação desbloqueada.",
          icon: Wrench,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    case "READY_FOR_GO_LIVE":
      return [
        {
          label: "Iniciar go-live",
          endpoint: "/wizard/go-live",
          successMessage: "Go-live iniciado.",
          icon: Sparkles,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    case "GO_LIVE":
      return [
        {
          label: "Iniciar estabilização",
          endpoint: "/wizard/estabilizar",
          successMessage: "Estabilização iniciada.",
          icon: Flag,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    case "STABILIZATION":
      return [
        {
          label: "Concluir",
          endpoint: "/wizard/concluir",
          successMessage: "Implantação concluída.",
          icon: CheckCircle2,
        },
        {
          label: "Cancelar",
          endpoint: "/wizard/cancelar",
          successMessage: "Implantação cancelada.",
          variant: "destructive",
          icon: XCircle,
        },
      ];
    default:
      return [];
  }
}

function getEtapaAtualNome(status: WizardResumo, etapas: WizardEtapa[]): string {
  return etapas.find((etapa) => etapa.codigo_etapa === status.etapa_atual)?.nome ?? status.etapa_atual;
}

function getEvidenceTypeLabel(value: string) {
  return EVIDENCIA_TIPO_LABEL[value] ?? formatInternalCode(value);
}

function getChecklistActionGuidance(codigoItem: string) {
  const nome = WIZARD_INTERNAL_TITLES[codigoItem] ?? formatInternalCode(codigoItem);
  return `Conclua o cadastro ou a configuração exigida na etapa de ${nome} para que a validação automática seja refeita com sucesso.`;
}

function buildContextualLink(href: string, unidadeProdutivaId: string | null) {
  if (!unidadeProdutivaId) return href;

  const [path, hash] = href.split("#", 2);
  const [pathname, query] = path.split("?", 2);
  const params = new URLSearchParams(query ?? "");
  params.set("unidade_produtiva_id", unidadeProdutivaId);
  const finalPath = `${pathname}?${params.toString()}`;
  return hash ? `${finalPath}#${hash}` : finalPath;
}
function WizardSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-4 w-[32rem]" />
      </div>
      <Card className="rounded-sm shadow-sm">
        <CardContent className="space-y-5 p-6">
          <Skeleton className="h-6 w-60" />
          <Skeleton className="h-3 w-full" />
          <div className="grid gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Skeleton className="h-[420px] w-full" />
        <Skeleton className="h-[420px] w-full" />
      </div>
      <Skeleton className="h-[280px] w-full" />
    </div>
  );
}

export function WizardClient() {
  const {
    statusQuery,
    checklistQuery,
    iniciarMutation,
    configurarCargaMutation,
    reavaliarChecklistMutation,
    actionMutation,
    hasActiveWizard,
    wizardNotStarted,
  } = useWizard();
  const [loadStrategy, setLoadStrategy] = useState<LoadStrategy | null>(null);
  const [erpIdSelection, setErpIdSelection] = useState<number | null>(null);
  const [erpSlugSelection, setErpSlugSelection] = useState<string | null>(null);
  const [erpNameSelection, setErpNameSelection] = useState<string | null>(null);
  const [editingCarga, setEditingCarga] = useState(false);

  const { data: erps = [], isLoading: isLoadingErps, isError: isErpsError, refetch: refetchErps } = useQuery({
    queryKey: ["erp-providers"],
    queryFn: () => apiFetch<{ id: number; nome: string; slug: string }[]>("/integracoes/marketplace/erps?ativa=true"),
  });

  const primaryAction = getPrimaryAction(statusQuery.data);
  const actionError =
    iniciarMutation.error ??
    configurarCargaMutation.error ??
    reavaliarChecklistMutation.error ??
    actionMutation.error ??
    null;
  const status = statusQuery.data;
  const statusLoadStrategy = getLoadStrategy(status);
  const statusErpName = getErpName(status);
  const statusErpId = isObject(status?.diagnostico_inicial_snapshot) ? Number((status?.diagnostico_inicial_snapshot as any).marketplace_integracao_id) || null : null;
  const statusErpSlug = isObject(status?.diagnostico_inicial_snapshot) ? (status?.diagnostico_inicial_snapshot as any).marketplace_integracao_slug : null;
  
  const effectiveLoadStrategy = loadStrategy ?? statusLoadStrategy;
  const effectiveErpName = loadStrategy === "ERP" ? erpNameSelection : statusErpName;
  const effectiveErpId = loadStrategy === "ERP" ? erpIdSelection : statusErpId;
  const effectiveErpSlug = loadStrategy === "ERP" ? erpSlugSelection : statusErpSlug;
  const showCargaSetup = wizardNotStarted || !statusLoadStrategy || editingCarga;
  const canStartWizard =
    loadStrategy !== null &&
    (loadStrategy === "MANUAL" || loadStrategy === "LATER"
      ? true
      : !!erpIdSelection);
  const canSaveCarga =
    effectiveLoadStrategy !== null &&
    (effectiveLoadStrategy === "MANUAL" || effectiveLoadStrategy === "LATER"
      ? true
      : !!effectiveErpId);

  const buildCargaPayload = (strategy: LoadStrategy, erpId: number | null, erpSlug: string | null, erpName: string | null) => {
    const intent = {
      utiliza_erp: strategy === "ERP",
      configurar_erp_depois: strategy === "LATER",
      marketplace_integracao_id: strategy === "ERP" ? erpId : null,
      marketplace_integracao_slug: strategy === "ERP" ? erpSlug : null,
      erp_nome: strategy === "ERP" ? erpName : null,
    };

    return {
      modo_implantacao: getWizardMode(strategy),
      origem: "NOVO_ASSINANTE",
      escopo_modulos: intent,
      diagnostico_inicial_snapshot: intent,
    };
  };

  const handleStart = async () => {
    if (!loadStrategy) return;
    await iniciarMutation.mutateAsync(buildCargaPayload(loadStrategy, erpIdSelection, erpSlugSelection, erpNameSelection));
  };

  const handleSaveCarga = async () => {
    if (!effectiveLoadStrategy) return;
    await configurarCargaMutation.mutateAsync(
      buildCargaPayload(effectiveLoadStrategy, effectiveErpId, effectiveErpSlug, effectiveErpName),
    );
    setEditingCarga(false);
  };

  const handleReevaluateChecklist = async () => {
    await reavaliarChecklistMutation.mutateAsync();
  };

  const checklist = checklistQuery.data?.itens ?? [];
  const isInitialLoading = statusQuery.isLoading || checklistQuery.isLoading;

  if (isInitialLoading) {
    return <WizardSkeleton />;
  }


  // --- Lógica React Flow ---

  const getNodeStatus = (code: string): "COMPLETED" | "ACTIVE" | "BLOCKED" => {
    const item = checklist.find(i => i.codigo_item === code);
    if (!item) return "COMPLETED"; // Se não exige no tenant, passa.
    if (item.status === "ATENDIDO" || item.status === "DISPENSADO") return "COMPLETED";

    if (code !== "CHECK_UNIDADE_PRODUTIVA") {
      const upItem = checklist.find(i => i.codigo_item === "CHECK_UNIDADE_PRODUTIVA");
      if (upItem && (upItem.status === "PENDENTE" || upItem.status === "FALHOU")) {
        return "BLOCKED";
      }
    }

    if (code !== "CHECK_UNIDADE_PRODUTIVA" && code !== "CHECK_ESTRUTURA_TERRITORIAL") {
      const terrItem = checklist.find(i => i.codigo_item === "CHECK_ESTRUTURA_TERRITORIAL");
      if (terrItem && (terrItem.status === "PENDENTE" || terrItem.status === "FALHOU")) {
        return "BLOCKED";
      }
    }

    if (item.status === "PENDENTE" || item.status === "FALHOU") return "ACTIVE";
    return "BLOCKED";
  };

  const getNodeDescription = (code: string): string => {
    const item = checklist.find(i => i.codigo_item === code);
    return item?.descricao ?? "";
  };

  const getNodeLink = (code: string): string | null => {
    const item = checklist.find(i => i.codigo_item === code);
    if (!item?.acao_link) return null;
    return buildContextualLink(item.acao_link, status?.unidade_produtiva_id ?? null);
  };

  const hasModulos = (codes: string[]) => {
    return codes.some(code => checklist.some(i => i.codigo_item === code));
  };

  const createNode = (id: string, x: number, y: number, code: string | null = null, customData: any = null): Node => {
    let data = customData;
    if (code) {
      data = {
        title: WIZARD_INTERNAL_TITLES[code] ?? formatInternalCode(code),
        description: getNodeDescription(code),
        status: getNodeStatus(code),
        link: getNodeLink(code),
        actionLabel: "Iniciar Tarefa"
      };
    }
    return {
      id,
      position: { x, y },
      data,
      type: 'bpmnNode'
    };
  };

  const createEdge = (source: string, target: string, animated = false): Edge => ({
    id: `e-${source}-${target}`,
    source,
    target,
    type: 'smoothstep',
    animated,
    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
    style: { strokeWidth: 2, stroke: '#94a3b8' }
  });

  // Construir Nodes e Edges
  const initialNodes: Node[] = [];
  const initialEdges: Edge[] = [];

  if (status) {
    initialNodes.push(createNode("node-base", 0, 450, null, {
      title: "Tenant Base Ativo",
      description: `Implantação ID: ${status.implantacao_id.substring(0, 8)}...`,
      status: "COMPLETED"
    }));

    initialNodes.push(createNode("node-strategy", 400, 450, null, {
      title: "Estratégia de Carga",
      description:
        statusLoadStrategy === "ERP"
          ? `Carga via ${statusErpName || "ERP"} definida para importação inicial.`
          : statusLoadStrategy === "MANUAL"
            ? "Cadastros base seguirão por criação manual assistida no wizard."
            : "Defina se a implantação usará carga manual ou integração ERP.",
      status: statusLoadStrategy ? "COMPLETED" : "ACTIVE",
      actionLabel: statusLoadStrategy === "ERP" ? "Revisar integração" : "Revisar estratégia",
    }));
    initialEdges.push(createEdge("node-base", "node-strategy", true));

    const hasErpInterface = statusLoadStrategy === "ERP" || hasModulos(["CHECK_INTEGRACAO_ERP"]);
    const strategyExitNodeId = hasErpInterface ? "node-erp" : "node-strategy";

    if (hasErpInterface) {
      initialNodes.push(createNode("node-erp", 800, 450, null, {
        title: statusErpName ? `ERP: ${statusErpName}` : "Integração ERP",
        description:
          statusLoadStrategy === "ERP"
            ? "Configure a carga inicial e valide os cadastros importados antes do fluxo operacional."
            : "Integração prevista para este tenant. Revise credenciais e escopo de carga.",
        status: statusLoadStrategy === "ERP" ? "COMPLETED" : "ACTIVE",
        link: "/dashboard/settings/integracoes/erp",
        actionLabel: statusLoadStrategy === "ERP" ? "Validar integração" : "Configurar integração",
      }));
      initialEdges.push(createEdge("node-strategy", "node-erp", true));
    }

    initialNodes.push(createNode("node-up", 1200, 450, "CHECK_UNIDADE_PRODUTIVA"));
    initialEdges.push(createEdge(strategyExitNodeId, "node-up", true));

    initialNodes.push(createNode("node-terr", 1600, 450, "CHECK_ESTRUTURA_TERRITORIAL"));
    initialEdges.push(createEdge("node-up", "node-terr", true));

    const finalNodeId = "node-final";

    // Ramos
    let lastNodes = [];

    if (hasModulos(["CHECK_AGRICULTURA_TALHAO", "CHECK_CULTURA"])) {
      initialNodes.push(createNode("node-agr-1", 2000, 0, "CHECK_AGRICULTURA_TALHAO"));
      initialEdges.push(createEdge("node-terr", "node-agr-1", true));
      initialNodes.push(createNode("node-agr-2", 2400, 0, "CHECK_CULTURA"));
      initialEdges.push(createEdge("node-agr-1", "node-agr-2", true));
      lastNodes.push("node-agr-2");
    }

    if (hasModulos(["CHECK_PECUARIA_PIQUETE"])) {
      initialNodes.push(createNode("node-pec-1", 2000, 180, "CHECK_PECUARIA_PIQUETE"));
      initialEdges.push(createEdge("node-terr", "node-pec-1", true));
      lastNodes.push("node-pec-1");
    }

    if (hasModulos(["CHECK_ESTOQUE_DEPOSITO", "CHECK_PRODUTO_CATALOGO"])) {
      initialNodes.push(createNode("node-est-1", 2000, 360, "CHECK_ESTOQUE_DEPOSITO"));
      initialEdges.push(createEdge("node-terr", "node-est-1", true));
      initialNodes.push(createNode("node-est-2", 2400, 360, "CHECK_PRODUTO_CATALOGO"));
      initialEdges.push(createEdge("node-est-1", "node-est-2", true));
      lastNodes.push("node-est-2");
    }

    if (hasModulos(["CHECK_FINANCEIRO_PLANO_CONTA"])) {
      initialNodes.push(createNode("node-fin-1", 2000, 540, "CHECK_FINANCEIRO_PLANO_CONTA"));
      initialEdges.push(createEdge("node-terr", "node-fin-1", true));
      lastNodes.push("node-fin-1");
    }

    if (hasModulos(["CHECK_EQUIPAMENTO_CADASTRO"])) {
      initialNodes.push(createNode("node-fro-1", 2000, 720, "CHECK_EQUIPAMENTO_CADASTRO"));
      initialEdges.push(createEdge("node-terr", "node-fro-1", true));
      lastNodes.push("node-fro-1");
    }

    if (lastNodes.length === 0) {
      lastNodes.push("node-terr");
    }

    initialNodes.push(createNode(finalNodeId, 2800, 450, null, {
      title: status.elegivel_para_go_live ? "Pronto para Go-Live" : "Revisão Go-Live",
      description: status.elegivel_para_go_live
        ? "Todas as dependências mínimas validadas."
        : "Resolva as pendências anteriores para liberar.",
      status: status.elegivel_para_go_live ? "COMPLETED" : "BLOCKED",
      actionLabel: status.elegivel_para_go_live ? "Liberar Operação" : "Pendente"
    }));

    lastNodes.forEach(node => {
      initialEdges.push(createEdge(node, finalNodeId, true));
    });
  }



  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <PageHeader
          title="Wizard de Implantação"
          description="Fluxo de ativação operacional do Tenant."
          icon={<Sparkles className="size-5" />}
          breadcrumbs={[
            { label: "Dashboard", href: "/dashboard" },
            { label: "Implantação", href: "/dashboard/implantacao/wizard" },
            { label: "Wizard" },
          ]}
          actions={
            <div className="flex gap-2">
              {!hasActiveWizard ? (
                <Button
                  size="sm"
                  variant="default"
                  className="rounded-sm"
                  onClick={handleStart}
                  disabled={iniciarMutation.isPending || !canStartWizard}
                >
                  {iniciarMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <primaryAction.icon className="size-4" />}
                  {canStartWizard ? primaryAction.label : "Defina a estratégia de carga"}
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-sm"
                    onClick={() => {
                      setEditingCarga((current) => !current);
                      setLoadStrategy(statusLoadStrategy);
                      setErpNameSelection(statusErpName);
                      setErpIdSelection(statusErpId);
                      setErpSlugSelection(statusErpSlug);
                    }}
                  >
                    <Pencil className="size-4 text-slate-500" />
                    <span className="text-slate-600">
                      {editingCarga ? "Fechar edição" : "Editar estratégia"}
                    </span>
                  </Button>
                  <Button size="sm" variant="outline" className="rounded-sm" onClick={handleReevaluateChecklist} disabled={reavaliarChecklistMutation.isPending}>
                    {reavaliarChecklistMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4 text-slate-500" />}
                    <span className="text-slate-600">Reavaliar fluxo</span>
                  </Button>
                </div>
              )}
            </div>
          }
        />
      </div>

      {actionError && (
        <Alert variant="destructive" className="rounded-sm">
          <AlertTriangle className="size-4" />
          <AlertTitle>Operação bloqueada</AlertTitle>
          <AlertDescription>{actionError.message}</AlertDescription>
        </Alert>
      )}

      {showCargaSetup ? (
        <Card className="rounded-sm shadow-sm border-slate-200">
          <CardHeader className="space-y-2">
            <CardTitle>
              {!statusLoadStrategy ? "Defina a estratégia de carga inicial" : "Editar estratégia de carga"}
            </CardTitle>
            <CardDescription>
              Antes de abrir o go-live, o wizard precisa saber se os cadastros serão criados manualmente
              ou se a carga inicial virá por integração ERP.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <Button
                  type="button"
                  variant={effectiveLoadStrategy === "MANUAL" ? "default" : "outline"}
                  className="h-auto w-full justify-start rounded-xl p-4 text-left"
                  onClick={() => setLoadStrategy("MANUAL")}
                >
                  <div className="flex w-full items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">Carga manual</p>
                      <p className="text-xs opacity-80">
                        Não utilizarei integração no momento.
                      </p>
                    </div>
                    {effectiveLoadStrategy === "MANUAL" ? <CheckCircle2 className="size-5" /> : null}
                  </div>
                </Button>
                <Button
                  type="button"
                  variant={effectiveLoadStrategy === "ERP" ? "default" : "outline"}
                  className="h-auto w-full justify-start rounded-xl p-4 text-left"
                  onClick={() => setLoadStrategy("ERP")}
                >
                  <div className="flex w-full items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">Carga via ERP</p>
                      <p className="text-xs opacity-80">
                        Integração e validação de cadastros.
                      </p>
                    </div>
                    {effectiveLoadStrategy === "ERP" ? <CheckCircle2 className="size-5" /> : null}
                  </div>
                </Button>
                <Button
                  type="button"
                  variant={effectiveLoadStrategy === "LATER" ? "default" : "outline"}
                  className="h-auto w-full justify-start rounded-xl p-4 text-left"
                  onClick={() => setLoadStrategy("LATER")}
                >
                  <div className="flex w-full items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">Configurarei depois</p>
                      <p className="text-xs opacity-80">
                        Pular a seleção e deixar para depois.
                      </p>
                    </div>
                    {effectiveLoadStrategy === "LATER" ? <Clock className="size-5" /> : null}
                  </div>
                </Button>
              </div>

              {effectiveLoadStrategy === "ERP" ? (
                <div className="space-y-4 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
                  <div className="space-y-2">
                    <label htmlFor="wizard-erp-name" className="text-sm font-medium text-slate-900">
                      ERP utilizado
                    </label>
                    {isLoadingErps ? (
                      <div className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="size-4 animate-spin" /> Carregando lista de ERPs...</div>
                    ) : isErpsError || erps.length === 0 ? (
                      <div className="rounded-md bg-red-50 p-4 border border-red-200">
                        <p className="text-sm text-red-800 font-medium mb-3">
                          Não foi possível carregar a lista de ERPs.
                        </p>
                        <div className="flex gap-3">
                          <Button variant="outline" size="sm" onClick={() => refetchErps()}>
                            <RefreshCw className="size-4 mr-2" />
                            Tentar novamente
                          </Button>
                          <Button variant="secondary" size="sm" onClick={() => setLoadStrategy("LATER")}>
                            Configurar depois
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Select
                        value={effectiveErpId ? String(effectiveErpId) : undefined}
                        onValueChange={(value) => {
                          const selected = erps.find((e) => String(e.id) === value);
                          if (selected) {
                            setErpIdSelection(selected.id);
                            setErpSlugSelection(selected.slug);
                            setErpNameSelection(selected.nome);
                          }
                        }}
                      >
                        <SelectTrigger className="w-full bg-white">
                          <SelectValue placeholder="Selecione um ERP" />
                        </SelectTrigger>
                        <SelectContent>
                          {erps.map((erp) => (
                            <SelectItem key={String(erp.id)} value={String(erp.id)}>
                              {erp.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Resumo da decisão</p>
              <div className="mt-4 space-y-3">
                <Badge variant="outline" className="border-slate-300 bg-white text-slate-700">
                  {getStrategyLabel(effectiveLoadStrategy)}
                </Badge>
                <p className="text-sm text-slate-600">
                  {effectiveLoadStrategy === "ERP"
                    ? "O wizard abrirá primeiro a trilha de integração e validação de dados importados."
                    : effectiveLoadStrategy === "MANUAL"
                      ? "O wizard seguirá direto para os cadastros estruturais e operacionais."
                      : "Escolha uma estratégia para liberar o início da implantação."}
                </p>
                {effectiveLoadStrategy === "ERP" && effectiveErpName ? (
                  <p className="text-sm text-slate-700">
                    ERP selecionado: <strong>{effectiveErpName}</strong>
                  </p>
                ) : null}
                {!hasActiveWizard || wizardNotStarted ? (
                  <Button
                    className="w-full rounded-sm"
                    onClick={handleStart}
                    disabled={iniciarMutation.isPending || !canStartWizard}
                  >
                    {iniciarMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <PlayCircle className="size-4" />}
                    {iniciarMutation.isPending ? "Iniciando..." : "Iniciar implantação"}
                  </Button>
                ) : (
                  <Button
                    className="w-full rounded-sm"
                    onClick={handleSaveCarga}
                    disabled={configurarCargaMutation.isPending || !canSaveCarga}
                  >
                    {configurarCargaMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <CheckCircle2 className="size-4" />}
                    {configurarCargaMutation.isPending ? "Salvando..." : "Salvar estratégia"}
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : status ? (
        <div className="space-y-5">
          <Card className="rounded-sm shadow-sm border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle>Estratégia de carga da implantação</CardTitle>
              <CardDescription>
                O wizard usa essa decisão para definir se os cadastros serão conduzidos manualmente ou validados por integração.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="border-slate-300 bg-white text-slate-700">
                    {getStrategyLabel(statusLoadStrategy)}
                  </Badge>
                  {statusErpName ? (
                    <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">
                      ERP: {statusErpName}
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm text-slate-600">
                  {statusLoadStrategy === "ERP"
                    ? "Os cadastros do ERP serão tratados primeiro pela trilha de integração."
                    : statusLoadStrategy === "MANUAL"
                      ? "Os cadastros estruturais e operacionais seguem pela trilha manual assistida."
                      : "Esta implantação não registrou a estratégia de carga. Revise o diagnóstico antes do go-live."}
                </p>
              </div>
              {statusLoadStrategy === "ERP" ? (
                <Button asChild variant="outline">
                  <Link href="/dashboard/settings/integracoes/erp">Abrir console ERP</Link>
                </Button>
              ) : null}
            </CardContent>
          </Card>

          <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-50/50 p-8 shadow-inner">
            <div className="-mx-8 -mb-8">
              <WizardFlow initialNodes={initialNodes} initialEdges={initialEdges} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
