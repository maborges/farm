"use client";

import { useState } from "react";
import { Smartphone, Plus } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { DispositivosTable } from "@/components/campo/dispositivos-table";
import { DispositivoDialog } from "@/components/campo/dispositivo-dialog";

export default function DispositivosPage() {
  const [open, setOpen] = useState(false);

  return (
    <div className="p-4 md:p-8 space-y-6">
      <PageHeader
        title="Dispositivos de Campo"
        description="Gerencie tablets e celulares dos operadores de campo."
        icon={<Smartphone className="size-5 text-primary" />}
        breadcrumbs={[
          { label: "Operacional", href: "/dashboard/operacional" },
          { label: "Campo", href: "/dashboard/operacional/campo/tarefas" },
          { label: "Dispositivos" },
        ]}
        actions={
          <Button 
            onClick={() => setOpen(true)} 
            variant="outline"
            size="sm" 
            className="gap-2 rounded-sm"
          >
            <Plus className="size-4" />
            Novo dispositivo
          </Button>
        }
      />
      
      <DispositivosTable />
      
      <DispositivoDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
