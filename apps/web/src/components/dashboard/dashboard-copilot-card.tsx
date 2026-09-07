import Link from "next/link";
import { ArrowRight, BrainCircuit } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export type DashboardCopilotCardProps = {
  subtitle: string;
  highlights: string[];
  ctaLabel: string;
  ctaHref: string;
  isLoading?: boolean;
};

export function DashboardCopilotCard({
  subtitle,
  highlights,
  ctaLabel,
  ctaHref,
  isLoading = false,
}: DashboardCopilotCardProps) {
  return (
    <Card className="overflow-hidden border border-primary/15 bg-gradient-to-br from-primary/[0.03] via-background to-background shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <BrainCircuit className="size-4" />
              </div>
              <div>
                <h2 className="text-base font-medium leading-snug text-foreground">Copiloto IA</h2>
                <CardDescription>{subtitle}</CardDescription>
              </div>
            </div>
            <Badge variant="outline" className="rounded-sm border-primary/20 bg-primary/5 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
              Leitura executiva
            </Badge>
          </div>
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href={ctaHref}>
              {ctaLabel}
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="rounded-sm border border-border bg-background p-3">
                <Skeleton className="h-3 w-24 rounded-sm" />
                <Skeleton className="mt-2 h-4 w-full rounded-sm" />
              </div>
            ))}
          </div>
        ) : highlights.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {highlights.map((highlight, index) => (
              <div key={index} className="rounded-sm border border-border bg-background p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Atenção {index + 1}
                </p>
                <p className="mt-1 text-sm text-foreground">{highlight}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-sm border border-dashed border-border bg-background/70 p-4 text-sm text-muted-foreground">
            Nenhuma leitura prioritária consolidada neste momento.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
