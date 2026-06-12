import { API_BASE_URL } from "../api/client";

type AvatarProps = {
  username: string;
  avatarUrl: string | null;
  size: string;
  className?: string;
};

export function Avatar({ username, avatarUrl, size, className = "" }: Readonly<AvatarProps>) {
  const initial = username[0]?.toUpperCase() ?? "?";
  if (avatarUrl) {
    const src = `${API_BASE_URL}/api/images/${avatarUrl.replace(/^images\//, "")}`;
    return (
      <img
        src={src}
        alt={username}
        className={`shrink-0 rounded-full object-cover ${size} ${className}`}
      />
    );
  }
  return (
    <span
      aria-label={username}
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-accent font-bold text-white ${size} ${className}`}
    >
      {initial}
    </span>
  );
}