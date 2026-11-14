import type { Language, TokenResponse, User } from "@/types";
import { api } from "./api";

export interface RegisterInput {
  full_name: string;
  email: string;
  password: string;
  preferred_language: Language;
  organization?: string;
}

export const authService = {
  login: (email: string, password: string) => api.post<TokenResponse>("/api/auth/login", { email, password }),
  register: (input: RegisterInput) => api.post<TokenResponse>("/api/auth/register", input),
  me: () => api.get<User>("/api/auth/me"),
  updateProfile: (input: Partial<Pick<User, "full_name" | "preferred_language" | "organization">>) =>
    api.patch<User>("/api/auth/me", input),
  changePassword: (current_password: string, new_password: string) =>
    api.post<void>("/api/auth/change-password", { current_password, new_password }),
};
