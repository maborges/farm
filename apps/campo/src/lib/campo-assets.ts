"use client";

import { useEffect, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db, type CachedFazenda, type CachedImageKind, type LocalSession } from "@/lib/db";

const IMAGE_FETCH_TIMEOUT_MS = 15_000;

export function cachedImageId(kind: CachedImageKind, ownerId: string): string {
  return `${kind}:${ownerId}`;
}

export async function cacheCampoImage(
  kind: CachedImageKind,
  ownerId: string,
  sourceUrl?: string | null,
): Promise<boolean> {
  if (!sourceUrl) return false;

  const id = cachedImageId(kind, ownerId);
  const current = await db.cached_images.get(id);
  if (current?.source_url === sourceUrl && current.blob instanceof Blob) return true;

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), IMAGE_FETCH_TIMEOUT_MS);

  try {
    const response = await fetch(sourceUrl, { cache: "no-store", signal: controller.signal });
    if (!response.ok) throw new Error(`Imagem retornou HTTP ${response.status}`);
    const blob = await response.blob();
    if (!blob.type.startsWith("image/")) {
      throw new Error(`Conteúdo não é uma imagem: ${blob.type || "desconhecido"}`);
    }

    await db.cached_images.put({
      id,
      kind,
      owner_id: ownerId,
      source_url: sourceUrl,
      blob,
      mime_type: blob.type,
      updated_at: new Date().toISOString(),
    });
    return true;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function cacheCampoBrandAssets(
  session: LocalSession,
  fazendas: Pick<CachedFazenda, "id" | "logo_url">[],
): Promise<void> {
  const jobs: Promise<unknown>[] = [];
  if (session.user_avatar_url) {
    jobs.push(cacheCampoImage("user_avatar", session.user_id, session.user_avatar_url));
  }
  for (const fazenda of fazendas) {
    if (fazenda.logo_url) {
      jobs.push(cacheCampoImage("fazenda_logo", fazenda.id, fazenda.logo_url));
    }
  }
  await Promise.allSettled(jobs);
}

export function useCachedCampoImage(
  kind: CachedImageKind,
  ownerId: string | undefined,
  sourceUrl?: string | null,
): string | undefined {
  const id = ownerId ? cachedImageId(kind, ownerId) : undefined;
  const cached = useLiveQuery(() => (id ? db.cached_images.get(id) : undefined), [id]);
  const [objectUrl, setObjectUrl] = useState<string>();

  useEffect(() => {
    if (!id || !ownerId) return;
    if (!sourceUrl) {
      void db.cached_images.delete(id);
      return;
    }

    void cacheCampoImage(kind, ownerId, sourceUrl).catch(() => {
      // A inicial ou o ícone da fazenda são fallbacks válidos.
    });
  }, [id, kind, ownerId, sourceUrl]);

  useEffect(() => {
    if (!cached?.blob) {
      setObjectUrl(undefined);
      return;
    }
    const nextUrl = URL.createObjectURL(cached.blob);
    setObjectUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [cached?.id, cached?.updated_at]);

  return objectUrl;
}
