import Link from "next/link";
import {
  BrainCircuit,
  CalendarClock,
  DollarSign,
  Droplets,
  Lock,
  Tractor,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";

interface FrotaToolbarProps {
  hasProfessionalTier: boolean;
  hasEnterpriseTier: boolean;
}

export function FrotaToolbar({
  hasProfessionalTier,
  hasEnterpriseTier,
}: FrotaToolbarProps) {
  return (
    <>
      <Button asChild variant="outline" size="sm">
        <Link href="/cadastros/equipamentos">
          <Tractor className="size-3.5" />
          Equipamentos
        </Link>
      </Button>
      <Button asChild variant="outline" size="sm">
        <Link href="/dashboard/operacional/manutencoes">
          <Wrench className="size-3.5" />
          Manutenções
        </Link>
      </Button>
      {hasProfessionalTier ? (
        <>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/manutencao-preventiva">
              <CalendarClock className="size-3.5" />
              Preventiva
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/consumo">
              <Droplets className="size-3.5" />
              Consumo
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/custos">
              <DollarSign className="size-3.5" />
              Custos
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/jornadas">
              <CalendarClock className="size-3.5" />
              Jornadas
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/disponibilidade">
              <Lock className="size-3.5" />
              Disponibilidade
            </Link>
          </Button>
        </>
      ) : null}
      {hasEnterpriseTier ? (
        <>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/inteligencia">
              <BrainCircuit className="size-3.5" />
              Inteligência
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/operacional/frota/agricultura">
              <Tractor className="size-3.5" />
              Uso agrícola
            </Link>
          </Button>
        </>
      ) : null}
    </>
  );
}
