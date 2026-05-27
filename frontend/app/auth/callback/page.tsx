"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Zap } from "lucide-react";
import { finishOAuth } from "../../lib/apis";

export default function OAuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    async function complete() {
      const provider = params.get("provider") as "google" | "github" | null;
      const code = params.get("code");

      if (!provider || !code) {
        setError("Missing OAuth provider or code.");
        return;
      }

      try {
        const redirectUri = `${window.location.origin}/auth/callback?provider=${provider}`;
        await finishOAuth(provider, code, redirectUri);
        router.push("/chat");
      } catch (err) {
        setError(err instanceof Error ? err.message : "OAuth callback failed.");
      }
    }

    complete();
  }, [params, router]);

  return (
    <div className="min-h-screen bg-void grid-bg flex items-center justify-center px-4 text-chrome">
      <div className="bg-surface-1 border border-border-1 rounded-xl p-8 w-full max-w-md text-center">
        <Zap size={24} className="text-plasma mx-auto mb-4" />
        {error ? (
          <>
            <h1 className="font-display text-xl font-bold mb-2">
              Sign in failed
            </h1>
            <p className="text-sm text-ember font-mono">{error}</p>
          </>
        ) : (
          <>
            <Loader2
              size={24}
              className="text-plasma mx-auto mb-4 animate-spin"
            />
            <h1 className="font-display text-xl font-bold mb-2">
              Completing sign in
            </h1>
            <p className="text-sm text-chrome-dim font-mono">Please wait...</p>
          </>
        )}
      </div>
    </div>
  );
}
