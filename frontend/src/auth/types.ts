export type UserRole = "ADMIN" | "USER";

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
}
