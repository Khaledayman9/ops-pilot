"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ChevronDown,
  LogIn,
  LogOut,
  Moon,
  Settings,
  Sun,
  User,
} from "lucide-react";
import { getAccessToken, clearTokens } from "../lib/apis";
import { useRouter } from "next/navigation";

export default function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const router = useRouter();

  useEffect(() => {
    function syncAuth() {
      setAuthed(Boolean(getAccessToken()));
    }
    syncAuth();
    const interval = setInterval(syncAuth, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const savedTheme =
      typeof window !== "undefined"
        ? localStorage.getItem("ops-pilot-theme")
        : null;
    const initialTheme = savedTheme === "light" ? "light" : "dark";
    setTheme(initialTheme);
    document.documentElement.dataset.theme = initialTheme;
  }, []);

  function handleLogout() {
    clearTokens();
    setAuthed(false);
    setOpen(false);
    router.push("/login");
  }

  function toggleTheme() {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("ops-pilot-theme", next);
      return next;
    });
  }

  return (
    <div className="fixed top-3 right-6 z-[70] flex items-start gap-2">
      <button
        type="button"
        onClick={toggleTheme}
        className="w-9 h-9 rounded-lg border border-border-1 bg-void/90 backdrop-blur text-chrome-dim hover:border-plasma hover:text-plasma transition-colors flex items-center justify-center"
        aria-label="Toggle theme"
        title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      >
        {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
      </button>

      <div className="relative">
        <button
          onClick={() => setOpen((value) => !value)}
          className="flex items-center gap-2 px-3 py-2 border border-border-1 rounded-lg bg-void/90 backdrop-blur text-xs font-mono text-chrome-dim hover:border-plasma hover:text-plasma transition-colors"
        >
          <User size={14} />
          Profile
          <ChevronDown size={13} />
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-48 bg-surface-1 border border-border-1 rounded-lg p-2 shadow-xl">
            {authed ? (
              <>
                <Link
                  href="/profile"
                  className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
                >
                  <User size={13} />
                  View profile
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-ember transition-colors"
                >
                  <LogOut size={13} />
                  Logout
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
              >
                <LogIn size={13} />
                Login
              </Link>
            )}

            <Link
              href="/settings"
              className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
            >
              <Settings size={13} />
              Settings
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
