import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "destructive" | "info" | "outline";
}

const VARIANTS: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default: "border-line bg-elevated text-muted",
  success: "border-success/30 bg-success/10 text-success",
  warning: "border-warning/30 bg-warning/10 text-warning",
  destructive: "border-danger/30 bg-danger/10 text-danger",
  info: "border-accent/30 bg-accent/10 text-accent",
  outline: "border-line text-muted",
};

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-2xs font-medium",
        VARIANTS[variant],
        className
      )}
      {...props}
    />
  );
}
