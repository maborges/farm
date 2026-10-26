"use client";

import * as React from "react";
import {
  Sun,
  CloudSun,
  Cloud,
  CloudFog,
  CloudDrizzle,
  CloudRain,
  CloudLightning,
  CloudSnow,
} from "lucide-react";

interface ClimaIconProps {
  icone?: string | null;
  className?: string;
  size?: number;
}

export function ClimaIcon({
  icone,
  className = "w-5 h-5",
  size,
}: ClimaIconProps): React.ReactElement {
  const norm = (icone || "").toLowerCase().trim();

  const props = {
    className,
    ...(size ? { size } : {}),
  };

  switch (norm) {
    case "sun":
      return <Sun {...props} className={`${className} text-amber-500`} />;
    case "cloudsun":
      return <CloudSun {...props} className={`${className} text-amber-500/90 dark:text-amber-400`} />;
    case "cloud":
      return <Cloud {...props} className={`${className} text-slate-500 dark:text-slate-400`} />;
    case "cloudfog":
      return <CloudFog {...props} className={`${className} text-slate-400 dark:text-slate-500`} />;
    case "clouddrizzle":
      return <CloudDrizzle {...props} className={`${className} text-cyan-600 dark:text-cyan-400`} />;
    case "cloudrain":
      return <CloudRain {...props} className={`${className} text-blue-600 dark:text-blue-400`} />;
    case "cloudlightning":
      return <CloudLightning {...props} className={`${className} text-amber-600 dark:text-amber-400`} />;
    case "cloudsnow":
      return <CloudSnow {...props} className={`${className} text-sky-500 dark:text-sky-300`} />;
    default:
      return <CloudSun {...props} className={`${className} text-blue-500/80`} />;
  }
}
