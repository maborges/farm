"use client";

import Link from "next/link";
import {
  BookOpen, Package, Users, Building2, ArrowRight, Layers,
  Tractor, Map, Wheat, Trees, Wrench,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";

const cards = [
  {
    href: "/cadastros/pessoas",
    icon: Users,
    title: "Pessoas & Parceiros",
    description: "Fornecedores, clientes, prestadores e colaboradores — base única com documentos, contatos e LGPD.",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    href: "/cadastros/produtos",
    icon: Package,
    title: "Catálogo de Produtos",
    description: "Insumos, sementes, defensivos, peças, combustíveis e serviços — catálogo unificado (almoxarifado → despesa).",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  {
    href: "/cadastros/propriedades-econ",
    icon: Trees,
    title: "Produtores",
    description: "Gestão de produtores rurais com explorações, fazendas vinculadas e hierarquia de áreas (glebas, talhões, piquetes).",
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    href: "/cadastros/propriedades",
    icon: Map,
    title: "Unidades Produtivas",
    description: "Operações, sedes, localização operacional e estrutura de áreas vinculadas à unidade produtiva.",
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  {
    href: "/cadastros/equipamentos",
    icon: Tractor,
    title: "Equipamentos & Frota",
    description: "Tratores, colhedoras, veículos e implementos — cadastro unificado usado por manutenção e operações.",
    color: "text-orange-600",
    bg: "bg-orange-50",
  },
  {
    href: "/cadastros/commodities",
    icon: Wheat,
    title: "Commodities",
    description: "Produtos de saída e receita: soja, milho, leite, gado — padrões de qualidade por IN/MAPA.",
    color: "text-lime-600",
    bg: "bg-lime-50",
  },
  {
    href: "/cadastros/tipos-servico",
    icon: Wrench,
    title: "Tipos de Serviço",
    description: "Serviços terceirizados (aplicação, colheita, transporte) com custo de referência para o orçamento de safra.",
    color: "text-cyan-600",
    bg: "bg-cyan-50",
  },
  {
    href: "/cadastros/centros-custo",
    icon: Layers,
    title: "Centros de Custo",
    description: "Estrutura de rateio financeiro — departamentos, projetos e safras.",
    color: "text-violet-600",
    bg: "bg-violet-50",
  },
  {
    href: "/unidades-produtivas",
    icon: Building2,
    title: "Fazendas & Unidades",
    description: "Propriedades, grupos de fazendas e unidades produtivas do produtor.",
    color: "text-slate-600",
    bg: "bg-slate-50",
  },
];

export default function CadastrosPage() {
  return (
    <div className="p-6 space-y-8 max-w-4xl mx-auto w-full">
      <PageHeader
        title="Cadastros"
        description="Dados mestres compartilhados entre todos os módulos do sistema."
        icon={<BookOpen className="text-primary" size={24} />}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {cards.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card className="h-full shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className={cn("p-2.5 rounded-sm", card.bg)}>
                    <card.icon className={cn("size-5", card.color)} />
                  </div>
                  <ArrowRight
                    size={16}
                    className="text-muted-foreground group-hover:translate-x-0.5 transition-transform mt-1"
                  />
                </div>
                <CardTitle className="text-base mt-3">{card.title}</CardTitle>
                <CardDescription className="text-xs">{card.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
