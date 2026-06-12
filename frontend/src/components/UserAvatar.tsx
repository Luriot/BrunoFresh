import type { User } from "../types";
import { Avatar } from "./Avatar";

type Props = {
  user: User;
  size?: string;
  className?: string;
};

export function UserAvatar({ user, size = "h-9 w-9", className = "" }: Readonly<Props>) {
  return <Avatar username={user.username} avatarUrl={user.avatar_url} size={size} className={className} />;
}