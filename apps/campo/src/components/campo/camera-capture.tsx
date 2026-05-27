"use client";

import { useCamera } from "@/hooks/useCamera";
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
    <CampoSurface className="flex flex-col gap-3 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-semibold text-white/85">
          Fotos
        </label>
        <CampoPill className="border-white/10 bg-white/6 text-white/65">
          {fotos.length}/2
        </CampoPill>
      </div>
      <div className="flex flex-wrap gap-3 sm:gap-4">
        {fotos.map((foto, i) => (
          <div key={i} className="relative size-24 overflow-hidden rounded-2xl border border-white/10 shadow-[0_12px_30px_rgba(0,0,0,0.2)] sm:size-28">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={foto} alt={`foto ${i + 1}`} className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="absolute right-1 top-1 flex size-6 items-center justify-center rounded-full border border-white/10 bg-black/60 text-xs text-white"
              aria-label="Remover foto"
            >
              ×
            </button>
          </div>
        ))}

        {canAddMore && (
          <CampoButton
            type="button"
            onClick={onOpen}
            variant="secondary"
            className="flex size-24 flex-col rounded-2xl border-dashed text-white/65 sm:size-28"
          >
            <span className="text-2xl">📷</span>
            <span className="text-xs font-medium">Adicionar</span>
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
