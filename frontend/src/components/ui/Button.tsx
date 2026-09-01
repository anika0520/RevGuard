import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "subtle" | "danger" | "ghost";
  size?: "sm" | "md";
}

const VARIANTS: Record<NonNullable<ButtonProps["variant"]>, string> = {
  default: "border border-line bg-surface text-fg hover:bg-elevated",
  primary: "border border-accent bg-accent text-white hover:opacity-90",
  subtle: "border border-accent/30 bg-accent/10 text-accent hover:bg-accent/20",
  danger: "border border-danger/30 bg-danger/10 text-danger hover:bg-danger/20",
  ghost: "border border-transparent text-muted hover:bg-elevated hover:text-fg",
};

const SIZES = {
  sm: "h-8 px-2.5 text-xs",
  md: "h-9 px-3.5 text-sm",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";
