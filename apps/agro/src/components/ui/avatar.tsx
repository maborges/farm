"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export function Avatar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            data-slot="avatar"
            className={cn("relative flex size-10 shrink-0 overflow-hidden rounded-full", className)}
            {...props}
        />
    )
}

export function AvatarImage({ className, src, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) {
    const [status, setStatus] = React.useState<"loading" | "loaded" | "error">("loading")

    React.useEffect(() => {
        setStatus(src ? "loading" : "error")
    }, [src])

    if (!src || status === "error") return null

    return (
        // eslint-disable-next-line @next/next/no-img-element
        <img
            src={src}
            alt={props.alt ?? ""}
            data-slot="avatar-image"
            className={cn(
                "absolute inset-0 aspect-square size-full object-cover z-10",
                status === "loaded" ? "block" : "hidden",
                className
            )}
            onLoad={() => setStatus("loaded")}
            onError={() => setStatus("error")}
            {...props}
        />
    )
}

export function AvatarFallback({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            data-slot="avatar-fallback"
            className={cn(
                "flex size-full items-center justify-center rounded-full bg-muted",
                className
            )}
            {...props}
        />
    )
}
