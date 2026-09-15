"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Search, Book, ChevronRight,
    Tractor, Sprout, HandCoins, HelpCircle,
    FileText, Lightbulb, ShieldCheck
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PageHeader } from "@/components/shared/page-header";
import ReactMarkdown from 'react-markdown';
import Link from "next/link";

interface KBArticle {
    id: string;
    titulo: string;
    slug: string;
    conteudo: string;
    visualizacoes: number;
}

interface KBCategory {
    id: string;
    nome: string;
    icone: string;
    artigos: KBArticle[];
}

export default function KnowledgeBasePage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedArticleSlug, setSelectedArticleSlug] = useState<string | null>(null);

    const { data: categories, isLoading } = useQuery<KBCategory[]>({
        queryKey: ["kb", "public"],
        queryFn: () => apiFetch("/kb/categories")
    });

    const { data: activeArticle, isLoading: isLoadingArticle } = useQuery<KBArticle>({
        queryKey: ["kb", "article", selectedArticleSlug],
        queryFn: () => apiFetch(`/kb/articles/${selectedArticleSlug}`),
        enabled: !!selectedArticleSlug
    });

    const getIcon = (name: string) => {
        const icons: any = {
            'Tractor': <Tractor size={20} />,
            'Sprout': <Sprout size={20} />,
            'HandCoins': <HandCoins size={20} />,
            'ShieldCheck': <ShieldCheck size={20} />,
            'Lightbulb': <Lightbulb size={20} />
        };
        return icons[name] || <FileText size={20} />;
    };

    if (isLoading) {
        return <div className="p-8 space-y-4"><Skeleton className="h-10 w-64" /><Skeleton className="h-96 w-full" /></div>;
    }

    // Filter categories and articles based on search
    const filteredKB = categories?.map(cat => ({
        ...cat,
        artigos: cat.artigos.filter(art =>
            art.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
            cat.nome.toLowerCase().includes(searchTerm.toLowerCase())
        )
    })).filter(cat => cat.artigos.length > 0);

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Base de Conhecimento"
                description="Pesquise por tutoriais, guias de uso e resoluções de problemas comuns."
                icon={<Book className="text-primary" size={22} />}
            />
            <div className="relative w-full max-w-2xl">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 size-5 text-muted-foreground" />
                <Input
                    placeholder="Ex: Como cadastrar um talhão, configurar sementes..."
                    className="pl-12 h-14 text-lg rounded-sm border-2 focus:ring-primary shadow-lg bg-surface"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            <div className="grid gap-8 md:grid-cols-12 flex-1">
                {/* Categories & Articles List */}
                <div className="md:col-span-4 space-y-6">
                    <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground opacity-50 px-2">Categorias de Apoio</h2>
                    <div className="space-y-4">
                        {filteredKB?.map((cat) => (
                            <div key={cat.id} className="space-y-2">
                                <div className="flex items-center gap-2 px-2 py-1 text-primary font-bold">
                                    {getIcon(cat.icone)}
                                    <span>{cat.nome}</span>
                                </div>
                                <div className="space-y-1">
                                    {cat.artigos.map(art => (
                                        <button
                                            key={art.id}
                                            onClick={() => setSelectedArticleSlug(art.slug)}
                                            className={`w-full text-left p-3 rounded-sm text-sm font-medium transition-all group flex items-center justify-between
                                                ${selectedArticleSlug === art.slug
                                                    ? 'bg-primary text-primary-foreground shadow-md'
                                                    : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                                                }`}
                                        >
                                            <span className="truncate">{art.titulo}</span>
                                            <ChevronRight size={14} className={`opacity-0 group-hover:opacity-100 ${selectedArticleSlug === art.slug ? 'opacity-100' : ''}`} />
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Article Content */}
                <Card className="md:col-span-8 bg-surface shadow-xl border-none overflow-hidden min-h-[600px] flex flex-col">
                    {selectedArticleSlug ? (
                        isLoadingArticle ? (
                            <CardContent className="p-12 space-y-4">
                                <Skeleton className="h-10 w-3/4" />
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-5/6" />
                                <Skeleton className="h-64 w-full" />
                            </CardContent>
                        ) : (
                            <>
                                <CardHeader className="p-10 border-b bg-muted/5">
                                    <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase mb-4">
                                        <Book size={14} /> Wiki DeepFarms
                                    </div>
                                    <CardTitle className="text-3xl font-black">{activeArticle?.titulo}</CardTitle>
                                    <CardDescription className="text-base mt-2">
                                        Última atualização: {new Date().toLocaleDateString('pt-BR')} • {activeArticle?.visualizacoes} visualizações
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="p-10 prose prose-slate max-w-none dark:prose-invert">
                                    <ReactMarkdown>
                                        {activeArticle?.conteudo || ""}
                                    </ReactMarkdown>

                                    <div className="mt-12 pt-8 border-t border-dashed flex flex-col items-center text-center space-y-4">
                                        <p className="text-sm font-medium text-muted-foreground">Este artigo foi útil?</p>
                                        <div className="flex gap-4">
                                            <Button variant="outline" size="sm" className="rounded-full px-6">Sim, obrigado!</Button>
                                            <Button variant="outline" size="sm" className="rounded-full px-6 text-red-500 hover:text-red-600">Não muito...</Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </>
                        )
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-12 text-center">
                            <Lightbulb size={80} className="mb-6 opacity-10 animate-pulse" />
                            <h3 className="text-xl font-bold text-foreground">Conhecimento é poder!</h3>
                            <p className="max-w-xs mt-2">Selecione um tópico à esquerda ou use a busca acima para encontrar o que precisa.</p>
                        </div>
                    )}
                </Card>
            </div>

            {/* CTA Help */}
            <div className="mt-12 p-8 bg-primary/5 rounded-sm border-2 border-primary/10 flex flex-col md:flex-row items-center justify-between gap-6">
                <div>
                    <h3 className="text-xl font-bold">Ainda precisa de ajuda?</h3>
                    <p className="text-muted-foreground">Fale diretamente com nossa equipe de especialistas através do canal oficial.</p>
                </div>
                <Button variant="outline" size="sm" className="rounded-full px-8 shadow-lg hover:scale-105 transition-transform">
                    <Link href="/settings/support">Falar com o Suporte</Link>
                </Button>
            </div>
        </div>
    );
}
