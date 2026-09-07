"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ChevronLeft, ChevronRight, Quote } from "lucide-react";
import { cn } from "@/lib/utils";

interface CarouselSlide {
  quote: string;
  author: string;
  role: string;
  region: string;
}

interface LandingCarouselProps {
  slides: CarouselSlide[];
  intervalMs?: number;
}

/**
 * Carrossel premium de depoimentos com transição fade,
 * indicadores e pause-on-hover.
 */
export function LandingCarousel({ slides, intervalMs = 6000 }: LandingCarouselProps) {
  const [current, setCurrent] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [direction, setDirection] = useState<"next" | "prev">("next");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const goTo = useCallback(
    (index: number, dir: "next" | "prev" = "next") => {
      setDirection(dir);
      setCurrent((index + slides.length) % slides.length);
    },
    [slides.length]
  );

  const next = useCallback(() => goTo(current + 1, "next"), [current, goTo]);
  const prev = useCallback(() => goTo(current - 1, "prev"), [current, goTo]);

  useEffect(() => {
    if (isPaused) return;
    timerRef.current = setInterval(next, intervalMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [next, isPaused, intervalMs]);

  const activeSlides = [
    { slide: slides[current], index: current, isSecond: false },
    { slide: slides[(current + 1) % slides.length], index: (current + 1) % slides.length, isSecond: true }
  ];

  return (
    <div
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Cards grid — mostra 1 no mobile, 2 no desktop */}
      <div className="grid gap-5 lg:grid-cols-2">
        {activeSlides.map(({ slide, index, isSecond }) => {
          return (
            <div
              key={`${index}-${current}`}
              className={cn(
                "relative rounded-sm border border-primary/10 bg-card/90 p-6 shadow-md backdrop-blur-sm",
                "transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
                isSecond && "hidden lg:block",
                "animate-[landing-fade-in_0.5s_ease-out]"
              )}
            >
              {/* Quote icon */}
              <Quote className="mb-3 size-8 text-primary/20" />

              <blockquote className="mb-5 text-[15px] leading-7 text-foreground/85">
                {slide.quote}
              </blockquote>

              <div className="flex items-center gap-3 border-t border-border/50 pt-4">
                <div className="flex size-10 items-center justify-center rounded-full bg-primary text-sm font-black text-primary-foreground">
                  {slide.author
                    .split(" ")
                    .map((n: string) => n[0])
                    .join("")
                    .slice(0, 2)}
                </div>
                <div>
                  <div className="text-sm font-bold text-foreground">{slide.author}</div>
                  <div className="text-xs text-muted-foreground">
                    {slide.role} · {slide.region}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Controls */}
      <div className="mt-5 flex items-center justify-center gap-3">
        <button
          onClick={prev}
          className="flex size-9 items-center justify-center rounded-full border border-primary/20 bg-card text-muted-foreground shadow-sm transition-all hover:border-primary/40 hover:text-primary hover:shadow-md"
          aria-label="Depoimento anterior"
        >
          <ChevronLeft className="size-4" />
        </button>

        <div className="flex items-center gap-1.5">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => goTo(i, i > current ? "next" : "prev")}
              aria-label={`Ir para depoimento ${i + 1}`}
              className={cn(
                "h-1.5 rounded-full transition-all duration-400",
                i === current
                  ? "w-6 bg-primary"
                  : "w-1.5 bg-primary/20 hover:bg-primary/35"
              )}
            />
          ))}
        </div>

        <button
          onClick={next}
          className="flex size-9 items-center justify-center rounded-full border border-primary/20 bg-card text-muted-foreground shadow-sm transition-all hover:border-primary/40 hover:text-primary hover:shadow-md"
          aria-label="Próximo depoimento"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  );
}
