import type { Recommender } from "../types";
import { Avatar } from "./Avatar";

const MAX_VISIBLE = 4;

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
          <Avatar username={r.username} avatarUrl={r.avatar_url} size={`${size} rounded-full border-2 border-white object-cover dark:border-[#252526]`} />
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
