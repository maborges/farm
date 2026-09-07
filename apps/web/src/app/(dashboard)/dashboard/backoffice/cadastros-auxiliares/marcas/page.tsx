"use client";
import { MarcasReusable } from "@/components/cadastros/tabelas-reusable/marcas-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { BookmarkCheck } from "lucide-react";

export default function MarcasBackofficePage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Marcas Globais"
        description="Gerencie os fabricantes e marcas disponíveis para todos os assinantes"
        breadcrumbs={[
          { label: "Backoffice", href: "/backoffice" },
          { label: "Cadastros Auxiliares", href: "/backoffice/cadastros-auxiliares" },
          { label: "Marcas" }
        ]}
        icon={<BookmarkCheck className="text-primary" size={22} />}
      />
      <MarcasReusable mode="backoffice" />
    </div>
  );
}
