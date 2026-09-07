"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Camera, X, MapPin, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface Foto {
  id: string;
  url: string;
  latitude?: number;
  longitude?: number;
}

interface Props {
  entradaId: string | null;
  fotosExistentes?: Foto[];
  onFotoAdded?: (foto: Foto) => void;
}

export function FotoUpload({ entradaId, fotosExistentes = [], onFotoAdded }: Props) {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [geo, setGeo] = useState<{ lat: number; lng: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function capturarGeolocalizacao() {
    if (!navigator.geolocation) {
      toast.warning("Geolocalização não disponível neste navegador.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setGeo({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => toast.warning("Não foi possível obter localização."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function handleFile(file: File) {
    if (!entradaId) {
      toast.error("Salve o registro antes de adicionar fotos.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error("Arquivo muito grande. Máximo: 10 MB.");
      return;
    }

    setUploading(true);
    try {
      // Compressão simples: redimensiona se > 1920px
      const compressed = await compressImage(file, 1920, 0.8);

      const formData = new FormData();
      formData.append("file", compressed, file.name);
      if (geo) {
        formData.append("latitude", String(geo.lat));
        formData.append("longitude", String(geo.lng));
      }

      const res = await fetch(`/api/v1/caderno/entradas/${entradaId}/fotos`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro no upload" }));
        throw new Error(err.detail || "Falha no upload");
      }

      const foto = await res.json();
      onFotoAdded?.(foto);
      toast.success("Foto adicionada com sucesso!");
      setPreview(null);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Erro ao enviar foto";
      toast.error(message);
    } finally {
      setUploading(false);
    }
  }

  async function compressImage(file: File, maxWidth: number, quality: number): Promise<Blob> {
    return new Promise((resolve) => {
      const img = new globalThis.Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        const ratio = Math.min(maxWidth / img.width, 1);
        canvas.width = img.width * ratio;
        canvas.height = img.height * ratio;
        const ctx = canvas.getContext("2d");
        ctx?.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => resolve(blob || file),
          "image/jpeg",
          quality
        );
      };
      img.src = URL.createObjectURL(file);
    });
  }

  function handleSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    // Preview
    const reader = new FileReader();
    reader.onload = (ev) => setPreview(ev.target?.result as string);
    reader.readAsDataURL(file);

    // Captura geolocalização no momento da seleção
    capturarGeolocalizacao();

    // Envia após preview
    setTimeout(() => handleFile(file), 200);
  }

  return (
    <div className="space-y-3">
      {/* Fotos existentes */}
      {fotosExistentes.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {fotosExistentes.map((f) => (
            <div key={f.id} className="relative aspect-square rounded-md overflow-hidden bg-muted group">
              <Image src={f.url} alt="Foto" fill className="object-cover" sizes="150px" />
              {f.latitude && f.longitude && (
                <MapPin className="absolute bottom-1 right-1 size-3 text-white drop-shadow" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Botão de captura */}
      <div className="flex items-center gap-3">
        <input
          type="file"
          accept="image/*"
          ref={fileInputRef}
          onChange={handleSelect}
          className="hidden"
          capture="environment"
        />
        <Button
          variant="outline"
          size="sm"
          className={cn("gap-2", uploading && "opacity-60")}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? <Loader2 className="size-3.5 animate-spin" /> : <Camera className="size-3.5" />}
          {uploading ? "Enviando..." : "Adicionar foto"}
        </Button>
        {geo && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <MapPin className="size-3" />
            {geo.lat.toFixed(4)}, {geo.lng.toFixed(4)}
          </span>
        )}
      </div>

      {/* Preview do upload */}
      {preview && (
        <div className="relative w-32 h-32 rounded-md overflow-hidden bg-muted">
          <Image src={preview} alt="Preview" fill className="object-cover" />
          <button
            type="button"
            className="absolute top-1 right-1 bg-black/60 rounded-full p-0.5 hover:bg-black/80"
            onClick={() => setPreview(null)}
          >
            <X className="size-3 text-white" />
          </button>
        </div>
      )}
    </div>
  );
}
