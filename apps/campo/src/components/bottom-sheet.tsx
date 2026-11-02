"use client";

import { useEffect, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { useDeviceContext } from "@/lib/device/use-device-context";

/**
 * Combina classes CSS condicionalmente.
 *
 * Args:
 *   values (Array<string | false | null | undefined>): Lista de classes.
 *
 * Return:
 *   string: Classes concatenadas.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

interface BottomSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  title?: string;
  description?: string;
}

/**
 * Container modal adaptativo que renderiza como Bottom Sheet nativo no celular e Dialog centralizado em Tablet/Desktop.
 *
 * Args:
 *   props (BottomSheetProps): Estado de abertura, callback, título, descrição e conteúdo.
 *
 * Return:
 *   JSX.Element | null: Modal adaptativo conforme o perfil do dispositivo.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function BottomSheet({
  open,
  onOpenChange,
  children,
  title,
  description,
}: BottomSheetProps) {
  const [isRendered, setIsRendered] = useState(open);
  const { layoutProfile } = useDeviceContext();
  const isBottomSheet = layoutProfile.sheetPresentation === "bottom-sheet";

  useEffect(() => {
    if (open) {
      setIsRendered(true);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
      const timer = setTimeout(() => setIsRendered(false), 260);
      return () => clearTimeout(timer);
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  if (!isRendered) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 z-50 bg-black/50 backdrop-blur-xs transition-opacity duration-250 ease-out",
          open ? "opacity-100" : "opacity-0"
        )}
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Surface: Bottom Sheet no Mobile | Centered Dialog no Tablet/Desktop */}
      <div
        data-presentation={layoutProfile.sheetPresentation}
        className={cn(
          "fixed z-50 flex flex-col border border-border bg-card shadow-2xl transition-all duration-250 ease-[cubic-bezier(0.32,0.72,0,1)]",
          isBottomSheet
            ? cn(
                "inset-x-0 bottom-0 rounded-t-2xl border-b-0",
                open ? "translate-y-0" : "translate-y-full"
              )
            : cn(
                "left-1/2 top-1/2 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-sm",
                open ? "scale-100 opacity-100" : "scale-95 opacity-0"
              )
        )}
        style={isBottomSheet ? { paddingBottom: "env(safe-area-inset-bottom)" } : undefined}
        role="dialog"
        aria-modal="true"
        aria-label={title ?? "Painel de opções"}
      >
        {isBottomSheet && (
          <div className="flex shrink-0 flex-col items-center justify-center pt-3 pb-1.5">
            <div className="h-1.5 w-11 rounded-full bg-muted-foreground/25" />
          </div>
        )}

        {(title || description || !isBottomSheet) && (
          <div className="flex items-start justify-between gap-3 border-b border-border/60 px-5 py-3.5">
            <div className="min-w-0 flex-1">
              {title && (
                <h2 className="text-sm font-bold tracking-tight text-foreground">
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                  {description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              aria-label="Fechar painel"
              className="inline-flex size-7 shrink-0 items-center justify-center rounded-sm border border-border bg-background text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}

        <div className="flex max-h-[80dvh] flex-col overflow-y-auto overscroll-contain">
          {children}
        </div>
      </div>
    </>
  );
}
