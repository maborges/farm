import { Tractor } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Card, CardContent } from "@/components/ui/card";

export function FrotaEmptyState() {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardContent className="p-6">
        <EmptyState
          icon={<Tractor />}
          title="Nenhum equipamento cadastrado"
          description="Cadastre equipamentos para começar a acompanhar custos, ordens de serviço e riscos operacionais."
          action={{ label: "Ir para cadastros", href: "/cadastros/equipamentos" }}
        />
      </CardContent>
    </Card>
  );
}
