export interface AuthUser {
  id: number;
  username: string;
  email: string;
  fullName: string;
  role: string;
  permissions: string[];
  isActive: boolean;
}
