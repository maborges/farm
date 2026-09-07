"use client";

import { Fuel, Plus, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { useState } from "react";
import { AbastecimentoFormModal } from "./abastecimento-form-modal";

export function AbastecimentoHeader() {
    const [isAddOpen, setIsAddOpen] = useState(false);

    return (
        <>
            <PageHeader
                title="Abastecimentos"
                description="Gestão de combustível, lubrificantes e consumo da frota agrícola."
                breadcrumbs={[
                    { label: "Operacional", href: "/operacional" },
                    { label: "Abastecimentos" }
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" className="h-8 border-dashed">
                            <Filter className="size-3.5 mr-1.5" /> Filtrar
                        </Button>
                        <Button size="sm" className="h-8" onClick={() => setIsAddOpen(true)}>
                            <Plus className="size-3.5 mr-1.5" /> Novo Registro
                        </Button>
                    </div>
                }
            />

            <AbastecimentoFormModal 
                open={isAddOpen} 
                onOpenChange={setIsAddOpen} 
            />
        </>
    );
}
