"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Plus, Edit, Trash2, Save, Eye, LayoutGrid, Search,
    BookPlus, EyeOff, Filter, ArrowUpDown, Check, X,
    Undo2, Redo2, History, Copy, Book
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle
} from "@/components/ui/alert-dialog";
import ReactMarkdown from 'react-markdown';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Article {
    id: string;
    categoria_id: string;
    titulo: string;
    slug: string;
    conteudo: string;
    is_publico: boolean;
    visualizacoes: number;
    created_at?: string;
    updated_at?: string;
}

interface Category {
    id: string;
    nome: string;
    icone: string;
    ordem: number;
    artigos: Article[];
}

type ArticleModalMode = 'create' | 'edit' | null;
type CategoryModalMode = 'create' | 'edit' | null;

export default function BackofficeKBPage() {
    const queryClient = useQueryClient();
    
    // States - Articles
    const [articleModalMode, setArticleModalMode] = useState<ArticleModalMode>(null);
    const [editingArticle, setEditingArticle] = useState<any>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [statusFilter, setStatusFilter] = useState<"all" | "public" | "private">("all");
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [articleToDelete, setArticleToDelete] = useState<{ id: string; titulo: string } | null>(null);
    
    // States - Categories
    const [categoryModalMode, setCategoryModalMode] = useState<CategoryModalMode>(null);
    const [editingCategory, setEditingCategory] = useState<any>(null);
    const [categoryDeleteDialogOpen, setCategoryDeleteDialogOpen] = useState(false);
    const [categoryToDelete, setCategoryToDelete] = useState<{ id: string; nome: string } | null>(null);

    const { data: categories, isLoading } = useQuery<Category[]>({
        queryKey: ["backoffice", "kb"],
        queryFn: () => apiFetch("/kb/categories")
    });

    // ─── Article Mutations ───────────────────────────────────────────────────

    const saveArticleMutation = useMutation({
        mutationFn: (data: any) => {
            const method = data.id ? "PATCH" : "POST";
            const url = data.id ? `/kb/articles/${data.id}` : "/kb/articles";
            return apiFetch(url, { method, body: JSON.stringify(data) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "kb"] });
            setArticleModalMode(null);
            setEditingArticle(null);
            toast.success("Artigo salvo com sucesso!");
        },
        onError: (e: any) => {
            toast.error(e.message || "Erro ao salvar artigo");
        }
    });

    const deleteArticleMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/kb/articles/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "kb"] });
            setDeleteDialogOpen(false);
            setArticleToDelete(null);
            toast.success("Artigo removido com sucesso!");
        },
        onError: (e: any) => {
            toast.error(e.message || "Erro ao remover artigo");
        }
    });

    // ─── Category Mutations ──────────────────────────────────────────────────

    const saveCategoryMutation = useMutation({
        mutationFn: (data: any) => {
            const method = data.id ? "PATCH" : "POST";
            const url = data.id ? `/kb/categories/${data.id}` : "/kb/categories";
            return apiFetch(url, { method, body: JSON.stringify(data) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "kb"] });
            setCategoryModalMode(null);
            setEditingCategory(null);
            toast.success("Categoria salva com sucesso!");
        },
        onError: (e: any) => {
            toast.error(e.message || "Erro ao salvar categoria");
        }
    });

    const deleteCategoryMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/kb/categories/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "kb"] });
            setCategoryDeleteDialogOpen(false);
            setCategoryToDelete(null);
            toast.success("Categoria removida com sucesso!");
        },
        onError: (e: any) => {
            toast.error(e.message || "Erro ao remover categoria");
        }
    });

    // ─── Handlers ────────────────────────────────────────────────────────────

    const handleOpenArticleModal = (article: any = null, categoryId: string = "") => {
        if (article) {
            setEditingArticle({ ...article });
            setArticleModalMode('edit');
        } else {
            setEditingArticle({ 
                titulo: "", 
                slug: "", 
                conteudo: "", 
                categoria_id: categoryId, 
                is_publico: true 
            });
            setArticleModalMode('create');
        }
    };

    const handleOpenCategoryModal = (category: any = null) => {
        if (category) {
            setEditingCategory({ ...category });
            setCategoryModalMode('edit');
        } else {
            setEditingCategory({ nome: "", icone: "FileText", ordem: 0 });
            setCategoryModalMode('create');
        }
    };

    const confirmDeleteArticle = (id: string, titulo: string) => {
        setArticleToDelete({ id, titulo });
        setDeleteDialogOpen(true);
    };

    const confirmDeleteCategory = (id: string, nome: string) => {
        setCategoryToDelete({ id, nome });
        setCategoryDeleteDialogOpen(true);
    };

    const generateSlug = (title: string): string => {
        return title
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/\s+/g, '-')
            .replace(/[^\w-]/g, '');
    };

    // ─── Filtered Categories ─────────────────────────────────────────────────

    const filteredCategories = useMemo(() => {
        if (!categories) return [];

        return categories
            .map(cat => ({
                ...cat,
                artigos: cat.artigos.filter(art => {
                    const matchesSearch = art.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
                                         art.slug.toLowerCase().includes(searchTerm.toLowerCase());
                    
                    const matchesStatus = statusFilter === "all" 
                        ? true 
                        : statusFilter === "public" 
                            ? art.is_publico 
                            : !art.is_publico;

                    return matchesSearch && matchesStatus;
                })
            }))
            .filter(cat => cat.artigos.length > 0 || searchTerm || statusFilter !== "all");
    }, [categories, searchTerm, statusFilter]);

    const totalArticles = useMemo(() => {
        return categories?.reduce((acc, cat) => acc + cat.artigos.length, 0) || 0;
    }, [categories]);

    const publicArticles = useMemo(() => {
        return categories?.reduce((acc, cat) => 
            acc + cat.artigos.filter(a => a.is_publico).length, 0) || 0;
    }, [categories]);

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* ─── Header ────────────────────────────────────────────────────── */}
            <PageHeader
                title="Base de Conhecimento"
                description="Crie e gerencie os artigos da base de conhecimento para os usuários."
                icon={<Book className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Base de Conhecimento" },
                ]}
                actions={
                    <div className="flex gap-2">
                        <Button 
                            variant="outline" 
                            size="sm"
                            className="gap-2 rounded-sm"
                            onClick={() => handleOpenCategoryModal()}
                        >
                            <LayoutGrid className="size-4" /> 
                            <span className="hidden sm:inline">Nova Categoria</span>
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenArticleModal()}
                            className="gap-2 rounded-sm"
                        >
                            <BookPlus className="size-4" /> 
                            <span className="hidden sm:inline">Novo Artigo</span>
                        </Button>
                    </div>
                }
            />

            {/* ─── Stats & Filters ──────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="bg-surface shadow-sm">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground font-medium">Total de Artigos</p>
                                <p className="text-2xl font-bold">{totalArticles}</p>
                            </div>
                            <BookPlus className="size-5 text-primary" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-surface shadow-sm">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground font-medium">Artigos Públicos</p>
                                <p className="text-2xl font-bold text-cyan-700 dark:text-cyan-100">{publicArticles}</p>
                            </div>
                            <Eye className="size-5 text-cyan-700 dark:text-cyan-100" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-surface shadow-sm">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground font-medium">Artigos Privados</p>
                                <p className="text-2xl font-bold text-violet-700 dark:text-violet-100">{totalArticles - publicArticles}</p>
                            </div>
                            <EyeOff className="size-5 text-violet-700 dark:text-violet-100" />
                        </div>
                    </CardContent>
                </Card>
                <Card className="bg-surface shadow-sm">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted-foreground font-medium">Categorias</p>
                                <p className="text-2xl font-bold">{categories?.length || 0}</p>
                            </div>
                            <LayoutGrid className="size-5 text-primary" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ─── Search & Filter Bar ──────────────────────────────────────── */}
            <Card className="bg-surface shadow-sm">
                <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
                        <div className="relative w-full md:w-96">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Buscar artigos por título ou slug..."
                                className="pl-10"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <Filter className="size-4 text-muted-foreground" />
                                <span className="text-sm font-medium">Status:</span>
                                <div className="flex gap-1">
                                    <Button
                                        size="sm"
                                        variant={statusFilter === "all" ? "default" : "ghost"}
                                        className="h-8 text-xs"
                                        onClick={() => setStatusFilter("all")}
                                    >
                                        Todos
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant={statusFilter === "public" ? "default" : "ghost"}
                                        className="h-8 text-xs"
                                        onClick={() => setStatusFilter("public")}
                                    >
                                        <Eye className="size-3 mr-1" /> Públicos
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant={statusFilter === "private" ? "default" : "ghost"}
                                        className="h-8 text-xs"
                                        onClick={() => setStatusFilter("private")}
                                    >
                                        <EyeOff className="size-3 mr-1" /> Privados
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* ─── Categories & Articles List ───────────────────────────────── */}
            <div className="grid gap-6">
                {filteredCategories.map((cat) => (
                    <Card key={cat.id} className="border-l-4 border-l-primary overflow-hidden">
                        <CardHeader className="bg-muted/30 py-4">
                            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                                <div className="flex items-center gap-3">
                                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                                        <LayoutGrid className="size-5" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <CardTitle className="text-base font-semibold">{cat.nome}</CardTitle>
                                            <Badge variant="secondary" className="text-xs">
                                                {cat.artigos.length} {cat.artigos.length === 1 ? 'artigo' : 'artigos'}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-muted-foreground mt-0.5">
                                            {cat.artigos.filter(a => a.is_publico).length} públicos • {cat.artigos.filter(a => !a.is_publico).length} privados
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button 
                                        size="sm" 
                                        variant="outline" 
                                        className="h-8 text-xs"
                                        onClick={() => handleOpenCategoryModal(cat)}
                                    >
                                        <Edit className="size-3.5 mr-1" /> Editar
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-8 text-xs text-primary"
                                        onClick={() => handleOpenArticleModal(null, cat.id)}
                                    >
                                        <Plus className="size-3.5 mr-1" /> Add Artigo
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {cat.artigos.length === 0 ? (
                                <div className="p-8 text-center text-muted-foreground">
                                    <BookPlus className="size-8 mx-auto mb-2 opacity-20" />
                                    <p className="text-sm">Nenhum artigo nesta categoria</p>
                                </div>
                            ) : (
                                <div className="divide-y">
                                    {cat.artigos.map(art => (
                                        <div 
                                            key={art.id} 
                                            className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-muted/30 transition-colors group"
                                        >
                                            <div className="flex items-start gap-4 flex-1">
                                                <div className="h-10 w-10 rounded-lg bg-primary/5 flex items-center justify-center text-primary shrink-0">
                                                    <Eye className="size-4" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h4 className="text-sm font-semibold truncate">{art.titulo}</h4>
                                                        {art.is_publico ? (
                                                            <Badge variant="outline" className="text-[10px] h-5 bg-cyan-500/10 text-cyan-700 border-cyan-200 dark:bg-cyan-500/20 dark:text-cyan-100 dark:border-cyan-400/30">
                                                                <Eye className="size-2.5 mr-0.5" /> Público
                                                            </Badge>
                                                        ) : (
                                                            <Badge variant="outline" className="text-[10px] h-5 bg-violet-500/10 text-violet-700 border-violet-200 dark:bg-violet-500/20 dark:text-violet-100 dark:border-violet-400/30">
                                                                <EyeOff className="size-2.5 mr-0.5" /> Privado
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                        <span className="font-mono bg-muted/50 px-2 py-0.5 rounded">/{art.slug}</span>
                                                        <span className="flex items-center gap-1">
                                                            <Eye className="size-3" /> {art.visualizacoes} visualizações
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 w-8 p-0"
                                                    onClick={() => handleOpenArticleModal(art)}
                                                >
                                                    <Edit className="size-4" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                                                    onClick={() => confirmDeleteArticle(art.id, art.titulo)}
                                                >
                                                    <Trash2 className="size-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
                
                {filteredCategories.length === 0 && (
                    <Card className="bg-surface">
                        <CardContent className="p-12 text-center">
                            <BookPlus className="size-12 mx-auto mb-4 opacity-20" />
                            <h3 className="text-lg font-semibold mb-2">Nenhum artigo encontrado</h3>
                            <p className="text-muted-foreground text-sm mb-4">
                                {searchTerm || statusFilter !== "all"
                                    ? "Tente ajustar os filtros de busca"
                                    : "Comece criando sua primeira categoria e artigo"}
                            </p>
                            <div className="flex gap-2 justify-center">
                                {searchTerm && (
                                    <Button variant="outline" size="sm" onClick={() => setSearchTerm("")}>
                                        <Undo2 className="size-3.5 mr-1" /> Limpar busca
                                    </Button>
                                )}
                                {statusFilter !== "all" && (
                                    <Button variant="outline" size="sm" onClick={() => setStatusFilter("all")}>
                                        <Filter className="size-3.5 mr-1" /> Limpar filtros
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* ─── Article Editor Modal ─────────────────────────────────────── */}
            <Dialog 
                open={articleModalMode !== null} 
                onOpenChange={(open) => {
                    if (!open) {
                        setArticleModalMode(null);
                        setEditingArticle(null);
                    }
                }}
            >
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-4xl max-h-[90vh] overflow-hidden p-0 flex flex-col">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="flex items-center gap-2">
                            <BookPlus className="size-5 text-primary" />
                            {articleModalMode === 'edit' ? 'Editar Artigo' : 'Criar Novo Artigo'}
                        </DialogTitle>
                        <DialogDescription>
                            Preencha as informações do artigo. Use Markdown para formatar o conteúdo.
                        </DialogDescription>
                    </DialogHeader>

                    <ScrollArea className="flex-1 min-h-0">
                        <div className="px-6 py-5 space-y-4">
                            <Tabs defaultValue="editor" className="w-full">
                                <TabsList className="bg-muted/50 p-1">
                                    <TabsTrigger value="editor" className="gap-2">
                                        <Undo2 className="size-4" /> Editor
                                    </TabsTrigger>
                                    <TabsTrigger value="preview" className="gap-2">
                                        <Eye className="size-4" /> Preview
                                    </TabsTrigger>
                                </TabsList>
                                
                                <TabsContent value="editor" className="space-y-4 mt-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                                Título do Artigo *
                                            </label>
                                            <Input
                                                placeholder="Ex: Como configurar sua primeira safra"
                                                value={editingArticle?.titulo || ""}
                                                onChange={(e) => {
                                                    const val = e.target.value;
                                                    const slug = generateSlug(val);
                                                    setEditingArticle({
                                                        ...editingArticle,
                                                        titulo: val,
                                                        slug: editingArticle?.id ? editingArticle.slug : slug
                                                    });
                                                }}
                                                disabled={articleModalMode === 'edit'}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                                Slug (URL) *
                                            </label>
                                            <div className="flex gap-2">
                                                <Input
                                                    placeholder="exemplo-de-slug"
                                                    value={editingArticle?.slug || ""}
                                                    onChange={(e) => setEditingArticle({
                                                        ...editingArticle,
                                                        slug: e.target.value
                                                    })}
                                                    className="font-mono text-sm"
                                                />
                                                {articleModalMode === 'create' && (
                                                    <Button
                                                        type="button"
                                                        variant="outline"
                                                        size="icon"
                                                        onClick={() => setEditingArticle({
                                                            ...editingArticle,
                                                            slug: generateSlug(editingArticle?.titulo || "")
                                                        })}
                                                        title="Gerar slug automaticamente"
                                                    >
                                                        <Undo2 className="size-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                            Conteúdo (Markdown) *
                                        </label>
                                        <Textarea
                                            className="min-h-[300px] font-mono text-sm leading-relaxed resize-y"
                                            placeholder="# Use Markdown para formatar seu artigo...&#10;&#10;## Seções&#10;- Listas&#10;- **Negrito**&#10;- *Itálico*"
                                            value={editingArticle?.conteudo || ""}
                                            onChange={(e) => setEditingArticle({
                                                ...editingArticle,
                                                conteudo: e.target.value
                                            })}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Dica: Use # para títulos, - para listas, **texto** para negrito
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                                Categoria *
                                            </label>
                                            <Select
                                                value={editingArticle?.categoria_id || ""}
                                                onValueChange={(value) => setEditingArticle({
                                                    ...editingArticle,
                                                    categoria_id: value
                                                })}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Selecione a categoria" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {categories?.map(c => (
                                                        <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="flex items-center gap-3 pt-6">
                                            <Switch
                                                id="is_publico"
                                                checked={editingArticle?.is_publico || false}
                                                onCheckedChange={(checked) => setEditingArticle({
                                                    ...editingArticle,
                                                    is_publico: checked
                                                })}
                                            />
                                            <label htmlFor="is_publico" className="text-sm font-medium flex items-center gap-2">
                                                {editingArticle?.is_publico ? (
                                                    <>
                                                        <Eye className="size-4 text-cyan-700 dark:text-cyan-100" />
                                                        <span>Artigo Público (visível para usuários)</span>
                                                    </>
                                                ) : (
                                                    <>
                                                        <EyeOff className="size-4 text-violet-700 dark:text-violet-100" />
                                                        <span>Artigo Privado (apenas admin)</span>
                                                    </>
                                                )}
                                            </label>
                                        </div>
                                    </div>
                                </TabsContent>

                                <TabsContent value="preview" className="mt-4">
                                    <Card className="border bg-muted/30">
                                        <CardContent className="p-6 prose prose-slate max-w-none dark:prose-invert prose-sm">
                                            {editingArticle?.conteudo ? (
                                                <ReactMarkdown>{editingArticle.conteudo}</ReactMarkdown>
                                            ) : (
                                                <p className="text-muted-foreground text-center py-8">
                                                    Digite algum conteúdo no editor para visualizar
                                                </p>
                                            )}
                                        </CardContent>
                                    </Card>
                                </TabsContent>
                            </Tabs>
                        </div>
                    </ScrollArea>

                    <DialogFooter className="gap-2 border-t px-6 py-5">
                        <Button
                            variant="ghost"
                            onClick={() => {
                                setArticleModalMode(null);
                                setEditingArticle(null);
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button
                            className="gap-2"
                            disabled={
                                !editingArticle?.titulo ||
                                !editingArticle?.conteudo ||
                                !editingArticle?.categoria_id ||
                                saveArticleMutation.isPending
                            }
                            onClick={() => saveArticleMutation.mutate(editingArticle)}
                        >
                            {saveArticleMutation.isPending ? (
                                <>
                                    <span className="animate-spin">⏳</span> Salvando...
                                </>
                            ) : (
                                <>
                                    <Save className="size-4" /> {editingArticle?.id ? 'Atualizar' : 'Criar'} Artigo
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ─── Category Modal ───────────────────────────────────────────── */}
            <Dialog 
                open={categoryModalMode !== null} 
                onOpenChange={(open) => {
                    if (!open) {
                        setCategoryModalMode(null);
                        setEditingCategory(null);
                    }
                }}
            >
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-md overflow-hidden p-0 flex flex-col">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="flex items-center gap-2">
                            <LayoutGrid className="size-5 text-primary" />
                            {categoryModalMode === 'edit' ? 'Editar Categoria' : 'Nova Categoria'}
                        </DialogTitle>
                        <DialogDescription>
                            Informe o nome e ícone da categoria.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 px-6 py-5">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Nome da Categoria *
                            </label>
                            <Input
                                placeholder="Ex: Pecuária, Agricultura, Financeiro..."
                                value={editingCategory?.nome || ""}
                                onChange={(e) => setEditingCategory({
                                    ...editingCategory,
                                    nome: e.target.value
                                })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Ícone (Lucide)
                            </label>
                            <Input
                                placeholder="Ex: Tractor, Sprout, HandCoins..."
                                value={editingCategory?.icone || ""}
                                onChange={(e) => setEditingCategory({
                                    ...editingCategory,
                                    icone: e.target.value
                                })}
                            />
                            <p className="text-xs text-muted-foreground">
                                Nome do ícone da biblioteca Lucide React
                            </p>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Ordem de exibição
                            </label>
                            <Input
                                type="number"
                                placeholder="0"
                                value={editingCategory?.ordem || 0}
                                onChange={(e) => setEditingCategory({
                                    ...editingCategory,
                                    ordem: parseInt(e.target.value) || 0
                                })}
                            />
                        </div>
                    </div>

                    <DialogFooter className="gap-2 border-t px-6 py-5">
                        <Button
                            variant="ghost"
                            onClick={() => {
                                setCategoryModalMode(null);
                                setEditingCategory(null);
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button
                            className="gap-2"
                            disabled={
                                !editingCategory?.nome ||
                                saveCategoryMutation.isPending
                            }
                            onClick={() => saveCategoryMutation.mutate(editingCategory)}
                        >
                            {saveCategoryMutation.isPending ? (
                                <>
                                    <span className="animate-spin">⏳</span> Salvando...
                                </>
                            ) : (
                                <>
                                    <Save className="size-4" /> {editingCategory?.id ? 'Atualizar' : 'Criar'} Categoria
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ─── Delete Article Confirmation ──────────────────────────────── */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2 text-red-600">
                            <Trash2 className="size-5" /> Excluir Artigo
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Tem certeza que deseja excluir o artigo "{articleToDelete?.titulo}"?
                            Esta ação não pode ser desfeita e o artigo será permanentemente removido.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => articleToDelete && deleteArticleMutation.mutate(articleToDelete.id)}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {deleteArticleMutation.isPending ? 'Excluindo...' : 'Excluir'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* ─── Delete Category Confirmation ─────────────────────────────── */}
            <AlertDialog open={categoryDeleteDialogOpen} onOpenChange={setCategoryDeleteDialogOpen}>
                <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2 text-red-600">
                            <Trash2 className="size-5" /> Excluir Categoria
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            Tem certeza que deseja excluir a categoria "{categoryToDelete?.nome}"?
                            <strong className="text-red-600 block mt-2">
                                ⚠️ Todos os artigos desta categoria também serão excluídos!
                            </strong>
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => categoryToDelete && deleteCategoryMutation.mutate(categoryToDelete.id)}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            {deleteCategoryMutation.isPending ? 'Excluindo...' : 'Excluir'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
