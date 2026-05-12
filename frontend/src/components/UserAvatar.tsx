import type { User } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

type Props = {
  user: User;
  /** Tailwind size class for width/height, e.g. "h-8 w-8". Default: "h-9 w-9" */
  size?: string;
  /** Extra classes */
  className?: string;
};

export function UserAvatar({ user, size = "h-9 w-9", className = "" }: Readonly<Props>) {
  const initial = user.username[0]?.toUpperCase() ?? "?";

  if (user.avatar_url) {
    const src = `${API_BASE_URL}/api/images/${user.avatar_url.replace(/^images\//, "")}`;
    return (
      <img
        src={src}
        alt={user.username}
        className={`shrink-0 rounded-full object-cover ${size} ${className}`}
      />
    );
  }

  return (
    <span
      aria-label={user.username}
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-accent font-bold text-white ${size} ${className}`}
    >
      {initial}
    </span>
  );
}
