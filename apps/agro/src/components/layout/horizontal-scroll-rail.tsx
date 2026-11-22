"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface HorizontalScrollRailProps {
  children: React.ReactNode;
  ariaLabel: string;
  as?: "div" | "nav";
  role?: React.AriaRole;
  testId?: string;
  className?: string;
  contentClassName?: string;
  showProgressBar?: boolean;
}

interface ScrollMetrics {
  canScrollLeft: boolean;
  canScrollRight: boolean;
  hasOverflow: boolean;
  thumbWidthPct: number;
  thumbOffsetPct: number;
}

const INITIAL_METRICS: ScrollMetrics = {
  canScrollLeft: false,
  canScrollRight: false,
  hasOverflow: false,
  thumbWidthPct: 100,
  thumbOffsetPct: 0,
};

function computeScrollMetrics(el: HTMLElement): ScrollMetrics {
  const { scrollLeft, scrollWidth, clientWidth } = el;
  const maxScroll = scrollWidth - clientWidth;
  if (maxScroll <= 4 || clientWidth <= 0) {
    return INITIAL_METRICS;
  }
  const ratio = Math.min(1, Math.max(0.15, clientWidth / scrollWidth));
  const thumbWidthPct = Math.round(ratio * 100);
  const progress = Math.min(1, Math.max(0, scrollLeft / maxScroll));
  const thumbOffsetPct = Math.round(progress * (100 - thumbWidthPct));
  return {
    canScrollLeft: scrollLeft > 4,
    canScrollRight: scrollLeft < maxScroll - 4,
    hasOverflow: true,
    thumbWidthPct,
    thumbOffsetPct,
  };
}

function getMobileSwipeHint(canLeft: boolean, canRight: boolean): string {
  if (canLeft && canRight) return "← Deslize →";
  if (canRight) return "Deslize →";
  return "← Deslize";
}

/**
 * Faixa horizontal com gradientes laterais, botões de passo e barra indicadora de rolagem.
 */
export function HorizontalScrollRail({
  children,
  ariaLabel,
  as = "div",
  role,
  testId,
  className,
  contentClassName,
  showProgressBar = true,
}: HorizontalScrollRailProps): React.ReactElement {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const [metrics, setMetrics] = React.useState<ScrollMetrics>(INITIAL_METRICS);

  const updateMetrics = React.useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const next = computeScrollMetrics(el);
    setMetrics((prev) =>
      prev.canScrollLeft === next.canScrollLeft &&
      prev.canScrollRight === next.canScrollRight &&
      prev.hasOverflow === next.hasOverflow &&
      prev.thumbWidthPct === next.thumbWidthPct &&
      prev.thumbOffsetPct === next.thumbOffsetPct
        ? prev
        : next
    );
  }, []);

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const rafId = window.requestAnimationFrame(updateMetrics);
    const onScroll = () => updateMetrics();
    el.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", updateMetrics, { passive: true });

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => updateMetrics());
      observer.observe(el);
    }

    return () => {
      window.cancelAnimationFrame(rafId);
      el.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", updateMetrics);
      observer?.disconnect();
    };
  }, [updateMetrics]);

  const scrollByStep = (direction: -1 | 1) => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollBy({ left: direction * 180, behavior: "smooth" });
  };

  const innerRail = (
    <>
      <div className="relative flex items-center">
        {metrics.canScrollLeft && (
          <div className="pointer-events-none absolute inset-y-0 left-0 z-10 flex items-center bg-gradient-to-r from-background via-background/85 to-transparent pr-4">
            <Button
              type="button"
              variant="outline"
              size="icon-xs"
              onClick={() => scrollByStep(-1)}
              aria-label="Rolar opções para a esquerda"
              className="pointer-events-auto shadow-sm bg-background/95"
            >
              <ChevronLeft className="size-3.5" />
            </Button>
          </div>
        )}

        <div
          ref={containerRef}
          role={role}
          aria-label={as === "div" ? ariaLabel : undefined}
          data-testid={testId}
          className={cn(
            "flex w-full min-w-0 items-center gap-1.5 overflow-x-auto scrollbar-none scroll-smooth snap-x snap-proximity",
            metrics.canScrollLeft && "pl-7",
            metrics.canScrollRight && "pr-7",
            contentClassName
          )}
        >
          {children}
        </div>

        {metrics.canScrollRight && (
          <div className="pointer-events-none absolute inset-y-0 right-0 z-10 flex items-center justify-end bg-gradient-to-l from-background via-background/85 to-transparent pl-4">
            <Button
              type="button"
              variant="outline"
              size="icon-xs"
              onClick={() => scrollByStep(1)}
              aria-label="Rolar opções para a direita"
              className="pointer-events-auto shadow-sm bg-background/95"
            >
              <ChevronRight className="size-3.5" />
            </Button>
          </div>
        )}
      </div>

      {metrics.hasOverflow && showProgressBar && (
        <div
          className="mt-1.5 flex items-center gap-2"
          aria-hidden="true"
          data-testid={testId ? `${testId}-scroll-hint` : undefined}
        >
          <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary/60 transition-[width,margin-left] duration-150"
              style={{
                width: `${metrics.thumbWidthPct}%`,
                marginLeft: `${metrics.thumbOffsetPct}%`,
              }}
            />
          </div>
          <span className="shrink-0 text-[10px] font-medium text-muted-foreground sm:hidden">
            {getMobileSwipeHint(metrics.canScrollLeft, metrics.canScrollRight)}
          </span>
        </div>
      )}
    </>
  );

  if (as === "nav") {
    return (
      <nav aria-label={ariaLabel} className={cn("relative w-full min-w-0", className)}>
        {innerRail}
      </nav>
    );
  }

  return <div className={cn("relative w-full min-w-0", className)}>{innerRail}</div>;
}
