"use client";

import { Camera, X } from "lucide-react";
import { CampoButton, CampoPill, CampoSurface } from "./ui";

interface CameraCaptureProps {
  fotos: string[];
  inputRef: React.RefObject<HTMLInputElement | null>;
  canAddMore: boolean;
  onOpen: () => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemove: (idx: number) => void;
}

export function CameraCapture({
  fotos,
  inputRef,
  canAddMore,
  onOpen,
  onFileChange,
  onRemove,
}: CameraCaptureProps) {
  return (
    <CampoSurface className="flex flex-col gap-2.5 p-3.5 sm:p-4">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-semibold text-foreground">
          Fotos
        </label>
        <CampoPill>
          {fotos.length}/2
        </CampoPill>
      </div>
      <div className="flex flex-wrap gap-2.5 sm:gap-3">
        {fotos.map((foto, i) => (
          <div key={i} className="relative size-20 overflow-hidden rounded-lg border border-border shadow-sm sm:size-24">
            <img src={foto} alt={`foto ${i + 1}`} className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="absolute right-1 top-1 flex size-5 items-center justify-center rounded-full border border-border bg-card/90 text-foreground shadow-sm hover:bg-destructive hover:text-destructive-foreground transition-colors"
              aria-label="Remover foto"
            >
              <X className="size-3" />
            </button>
          </div>
        ))}

        {canAddMore && (
          <CampoButton
            type="button"
            onClick={onOpen}
            variant="secondary"
            className="flex size-20 flex-col rounded-lg border-dashed text-muted-foreground sm:size-24"
          >
            <Camera className="size-5 mb-1" strokeWidth={1.5} />
            <span className="text-[11px] font-medium">Adicionar</span>
          </CampoButton>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={onFileChange}
      />
    </CampoSurface>
  );
}
