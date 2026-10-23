import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Merge conditional class lists, with Tailwind conflict resolution.
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
