"use client";

import React, { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import {
    BookOpen,
    Search,
    HelpCircle,
    Compass,
    Printer,
    Sparkles,
    AlertTriangle,
    ExternalLink,
    X,
    Layers,
    Video,
    ImageIcon,
    LayoutDashboard,
} from "lucide-react";
import { cn } from "@/lib/utils";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import {
    MODULOS,
    GUIAS_POR_MODULO,
    ELEMENTOS_POR_MODULO,
    FAQS_POR_MODULO,
} from "./manual-data";

export default function ManualPage() {
    const [busca, setBusca] = useState("");
    const [moduloAtivo, setModuloAtivo] = useState("00-navegacao");
    const [abaAtiva, setAbaAtiva] = useState<"passo-a-passo" | "elementos" | "faq">("passo-a-passo");
    const [modoMidia, setModoMidia] = useState<"imagem" | "video">("imagem");
    const [etapaVisualIndex, setEtapaVisualIndex] = useState(0);

    // Normalização de texto de busca (remove acentos e espaços extras)
    const termoBusca = useMemo(() => {
        return busca
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    }, [busca]);

    const estaBuscando = termoBusca.length > 0;

    // Função utilitária de busca textual
    const casaBusca = (textos: string[], tags: string[] = []): boolean => {
        if (!estaBuscando) return true;
        const textoCompleto = [...textos, ...tags]
            .join(" ")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase();
        return textoCompleto.includes(termoBusca);
    };

    // Dados ativos conforme o módulo selecionado
    const moduloAtual = useMemo(() => {
        return MODULOS.find((m) => m.id === moduloAtivo) || MODULOS[0];
    }, [moduloAtivo]);

    const etapaAtual = useMemo(() => {
        if (moduloAtual.etapasVisuais && moduloAtual.etapasVisuais.length > 0) {
            return moduloAtual.etapasVisuais[etapaVisualIndex] ?? moduloAtual.etapasVisuais[0];
        }
        return null;
    }, [moduloAtual, etapaVisualIndex]);

    const imagemExibida = etapaAtual ? etapaAtual.imagemUrl : moduloAtual.imagemUrl;

    const guiasAtivos = useMemo(() => {
        return GUIAS_POR_MODULO[moduloAtivo] || GUIAS_POR_MODULO["00-navegacao"];
    }, [moduloAtivo]);

    const elementosAtivos = useMemo(() => {
        return ELEMENTOS_POR_MODULO[moduloAtivo] || ELEMENTOS_POR_MODULO["00-navegacao"];
    }, [moduloAtivo]);

    const faqsAtivas = useMemo(() => {
        return FAQS_POR_MODULO[moduloAtivo] || FAQS_POR_MODULO["00-navegacao"];
    }, [moduloAtivo]);

    // ── Filtragem dos dados em tempo real ───────────────────────────────────
    const guiasFiltrados = useMemo(() => {
        return guiasAtivos.filter((guia) =>
            casaBusca([guia.titulo, ...guia.passos, guia.destaque?.texto ?? ""], guia.tags)
        );
    }, [guiasAtivos, termoBusca]);

    const elementosFiltrados = useMemo(() => {
        return elementosAtivos.filter((item) =>
            casaBusca([item.label, item.descricao, item.local], item.tags)
        );
    }, [elementosAtivos, termoBusca]);

    const faqsFiltradas = useMemo(() => {
        return faqsAtivas.filter((faq) =>
            casaBusca([faq.pergunta, faq.resposta], faq.tags)
        );
    }, [faqsAtivas, termoBusca]);

    const modulosFiltrados = useMemo(() => {
        return MODULOS.filter((mod) =>
            casaBusca([mod.titulo, mod.descricao, mod.numero], mod.tags)
        );
    }, [termoBusca]);

    const totalResultados = guiasFiltrados.length + elementosFiltrados.length + faqsFiltradas.length;

    // Se o usuário estiver pesquisando e a aba atual não tiver resultados, muda para a que tem
    useEffect(() => {
        if (estaBuscando) {
            if (abaAtiva === "passo-a-passo" && guiasFiltrados.length === 0) {
                if (elementosFiltrados.length > 0) setAbaAtiva("elementos");
                else if (faqsFiltradas.length > 0) setAbaAtiva("faq");
            } else if (abaAtiva === "elementos" && elementosFiltrados.length === 0) {
                if (guiasFiltrados.length > 0) setAbaAtiva("passo-a-passo");
                else if (faqsFiltradas.length > 0) setAbaAtiva("faq");
            } else if (abaAtiva === "faq" && faqsFiltradas.length === 0) {
                if (guiasFiltrados.length > 0) setAbaAtiva("passo-a-passo");
                else if (elementosFiltrados.length > 0) setAbaAtiva("elementos");
            }
        }
    }, [estaBuscando, guiasFiltrados.length, elementosFiltrados.length, faqsFiltradas.length, abaAtiva]);

    const ModuloIcon = moduloAtual.icone;

    return (
        <div className="flex flex-1 flex-col gap-6 p-6">
            {/* ── Cabeçalho Principal (Container padrão da aplicação) ─── */}
            <PageHeader
                title="Manual do Usuário & Central de Ajuda"
                description="Consulte o passo a passo ilustrado, tire dúvidas e domine todos os processos da sua fazenda de forma simples."
                icon={<BookOpen className="size-5 text-primary" />}
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Manual do Usuário" },
                ]}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.print()}
                        className="gap-2 rounded-sm text-xs"
                    >
                        <Printer className="size-3.5 text-muted-foreground" />
                        Imprimir / Salvar PDF
                    </Button>
                }
            />

            {/* ── Barra de Pesquisa Rápida ────────────────────────────── */}
            <Card className="rounded-sm border border-primary/20 bg-card shadow-sm">
                <CardContent className="p-4 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                        <Search className="size-3.5" />
                        <span>Pesquisa no Manual da Fazenda</span>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                        <Input
                            placeholder="Digite o que deseja encontrar (ex: 'trocar fazenda', 'talhão', 'adubo', 'trator', 'porteira', 'gmd', 'diesel')..."
                            value={busca}
                            onChange={(e) => setBusca(e.target.value)}
                            className="h-9 text-xs pl-9 pr-9 rounded-sm bg-background border-border/80 focus-visible:ring-primary"
                        />
                        {busca && (
                            <button
                                onClick={() => setBusca("")}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                                aria-label="Limpar busca"
                                title="Limpar busca"
                            >
                                <X className="size-3.5" />
                            </button>
                        )}
                    </div>

                    {estaBuscando && (
                        <div className="flex items-center justify-between text-xs pt-1">
                            <span className="text-muted-foreground">
                                Encontrado(s) <strong>{totalResultados}</strong> resultado(s) no {moduloAtual.numero} para &quot;<strong>{busca}</strong>&quot;:
                            </span>
                            <div className="flex gap-2">
                                <Badge variant="outline" className="text-[10px] rounded-sm py-0">
                                    Guias: {guiasFiltrados.length}
                                </Badge>
                                <Badge variant="outline" className="text-[10px] rounded-sm py-0">
                                    Elementos: {elementosFiltrados.length}
                                </Badge>
                                <Badge variant="outline" className="text-[10px] rounded-sm py-0">
                                    Dúvidas: {faqsFiltradas.length}
                                </Badge>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* ── Seletor de Módulos (Grid Responsivo com os 15 Módulos Ativos) ── */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Módulos da Plataforma ({modulosFiltrados.length} áreas operacionais)
                    </span>
                    <span className="text-xs text-muted-foreground">
                        Clique em qualquer módulo para consultar seus guias e procedimentos
                    </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5">
                    {modulosFiltrados.map((mod) => {
                        const Icon = mod.icone;
                        const isSelected = moduloAtivo === mod.id;
                        return (
                            <button
                                key={mod.id}
                                onClick={() => {
                                    setModuloAtivo(mod.id);
                                    setEtapaVisualIndex(0);
                                }}
                                className={`text-left p-2.5 rounded-sm border transition-all flex flex-col justify-between gap-1.5 cursor-pointer ${isSelected
                                        ? "border-primary bg-primary/10 shadow-sm ring-1 ring-primary/30"
                                        : "border-border bg-card hover:border-primary/40 hover:bg-muted/40"
                                    }`}
                            >
                                <div className="flex items-center justify-between gap-1 w-full">
                                    <div
                                        className={`size-6 rounded-sm flex items-center justify-center shrink-0 ${isSelected ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary"
                                            }`}
                                    >
                                        <Icon className="size-3.5" />
                                    </div>
                                    <Badge
                                        variant="default"
                                        className="text-[8px] px-1 py-0 rounded-sm font-semibold uppercase bg-emerald-600 text-white"
                                    >
                                        Ativo
                                    </Badge>
                                </div>
                                <div>
                                    <p className="text-[9px] text-muted-foreground font-semibold uppercase tracking-wider">
                                        {mod.numero}
                                    </p>
                                    <p className="text-[11px] font-bold text-foreground leading-tight line-clamp-1">
                                        {mod.titulo}
                                    </p>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* ── CONTEÚDO DO MÓDULO SELECIONADO ───────────────────────── */}
            <div className="space-y-6">
                {/* Banner do Módulo */}
                <div className="bg-card border rounded-sm p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-[10px] font-bold uppercase rounded-sm border-primary/40 text-primary">
                                {moduloAtual.numero}
                            </Badge>
                            <span className="text-xs text-muted-foreground">Guia Operacional Prático</span>
                        </div>
                        <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
                            <ModuloIcon className="size-5 text-primary" />
                            {moduloAtual.titulo}
                        </h2>
                        <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl leading-relaxed">
                            {moduloAtual.descricao}
                        </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                        <Button asChild variant="outline" size="sm" className="rounded-sm text-xs gap-1.5">
                            <Link href={moduloAtual.rota}>
                                <ExternalLink className="size-3.5 text-primary" />
                                {moduloAtual.btnTexto}
                            </Link>
                        </Button>
                    </div>
                </div>

                {/* Abas de Navegação Interna do Módulo com Ícones Padronizados Lucide */}
                <Tabs value={abaAtiva} onValueChange={(v) => setAbaAtiva(v as typeof abaAtiva)} className="w-full">
                    <TabsList className="bg-muted/40 p-1 rounded-sm border w-full sm:w-auto grid grid-cols-3 sm:inline-flex h-auto gap-1">
                        <TabsTrigger
                            value="passo-a-passo"
                            className="text-xs py-1.5 px-3 rounded-sm gap-2 data-[state=active]:bg-card data-[state=active]:shadow-sm"
                        >
                            <BookOpen className="size-3.5 text-primary" />
                            <span>Guias Passo a Passo</span>
                            {estaBuscando && (
                                <Badge variant="secondary" className="text-[9px] py-0 px-1 rounded-sm">
                                    {guiasFiltrados.length}
                                </Badge>
                            )}
                        </TabsTrigger>
                        <TabsTrigger
                            value="elementos"
                            className="text-xs py-1.5 px-3 rounded-sm gap-2 data-[state=active]:bg-card data-[state=active]:shadow-sm"
                        >
                            <Compass className="size-3.5 text-primary" />
                            <span>A Tela e Seus Recursos</span>
                            {estaBuscando && (
                                <Badge variant="secondary" className="text-[9px] py-0 px-1 rounded-sm">
                                    {elementosFiltrados.length}
                                </Badge>
                            )}
                        </TabsTrigger>
                        <TabsTrigger
                            value="faq"
                            className="text-xs py-1.5 px-3 rounded-sm gap-2 data-[state=active]:bg-card data-[state=active]:shadow-sm"
                        >
                            <HelpCircle className="size-3.5 text-primary" />
                            <span>Dúvidas e Soluções</span>
                            {estaBuscando && (
                                <Badge variant="secondary" className="text-[9px] py-0 px-1 rounded-sm">
                                    {faqsFiltradas.length}
                                </Badge>
                            )}
                        </TabsTrigger>
                    </TabsList>

                    {/* ── ABA 1: GUIAS PASSO A PASSO ────────────────────── */}
                    <TabsContent value="passo-a-passo" className="space-y-4 mt-4">
                        {/* Destaque específico do Módulo 00 (A Estrutura em 3 Níveis) */}
                        {moduloAtivo === "00-navegacao" && !estaBuscando && (
                            <Card className="rounded-sm border shadow-sm">
                                <CardHeader className="pb-3 border-b bg-muted/20">
                                    <div className="flex items-center gap-2">
                                        <Layers className="size-4 text-primary" />
                                        <CardTitle className="text-sm font-bold">
                                            O Conceito Mais Importante: Os 3 Níveis da Sua Fazenda
                                        </CardTitle>
                                    </div>
                                    <CardDescription className="text-xs">
                                        Para nunca misturar contas, compras ou animais de propriedades diferentes, a DeepFarms trabalha com 3 níveis:
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <div className="border rounded-sm p-3.5 bg-card space-y-1.5 relative overflow-hidden">
                                        <div className="flex items-center gap-2">
                                            <span className="size-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 text-xs font-bold flex items-center justify-center">1</span>
                                            <h4 className="text-xs font-bold uppercase text-foreground">O Assinante</h4>
                                        </div>
                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                            É <strong>você</strong>, a pessoa com e-mail e senha de acesso.
                                        </p>
                                    </div>

                                    <div className="border rounded-sm p-3.5 bg-card space-y-1.5 relative overflow-hidden">
                                        <div className="flex items-center gap-2">
                                            <span className="size-5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 text-xs font-bold flex items-center justify-center">2</span>
                                            <h4 className="text-xs font-bold uppercase text-foreground">O Produtor (Maleta)</h4>
                                        </div>
                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                            É o <strong>grupo familiar, empresa ou CPF/CNPJ</strong> titular da conta (ex: <em>Grupo AgroSaaS</em>).
                                        </p>
                                    </div>

                                    <div className="border rounded-sm p-3.5 bg-card space-y-1.5 relative overflow-hidden border-emerald-500/40 bg-emerald-50/20 dark:bg-emerald-950/10">
                                        <div className="flex items-center gap-2">
                                            <span className="size-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 text-xs font-bold flex items-center justify-center">3</span>
                                            <h4 className="text-xs font-bold uppercase text-emerald-700 dark:text-emerald-400">Contexto Ativo (A Fazenda)</h4>
                                        </div>
                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                            É a <strong>fazenda física onde você está trabalhando agora</strong> (ex: <em>Terra Nostra</em>). Ao trocar aqui, você entra na porteira daquela fazenda.
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Acordeão com os Processos Operacionais Filtrados */}
                        {guiasFiltrados.length === 0 ? (
                            <Card className="p-8 text-center text-xs text-muted-foreground rounded-sm border">
                                <p>Nenhum guia passo a passo corresponde a &quot;<strong>{busca}</strong>&quot; no {moduloAtual.numero}.</p>
                                <Button variant="outline" size="sm" onClick={() => setBusca("")} className="mt-3 text-xs rounded-sm">
                                    Limpar busca
                                </Button>
                            </Card>
                        ) : (
                            <Accordion type="single" collapsible defaultValue={guiasFiltrados[0]?.id} className="space-y-2">
                                {guiasFiltrados.map((guia) => (
                                    <AccordionItem key={guia.id} value={guia.id} className="border rounded-sm bg-card px-4 shadow-sm">
                                        <AccordionTrigger className="text-xs sm:text-sm font-bold text-left hover:no-underline py-3.5">
                                            <span className="flex items-center gap-2">
                                                <span className="size-5 rounded-full bg-primary/10 text-primary text-xs flex items-center justify-center font-bold">
                                                    {guia.numero}
                                                </span>
                                                <span>{guia.titulo}</span>
                                            </span>
                                        </AccordionTrigger>
                                        <AccordionContent className="text-xs text-muted-foreground space-y-3 pb-4 pt-1 border-t">
                                            <ol className="space-y-2 list-decimal pl-4">
                                                {guia.passos.map((passo, idx) => (
                                                    <li key={idx} className="leading-relaxed">
                                                        {passo}
                                                    </li>
                                                ))}
                                            </ol>

                                            {guia.destaque && (
                                                <div
                                                    className={`p-3 rounded-sm border text-xs flex items-start gap-2.5 ${guia.destaque.tipo === "alerta"
                                                            ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/40 text-amber-900 dark:text-amber-200"
                                                            : "bg-muted/50 border-border text-foreground"
                                                        }`}
                                                >
                                                    {guia.destaque.tipo === "alerta" ? (
                                                        <AlertTriangle className="size-4 shrink-0 text-amber-600 mt-0.5" />
                                                    ) : (
                                                        <Sparkles className="size-4 shrink-0 text-primary mt-0.5" />
                                                    )}
                                                    <span className="leading-relaxed">{guia.destaque.texto}</span>
                                                </div>
                                            )}
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        )}
                    </TabsContent>

                    {/* ── ABA 2: A TELA, SEUS BOTÕES E VÍDEOS ─────────────── */}
                    <TabsContent value="elementos" className="space-y-4 mt-4">
                        <Card className="rounded-sm border shadow-sm overflow-hidden">
                            <CardHeader className="bg-muted/30 border-b pb-3">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                    <div>
                                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                                            <Compass className="size-4 text-primary" />
                                            A Tela e Seus Recursos — {moduloAtual.titulo}
                                        </CardTitle>
                                        <CardDescription className="text-xs">
                                            Conheça os botões, indicadores e áreas de operação em {moduloAtual.titulo}:
                                        </CardDescription>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {/* Alternador de Mídia se houver imagem ou vídeo configurado */}
                                        {moduloAtual.videoUrl && (
                                            <div className="flex rounded-sm border bg-background p-0.5">
                                                <button
                                                    onClick={() => setModoMidia("imagem")}
                                                    className={`text-[10px] px-2 py-0.5 rounded-sm flex items-center gap-1 ${modoMidia === "imagem" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground"
                                                        }`}
                                                >
                                                    <ImageIcon className="size-3" />
                                                    Print
                                                </button>
                                                <button
                                                    onClick={() => setModoMidia("video")}
                                                    className={`text-[10px] px-2 py-0.5 rounded-sm flex items-center gap-1 ${modoMidia === "video" ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground"
                                                        }`}
                                                >
                                                    <Video className="size-3" />
                                                    Vídeo
                                                </button>
                                            </div>
                                        )}
                                        <Badge variant="outline" className="text-[10px] rounded-sm py-0.5">
                                            {elementosFiltrados.length} recursos mapeados
                                        </Badge>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-4 sm:p-6 space-y-5">
                                {/* Player de Vídeo ou Imagem da Aplicação */}
                                {modoMidia === "video" && moduloAtual.videoUrl ? (
                                    <div className="border rounded-sm overflow-hidden shadow-sm bg-black">
                                        <video
                                            src={moduloAtual.videoUrl}
                                            controls
                                            poster={moduloAtual.imagemUrl}
                                            className="w-full max-h-[480px] object-contain mx-auto"
                                        >
                                            {moduloAtual.legendaUrl && (
                                                <track
                                                    src={moduloAtual.legendaUrl}
                                                    kind="subtitles"
                                                    srcLang="pt-BR"
                                                    label="Português"
                                                    default
                                                />
                                            )}
                                        </video>
                                    </div>
                                ) : imagemExibida ? (
                                    <div className="space-y-3">
                                        {/* Seletor de Etapas do Processo / Fluxo com Dialog */}
                                        {moduloAtual.etapasVisuais && moduloAtual.etapasVisuais.length > 1 && (
                                            <div className="space-y-2">
                                                <div className="flex flex-wrap items-center gap-1.5 p-1 bg-muted/40 rounded-sm border">
                                                    {moduloAtual.etapasVisuais.map((etapa, idx) => {
                                                        const isAtiva = idx === etapaVisualIndex;
                                                        return (
                                                            <button
                                                                key={etapa.id}
                                                                onClick={() => setEtapaVisualIndex(idx)}
                                                                className={cn(
                                                                    "text-xs px-2.5 py-1 rounded-sm font-medium transition-all flex items-center gap-1.5 cursor-pointer",
                                                                    isAtiva
                                                                        ? "bg-primary text-primary-foreground shadow-sm"
                                                                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                                                                )}
                                                            >
                                                                {etapa.tipo === "dialog" ? (
                                                                    <Layers className="size-3" />
                                                                ) : (
                                                                    <LayoutDashboard className="size-3" />
                                                                )}
                                                                {etapa.titulo}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                                {etapaAtual && (
                                                    <div className="text-xs text-muted-foreground bg-muted/20 border-l-2 border-primary pl-3 py-1.5 rounded-r-sm">
                                                        <strong className="text-foreground">{etapaAtual.titulo}:</strong> {etapaAtual.descricao}
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        <div className="border rounded-sm overflow-hidden shadow-sm bg-background">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img
                                                src={imagemExibida}
                                                alt={etapaAtual ? etapaAtual.titulo : `Tela de ${moduloAtual.titulo}`}
                                                className="w-full h-auto object-cover"
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="border border-dashed rounded-sm p-6 text-center space-y-2 bg-muted/10">
                                        <ModuloIcon className="size-8 mx-auto text-primary/70" />
                                        <p className="text-xs font-bold text-foreground">
                                            {moduloAtual.titulo} ({moduloAtual.numero})
                                        </p>
                                        <p className="text-xs text-muted-foreground max-w-md mx-auto">
                                            {moduloAtual.descricao}
                                        </p>
                                    </div>
                                )}

                                {/* Guia Visual dos Botões Filtrados */}
                                {elementosFiltrados.length === 0 ? (
                                    <div className="p-6 text-center text-xs text-muted-foreground rounded-sm border">
                                        <p>Nenhum elemento da tela corresponde a &quot;<strong>{busca}</strong>&quot; no {moduloAtual.numero}.</p>
                                        <Button variant="outline" size="sm" onClick={() => setBusca("")} className="mt-2 text-xs rounded-sm">
                                            Limpar busca
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                                            O que faz cada botão e indicador desta tela:
                                        </h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                                            {elementosFiltrados.map((item) => {
                                                const Icon = item.icone;
                                                return (
                                                    <div key={item.id} className="border rounded-sm p-3 bg-muted/20 space-y-1">
                                                        <div className="flex items-center justify-between gap-1.5 font-bold text-foreground">
                                                            <div className="flex items-center gap-1.5">
                                                                <Icon className="size-3.5 text-primary" />
                                                                <span>{item.label}</span>
                                                            </div>
                                                            <Badge variant="outline" className="text-[9px] py-0 px-1 rounded-sm text-muted-foreground">
                                                                {item.local}
                                                            </Badge>
                                                        </div>
                                                        <p className="text-muted-foreground leading-relaxed">
                                                            {item.descricao}
                                                        </p>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* ── ABA 3: PERGUNTAS FREQUENTES & DÚVIDAS ─────────── */}
                    <TabsContent value="faq" className="space-y-4 mt-4">
                        <Card className="rounded-sm border shadow-sm">
                            <CardHeader className="pb-3 border-b bg-muted/20">
                                <div className="flex items-center gap-2">
                                    <HelpCircle className="size-4 text-primary" />
                                    <CardTitle className="text-sm font-bold">
                                        Dúvidas Frequentes & O Que Deu Errado? ({moduloAtual.numero})
                                    </CardTitle>
                                </div>
                                <CardDescription className="text-xs">
                                    Respostas práticas e diretas para situações comuns do dia a dia neste módulo:
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="p-4">
                                {faqsFiltradas.length === 0 ? (
                                    <div className="text-center py-8 text-xs text-muted-foreground space-y-2">
                                        <Search className="size-6 mx-auto text-muted-foreground/60" />
                                        <p>Nenhuma dúvida encontrada para &quot;<strong>{busca}</strong>&quot; no {moduloAtual.numero}.</p>
                                        <Button variant="outline" size="sm" onClick={() => setBusca("")} className="text-xs rounded-sm">
                                            Limpar pesquisa
                                        </Button>
                                    </div>
                                ) : (
                                    <Accordion type="single" collapsible defaultValue={faqsFiltradas[0]?.id} className="space-y-2">
                                        {faqsFiltradas.map((faq) => (
                                            <AccordionItem
                                                key={faq.id}
                                                value={faq.id}
                                                className="border rounded-sm bg-card px-4 shadow-sm"
                                            >
                                                <AccordionTrigger className="text-xs sm:text-sm font-bold text-left hover:no-underline py-3.5">
                                                    {faq.pergunta}
                                                </AccordionTrigger>
                                                <AccordionContent className="text-xs text-muted-foreground leading-relaxed pb-4 pt-1 border-t space-y-2">
                                                    <p className="leading-relaxed">{faq.resposta}</p>
                                                    <div className="flex flex-wrap gap-1 pt-1">
                                                        {faq.tags.map((tag) => (
                                                            <Badge key={tag} variant="outline" className="text-[9px] py-0 px-1 text-muted-foreground/70 rounded-sm">
                                                                #{tag}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </AccordionContent>
                                            </AccordionItem>
                                        ))}
                                    </Accordion>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    );
}
