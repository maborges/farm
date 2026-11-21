"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ClimaDashboardSkeleton(): React.ReactElement {
  return (
    <div className="flex flex-col gap-4" id="skeleton-dashboard">
      {/* Banner de Carregamento Ativo */}
      <Alert variant="default">
        <Loader2 className="size-4 animate-spin text-primary" />
        <AlertDescription className="text-xs">
          Consultando projeção meteorológica para a localidade...
        </AlertDescription>
      </Alert>

      {/* Skeleton Condições Atuais */}
      <Card>
        <CardHeader className="border-b border-border/60">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-3 w-64 mt-1" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="p-4 rounded-sm bg-muted/20 border border-border/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Skeleton className="size-12" />
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="p-3 rounded-sm bg-muted/20 border border-border/50 flex flex-col gap-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-6 w-12" />
                <Skeleton className="h-2 w-20" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Skeleton Horária */}
      <Card>
        <CardHeader className="border-b border-border/60">
          <Skeleton className="h-4 w-40" />
        </CardHeader>
        <CardContent>
          <div className="flex gap-2.5 overflow-hidden">
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <div key={i} className="shrink-0 w-24 p-3 rounded-sm bg-muted/20 border border-border/50 flex flex-col items-center gap-2">
                <Skeleton className="h-3 w-10" />
                <Skeleton className="size-6" />
                <Skeleton className="h-4 w-8" />
                <Skeleton className="h-2 w-12" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Skeleton Diária */}
      <Card>
        <CardHeader className="border-b border-border/60">
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent className="divide-y divide-border/40">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Skeleton className="size-6" />
                <div className="flex flex-col gap-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-2 w-12" />
                </div>
              </div>
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
