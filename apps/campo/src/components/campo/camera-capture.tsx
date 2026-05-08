"use client";

import { useCamera } from "@/hooks/useCamera";

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
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-neutral-400">
        Fotos ({fotos.length}/2)
      </label>
      <div className="flex gap-3 flex-wrap">
        {fotos.map((foto, i) => (
          <div key={i} className="relative size-20 rounded-xl overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={foto} alt={`foto ${i + 1}`} className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => onRemove(i)}
              className="absolute top-0.5 right-0.5 size-5 bg-black/70 rounded-full text-xs flex items-center justify-center"
              aria-label="Remover foto"
            >
              ×
            </button>
          </div>
        ))}

        {canAddMore && (
          <button
            type="button"
            onClick={onOpen}
            className="size-20 rounded-xl border-2 border-dashed border-neutral-600 flex flex-col items-center justify-center gap-1 text-neutral-500 hover:border-green-500 hover:text-green-400 transition-colors"
          >
            <span className="text-2xl">📷</span>
            <span className="text-xs">Foto</span>
          </button>
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
    </div>
  );
}
