"use client";

import { CulturasReusable } from "@/components/cadastros/tabelas-reusable/culturas-reusable";
import { PageHeader } from "@/components/shared/page-header";
import { Sprout } from "lucide-react";

export default function CulturasPage() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Culturas e Variedades"
        description="Gerencie a biblioteca de referências agrícolas para suas safras"
        breadcrumbs={[
          { label: "Agricultura", href: "/agricola" },
          { label: "Cadastros", href: "/agricola/cadastros" },
          { label: "Culturas e Variedades" }
        ]}
        icon={<Sprout className="text-primary" size={22} />}
      />

      <CulturasReusable mode="subscriber" />
    </div>
  );
}

