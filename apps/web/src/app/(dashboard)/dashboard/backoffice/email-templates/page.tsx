"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Mail, Plus, Search, Eye, Pencil, Check, X,
    Send, MousePointerClick, MailOpen,
} from "lucide-react";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

interface EmailTemplate {
    id: string;
    codigo: string;
    nome: string;
    descricao: string | null;
    assunto: string;
    corpo_html: string;
    corpo_texto: string;
    variaveis: string[];
    tipo: string;
    ativo: boolean;
    editado_por_id: string | null;
    created_at: string;
    updated_at: string;
}

interface EmailStats {
    total_templates: number;
    ativos: number;
    inativos: number;
    por_tipo: Record<string, number>;
    emails_enviados: number;
    emails_abertos: number;
    emails_clicados: number;
    taxa_abertura: number;
}

const TIPO_LABELS: Record<string, string> = {
    transacional: "Transacional",
    marketing: "Marketing",
    sistema: "Sistema",
};

const TIPO_COLORS: Record<string, string> = {
    transacional: "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30",
    marketing: "bg-fuchsia-500/10 text-fuchsia-700 border-fuchsia-200 dark:bg-fuchsia-500/20 dark:text-fuchsia-100 dark:border-fuchsia-400/30",
    sistema: "bg-amber-500/10 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30",
};

const emptyForm = {
    codigo: "",
    nome: "",
    descricao: "",
    assunto: "",
    corpo_html: "",
    corpo_texto: "",
    variaveis: [] as string[],
    tipo: "transacional",
    ativo: true,
};

export default function EmailTemplatesPage() {
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState("");
    const [tipoFilter, setTipoFilter] = useState("");
    const [showDialog, setShowDialog] = useState(false);
    const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null);
    const [previewTemplate, setPreviewTemplate] = useState<EmailTemplate | null>(null);
    const [formData, setFormData] = useState(emptyForm);
    const [variaveisInput, setVariaveisInput] = useState("");

    const { data: templates, isLoading } = useQuery<EmailTemplate[]>({
        queryKey: ["backoffice", "email-templates", tipoFilter],
        queryFn: () => {
            const params = new URLSearchParams();
            if (tipoFilter) params.set("tipo", tipoFilter);
            const qs = params.toString();
            return apiFetch(`/backoffice/email-templates${qs ? `?${qs}` : ""}`);
        },
    });

    const { data: stats } = useQuery<EmailStats>({
        queryKey: ["backoffice", "email-templates", "stats"],
        queryFn: () => apiFetch("/backoffice/email-templates/stats"),
    });

    const createMutation = useMutation({
        mutationFn: (data: typeof formData) =>
            apiFetch("/backoffice/email-templates", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "email-templates"] });
            toast.success("Template criado com sucesso!");
            closeDialog();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar template"),
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: Partial<typeof formData> }) =>
            apiFetch(`/backoffice/email-templates/${id}`, {
                method: "PUT",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "email-templates"] });
            toast.success("Template atualizado!");
            closeDialog();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao atualizar template"),
    });

    const closeDialog = () => {
        setShowDialog(false);
        setEditingTemplate(null);
        setFormData(emptyForm);
        setVariaveisInput("");
    };

    const openCreate = () => {
        setEditingTemplate(null);
        setFormData(emptyForm);
        setVariaveisInput("");
        setShowDialog(true);
    };

    const openEdit = (t: EmailTemplate) => {
        setEditingTemplate(t);
        setFormData({
            codigo: t.codigo,
            nome: t.nome,
            descricao: t.descricao || "",
            assunto: t.assunto,
            corpo_html: t.corpo_html,
            corpo_texto: t.corpo_texto,
            variaveis: Array.isArray(t.variaveis) ? t.variaveis : [],
            tipo: t.tipo,
            ativo: t.ativo,
        });
        setVariaveisInput(Array.isArray(t.variaveis) ? t.variaveis.join(", ") : "");
        setShowDialog(true);
    };

    const handleSubmit = () => {
        const vars = variaveisInput.split(",").map((v) => v.trim()).filter(Boolean);
        const payload = { ...formData, variaveis: vars };

        if (editingTemplate) {
            updateMutation.mutate({ id: editingTemplate.id, data: payload });
        } else {
            createMutation.mutate(payload);
        }
    };

    const filteredTemplates = templates?.filter((t) =>
        t.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
        t.assunto.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
                </div>
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Templates de E-mail"
                description="Gerencie os templates de email transacionais, marketing e sistema."
                icon={<Mail className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Templates de E-mail" },
                ]}
                actions={
                    <Button onClick={openCreate} size="sm" variant="outline" className="rounded-sm">
                        <Plus className="size-4 mr-2" /> Novo Template
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <Mail size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Templates</p>
                            <p className="text-2xl font-black">{stats?.total_templates ?? 0}</p>
                            <p className="text-[10px] text-muted-foreground">{stats?.ativos ?? 0} ativos</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-blue-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-600">
                            <Send size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Enviados</p>
                            <p className="text-2xl font-black">{stats?.emails_enviados ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-green-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-green-500/10 flex items-center justify-center text-green-600">
                            <MailOpen size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Taxa Abertura</p>
                            <p className="text-2xl font-black">{stats?.taxa_abertura ?? 0}%</p>
                            <p className="text-[10px] text-muted-foreground">{stats?.emails_abertos ?? 0} abertos</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-purple-500">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-600">
                            <MousePointerClick size={24} />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Cliques</p>
                            <p className="text-2xl font-black">{stats?.emails_clicados ?? 0}</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-3">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Buscar por nome, código ou assunto..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10"
                    />
                </div>
                <Select value={tipoFilter} onValueChange={(v) => setTipoFilter(v === "all" ? "" : v)}>
                    <SelectTrigger className="w-48"><SelectValue placeholder="Todos os tipos" /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos os tipos</SelectItem>
                        <SelectItem value="transacional">Transacional</SelectItem>
                        <SelectItem value="marketing">Marketing</SelectItem>
                        <SelectItem value="sistema">Sistema</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* Table */}
            <Card className="overflow-hidden">
                <Table>
                    <TableHeader className="bg-muted/50 text-xs uppercase">
                        <TableRow>
                            <TableHead>Código / Nome</TableHead>
                            <TableHead>Assunto</TableHead>
                            <TableHead>Tipo</TableHead>
                            <TableHead>Variáveis</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Atualizado</TableHead>
                            <TableHead className="text-right">Ações</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredTemplates?.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                                    Nenhum template encontrado.
                                </TableCell>
                            </TableRow>
                        )}
                        {filteredTemplates?.map((t) => (
                            <TableRow key={t.id} className="group transition-colors hover:bg-muted/10">
                                <TableCell>
                                    <div className="flex flex-col">
                                        <code className="font-mono text-[11px] text-muted-foreground">{t.codigo}</code>
                                        <span className="font-bold text-foreground text-sm">{t.nome}</span>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <span className="text-sm text-foreground">{t.assunto}</span>
                                </TableCell>
                                <TableCell>
                                    <Badge className={`text-[9px] font-black uppercase border ${TIPO_COLORS[t.tipo] ?? ""}`}>
                                        {TIPO_LABELS[t.tipo] ?? t.tipo}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-wrap gap-1">
                                        {(Array.isArray(t.variaveis) ? t.variaveis : []).slice(0, 3).map((v) => (
                                            <Badge key={v} variant="outline" className="text-[9px] font-mono">
                                                {`{{${v}}}`}
                                            </Badge>
                                        ))}
                                        {Array.isArray(t.variaveis) && t.variaveis.length > 3 && (
                                            <Badge variant="outline" className="text-[9px]">
                                                +{t.variaveis.length - 3}
                                            </Badge>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell>
                                    {t.ativo ? (
                                        <StatusBadge status="ativo" />
                                    ) : (
                                        <StatusBadge status="inativo" />
                                    )}
                                </TableCell>
                                <TableCell>
                                    <span className="text-xs text-muted-foreground">
                                        {format(new Date(t.updated_at), "dd/MM/yy HH:mm", { locale: ptBR })}
                                    </span>
                                </TableCell>
                                <TableCell className="text-right">
                                    <div className="flex gap-1 justify-end">
                                        <Button variant="ghost" size="icon" className="size-8" onClick={() => setPreviewTemplate(t)}>
                                            <Eye className="size-3.5" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="size-8" onClick={() => openEdit(t)}>
                                            <Pencil className="size-3.5" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Card>

            {/* Create/Edit Dialog */}
            <Dialog open={showDialog} onOpenChange={() => closeDialog()}>
                <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Mail className="size-5" />
                            {editingTemplate ? "Editar Template" : "Novo Template"}
                        </DialogTitle>
                        <DialogDescription>
                            {editingTemplate ? `Editando: ${editingTemplate.codigo}` : "Configure um novo template de email."}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="codigo">Código</Label>
                                <Input
                                    id="codigo"
                                    placeholder="ex: welcome_user"
                                    value={formData.codigo}
                                    onChange={(e) => setFormData({ ...formData, codigo: e.target.value })}
                                    disabled={!!editingTemplate}
                                    className="font-mono"
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label>Tipo</Label>
                                <Select value={formData.tipo} onValueChange={(v) => setFormData({ ...formData, tipo: v })}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="transacional">Transacional</SelectItem>
                                        <SelectItem value="marketing">Marketing</SelectItem>
                                        <SelectItem value="sistema">Sistema</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="nome">Nome</Label>
                            <Input id="nome" placeholder="Boas-vindas ao Usuário" value={formData.nome} onChange={(e) => setFormData({ ...formData, nome: e.target.value })} />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="descricao">Descrição</Label>
                            <Input id="descricao" placeholder="Descrição opcional..." value={formData.descricao} onChange={(e) => setFormData({ ...formData, descricao: e.target.value })} />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="assunto">Assunto do Email</Label>
                            <Input id="assunto" placeholder="Bem-vindo, {{nome_usuario}}!" value={formData.assunto} onChange={(e) => setFormData({ ...formData, assunto: e.target.value })} />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="variaveis">Variáveis Disponíveis (separadas por vírgula)</Label>
                            <Input
                                id="variaveis"
                                placeholder="nome_usuario, tenant_nome, data_vencimento"
                                value={variaveisInput}
                                onChange={(e) => setVariaveisInput(e.target.value)}
                                className="font-mono text-sm"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="corpo_html">Corpo HTML</Label>
                            <Textarea
                                id="corpo_html"
                                placeholder="<h1>Olá, {{nome_usuario}}!</h1>..."
                                value={formData.corpo_html}
                                onChange={(e) => setFormData({ ...formData, corpo_html: e.target.value })}
                                rows={8}
                                className="font-mono text-xs"
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="corpo_texto">Corpo Texto (fallback)</Label>
                            <Textarea
                                id="corpo_texto"
                                placeholder="Olá, {{nome_usuario}}!..."
                                value={formData.corpo_texto}
                                onChange={(e) => setFormData({ ...formData, corpo_texto: e.target.value })}
                                rows={4}
                                className="text-sm"
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={closeDialog}>Cancelar</Button>
                        <Button
                            onClick={handleSubmit}
                            disabled={createMutation.isPending || updateMutation.isPending || !formData.codigo || !formData.nome || !formData.assunto}
                        >
                            {(createMutation.isPending || updateMutation.isPending) ? "Salvando..." : editingTemplate ? "Salvar" : "Criar Template"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Preview Dialog */}
            <Dialog open={!!previewTemplate} onOpenChange={() => setPreviewTemplate(null)}>
                <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Eye className="size-5" /> Preview: {previewTemplate?.nome}
                        </DialogTitle>
                    </DialogHeader>

                    {previewTemplate && (
                        <Tabs defaultValue="html" className="w-full">
                            <TabsList>
                                <TabsTrigger value="html">HTML</TabsTrigger>
                                <TabsTrigger value="texto">Texto</TabsTrigger>
                                <TabsTrigger value="codigo">Código Fonte</TabsTrigger>
                            </TabsList>
                            <TabsContent value="html">
                                <div className="border rounded-sm p-1 bg-white">
                                    <div className="p-4 border-b bg-muted/30">
                                        <p className="text-xs text-muted-foreground">Assunto:</p>
                                        <p className="font-bold text-sm">{previewTemplate.assunto}</p>
                                    </div>
                                    <div
                                        className="p-4 prose prose-sm max-w-none"
                                        dangerouslySetInnerHTML={{ __html: previewTemplate.corpo_html }}
                                    />
                                </div>
                            </TabsContent>
                            <TabsContent value="texto">
                                <pre className="p-4 bg-muted/50 rounded-sm text-sm whitespace-pre-wrap">
                                    {previewTemplate.corpo_texto}
                                </pre>
                            </TabsContent>
                            <TabsContent value="codigo">
                                <pre className="p-4 bg-muted/50 rounded-sm text-xs font-mono overflow-x-auto max-h-96">
                                    {previewTemplate.corpo_html}
                                </pre>
                            </TabsContent>
                        </Tabs>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
