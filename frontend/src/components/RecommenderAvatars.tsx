import type { Recommender } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";
const MAX_VISIBLE = 4;

function Avatar({ r, size }: { r: Recommender; size: string }) {
  const initial = r.username[0]?.toUpperCase() ?? "?";
  if (r.avatar_url) {
    const src = `${API_BASE_URL}/api/images/${r.avatar_url.replace(/^images\//, "")}`;
    return (
      <img
        src={src}
        alt={r.username}
        title={r.username}
        className={`${size} rounded-full border-2 border-white object-cover dark:border-[#252526]`}
      />
    );
  }
  return (
    <span
      title={r.username}
      className={`${size} inline-flex items-center justify-center rounded-full border-2 border-white bg-accent text-[10px] font-bold text-white dark:border-[#252526]`}
    >
      {initial}
    </span>
  );
}

type Props = {
  recommenders: Recommender[];
  /** Tailwind size classes. Default: "h-6 w-6" */
  size?: string;
};

export function RecommenderAvatars({ recommenders, size = "h-6 w-6" }: Readonly<Props>) {
  if (recommenders.length === 0) return null;

  const visible = recommenders.slice(0, MAX_VISIBLE);
  const overflow = recommenders.length - MAX_VISIBLE;

  return (
    <div className="flex items-center" aria-label={recommenders.map((r) => r.username).join(", ")}>
      {visible.map((r, i) => (
        <span
          key={r.username}
          className="block"
          style={{ marginLeft: i === 0 ? 0 : "-0.35rem" }}
        >
          <Avatar r={r} size={size} />
        </span>
      ))}
      {overflow > 0 && (
        <span
          title={recommenders
            .slice(MAX_VISIBLE)
            .map((r) => r.username)
            .join(", ")}
          className={`${size} -ml-1.5 inline-flex items-center justify-center rounded-full border-2 border-white bg-gray-400 text-[10px] font-bold text-white dark:border-[#252526]`}
        >
          +{overflow}
        </span>
      )}
    </div>
  );
}
