import { Briefcase } from "lucide-react";
import { CarteiraClient } from "@/components/carteira/carteira-client";
import { PageHeader } from "@/components/shared/page-header";

export default function CarteiraPage() {
    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Carteira de Propriedades"
                description="Visão consolidada das contas e fazendas vinculadas ao seu perfil, com acesso rápido em 1 clique."
                icon={<Briefcase className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Carteira" }]}
            />
            <CarteiraClient />
        </div>
    );
}
