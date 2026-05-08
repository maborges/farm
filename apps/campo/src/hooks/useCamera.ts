"use client";

import { useState, useRef } from "react";

const MAX_FOTOS = 2;
const MAX_WIDTH = 1280;
const QUALITY = 0.7;

export function useCamera() {
  const [fotos, setFotos] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const canAddMore = fotos.length < MAX_FOTOS;

  const openCamera = () => {
    if (!canAddMore) return;
    inputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const compressed = await compressImage(file);
    setFotos((prev) => [...prev.slice(0, MAX_FOTOS - 1), compressed]);
    // Reset input para permitir mesma foto novamente
    e.target.value = "";
  };

  const removePhoto = (idx: number) => {
    setFotos((prev) => prev.filter((_, i) => i !== idx));
  };

  return { fotos, inputRef, canAddMore, openCamera, handleFileChange, removePhoto };
}

async function compressImage(file: File): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const ratio = Math.min(1, MAX_WIDTH / img.width);
      canvas.width = img.width * ratio;
      canvas.height = img.height * ratio;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", QUALITY));
    };
    img.src = url;
  });
}
