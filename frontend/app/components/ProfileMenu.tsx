"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown, LogIn, Settings, User, UserPlus } from "lucide-react";
import { getAccessToken } from "../lib/apis";

export default function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(getAccessToken()));
  }, []);

  return (
    <div className="fixed top-3 right-6 z-[70]">
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
            <Link
              href="/profile"
              className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
            >
              <User size={13} />
              View profile
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
              >
                <LogIn size={13} />
                Login
              </Link>
              <Link
                href="/register"
                className="flex items-center gap-2 px-3 py-2 rounded text-xs font-mono text-chrome-dim hover:bg-surface-2 hover:text-plasma"
              >
                <UserPlus size={13} />
                Register
              </Link>
            </>
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
  );
}
