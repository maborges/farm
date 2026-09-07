"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    DndContext,
    DragOverlay,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragStartEvent,
    DragOverEvent,
    DragEndEvent,
    rectIntersection,
    UniqueIdentifier,
} from "@dnd-kit/core";
import {
    arrayMove,
    sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import {
    Target, Plus, RefreshCw, LayoutGrid, List, ShoppingCart, Loader2, UserPlus, Layers, XCircle
} from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Dialog, DialogContent, DialogFooter,
    DialogHeader, DialogTitle, DialogBody, DialogDescription
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { ConvertLeadWizard } from "@/components/backoffice/convert-lead-wizard";
import { apiFetch } from "@/lib/api";

import {
    CRMStats, Estagio, KanbanData, PlanoComercial, ModuloOferta, Lead, LeadListData, ORIGENS
} from "./types";
import { CrmStatsCards } from "./CrmStatsCards";
import { CrmKanbanBoard, SortableLeadCard } from "./CrmKanbanBoard";
import { CrmLeadsList } from "./CrmLeadsList";
import { CrmLeadDetailSheet } from "./CrmLeadDetailSheet";

// ==================== FORMATTERS ====================

function maskBRL(value: string): string {
    const digits = value.replace(/\D/g, "");
    if (!digits) return "";
    const num = parseInt(digits, 10);
    return (num / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatTelefone(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

function formatCPFCNPJ(value: string): string {
    const digits = value.replace(/\D/g, "");

    // CPF: XXX.XXX.XXX-XX (11 dígitos)
    if (digits.length <= 11) {
        if (digits.length <= 3) return digits;
        if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
        if (digits.length <= 9) return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
        return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
    }

    // CNPJ: XX.XXX.XXX/XXXX-XX (14 dígitos)
    const cnpj = digits.slice(0, 14);
    if (cnpj.length <= 2) return cnpj;
    if (cnpj.length <= 5) return `${cnpj.slice(0, 2)}.${cnpj.slice(2)}`;
    if (cnpj.length <= 8) return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5)}`;
    if (cnpj.length <= 12) return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8)}`;
    return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
}

interface CrmClientProps {
  initialStats: CRMStats | null;
  initialPipeline: Estagio[] | null;
  initialKanban: KanbanData | null;
  initialPlans: PlanoComercial[] | null;
}

export function CrmClient({
  initialStats,
  initialPipeline,
  initialKanban,
  initialPlans,
}: CrmClientProps) {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState("kanban");
    const [showNewLead, setShowNewLead] = useState(false);
    const [showNewEstagio, setShowNewEstagio] = useState(false);
    const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
    const [statusFilter, setStatusFilter] = useState("ativo");
    const [loseTarget, setLoseTarget] = useState<Lead | null>(null);
    const [motivoPerda, setMotivoPerda] = useState("");
    const [convertWizardLead, setConvertWizardLead] = useState<Lead | null>(null);

    // ---- New Lead form ----
    const [newLead, setNewLead] = useState({
        nome: "", email: "", telefone: "", empresa: "", documento: "",
        estagio_id: "", origem: "manual", valor_estimado: "",
        plano_interesse: "", qtd_fazendas: "", qtd_usuarios: "", notas: "",
    });

    // ---- New Estagio form ----
    const [newEstagio, setNewEstagio] = useState({ nome: "", cor: "#3b82f6", ordem: "0" });

    // ---- New Oferta form ----
    const [showNewOferta, setShowNewOferta] = useState(false);
    const [newOferta, setNewOferta] = useState({
        tipo_oferta: "plano_padrao",
        plano_base_id: "",
        modulos_selecionados: [] as string[],
        preco_total_mensal: "",
        preco_total_anual: "",
        desconto_percentual: "0",
        justificativa: "",
        vigencia_dias: "30",
    });

    // ==================== QUERIES ====================

    const { data: stats } = useQuery<CRMStats>({
        queryKey: ["crm", "stats"],
        queryFn: () => apiFetch("/backoffice/crm/stats"),
        initialData: initialStats ?? undefined,
    });

    const { data: kanban, isLoading: kanbanLoading } = useQuery<KanbanData>({
        queryKey: ["crm", "kanban"],
        queryFn: () => apiFetch("/backoffice/crm/kanban"),
        enabled: activeTab === "kanban",
        initialData: initialKanban ?? undefined,
    });

    const startContainerRef = useRef<string | null>(null);

    // ==================== MUTATIONS ====================

    const invalidateCRM = useCallback(() => {
        queryClient.invalidateQueries({ queryKey: ["crm"] });
    }, [queryClient]);

    const moveLeadMutation = useMutation({
        mutationFn: ({ leadId, estagioId }: { leadId: string; estagioId: string }) =>
            apiFetch(`/backoffice/crm/leads/${leadId}/move`, {
                method: "PATCH",
                body: JSON.stringify({ estagio_id: estagioId }),
            }),
        onMutate: async ({ leadId, estagioId }) => {
            await queryClient.cancelQueries({ queryKey: ["crm", "kanban"] });
            const previousKanban = queryClient.getQueryData<KanbanData>(["crm", "kanban"]);

            if (previousKanban) {
                const newLeadsPorEstagio = { ...previousKanban.leads_por_estagio };
                let movedLead: Lead | undefined;

                for (const [estId, leads] of Object.entries(newLeadsPorEstagio)) {
                    const idx = leads.findIndex((l) => l.id === leadId);
                    if (idx !== -1) {
                        movedLead = { ...leads[idx] };
                        newLeadsPorEstagio[estId] = leads.filter((l) => l.id !== leadId);
                        break;
                    }
                }

                if (movedLead) {
                    movedLead.estagio_id = estagioId;
                    const targetEstagio = previousKanban.estagios.find((e) => e.id === estagioId);
                    if (targetEstagio) {
                        movedLead.estagio = targetEstagio;
                    }
                    newLeadsPorEstagio[estagioId] = [
                        ...(newLeadsPorEstagio[estagioId] || []),
                        movedLead,
                    ];

                    queryClient.setQueryData<KanbanData>(["crm", "kanban"], {
                        ...previousKanban,
                        leads_por_estagio: newLeadsPorEstagio,
                    });
                }
            }

            return { previousKanban };
        },
        onSuccess: () => {
            toast.success("Lead movido!");
        },
        onError: (err: any, variables, context) => {
            if (context?.previousKanban) {
                queryClient.setQueryData(["crm", "kanban"], context.previousKanban);
            }
            toast.error(err.message || "Erro ao mover lead");
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ["crm", "kanban"] });
            queryClient.invalidateQueries({ queryKey: ["crm", "stats"] });
        },
    });

    const createLeadMutation = useMutation({
        mutationFn: (data: Record<string, unknown>) =>
            apiFetch("/backoffice/crm/leads", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            invalidateCRM();
            setShowNewLead(false);
            setNewLead({
                nome: "", email: "", telefone: "", empresa: "", documento: "",
                estagio_id: "", origem: "manual", valor_estimado: "",
                plano_interesse: "", qtd_fazendas: "", qtd_usuarios: "", notas: "",
            });
            toast.success("Lead criado!");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar lead"),
    });

    const convertLeadMutation = {
        mutate: (leadId: string) => {
            const lead = (leadsList?.items ?? []).find((l: Lead) => l.id === leadId) ?? selectedLead;
            if (!lead) return;
            setConvertWizardLead(lead);
        },
        isPending: false,
    };

    const loseLeadMutation = useMutation({
        mutationFn: ({ leadId, motivo }: { leadId: string; motivo: string }) =>
            apiFetch(`/backoffice/crm/leads/${leadId}/lose`, {
                method: "PATCH",
                body: JSON.stringify({ motivo_perda: motivo }),
            }),
        onMutate: async ({ leadId, motivo }) => {
            await queryClient.cancelQueries({ queryKey: ["crm", "kanban"] });
            await queryClient.cancelQueries({ queryKey: ["crm", "stats"] });
            await queryClient.cancelQueries({ queryKey: ["crm", "leads"] });

            const previousKanban = queryClient.getQueryData<KanbanData>(["crm", "kanban"]);
            const previousStats = queryClient.getQueryData<CRMStats>(["crm", "stats"]);
            const previousLeadsList = queryClient.getQueryData<LeadListData>(["crm", "leads", statusFilter]);

            let lostLead: Lead | undefined;

            if (previousKanban) {
                const newLeadsPorEstagio = { ...previousKanban.leads_por_estagio };
                for (const [estId, leads] of Object.entries(newLeadsPorEstagio)) {
                    const idx = leads.findIndex((l) => l.id === leadId);
                    if (idx !== -1) {
                        lostLead = leads[idx];
                        newLeadsPorEstagio[estId] = leads.filter((l) => l.id !== leadId);
                        break;
                    }
                }
                queryClient.setQueryData<KanbanData>(["crm", "kanban"], {
                    ...previousKanban,
                    leads_por_estagio: newLeadsPorEstagio,
                });
            }

            if (previousStats) {
                const updatedStats = { ...previousStats };
                updatedStats.leads_ativos = Math.max(0, updatedStats.leads_ativos - 1);
                updatedStats.leads_perdidos = updatedStats.leads_perdidos + 1;
                
                const leadValue = lostLead?.valor_estimado || 0;
                if (leadValue > 0) {
                    updatedStats.valor_pipeline = Math.max(0, updatedStats.valor_pipeline - leadValue);
                }
                queryClient.setQueryData<CRMStats>(["crm", "stats"], updatedStats);
            }

            if (previousLeadsList) {
                const updatedList = { ...previousLeadsList };
                if (statusFilter === "ativo") {
                    updatedList.items = updatedList.items.filter((l) => l.id !== leadId);
                    updatedList.total = Math.max(0, updatedList.total - 1);
                } else if (statusFilter === "perdido" && lostLead) {
                    const updatedLead = { ...lostLead, status: "perdido", motivo_perda: motivo };
                    updatedList.items = [updatedLead, ...updatedList.items];
                    updatedList.total = updatedList.total + 1;
                }
                queryClient.setQueryData<LeadListData>(["crm", "leads", statusFilter], updatedList);
            }

            return { previousKanban, previousStats, previousLeadsList };
        },
        onSuccess: () => {
            setLoseTarget(null);
            setMotivoPerda("");
            setSelectedLead(null);
            toast.success("Lead marcado como perdido");
        },
        onError: (err: any, variables, context) => {
            if (context?.previousKanban) {
                queryClient.setQueryData(["crm", "kanban"], context.previousKanban);
            }
            if (context?.previousStats) {
                queryClient.setQueryData(["crm", "stats"], context.previousStats);
            }
            if (context?.previousLeadsList) {
                queryClient.setQueryData(["crm", "leads", statusFilter], context.previousLeadsList);
            }
            toast.error(err.message || "Erro ao marcar lead como perdido");
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ["crm"] });
        },
    });

    const reopenLeadMutation = useMutation({
        mutationFn: (leadId: string) =>
            apiFetch(`/backoffice/crm/leads/${leadId}/reopen`, { method: "PATCH" }),
        onSuccess: () => {
            invalidateCRM();
            setSelectedLead(null);
            toast.success("Lead reaberto!");
        },
        onError: (err: any) => toast.error(err.message || "Erro"),
    });

    const createEstagioMutation = useMutation({
        mutationFn: (data: Record<string, unknown>) =>
            apiFetch("/backoffice/crm/pipeline", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            invalidateCRM();
            setShowNewEstagio(false);
            setNewEstagio({ nome: "", cor: "#3b82f6", ordem: "0" });
            toast.success("Estágio criado!");
        },
        onError: (err: any) => toast.error(err.message || "Erro"),
    });

    const createOfertaMutation = useMutation({
        mutationFn: (data: Record<string, unknown>) =>
            apiFetch(`/backoffice/crm/ofertas/leads/${selectedLead!.id}/oferta`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            invalidateCRM();
            setShowNewOferta(false);
            setNewOferta({
                tipo_oferta: "plano_padrao",
                plano_base_id: "",
                modulos_selecionados: [],
                preco_total_mensal: "",
                preco_total_anual: "",
                desconto_percentual: "0",
                justificativa: "",
                vigencia_dias: "30",
            });
            toast.success("Oferta criada com sucesso!");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar oferta"),
    });

    // ---- DND State ----
    const [kanbanLeads, setKanbanLeads] = useState<Record<string, Lead[]>>({});
    const [activeLead, setActiveLead] = useState<Lead | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // Sync local state when query finishes OR when we are NOT dragging
    useEffect(() => {
        if (kanban?.leads_por_estagio && !activeLead) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setKanbanLeads(kanban.leads_por_estagio);
        }
    }, [kanban?.leads_por_estagio, activeLead]);

    const findContainer = useCallback((id: UniqueIdentifier) => {
        const idAsString = String(id);
        if (idAsString in kanbanLeads) return idAsString;

        return Object.keys(kanbanLeads).find((key) =>
            kanbanLeads[key].some((item) => String(item.id) === idAsString)
        );
    }, [kanbanLeads]);

    const handleDragStart = useCallback((event: DragStartEvent) => {
        const { active } = event;
        const lead = active.data.current?.lead as Lead;
        if (lead) {
            setActiveLead(lead);
            // Capture the starting container
            const startContainer = findContainer(active.id);
            if (startContainer) startContainerRef.current = startContainer;
        }
    }, [findContainer]);

    const handleDragOver = useCallback((event: DragOverEvent) => {
        const { active, over } = event;
        const overId = over?.id;

        if (!overId || active.id === overId) return;

        const activeId = active.id;
        const activeContainer = findContainer(activeId);
        const overContainer = findContainer(overId);

        if (!activeContainer || !overContainer || activeContainer === overContainer) {
            return;
        }

        setKanbanLeads((prev) => {
            const activeItems = prev[activeContainer] || [];
            const overItems = prev[overContainer] || [];

            const activeIndex = activeItems.findIndex((item) => item.id === activeId);
            const overIndex = overItems.findIndex((item) => item.id === overId);

            let newIndex: number;
            if (String(overId) in prev) {
                newIndex = overItems.length;
            } else {
                const isAtEnd = overIndex === overItems.length - 1;
                newIndex = overIndex >= 0 ? overIndex + (isAtEnd ? 1 : 0) : overItems.length;
            }

            const itemToMove = activeItems[activeIndex];
            if (!itemToMove) return prev;

            return {
                ...prev,
                [activeContainer]: activeItems.filter((item) => item.id !== activeId),
                [overContainer]: [
                    ...overItems.slice(0, newIndex),
                    { ...itemToMove, estagio_id: overContainer },
                    ...overItems.slice(newIndex),
                ],
            };
        });
    }, [findContainer]);

    const handleDragEnd = useCallback((event: DragEndEvent) => {
        const { active, over } = event;
        const overId = over?.id;

        if (!overId) {
            setActiveLead(null);
            startContainerRef.current = null;
            if (kanban?.leads_por_estagio) setKanbanLeads(kanban.leads_por_estagio);
            return;
        }

        const activeId = String(active.id);
        const startContainer = startContainerRef.current;
        const overContainer = findContainer(overId);

        if (!startContainer || !overContainer) {
            setActiveLead(null);
            startContainerRef.current = null;
            return;
        }

        // Check if moved to a different column
        if (startContainer !== overContainer) {
            moveLeadMutation.mutate({ leadId: activeId, estagioId: overContainer });
        } else if (active.id !== overId) {
            // Reorder within the same column
            const oldIndex = kanbanLeads[startContainer]?.findIndex((item) => item.id === activeId);
            const newIndex = kanbanLeads[overContainer]?.findIndex((item) => item.id === String(overId));

            if (oldIndex !== undefined && newIndex !== undefined && oldIndex !== newIndex && oldIndex !== -1 && newIndex !== -1) {
                setKanbanLeads((items) => ({
                    ...items,
                    [overContainer]: arrayMove(items[overContainer], oldIndex, newIndex),
                }));
            }
        }

        setActiveLead(null);
        startContainerRef.current = null;
    }, [findContainer, kanbanLeads, kanban, moveLeadMutation]);

    const { data: pipeline } = useQuery<Estagio[]>({
        queryKey: ["crm", "pipeline"],
        queryFn: () => apiFetch("/backoffice/crm/pipeline?ativo=true"),
        initialData: initialPipeline ?? undefined,
    });

    const { data: planos } = useQuery<PlanoComercial[]>({
        queryKey: ["crm", "ofertas", "planos"],
        queryFn: () => apiFetch("/backoffice/crm/ofertas/planos?ativo_apenas=true"),
        enabled: showNewLead || showNewOferta,
        initialData: initialPlans ?? undefined,
    });

    const { data: modulos } = useQuery<ModuloOferta[]>({
        queryKey: ["crm", "ofertas", "produtos"],
        queryFn: () => apiFetch("/backoffice/crm/ofertas/produtos"),
        enabled: showNewOferta,
    });

    const { data: leadsList, isLoading: leadsLoading } = useQuery<LeadListData>({
        queryKey: ["crm", "leads", statusFilter],
        queryFn: () => {
            const params = new URLSearchParams();
            if (statusFilter) params.set("status", statusFilter);
            return apiFetch(`/backoffice/crm/leads?${params.toString()}`);
        },
        enabled: activeTab === "lista",
    });

    // ==================== HANDLERS ====================

    function handleCreateLead() {
        if (!newLead.nome || !newLead.estagio_id) {
            toast.error("Nome e estágio são obrigatórios");
            return;
        }

        const payload: Record<string, unknown> = {
            nome: newLead.nome,
            estagio_id: newLead.estagio_id,
            origem: newLead.origem,
        };

        if (newLead.email) payload.email = newLead.email;
        if (newLead.telefone) payload.telefone = newLead.telefone;
        if (newLead.empresa) payload.empresa = newLead.empresa;
        if (newLead.documento) payload.documento = newLead.documento;

        if (newLead.valor_estimado) {
            const numVal = parseFloat(newLead.valor_estimado.replace(/\./g, "").replace(",", "."));
            if (!isNaN(numVal)) payload.valor_estimado = numVal;
        }

        if (newLead.plano_interesse) payload.plano_interesse = newLead.plano_interesse;
        if (newLead.qtd_fazendas) payload.qtd_fazendas = parseInt(newLead.qtd_fazendas, 10);
        if (newLead.qtd_usuarios) payload.qtd_usuarios = parseInt(newLead.qtd_usuarios, 10);
        if (newLead.notas) payload.notas = newLead.notas;

        createLeadMutation.mutate(payload);
    }

    function handleCreateEstagio() {
        if (!newEstagio.nome) { toast.error("Nome é obrigatório"); return; }
        createEstagioMutation.mutate({
            nome: newEstagio.nome,
            cor: newEstagio.cor,
            ordem: parseInt(newEstagio.ordem) || 0,
        });
    }

    function handleCreateOferta() {
        if (!newOferta.preco_total_mensal || !newOferta.preco_total_anual) {
            toast.error("Preços (mensal e anual) são obrigatórios");
            return;
        }
        const payload: Record<string, unknown> = {
            tipo_oferta: newOferta.tipo_oferta,
            preco_total_mensal: parseFloat(newOferta.preco_total_mensal),
            preco_total_anual: parseFloat(newOferta.preco_total_anual),
            desconto_percentual: parseFloat(newOferta.desconto_percentual) || 0,
            vigencia_dias: parseInt(newOferta.vigencia_dias) || 30,
        };
        if (newOferta.tipo_oferta === "plano_padrao" && newOferta.plano_base_id) {
            payload.plano_base_id = newOferta.plano_base_id;
        }
        if (newOferta.tipo_oferta === "custom_modular" && newOferta.modulos_selecionados.length > 0) {
            payload.modulos_selecionados = newOferta.modulos_selecionados;
        }
        if (newOferta.justificativa) {
            payload.justificativa = newOferta.justificativa;
        }
        createOfertaMutation.mutate(payload);
    }

    const formatCurrency = (val: number) =>
        new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val);

    // ==================== LOADING ====================

    if (kanbanLoading && activeTab === "kanban") {
        return (
            <div className="p-6 space-y-6 w-full max-w-full">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
                <div className="flex gap-4">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-96 w-72" />)}
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6 w-full max-w-full">
            <PageHeader
                title="CRM"
                description="Gerencie leads e oportunidades comerciais."
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice" },
                    { label: "CRM" },
                ]}
                icon={<Target className="h-8 w-8 text-primary" />}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowNewEstagio(true)} className="rounded-sm">
                            <Plus size={16} className="mr-2" /> Estágio
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowNewLead(true)}
                            className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                        >
                            <Plus size={16} className="mr-2" /> Novo Lead
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <CrmStatsCards stats={stats} formatCurrency={formatCurrency} />

            {/* Tabs: Kanban | Lista */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <DndContext
                    sensors={sensors}
                    collisionDetection={rectIntersection}
                    onDragStart={handleDragStart}
                    onDragOver={handleDragOver}
                    onDragEnd={handleDragEnd}
                >
                    <div className="flex items-center justify-between border-b bg-muted/5">
                        <TabsList className="w-full justify-start h-10 gap-1 bg-transparent p-0 rounded-none">
                            <TabsTrigger
                                value="kanban"
                                className="rounded-t-sm border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2"
                            >
                                <LayoutGrid className="size-3.5" /> Kanban
                            </TabsTrigger>
                            <TabsTrigger
                                value="lista"
                                className="rounded-t-sm border-b-2 border-transparent data-[selected]:border-primary data-[selected]:bg-accent transition-all hover:bg-accent gap-1.5 px-3 py-2"
                            >
                                <List className="size-3.5" /> Lista
                            </TabsTrigger>
                            <div className="flex-1" />
                            <Button variant="ghost" size="sm" onClick={invalidateCRM} className="mb-1">
                                <RefreshCw className="size-3.5 mr-1" /> Atualizar
                            </Button>
                        </TabsList>
                    </div>

                    {/* ---- KANBAN VIEW ---- */}
                    <TabsContent value="kanban" className="mt-4">
                        <CrmKanbanBoard
                            kanban={kanban}
                            kanbanLeads={kanbanLeads}
                            onLeadClick={setSelectedLead}
                            onMove={(leadId, estagioId) => moveLeadMutation.mutate({ leadId, estagioId })}
                            onConvert={(id) => convertLeadMutation.mutate(id)}
                            onLose={(l) => setLoseTarget(l)}
                            setShowNewEstagio={setShowNewEstagio}
                        />

                        <DragOverlay adjustScale={false}>
                            {activeLead ? (
                                <div className="w-[280px]">
                                    <SortableLeadCard
                                        lead={activeLead}
                                        onClick={() => { }}
                                        onMove={() => { }}
                                        onConvert={() => { }}
                                        onLose={() => { }}
                                        estagios={kanban?.estagios ?? []}
                                    />
                                </div>
                            ) : null}
                        </DragOverlay>
                    </TabsContent>
                </DndContext>

                {/* ---- LIST VIEW ---- */}
                <TabsContent value="lista" className="mt-4">
                    <CrmLeadsList
                        statusFilter={statusFilter}
                        setStatusFilter={setStatusFilter}
                        leadsList={leadsList}
                        leadsLoading={leadsLoading}
                        onLeadClick={setSelectedLead}
                        formatCurrency={formatCurrency}
                    />
                </TabsContent>
            </Tabs>

            {/* ==================== DIALOGS ==================== */}

            {/* New Lead Dialog */}
            <Dialog open={showNewLead} onOpenChange={setShowNewLead}>
                <DialogContent className="max-w-xl p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
                    <DialogHeader className="px-6 pt-6 pb-2">
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <UserPlus className="size-4 text-primary" />
                            </div>
                            <DialogTitle>Novo Lead</DialogTitle>
                        </div>
                    </DialogHeader>
                    <DialogBody className="px-6 py-6 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-2 space-y-2">
                                <Label className="text-sm font-medium" htmlFor="nome">Nome <span className="text-red-500">*</span></Label>
                                <Input className="h-8 rounded-sm" id="nome" value={newLead.nome} onChange={(e) => setNewLead({ ...newLead, nome: e.target.value })} placeholder="Nome do lead" />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="email">Email</Label>
                                <Input className="h-8 rounded-sm" id="email" value={newLead.email} onChange={(e) => setNewLead({ ...newLead, email: e.target.value })} placeholder="email@empresa.com" />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="telefone">Telefone</Label>
                                <Input
                                    className="h-8 rounded-sm"
                                    id="telefone"
                                    value={newLead.telefone}
                                    onChange={(e) => setNewLead({ ...newLead, telefone: formatTelefone(e.target.value) })}
                                    placeholder="(11) 99999-0000"
                                    maxLength={14}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="empresa">Empresa</Label>
                                <Input className="h-8 rounded-sm" id="empresa" value={newLead.empresa} onChange={(e) => setNewLead({ ...newLead, empresa: e.target.value })} placeholder="Fazenda XYZ" />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="documento">CPF/CNPJ</Label>
                                <Input
                                    className="h-8 rounded-sm"
                                    id="documento"
                                    value={newLead.documento}
                                    onChange={(e) => setNewLead({ ...newLead, documento: formatCPFCNPJ(e.target.value) })}
                                    placeholder="000.000.000-00 ou 00.000.000/0000-00"
                                    maxLength={18}
                                />
                            </div>
                        </div>

                        <Separator />

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="estagio">Estágio <span className="text-red-500">*</span></Label>
                                <Select value={newLead.estagio_id} onValueChange={(v: string) => setNewLead({ ...newLead, estagio_id: v })} disabled={!pipeline || pipeline.length === 0}>
                                    <SelectTrigger className="h-8 rounded-sm" id="estagio">
                                        <SelectValue placeholder={newLead.estagio_id ? (pipeline?.find(e => e.id === newLead.estagio_id)?.nome ?? newLead.estagio_id) : (!pipeline ? "Carregando..." : pipeline.length === 0 ? "Nenhum estágio disponível" : "Selecione um estágio...")} />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {pipeline && pipeline.length > 0 ? (
                                            pipeline.map((e) => (
                                                <SelectItem key={e.id} value={e.id}>{e.nome}</SelectItem>
                                            ))
                                        ) : (
                                            <div className="p-2 text-xs text-muted-foreground text-center">
                                                {!pipeline ? "Carregando estagios..." : "Nenhum estágio disponível"}
                                            </div>
                                        )}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="origem">Origem</Label>
                                <Select value={newLead.origem} onValueChange={(v: string) => setNewLead({ ...newLead, origem: v })}>
                                    <SelectTrigger className="h-8 rounded-sm" id="origem"><SelectValue /></SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {Object.entries(ORIGENS).map(([k, v]) => (
                                            <SelectItem key={k} value={k}>{v.label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="valor_estimado">Valor Estimado</Label>
                                <div className="relative">
                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">R$</span>
                                    <Input
                                        id="valor_estimado"
                                        type="text"
                                        inputMode="decimal"
                                        value={newLead.valor_estimado}
                                        onChange={(e) => setNewLead({ ...newLead, valor_estimado: maskBRL(e.target.value) })}
                                        placeholder="0,00"
                                        className="h-8 rounded-sm pl-9"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="plano">Plano de Interesse</Label>
                                <Select value={newLead.plano_interesse} onValueChange={(v: string) => setNewLead({ ...newLead, plano_interesse: v })}>
                                    <SelectTrigger className="h-8 rounded-sm" id="plano">
                                        <SelectValue placeholder="Selecione um plano..." />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        <SelectItem value="none_value">Nenhum</SelectItem>
                                        {planos?.map((p) => (
                                            <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="fazendas">Qtd. Fazendas</Label>
                                <Input className="h-8 rounded-sm" id="fazendas" type="number" value={newLead.qtd_fazendas} onChange={(e) => setNewLead({ ...newLead, qtd_fazendas: e.target.value })} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="usuarios">Qtd. Usuários</Label>
                                <Input className="h-8 rounded-sm" id="usuarios" type="number" value={newLead.qtd_usuarios} onChange={(e) => setNewLead({ ...newLead, qtd_usuarios: e.target.value })} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-sm font-medium" htmlFor="notas">Notas</Label>
                            <Textarea className="rounded-sm" id="notas" value={newLead.notas} onChange={(e) => setNewLead({ ...newLead, notas: e.target.value })} placeholder="Observações sobre o lead..." rows={3} />
                        </div>
                    </DialogBody>
                    <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setShowNewLead(false)}>Cancelar</Button>
                        <Button variant="outline" size="sm" className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm" onClick={handleCreateLead} disabled={createLeadMutation.isPending}>
                            {createLeadMutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                            {createLeadMutation.isPending ? "Criando..." : "Criar Lead"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={showNewEstagio} onOpenChange={setShowNewEstagio}>
                <DialogContent className="max-w-sm p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
                    <DialogHeader className="px-6 pt-6 pb-2">
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <Layers className="size-4 text-primary" />
                            </div>
                            <DialogTitle>Novo Estágio</DialogTitle>
                        </div>
                    </DialogHeader>
                    <DialogBody className="px-6 py-6 space-y-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-medium" htmlFor="nome-estagio">Nome <span className="text-red-500">*</span></Label>
                            <Input className="h-8 rounded-sm" id="nome-estagio" value={newEstagio.nome} onChange={(e) => setNewEstagio({ ...newEstagio, nome: e.target.value })} placeholder="Ex: Qualificação" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="cor">Cor</Label>
                                <div className="flex gap-2 items-center">
                                    <input
                                        id="cor"
                                        type="color"
                                        value={newEstagio.cor}
                                        onChange={(e) => setNewEstagio({ ...newEstagio, cor: e.target.value })}
                                        className="w-10 h-8 rounded border cursor-pointer"
                                    />
                                    <Input className="h-8 rounded-sm flex-1" value={newEstagio.cor} onChange={(e) => setNewEstagio({ ...newEstagio, cor: e.target.value })} />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium" htmlFor="ordem">Ordem</Label>
                                <Input className="h-8 rounded-sm" id="ordem" type="number" value={newEstagio.ordem} onChange={(e) => setNewEstagio({ ...newEstagio, ordem: e.target.value })} />
                            </div>
                        </div>
                    </DialogBody>
                    <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setShowNewEstagio(false)}>Cancelar</Button>
                        <Button variant="outline" size="sm" className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm" onClick={handleCreateEstagio} disabled={createEstagioMutation.isPending}>
                            {createEstagioMutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                            {createEstagioMutation.isPending ? "Criando..." : "Criar Estágio"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Lose Lead Dialog */}
            <Dialog open={!!loseTarget} onOpenChange={() => setLoseTarget(null)}>
                <DialogContent className="max-w-sm p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
                    <DialogHeader className="px-6 pt-6 pb-2">
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-red-500/10 flex items-center justify-center">
                                <XCircle className="size-4 text-red-600" />
                            </div>
                            <DialogTitle>Marcar como Perdido</DialogTitle>
                        </div>
                    </DialogHeader>
                    <DialogBody className="px-6 py-6 space-y-4">
                        <p className="text-sm text-muted-foreground mb-4">
                            Por que o lead <strong className="text-foreground">{loseTarget?.nome}</strong> foi perdido?
                        </p>
                        <Textarea
                            className="rounded-sm"
                            value={motivoPerda}
                            onChange={(e) => setMotivoPerda(e.target.value)}
                            placeholder="Motivo da perda..."
                            rows={3}
                        />
                    </DialogBody>
                    <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setLoseTarget(null)}>Cancelar</Button>
                        <Button
                            variant="destructive"
                            size="sm"
                            className="rounded-sm shadow-sm"
                            onClick={() => loseTarget && loseLeadMutation.mutate({ leadId: loseTarget.id, motivo: motivoPerda })}
                            disabled={!motivoPerda || loseLeadMutation.isPending}
                        >
                            {loseLeadMutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <XCircle size={14} className="mr-2" />}
                            Confirmar Perda
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* New Oferta Dialog */}
            <Dialog open={showNewOferta} onOpenChange={setShowNewOferta}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Criar Oferta Personalizada</DialogTitle>
                        <DialogDescription>
                            Para: <strong>{selectedLead?.nome}</strong>
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        {/* Tipo de Oferta */}
                        <div className="grid gap-2">
                            <Label htmlFor="tipo-oferta">Tipo de Oferta *</Label>
                            <Select value={newOferta.tipo_oferta} onValueChange={(v: string) => setNewOferta({ ...newOferta, tipo_oferta: v })}>
                                <SelectTrigger id="tipo-oferta">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="plano_padrao">Plano Padrão</SelectItem>
                                    <SelectItem value="custom_modular">Modular (À la carte)</SelectItem>
                                    <SelectItem value="enterprise">Enterprise (Customizado)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Plano Base (se plano_padrao) */}
                        {newOferta.tipo_oferta === "plano_padrao" && (
                            <div className="grid gap-2">
                                <Label htmlFor="plano-base">Plano Base</Label>
                                <Select value={newOferta.plano_base_id} onValueChange={(v: string) => setNewOferta({ ...newOferta, plano_base_id: v })}>
                                    <SelectTrigger id="plano-base">
                                        <SelectValue placeholder="Selecione um plano..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {planos?.map((p) => (
                                            <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Módulos (se custom_modular) */}
                        {newOferta.tipo_oferta === "custom_modular" && (
                            <div className="grid gap-2">
                                <Label>Módulos Selecionados</Label>
                                <div className="border rounded p-3 space-y-2 max-h-48 overflow-y-auto">
                                    {modulos?.map((m) => (
                                        <div key={m.id} className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                id={m.id}
                                                checked={newOferta.modulos_selecionados.includes(m.id)}
                                                onChange={(e) => {
                                                    const selected = e.target.checked
                                                        ? [...newOferta.modulos_selecionados, m.id]
                                                        : newOferta.modulos_selecionados.filter(x => x !== m.id);
                                                    setNewOferta({ ...newOferta, modulos_selecionados: selected });
                                                }}
                                                className="rounded"
                                            />
                                            <label htmlFor={m.id} className="text-sm cursor-pointer flex-1">
                                                {m.icone && <span className="mr-1">{m.icone}</span>}
                                                {m.nome}
                                            </label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Preços */}
                        <div className="grid grid-cols-2 gap-2">
                            <div className="grid gap-2">
                                <Label htmlFor="preco-mensal">Preço Mensal (R$) *</Label>
                                <Input
                                    id="preco-mensal"
                                    type="number"
                                    step="0.01"
                                    value={newOferta.preco_total_mensal}
                                    onChange={(e) => setNewOferta({ ...newOferta, preco_total_mensal: e.target.value })}
                                    placeholder="0.00"
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="preco-anual">Preço Anual (R$) *</Label>
                                <Input
                                    id="preco-anual"
                                    type="number"
                                    step="0.01"
                                    value={newOferta.preco_total_anual}
                                    onChange={(e) => setNewOferta({ ...newOferta, preco_total_anual: e.target.value })}
                                    placeholder="0.00"
                                />
                            </div>
                        </div>

                        {/* Desconto */}
                        <div className="grid gap-2">
                            <Label htmlFor="desconto">Desconto (%)</Label>
                            <Input
                                id="desconto"
                                type="number"
                                step="0.01"
                                value={newOferta.desconto_percentual}
                                onChange={(e) => setNewOferta({ ...newOferta, desconto_percentual: e.target.value })}
                                placeholder="0"
                            />
                        </div>

                        {/* Justificativa */}
                        <div className="grid gap-2">
                            <Label htmlFor="justificativa">Justificativa</Label>
                            <Textarea
                                id="justificativa"
                                value={newOferta.justificativa}
                                onChange={(e) => setNewOferta({ ...newOferta, justificativa: e.target.value })}
                                placeholder="Explicar motivo da oferta especial..."
                                className="h-20"
                            />
                        </div>

                        {/* Validade */}
                        <div className="grid gap-2">
                            <Label htmlFor="vigencia">Dias para validação do código</Label>
                            <Input
                                id="vigencia"
                                type="number"
                                value={newOferta.vigencia_dias}
                                onChange={(e) => setNewOferta({ ...newOferta, vigencia_dias: e.target.value })}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowNewOferta(false)}>Cancelar</Button>
                        <Button onClick={handleCreateOferta} disabled={createOfertaMutation.isPending}>
                            {createOfertaMutation.isPending ? "Criando..." : "Criar Oferta"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Lead Detail Sheet */}
            <CrmLeadDetailSheet
                selectedLead={selectedLead}
                onClose={() => setSelectedLead(null)}
                onShowOferta={() => setShowNewOferta(true)}
                onConvert={(id) => convertLeadMutation.mutate(id)}
                onLose={(l) => setLoseTarget(l)}
                onReopen={(id) => reopenLeadMutation.mutate(id)}
                planos={planos}
                formatCurrency={formatCurrency}
            />

            <ConvertLeadWizard
                lead={convertWizardLead}
                open={!!convertWizardLead}
                onOpenChange={(v) => { if (!v) setConvertWizardLead(null); }}
                onSuccess={() => { invalidateCRM(); setSelectedLead(null); }}
            />
        </div>
    );
}
