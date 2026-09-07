"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AgricolaRootPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/agricola/dashboard"); }, [router]);
  return null;
}
