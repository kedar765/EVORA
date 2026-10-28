
"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  UserRound,
  AlertCircle,
  Zap,
  BrainCircuit,
  ShieldCheck,
  BarChart3,
} from "lucide-react";

import { useAuth } from "@/lib/auth";

interface AuthFormProps {
  mode?: "login" | "signup";
}

type AuthMode = "login" | "signup";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function AuthForm({
  mode = "login",
}: AuthFormProps) {
  const router = useRouter();

  const {
    isAuthenticated,
    isLoading,
    login,
    signup,
  } = useAuth();

  const [currentMode, setCurrentMode] =
    useState<AuthMode>(mode);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [showPassword, setShowPassword] =
    useState(false);

  const [rememberMe, setRememberMe] =
    useState(false);

  const [submitting, setSubmitting] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const isLogin = currentMode === "login";

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  const changeMode = (newMode: AuthMode) => {
    setCurrentMode(newMode);
    setError(null);
    setPassword("");
    setConfirmPassword("");
    setShowPassword(false);
  };

  const validateForm = (): string | null => {
    const cleanEmail = email.trim();

    if (!EMAIL_PATTERN.test(cleanEmail)) {
      return "Please enter a valid email address.";
    }

    if (!password) {
      return "Please enter your password.";
    }

    if (isLogin) {
      return null;
    }

    if (fullName.trim().length < 2) {
      return "Full name must contain at least 2 characters.";
    }

    if (password.length < 8) {
      return "Password must contain at least 8 characters.";
    }

    if (password.length > 128) {
      return "Password cannot exceed 128 characters.";
    }

    if (password !== confirmPassword) {
      return "Passwords do not match.";
    }

    return null;
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (submitting || isLoading) {
      return;
    }

    setError(null);

    const validationError = validateForm();

    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);

    try {
      const cleanEmail = email.trim().toLowerCase();

      const success = isLogin
        ? await login(
            cleanEmail,
            password,
            rememberMe
          )
        : await signup(
            fullName.trim(),
            cleanEmail,
            password
          );

      if (!success) {
        setError(
          isLogin
            ? "Unable to sign in. Check your credentials and backend connection."
            : "Unable to create account. Check your details and backend connection."
        );
        return;
      }

      // The AuthProvider handles dashboard navigation.
      setPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Authentication failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div
          role="status"
          className="flex flex-col items-center gap-3"
        >
          <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />

          <p className="text-sm font-medium text-slate-600">
            Verifying your session...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4 sm:p-6">
      <div className="w-full max-w-5xl bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden grid lg:grid-cols-12">

        {/* Left: EVORA Information */}
        <div className="lg:col-span-5 bg-gradient-to-br from-blue-900 via-indigo-900 to-slate-950 p-8 sm:p-10 text-white flex flex-col justify-between min-h-[340px] lg:min-h-[620px]">
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
                <Zap className="w-5 h-5" />
              </div>

              <span className="text-2xl font-black tracking-tight">
                EVORA
              </span>
            </Link>

            <p className="text-xs text-blue-200 mt-2">
              Enterprise Business Intelligence
            </p>
          </div>

          <div className="space-y-6 py-8">
            <div className="w-14 h-14 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center">
              <BrainCircuit className="w-7 h-7 text-cyan-300" />
            </div>

            <div>
              <h2 className="text-2xl sm:text-3xl font-bold leading-tight">
                Smarter Business
                <span className="block text-cyan-300">
                  Decisions with AI
                </span>
              </h2>

              <p className="mt-3 text-sm text-blue-100 leading-relaxed">
                Analyze business performance,
                identify unusual patterns, estimate
                outcomes, and compare possible
                decisions using EVORA.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3 rounded-xl bg-white/10 border border-white/10 p-3">
                <BarChart3 className="w-5 h-5 text-cyan-300 shrink-0" />

                <div>
                  <p className="text-sm font-semibold">
                    Business Analytics
                  </p>
                  <p className="text-xs text-blue-200">
                    Understand your business data
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-xl bg-white/10 border border-white/10 p-3">
                <ShieldCheck className="w-5 h-5 text-cyan-300 shrink-0" />

                <div>
                  <p className="text-sm font-semibold">
                    Risk Intelligence
                  </p>
                  <p className="text-xs text-blue-200">
                    Detect anomalies and review risks
                  </p>
                </div>
              </div>
            </div>
          </div>

          <p className="text-xs text-blue-200 border-t border-white/15 pt-4">
            EVORA — AI Business Intelligence
            & Decision Support
          </p>
        </div>

        {/* Right: Authentication Form */}
        <div className="lg:col-span-7 p-7 sm:p-10 lg:p-12 flex items-center justify-center">
          <div className="w-full max-w-md space-y-6">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                {isLogin
                  ? "Welcome Back"
                  : "Create Your Account"}
              </h1>

              <p className="text-sm text-slate-500 mt-2">
                {isLogin
                  ? "Sign in to access your EVORA dashboard."
                  : "Register to start analyzing your business data."}
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl bg-rose-50 border border-rose-200 p-3.5"
              >
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />

                <p className="text-xs font-medium text-rose-700 leading-relaxed">
                  {error}
                </p>
              </div>
            )}

            <form
              onSubmit={handleSubmit}
              className="space-y-4"
            >
              {!isLogin && (
                <div>
                  <label
                    htmlFor="auth-name"
                    className="block text-xs font-semibold text-slate-700 mb-1.5"
                  >
                    Full Name
                  </label>

                  <div className="relative">
                    <UserRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />

                    <input
                      id="auth-name"
                      type="text"
                      value={fullName}
                      onChange={(e) =>
                        setFullName(e.target.value)
                      }
                      placeholder="Enter your full name"
                      autoComplete="name"
                      required
                      minLength={2}
                      maxLength={100}
                      disabled={submitting}
                      className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-600"
                    />
                  </div>
                </div>
              )}

              <div>
                <label
                  htmlFor="auth-email"
                  className="block text-xs font-semibold text-slate-700 mb-1.5"
                >
                  Email Address
                </label>

                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />

                  <input
                    id="auth-email"
                    type="email"
                    value={email}
                    onChange={(e) =>
                      setEmail(e.target.value)
                    }
                    placeholder="name@example.com"
                    autoComplete="email"
                    maxLength={254}
                    required
                    disabled={submitting}
                    className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-600"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="auth-password"
                  className="block text-xs font-semibold text-slate-700 mb-1.5"
                >
                  Password
                </label>

                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />

                  <input
                    id="auth-password"
                    type={
                      showPassword
                        ? "text"
                        : "password"
                    }
                    value={password}
                    onChange={(e) =>
                      setPassword(e.target.value)
                    }
                    placeholder="Enter your password"
                    autoComplete={
                      isLogin
                        ? "current-password"
                        : "new-password"
                    }
                    minLength={isLogin ? undefined : 8}
                    maxLength={128}
                    required
                    disabled={submitting}
                    className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-11 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-600"
                  />

                  <button
                    type="button"
                    onClick={() =>
                      setShowPassword((value) => !value)
                    }
                    aria-label={
                      showPassword
                        ? "Hide password"
                        : "Show password"
                    }
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-blue-700"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {!isLogin && (
                  <p className="text-xs text-slate-500 mt-1.5">
                    Use at least 8 characters.
                  </p>
                )}
              </div>

              {!isLogin && (
                <div>
                  <label
                    htmlFor="auth-confirm-password"
                    className="block text-xs font-semibold text-slate-700 mb-1.5"
                  >
                    Confirm Password
                  </label>

                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />

                    <input
                      id="auth-confirm-password"
                      type={
                        showPassword
                          ? "text"
                          : "password"
                      }
                      value={confirmPassword}
                      onChange={(e) =>
                        setConfirmPassword(e.target.value)
                      }
                      placeholder="Confirm your password"
                      autoComplete="new-password"
                      required
                      disabled={submitting}
                      className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-600"
                    />
                  </div>
                </div>
              )}

              {isLogin && (
                <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) =>
                      setRememberMe(e.target.checked)
                    }
                    disabled={submitting}
                    className="w-4 h-4 accent-blue-700"
                  />

                  Remember me
                </label>
              )}

              <button
                type="submit"
                disabled={submitting || isLoading}
                className="w-full flex items-center justify-center rounded-xl bg-blue-800 hover:bg-blue-900 text-white py-3 text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting
                  ? isLogin
                    ? "Signing In..."
                    : "Creating Account..."
                  : isLogin
                  ? "Sign In"
                  : "Create Account"}
              </button>
            </form>

            <div className="border-t border-slate-200 pt-5 text-center">
              {isLogin ? (
                <p className="text-sm text-slate-600">
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() =>
                      changeMode("signup")
                    }
                    className="font-semibold text-blue-800 hover:underline"
                  >
                    Create Account
                  </button>
                </p>
              ) : (
                <p className="text-sm text-slate-600">
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() =>
                      changeMode("login")
                    }
                    className="font-semibold text-blue-800 hover:underline"
                  >
                    Sign In
                  </button>
                </p>
              )}
            </div>

            <p className="text-center text-xs text-slate-400">
              Authentication is verified by the EVORA backend.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
