"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Lock } from "lucide-react";

import { trackMonetizationEvent } from "@/lib/monetization";
import { PlanTier, getCommercialPlanName } from "@/lib/constants/planos";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type TierValue = (typeof PlanTier)[keyof typeof PlanTier];

interface TierUpgradeCardProps {
  title: string;
  description: string;
  requiredTier: TierValue;
  feature: string;
  surface: string;
}

export function TierUpgradeCard({
  title,
  description,
  requiredTier,
  feature,
  surface,
}: TierUpgradeCardProps) {
  useEffect(() => {
    trackMonetizationEvent("monetization_blocked", {
      feature,
      surface,
      requiredTier,
      reason: "insufficient_tier",
    });
  }, [feature, requiredTier, surface]);

  const planName = getCommercialPlanName(requiredTier) ?? requiredTier;

  return (
    <Alert className="rounded-sm">
      <Lock className="size-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="space-y-3">
        <p>{description} Disponível no plano {planName}.</p>
        <Button asChild size="sm" variant="outline">
          <Link
            href="/dashboard/settings/billing"
            onClick={() =>
              trackMonetizationEvent("monetization_cta_clicked", {
                feature,
                surface,
                requiredTier,
                ctaLabel: "Ver planos",
              })
            }
          >
            Ver planos
          </Link>
        </Button>
      </AlertDescription>
    </Alert>
  );
}
