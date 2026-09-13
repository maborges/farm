"use client";

import Link from "next/link";
import { BookOpen, BrainCircuit, ClipboardCheck, Package, Sprout } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";

const TUTORIAIS = [
  { title: "Comece pela Visão do Dia", description: "Entenda alertas, pendências e os indicadores prioritários.", href: "/dashboard", icon: BrainCircuit },
  { title: "Organize uma safra", description: "Crie a safra, acompanhe fases e registre operações agrícolas.", href: "/agricola/safras", icon: Sprout },
  { title: "Registre uma tarefa de campo", description: "Acompanhe execução, responsáveis e pendências operacionais.", href: "/dashboard/operacional/campo/tarefas", icon: ClipboardCheck },
  { title: "Controle seu estoque", description: "Consulte saldos, movimentações e itens que precisam de reposição.", href: "/suprimentos/estoque", icon: Package },
];

export default function AprendizadoPage() {
  return <div className="flex flex-1 flex-col gap-6 p-6"><PageHeader title="Aprendizado" description="Guias rápidos para tirar mais proveito do DeepFarms." icon={<BookOpen className="text-primary" size={22} />} breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Aprendizado" }]} /><div className="grid gap-4 sm:grid-cols-2">{TUTORIAIS.map(({ title, description, href, icon: Icon }) => <article key={href} className="rounded-sm border bg-card p-5 shadow-sm"><Icon className="mb-4 size-6 text-primary" aria-hidden="true" /><h2 className="text-base font-semibold">{title}</h2><p className="mt-1 min-h-10 text-sm text-muted-foreground">{description}</p><Button asChild variant="outline" size="sm" className="mt-4"><Link href={href}>Abrir tela</Link></Button></article>)}</div><div className="rounded-sm border border-dashed p-5 text-sm text-muted-foreground"><p className="font-medium text-foreground">Dica contextual</p><p className="mt-1">Use o menu Adicionar no topo para iniciar os cadastros mais comuns sem sair do fluxo atual.</p></div></div>;
}

