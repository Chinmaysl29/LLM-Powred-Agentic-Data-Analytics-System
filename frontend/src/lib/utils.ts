/**
 * Lightweight class-name utility.
 * Filters falsy values and joins the rest with a space.
 * Drop-in equivalent of the shadcn `cn` helper for projects without Tailwind.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
