"use client";

import { animate } from "framer-motion";
import { useEffect, useRef } from "react";

/** Animates a figure to its new value -- the dashboard should feel alive during a demo. */
export function CountUp({
  value,
  format,
  className,
  duration = 0.9,
}: {
  value: number;
  format: (v: number) => string;
  className?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef(0);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const from = previous.current;
    previous.current = value;
    const controls = animate(from, value, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => {
        node.textContent = format(v);
      },
    });
    return () => controls.stop();
  }, [value, duration, format]);

  return (
    <span ref={ref} className={className}>
      {format(value)}
    </span>
  );
}
