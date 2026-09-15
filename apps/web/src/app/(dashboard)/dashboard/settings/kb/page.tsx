"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
    BookOpen, ChevronRight, CircleHelp, FileText, HandCoins, Lightbulb,
    Package, Search, ShieldCheck, Sprout, Tractor, UsersRound,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";

interface KBArticle {
    id: string;
    titulo: string;
    slug: string;
    conteudo: string;
    visualizacoes: number;
    updated_at: string;
}

interface KBCategory {
    id: string;
    nome: string;
    icone: string | null;
    artigos: KBArticle[];
}

const categoryIcons: Record<string, LucideIcon> = {
    BookOpen,
    HandCoins,
    Lightbulb,
    Package,
    ShieldCheck,
    Sprout,
    Tractor,
    UsersRound,
};

function formatDate(value: string): string {
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(new Date(value));
}

export default function KnowledgeBasePage() {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedArticleSlug, setSelectedArticleSlug] = useState<string | null>(null);
    const normalizedSearch = searchTerm.trim().toLocaleLowerCase("pt-BR");

    const { data: categories = [], isLoading, isError, refetch } = useQuery<KBCategory[]>({
        queryKey: ["kb", "public"],
        queryFn: () => apiFetch("/kb/categories"),
    });

    const filteredCategories = useMemo(() => categories
        .map((category) => ({
            ...category,
            artigos: category.artigos.filter((article) => !normalizedSearch
                || category.nome.toLocaleLowerCase("pt-BR").includes(normalizedSearch)
                || article.titulo.toLocaleLowerCase("pt-BR").includes(normalizedSearch)
                || article.conteudo.toLocaleLowerCase("pt-BR").includes(normalizedSearch)),
        }))
        .filter((category) => category.artigos.length > 0), [categories, normalizedSearch]);

    const selectedArticle = useMemo(() => filteredCategories
        .flatMap((category) => category.artigos)
        .find((article) => article.slug === selectedArticleSlug) ?? null,
    [filteredCategories, selectedArticleSlug]);

    useEffect(() => {
        if (!selectedArticle && filteredCategories[0]?.artigos[0]) {
            setSelectedArticleSlug(filteredCategories[0].artigos[0].slug);
        }
    }, [filteredCategories, selectedArticle]);

    const articleCount = categories.reduce((total, category) => total + category.artigos.length, 0);

    if (isLoading) {
        return (
            <div className="flex flex-col gap-6 p-6 lg:p-8">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-12 w-full max-w-2xl" />
                <Skeleton className="h-[560px] w-full" />
            </div>
        );
    }

    return (
        <div className="flex w-full max-w-full flex-col gap-6 p-6 lg:p-8">
            <PageHeader
                title="Base de Conhecimento"
                description="Guias práticos para configurar, planejar, executar e acompanhar a operação."
                icon={<BookOpen className="text-primary" size={22} />}
            />

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <Card><CardHeader className="gap-1 p-4"><CardDescription>Tópicos disponíveis</CardDescription><CardTitle className="text-2xl">{categories.length}</CardTitle></CardHeader></Card>
                <Card><CardHeader className="gap-1 p-4"><CardDescription>Guias e tutoriais</CardDescription><CardTitle className="text-2xl">{articleCount}</CardTitle></CardHeader></Card>
                <Card className="md:col-span-2 xl:col-span-1"><CardHeader className="gap-1 p-4"><CardDescription>Como usar</CardDescription><CardTitle className="text-sm">Escolha um tópico ou pesquise uma tarefa</CardTitle></CardHeader></Card>
            </div>

            <div className="relative w-full max-w-3xl">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input aria-label="Pesquisar na Base de Conhecimento" placeholder="Ex.: cadastrar talhão, importar XML, registrar pesagem" className="pl-9" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} />
            </div>

            {isError ? (
                <Alert variant="destructive"><CircleHelp /><AlertTitle>Não foi possível carregar a Base de Conhecimento</AlertTitle><AlertDescription className="flex flex-wrap items-center gap-3">Verifique sua conexão e tente novamente.<Button size="sm" variant="outline" onClick={() => refetch()}>Tentar novamente</Button></AlertDescription></Alert>
            ) : categories.length === 0 ? (
                <Alert><BookOpen /><AlertTitle>A Base de Conhecimento está sendo preparada</AlertTitle><AlertDescription>Os guias ainda não foram publicados. Enquanto isso, a equipe pode usar o canal de suporte para obter ajuda.</AlertDescription></Alert>
            ) : (
                <div className="grid min-h-[560px] gap-5 lg:grid-cols-[minmax(280px,0.8fr)_minmax(0,2fr)]">
                    <Card className="overflow-hidden">
                        <CardHeader className="border-b p-4"><CardTitle className="text-base">Navegue por tópico</CardTitle><CardDescription>Conteúdos organizados pela rotina da fazenda.</CardDescription></CardHeader>
                        <ScrollArea className="h-[500px] lg:h-[640px]"><CardContent className="flex flex-col gap-5 p-4">
                            {filteredCategories.map((category) => {
                                const Icon = categoryIcons[category.icone ?? ""] ?? FileText;
                                return <section key={category.id} className="flex flex-col gap-2">
                                    <div className="flex items-center gap-2 text-sm font-semibold"><Icon className="size-4 text-primary" />{category.nome}</div>
                                    <div className="flex flex-col gap-1">{category.artigos.map((article) => (
                                        <Button key={article.id} variant={selectedArticleSlug === article.slug ? "secondary" : "ghost"} className="h-auto justify-between whitespace-normal px-3 py-2 text-left text-sm" onClick={() => setSelectedArticleSlug(article.slug)}><span>{article.titulo}</span><ChevronRight data-icon="inline-end" /></Button>
                                    ))}</div>
                                </section>;
                            })}
                            {filteredCategories.length === 0 ? <p className="text-sm text-muted-foreground">Nenhum guia corresponde à sua busca.</p> : null}
                        </CardContent></ScrollArea>
                    </Card>

                    <Card className="overflow-hidden">
                        {selectedArticle ? <>
                            <CardHeader className="border-b p-6"><CardDescription>Guia da Base de Conhecimento</CardDescription><CardTitle className="text-2xl">{selectedArticle.titulo}</CardTitle><CardDescription>Atualizado em {formatDate(selectedArticle.updated_at)} · {selectedArticle.visualizacoes} visualizações</CardDescription></CardHeader>
                            <ScrollArea className="h-[500px] lg:h-[640px]"><CardContent className="prose max-w-none p-6 dark:prose-invert"><ReactMarkdown>{selectedArticle.conteudo}</ReactMarkdown></CardContent></ScrollArea>
                        </> : <CardContent className="flex h-full min-h-[500px] flex-col items-center justify-center gap-3 p-8 text-center"><Search className="size-10 text-muted-foreground" /><CardTitle>Nenhum guia encontrado</CardTitle><CardDescription>Tente outra palavra ou navegue pelos tópicos disponíveis.</CardDescription></CardContent>}
                    </Card>
                </div>
            )}

            <Card><CardHeader className="flex-row items-center justify-between gap-4 p-5"><div className="flex flex-col gap-1"><CardTitle className="text-base">Ainda precisa de ajuda?</CardTitle><CardDescription>Descreva a situação para que a equipe de suporte possa orientar você.</CardDescription></div><Button asChild size="sm" variant="outline"><Link href="/dashboard/settings/support">Falar com o suporte</Link></Button></CardHeader></Card>
        </div>
    );
}
