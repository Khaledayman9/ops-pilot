"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

type NavVariant = "home" | "inner" | "auth";

export default function NavBar({
  variant = "inner",
}: {
  variant?: NavVariant;
}) {
  return (
    <nav className="fixed top-0 w-full z-50 border-b border-border-1 bg-void/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Zap size={18} className="text-plasma" />
          <span className="font-display font-semibold text-chrome tracking-tight text-sm">
            ops<span className="text-plasma">-pilot</span>
          </span>
        </Link>

        {variant === "home" && (
          <div className="flex items-center gap-5 text-xs font-mono">
            <a
              href="#orchestration"
              className="text-chrome-dim hover:text-plasma transition-colors hidden md:block"
            >
              Orchestration
            </a>
            <Link
              href="/help"
              className="text-chrome-dim hover:text-plasma transition-colors hidden sm:block"
            >
              Help
            </Link>
            <Link
              href="/contact"
              className="text-chrome-dim hover:text-plasma transition-colors hidden sm:block"
            >
              Contact
            </Link>
            <Link
              href="/settings"
              className="text-chrome-dim hover:text-plasma transition-colors hidden sm:block"
            >
              Settings
            </Link>
            <Link
              href="/chat"
              className="px-4 py-1.5 bg-plasma text-void font-display font-semibold rounded text-xs hover:bg-plasma-dim transition-colors"
            >
              LAUNCH
            </Link>
          </div>
        )}

        {variant === "inner" && (
          <div className="flex items-center gap-5 text-xs font-mono text-chrome-dim">
            <Link href="/" className="hover:text-plasma transition-colors">
              Home
            </Link>
            <Link href="/chat" className="hover:text-plasma transition-colors">
              Chat
            </Link>
            <Link
              href="/settings"
              className="hover:text-plasma transition-colors"
            >
              Settings
            </Link>
          </div>
        )}

        {variant === "auth" && (
          <div className="flex items-center gap-5 text-xs font-mono text-chrome-dim">
            <Link href="/" className="hover:text-plasma transition-colors">
              Home
            </Link>
            <Link href="/chat" className="hover:text-plasma transition-colors">
              Chat
            </Link>
            <Link
              href="/settings"
              className="hover:text-plasma transition-colors"
            >
              Settings
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
