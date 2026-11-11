"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { inputBaseClassName } from "./input";

export interface PasswordInputProps extends React.ComponentProps<"input"> {}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, disabled, autoComplete = "off", ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false);

    return (
      <div className="relative w-full">
        <input
          ref={ref}
          type={showPassword ? "text" : "password"}
          autoComplete={autoComplete}
          disabled={disabled}
          data-slot="input"
          className={cn(inputBaseClassName, "pr-9", className)}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShowPassword((prev) => !prev)}
          disabled={disabled}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 size-6 flex items-center justify-center rounded-sm text-muted-foreground/80 hover:text-foreground hover:bg-muted/60 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:pointer-events-none disabled:opacity-40"
          aria-label={showPassword ? "Ocultar senha" : "Visualizar senha"}
          title={showPassword ? "Ocultar senha" : "Visualizar senha"}
        >
          {showPassword ? (
            <EyeOff className="size-3.5" />
          ) : (
            <Eye className="size-3.5" />
          )}
        </button>
      </div>
    );
  }
);

PasswordInput.displayName = "PasswordInput";

export { PasswordInput };
