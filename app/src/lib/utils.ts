import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** shadcn/ui's class combiner. Kept at the path `components.json` declares. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
