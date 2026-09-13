"use client";

import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type SectionShellProps = {
  title: string;
  description: string;
  action?: ReactNode;
  children: ReactNode;
};

export function SectionShell({ title, description, action, children }: SectionShellProps) {
  return (
    <Card className="overflow-hidden border border-border/60 bg-card shadow-premium">
      <CardHeader className="pb-4 border-b border-border/40 bg-muted/10">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <CardTitle className="text-xl font-light text-foreground">{title}</CardTitle>
            <CardDescription className="text-xs font-medium text-muted-foreground/80">{description}</CardDescription>
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export type SectionSkeletonProps = {
  cards?: number;
  columnsClassName: string;
};

export function SectionSkeleton({ cards = 4, columnsClassName }: SectionSkeletonProps) {
  return (
    <div className={cn("grid gap-4", columnsClassName)}>
      {Array.from({ length: cards }).map((_, index) => (
        <Card key={index} className="overflow-hidden border shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <Skeleton className="size-10 rounded-sm" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-7 w-24" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
