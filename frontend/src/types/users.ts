export type User = {
  id: number;
  username: string;
  role: "admin" | "user";
  avatar_url: string | null;
};
