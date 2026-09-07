import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  /** Ação principal obrigatória (baseline-ui: empty states devem ter uma ação clara) */
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  /** Ação secundária opcional */
  secondaryAction?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center px-6 py-16 gap-4",
        className
      )}
    >
      {icon && (
        <div className="size-14 rounded-full bg-muted flex items-center justify-center text-muted-foreground [&>svg]:size-7 shrink-0">
          {icon}
        </div>
      )}

      <div className="space-y-1 max-w-sm">
        <p className="font-semibold text-foreground text-balance">{title}</p>
        {description && (
          <p className="text-sm text-muted-foreground text-pretty">{description}</p>
        )}
      </div>

      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 flex-wrap justify-center">
          {action && (
            action.href ? (
              <Button asChild size="sm" variant="outline" className="rounded-sm">
                <a href={action.href}>{action.label}</a>
              </Button>
            ) : (
              <Button size="sm" variant="outline" className="rounded-sm" onClick={action.onClick}>
                {action.label}
              </Button>
            )
          )}
          {secondaryAction && (
            secondaryAction.href ? (
              <Button variant="outline" size="sm" asChild>
                <a href={secondaryAction.href}>{secondaryAction.label}</a>
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={secondaryAction.onClick}>
                {secondaryAction.label}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}
