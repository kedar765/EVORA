
"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  provider?: "email" | "google" | "github";
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
    rememberMe?: boolean
  ) => Promise<boolean>;
  signup: (
    name: string,
    email: string,
    password: string
  ) => Promise<boolean>;
  loginWithGoogle: () => Promise<boolean>;
  loginWithGitHub: () => Promise<boolean>;
  logout: () => void;
}

interface SessionResponse {
  user?: {
    id: string;
    email: string;
    fullName?: string;
    avatar?: string;
    provider?: User["provider"];
  };
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const AuthContext = createContext<
  AuthContextType | undefined
>(undefined);

function formatUser(
  data: NonNullable<SessionResponse["user"]>
): User {
  return {
    id: data.id,
    name: data.fullName || data.email.split("@")[0],
    email: data.email,
    avatar: data.avatar,
    provider: data.provider || "email",
  };
}

async function fetchCurrentUser(): Promise<User | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/auth/me`,
    {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    }
  );

  if (!response.ok) {
    return null;
  }

  const data: SessionResponse = await response.json();

  if (!data.user?.id || !data.user?.email) {
    return null;
  }

  return formatUser(data.user);
}

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function verifySession() {
      try {
        const currentUser = await fetchCurrentUser();

        if (active) {
          setUser(currentUser);
        }
      } catch {
        if (active) {
          setUser(null);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    verifySession();

    return () => {
      active = false;
    };
  }, []);

  const login = async (
    email: string,
    password: string,
    rememberMe = false
  ): Promise<boolean> => {
    setIsLoading(true);

    try {
      const response = await api.login({
        email,
        password,
        rememberMe,
      });

      if (!response.success) {
        return false;
      }

      const verifiedUser = await fetchCurrentUser();

      if (!verifiedUser) {
        return false;
      }

      setUser(verifiedUser);
      router.replace("/dashboard");

      return true;
    } catch (error) {
      console.error("Login failed:", error);
      setUser(null);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (
    name: string,
    email: string,
    password: string
  ): Promise<boolean> => {
    setIsLoading(true);

    try {
      const response = await api.signup({
        fullName: name,
        email,
        password,
      });

      if (!response.success) {
        return false;
      }

      const verifiedUser = await fetchCurrentUser();

      if (!verifiedUser) {
        return false;
      }

      setUser(verifiedUser);
      router.replace("/dashboard");

      return true;
    } catch (error) {
      console.error("Signup failed:", error);
      setUser(null);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  // Disabled until real OAuth is implemented.
  const loginWithGoogle = async (): Promise<boolean> => {
    return false;
  };

  const loginWithGitHub = async (): Promise<boolean> => {
    return false;
  };

  const logout = (): void => {
    async function endSession() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/logout`,
          {
            method: "POST",
            credentials: "include",
          }
        );

        if (!response.ok) {
          throw new Error("Logout failed");
        }

        setUser(null);

        localStorage.removeItem("evora_session");

        sessionStorage.removeItem("evora_active_upload");
        sessionStorage.removeItem("evora_dataset_preview");
        sessionStorage.removeItem("evora_full_dataset");

        router.replace("/login");
      } catch (error) {
        console.error("Logout failed:", error);
      }
    }

    void endSession();
  };

  return React.createElement(
    AuthContext.Provider,
    {
      value: {
        user,
        isAuthenticated: user !== null,
        isLoading,
        login,
        signup,
        loginWithGoogle,
        loginWithGitHub,
        logout,
      },
    },
    children
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used within AuthProvider"
    );
  }

  return context;
}
