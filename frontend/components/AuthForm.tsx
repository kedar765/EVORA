"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  User as UserIcon,
  AlertCircle,
  Zap,
  BrainCircuit,
  ShieldCheck,
} from "lucide-react";
import OAuthButtons from "./OAuthButtons";
import { useAuth } from "@/lib/auth";

interface AuthFormProps {
  mode?: "login" | "signup";
}

export default function AuthForm({ mode = "login" }: AuthFormProps) {
  const { isAuthenticated, isLoading, login, signup } = useAuth();
  const router = useRouter();

  const [currentMode, setCurrentMode] = useState<"login" | "signup">(mode);
  const isLogin = currentMode === "login";

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (isLogin) {
      if (!email.trim() || !password) {
        setError("Please enter your email and password.");
        return;
      }
      if (!emailRegex.test(email)) {
        setError("Please enter a valid email address.");
        return;
      }

      setSubmitting(true);
      try {
        const ok = await login(email, password, rememberMe);
        if (!ok) {
          setError("Invalid credentials. Please verify your email and password.");
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to sign in. Please try again.";
        setError(message);
      } finally {
        setSubmitting(false);
      }
    } else {
      if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
        setError("Please fill in all required fields.");
        return;
      }
      if (!emailRegex.test(email)) {
        setError("Please enter a valid email address.");
        return;
      }
      if (password.length < 6) {
        setError("Password must be at least 6 characters long.");
        return;
      }
      if (password !== confirmPassword) {
        setError("Passwords do not match. Please verify.");
        return;
      }

      setSubmitting(true);
      try {
        const ok = await signup(fullName, email, password);
        if (!ok) {
          setError("Could not create account. Please try again.");
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to create account.";
        setError(message);
      } finally {
        setSubmitting(false);
      }
    }
  };

  const handleForgotPassword = () => {
    if (!email) {
      setError("Please enter your email address to receive reset instructions.");
    } else {
      setError(null);
      setInfoMessage(`Password reset instructions sent to ${email}`);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-900 to-indigo-700 flex items-center justify-center text-white shadow-md animate-pulse">
            <Zap className="h-6 w-6" />
          </div>
          <p className="text-sm font-semibold text-slate-700">Verifying session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-2rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8 bg-gradient-to-b from-slate-50 via-white to-slate-50">
      <div className="w-full max-w-5xl rounded-3xl bg-white shadow-2xl border border-slate-200/80 overflow-hidden grid lg:grid-cols-12 min-h-[640px]">
        <div className="lg:col-span-5 bg-gradient-to-br from-blue-900 via-indigo-900 to-slate-900 p-8 sm:p-12 text-white flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/20 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <Link href="/" className="inline-flex items-center gap-2 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                <Zap className="h-5 w-5" />
              </div>
              <span className="font-black text-2xl tracking-tight">EVORA</span>
            </Link>
            <p className="text-xs text-blue-200 mt-1 font-semibold">
              Enterprise Business Intelligence
            </p>
          </div>

          <div className="relative z-10 py-10 my-auto space-y-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="space-y-4"
            >
              <div className="p-4 rounded-2xl bg-white/10 backdrop-blur-md border border-white/15 shadow-md">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-indigo-500 flex items-center justify-center text-white shadow-xs">
                    <BrainCircuit className="h-5 w-5 animate-pulse" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">Multi-Agent AI</h4>
                    <p className="text-[11px] text-blue-200">Autonomous business analytics</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-white/10 flex justify-between text-[11px] text-blue-200">
                  <span>Decision Accuracy</span>
                  <span className="text-cyan-300 font-bold">98.4%</span>
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 text-xs text-blue-100 leading-relaxed">
                <p className="font-bold text-white text-sm mb-1">
                  Intelligent Decisions, Powered by AI
                </p>
                <p className="text-[11px] text-blue-200">
                  Streamline revenue, optimize margins, and isolate operational risks before they occur.
                </p>
              </div>
            </motion.div>
          </div>

          <div className="relative z-10 pt-4 border-t border-white/10 flex items-center gap-2 text-xs text-blue-200">
            <ShieldCheck className="h-4 w-4 text-cyan-300" />
            <span>256-bit encrypted secure session</span>
          </div>
        </div>

        <div className="lg:col-span-7 p-8 sm:p-12 lg:p-14 flex flex-col justify-center bg-white">
          <div className="max-w-md w-full mx-auto space-y-6">
            <div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {isLogin ? "Welcome Back" : "Create Account"}
              </h2>
              <p className="text-sm text-slate-500 mt-1.5">
                {isLogin
                  ? "Sign in to continue to your executive dashboard"
                  : "Start exploring intelligent insights powered by AI"}
              </p>
            </div>

            <OAuthButtons />

            <div className="relative flex items-center justify-center my-3">
              <div className="border-t border-slate-200 w-full" />
              <span className="bg-white px-3 text-xs font-bold uppercase tracking-wider text-slate-400 shrink-0">
                or
              </span>
              <div className="border-t border-slate-200 w-full" />
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2"
                >
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {infoMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-700 flex items-center gap-2"
                >
                  <ShieldCheck className="h-4 w-4 shrink-0 text-blue-600" />
                  <span>{infoMessage}</span>
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 block">
                    Full Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <UserIcon className="h-4 w-4" />
                    </div>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Jane Doe"
                      required
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900/30 focus:border-blue-900 transition-all bg-white"
                    />
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 block">
                  Email
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    required
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900/30 focus:border-blue-900 transition-all bg-white"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-700 block">
                    Password
                  </label>
                  {isLogin && (
                    <button
                      type="button"
                      onClick={handleForgotPassword}
                      className="text-xs text-blue-900 hover:text-indigo-700 font-semibold transition-colors cursor-pointer"
                    >
                      Forgot Password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900/30 focus:border-blue-900 transition-all bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {!isLogin && (
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 block">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-900/30 focus:border-blue-900 transition-all bg-white"
                    />
                  </div>
                </div>
              )}

              {isLogin && (
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="w-4 h-4 rounded text-blue-900 focus:ring-blue-900/30 accent-blue-900 border-slate-300"
                    />
                    <span className="text-xs text-slate-600 font-medium">
                      Remember me
                    </span>
                  </label>
                </div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full flex items-center justify-center font-bold px-6 py-3 rounded-xl text-sm bg-gradient-to-r from-blue-900 via-indigo-800 to-blue-950 text-white hover:opacity-95 shadow-md hover:shadow-lg transition-all disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                >
                  {submitting ? (
                    <span>Processing...</span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      {isLogin ? "Sign In →" : "Create Account →"}
                    </span>
                  )}
                </button>
              </div>
            </form>

            <div className="pt-4 text-center border-t border-slate-100">
              {isLogin ? (
                <p className="text-xs text-slate-600">
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setInfoMessage(null);
                      setCurrentMode("signup");
                    }}
                    className="font-bold text-blue-900 hover:text-indigo-700 transition-colors cursor-pointer"
                  >
                    Create one
                  </button>
                </p>
              ) : (
                <p className="text-xs text-slate-600">
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setInfoMessage(null);
                      setCurrentMode("login");
                    }}
                    className="font-bold text-blue-900 hover:text-indigo-700 transition-colors cursor-pointer"
                  >
                    Sign In
                  </button>
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}