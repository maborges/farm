"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DispositivosTable } from "@/components/campo/dispositivos-table";
import { DispositivoDialog } from "@/components/campo/dispositivo-dialog";
import { Plus } from "lucide-react";

export function DispositivosClient() {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setOpen(true)} size="sm" className="gap-2">
          <Plus className="size-4" />
          Novo Dispositivo
        </Button>
      </div>
      <DispositivosTable />
      <DispositivoDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
