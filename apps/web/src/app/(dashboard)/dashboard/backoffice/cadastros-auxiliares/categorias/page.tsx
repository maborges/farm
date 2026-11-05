"use client";
import { CategoriasReusable } from "@/components/cadastros/tabelas-reusable/categorias-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { FolderTree } from "lucide-react";

export default function CategoriasBackofficePage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Categorias de Produto"
        description="Estrutura hierárquica global para classificação de insumos e produtos"
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Tabelas do Sistema", href: "/dashboard/backoffice/tabelas" },
          { label: "Categorias" }
        ]}
        icon={<FolderTree className="text-primary" size={22} />}
      />
      <CategoriasReusable mode="backoffice" />
    </div>
  );
}
