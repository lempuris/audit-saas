import type { RiskRating } from "../types/clients";

const STYLES: Record<RiskRating, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-red-100 text-red-800",
};

export default function RiskBadge({ rating }: { rating: RiskRating | null }) {
  if (!rating) {
    return <span className="text-xs text-slate-400">unrated</span>;
  }
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${STYLES[rating]}`}>{rating}</span>
  );
}
