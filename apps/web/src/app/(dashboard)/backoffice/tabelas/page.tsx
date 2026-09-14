import Link from "next/link";
import { Sprout, Wheat, ClipboardList, Bug, Table2, CheckSquare } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";

const TABELAS = [
  {
    href: "/backoffice/tabelas/culturas",
    icon: Sprout,
    title: "Culturas",
    description: "Culturas agrícolas disponíveis para uso em safras (soja, milho, café...)",
  },
  {
    href: "/backoffice/tabelas/commodities",
    icon: Wheat,
    title: "Commodities",
    description: "Produtos de saída da produção rural com parâmetros de qualidade MAPA",
  },
  {
    href: "/backoffice/tabelas/agro-templates",
    icon: ClipboardList,
    title: "Templates Agrícolas",
    description: "Governança (Checklist/Gates) e Operações (OS) pré-definidas por cultura",
  },
  {
    href: "/backoffice/tabelas/monitoramento-catalogo",
    icon: Bug,
    title: "Catálogo de Monitoramento",
    description: "Pragas, doenças e plantas daninhas com NDE padrão por cultura",
  },
  {
    href: "/backoffice/tabelas/tipos-operacao",
    icon: CheckSquare,
    title: "Tipos de Operação",
    description: "Tipos agrícolas persistidos no banco com fases permitidas para uso nas telas de operação",
  },
];

export default function BackofficeTabelasPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Tabelas Padrão do Sistema"
        description="Registros globais disponíveis para consulta e uso em todos os produtores do sistema."
        breadcrumbs={[
          { label: "Backoffice", href: "/backoffice" },
          { label: "Tabelas Padrão" }
        ]}
        icon={<Table2 className="text-primary" size={22} />}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-4">
        {TABELAS.map((t) => (
          <Link key={t.href} href={t.href}>
            <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full group border-muted-foreground/10 bg-card/50">
              <CardHeader className="flex flex-row items-start gap-4 p-5">
                <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <t.icon className="size-5" />
                </div>
                <div className="space-y-1">
                  <CardTitle className="text-base font-semibold group-hover:text-primary transition-colors">{t.title}</CardTitle>
                  <CardDescription className="text-xs leading-relaxed text-muted-foreground">{t.description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
