import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

export function SortIcon({ active, order }: Readonly<{ active: boolean; order: "asc" | "desc" }>) {
  if (!active) return <ChevronsUpDown className="h-3 w-3 opacity-50" aria-hidden="true" />;
  if (order === "asc") return <ArrowUp className="h-3 w-3" aria-hidden="true" />;
  return <ArrowDown className="h-3 w-3" aria-hidden="true" />;
}