"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Plus, Package, DollarSign, BarChart3, Edit, Trash2, Eye,
    Layers, Tag, TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/ui/status-badge";

interface Produto {
    id: string;
    nome: string;
    slug: string;
    descricao: string;
    categoria: "core" | "addon";
    ativo: boolean;
    icone: string;
}

interface Plano {
    id: string;
    nome: string;
    slug: string;
    descricao: string | null;
    tipo_oferta: "bundle" | "modular" | "misto";
    modulos_inclusos: string[];
    preco_mensal_padrao: number | null;
    preco_anual_padrao: number | null;
    ativo: boolean;
}

interface PrecoDinamico {
    preco_mensal: number;
    preco_anual: number;
    desconto_aplicado: number;
}

export default function OfertasPage() {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState("produtos");
    const [showProductDialog, setShowProductDialog] = useState(false);
    const [showPlanDialog, setShowPlanDialog] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<Produto | null>(null);
    const [selectedPlan, setSelectedPlan] = useState<Plano | null>(null);
    const [precoDinamico, setPrecoDinamico] = useState<PrecoDinamico | null>(null);

    // Form states
    const [productForm, setProductForm] = useState({
        nome: "",
        slug: "",
        descricao: "",
        categoria: "core" as "core" | "addon",
        icone: "📦",
    });

    const [planForm, setPlanForm] = useState({
        nome: "",
        slug: "",
        descricao: "",
        tipo_oferta: "bundle" as "bundle" | "modular" | "misto",
        modulos_inclusos: [] as string[],
        preco_mensal_padrao: 0,
        preco_anual_padrao: 0,
    });

    // Queries
    const { data: produtos = [], isLoading: produtosLoading } = useQuery<Produto[]>({
        queryKey: ["crm", "ofertas", "produtos"],
        queryFn: () => apiFetch("/backoffice/crm/ofertas/produtos"),
    });

    const { data: planos = [], isLoading: planosLoading } = useQuery<Plano[]>({
        queryKey: ["crm", "ofertas", "planos"],
        queryFn: () => apiFetch("/backoffice/crm/ofertas/planos"),
    });

    // Mutations
    const createProductMutation = useMutation({
        mutationFn: (data: typeof productForm) =>
            apiFetch("/backoffice/crm/ofertas/produtos", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["crm", "ofertas", "produtos"] });
            toast.success("Produto criado com sucesso!");
            setShowProductDialog(false);
            resetProductForm();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar produto"),
    });

    const createPlanMutation = useMutation({
        mutationFn: (data: typeof planForm) =>
            apiFetch("/backoffice/crm/ofertas/planos", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["crm", "ofertas", "planos"] });
            toast.success("Plano criado com sucesso!");
            setShowPlanDialog(false);
            resetPlanForm();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar plano"),
    });

    const resetProductForm = () => {
        setProductForm({
            nome: "",
            slug: "",
            descricao: "",
            categoria: "core",
            icone: "📦",
        });
    };

    const resetPlanForm = () => {
        setPlanForm({
            nome: "",
            slug: "",
            descricao: "",
            tipo_oferta: "bundle",
            modulos_inclusos: [],
            preco_mensal_padrao: 0,
            preco_anual_padrao: 0,
        });
    };

    const stats = {
        produtosTotal: produtos.length,
        produtosCore: produtos.filter(p => p.categoria === "core" && p.ativo).length,
        planosTotal: planos.length,
        planosAtivos: planos.filter(p => p.ativo).length,
    };

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Ofertas & Planos Comerciais"
                description="Gerencie produtos, módulos e planos de assinatura."
                breadcrumbs={[{ label: "Backoffice" }, { label: "Comercial" }, { label: "Ofertas" }]}
            />

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard
                    icon={Package}
                    label="Produtos"
                    value={stats.produtosTotal}
                    color="primary"
                />
                <StatCard
                    icon={Tag}
                    label="Core Modules"
                    value={stats.produtosCore}
                    color="success"
                />
                <StatCard
                    icon={Layers}
                    label="Planos"
                    value={stats.planosTotal}
                    color="backoffice"
                />
                <StatCard
                    icon={TrendingUp}
                    label="Planos Ativos"
                    value={stats.planosAtivos}
                    color="warning"
                />
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="produtos" className="gap-1">
                        <Package className="size-4" /> Produtos
                    </TabsTrigger>
                    <TabsTrigger value="planos" className="gap-1">
                        <Layers className="size-4" /> Planos
                    </TabsTrigger>
                </TabsList>

                {/* Produtos Tab */}
                <TabsContent value="produtos" className="space-y-4 mt-4">
                    <div className="flex justify-end">
                        <Button onClick={() => setShowProductDialog(true)} size="sm">
                            <Plus className="size-4 mr-2" /> Novo Produto
                        </Button>
                    </div>

                    {produtosLoading ? (
                        <div className="grid gap-4 md:grid-cols-3">
                            {Array.from({ length: 3 }).map((_, i) => (
                                <Skeleton key={i} className="h-32" />
                            ))}
                        </div>
                    ) : produtos.length === 0 ? (
                        <Card>
                            <CardContent className="p-8 text-center text-muted-foreground">
                                Nenhum produto criado ainda.
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-3">
                            {produtos.map((produto) => (
                                <Card key={produto.id} className="hover:shadow-md transition-shadow">
                                    <CardHeader className="pb-3">
                                        <div className="flex items-start justify-between">
                                            <div className="text-2xl">{produto.icone}</div>
                                            <StatusBadge status={produto.ativo ? "ativo" : "inativo"} />
                                        </div>
                                        <CardTitle className="text-base">{produto.nome}</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-2">
                                        <p className="text-xs text-muted-foreground">{produto.descricao}</p>
                                        <p className="text-xs">
                                            <span className="font-semibold">Slug:</span> {produto.slug}
                                        </p>
                                        <Badge variant="outline" className="text-[10px]">
                                            {produto.categoria === "core" ? "Core" : "Add-on"}
                                        </Badge>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                {/* Planos Tab */}
                <TabsContent value="planos" className="space-y-4 mt-4">
                    <div className="flex justify-end">
                        <Button onClick={() => setShowPlanDialog(true)} size="sm">
                            <Plus className="size-4 mr-2" /> Novo Plano
                        </Button>
                    </div>

                    {planosLoading ? (
                        <div className="grid gap-4 md:grid-cols-2">
                            {Array.from({ length: 2 }).map((_, i) => (
                                <Skeleton key={i} className="h-48" />
                            ))}
                        </div>
                    ) : planos.length === 0 ? (
                        <Card>
                            <CardContent className="p-8 text-center text-muted-foreground">
                                Nenhum plano criado ainda.
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2">
                            {planos.map((plano) => (
                                <Card key={plano.id} className="hover:shadow-md transition-shadow">
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <CardTitle className="text-base">{plano.nome}</CardTitle>
                                                <p className="text-xs text-muted-foreground mt-1">{plano.descricao}</p>
                                            </div>
                                            <Badge variant="outline">{plano.tipo_oferta}</Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <div>
                                            <p className="text-xs font-semibold text-muted-foreground mb-2">Módulos:</p>
                                            <div className="flex flex-wrap gap-1">
                                                {plano.modulos_inclusos.map((mod) => (
                                                    <Badge key={mod} variant="secondary" className="text-[10px]">
                                                        {mod}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                        {plano.preco_mensal_padrao && (
                                            <div className="flex items-center gap-2 text-sm">
                                                <DollarSign className="size-4 text-green-600" />
                                                <span className="font-semibold">
                                                    R${plano.preco_mensal_padrao}/mês
                                                </span>
                                            </div>
                                        )}
                                        <StatusBadge status={plano.ativo ? "ativo" : "inativo"} />
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* Product Dialog */}
            <Dialog open={showProductDialog} onOpenChange={setShowProductDialog}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Package className="size-5" /> Novo Produto
                        </DialogTitle>
                        <DialogDescription>
                            Crie um novo módulo/produto que pode ser oferecido aos assinantes.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="nome">Nome *</Label>
                            <Input
                                id="nome"
                                value={productForm.nome}
                                onChange={(e) => setProductForm({ ...productForm, nome: e.target.value })}
                                placeholder="Ex: CRM"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="slug">Slug *</Label>
                            <Input
                                id="slug"
                                value={productForm.slug}
                                onChange={(e) => setProductForm({ ...productForm, slug: e.target.value.toLowerCase() })}
                                placeholder="ex: crm"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="descricao">Descrição</Label>
                            <Input
                                id="descricao"
                                value={productForm.descricao}
                                onChange={(e) => setProductForm({ ...productForm, descricao: e.target.value })}
                                placeholder="Descrição breve do módulo"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="icone">Ícone</Label>
                                <Input
                                    id="icone"
                                    value={productForm.icone}
                                    onChange={(e) => setProductForm({ ...productForm, icone: e.target.value })}
                                    placeholder="📊"
                                    maxLength={2}
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="categoria">Categoria</Label>
                                <Select
                                    value={productForm.categoria}
                                    onValueChange={(value) => setProductForm({ ...productForm, categoria: value as "core" | "addon" })}
                                >
                                    <SelectTrigger id="categoria" className="h-8 rounded-sm border-border bg-background px-3 text-sm">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        <SelectItem value="core">Core</SelectItem>
                                        <SelectItem value="addon">Add-on</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowProductDialog(false)}>
                            Cancelar
                        </Button>
                        <Button
                            onClick={() => createProductMutation.mutate(productForm)}
                            disabled={createProductMutation.isPending || !productForm.nome || !productForm.slug}
                        >
                            {createProductMutation.isPending ? "Criando..." : "Criar Produto"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Plan Dialog */}
            <Dialog open={showPlanDialog} onOpenChange={setShowPlanDialog}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Layers className="size-5" /> Novo Plano
                        </DialogTitle>
                        <DialogDescription>
                            Agregue módulos em um plano comercial.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="plan-nome">Nome *</Label>
                            <Input
                                id="plan-nome"
                                value={planForm.nome}
                                onChange={(e) => setPlanForm({ ...planForm, nome: e.target.value })}
                                placeholder="Ex: Profissional"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="plan-slug">Slug *</Label>
                            <Input
                                id="plan-slug"
                                value={planForm.slug}
                                onChange={(e) => setPlanForm({ ...planForm, slug: e.target.value.toLowerCase() })}
                                placeholder="ex: profissional"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label>Módulos Inclusos</Label>
                            <div className="space-y-2 max-h-32 overflow-y-auto border rounded-md p-3">
                                {produtos.map((produto) => (
                                    <label key={produto.id} className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={planForm.modulos_inclusos.includes(produto.slug)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setPlanForm({
                                                        ...planForm,
                                                        modulos_inclusos: [...planForm.modulos_inclusos, produto.slug],
                                                    });
                                                } else {
                                                    setPlanForm({
                                                        ...planForm,
                                                        modulos_inclusos: planForm.modulos_inclusos.filter(s => s !== produto.slug),
                                                    });
                                                }
                                            }}
                                        />
                                        <span className="text-sm">{produto.icone} {produto.nome}</span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="preco-mensal">Preço Mensal</Label>
                                <Input
                                    id="preco-mensal"
                                    type="number"
                                    value={planForm.preco_mensal_padrao || ""}
                                    onChange={(e) => setPlanForm({ ...planForm, preco_mensal_padrao: parseFloat(e.target.value) || 0 })}
                                    placeholder="0,00"
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="preco-anual">Preço Anual</Label>
                                <Input
                                    id="preco-anual"
                                    type="number"
                                    value={planForm.preco_anual_padrao || ""}
                                    onChange={(e) => setPlanForm({ ...planForm, preco_anual_padrao: parseFloat(e.target.value) || 0 })}
                                    placeholder="0,00"
                                />
                            </div>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowPlanDialog(false)}>
                            Cancelar
                        </Button>
                        <Button
                            onClick={() => createPlanMutation.mutate(planForm)}
                            disabled={createPlanMutation.isPending || !planForm.nome || !planForm.slug}
                        >
                            {createPlanMutation.isPending ? "Criando..." : "Criar Plano"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
