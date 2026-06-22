/**
 * Auth-related TypeScript types.
 */

export type Role = 'Admin' | 'Operations' | 'Accounts' | 'Sales';

export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  role: Role;
  phone: string;
  department: string;
  avatar_url: string | null;
  marketing_person_id: number | null;
}

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  login(username: string, password: string): Promise<void>;
  logout(): void;
  refreshUser(): Promise<void>;
  role: Role | null;
}
