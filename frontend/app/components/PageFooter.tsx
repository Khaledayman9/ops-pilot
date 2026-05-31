import Link from "next/link";
import { Zap } from "lucide-react";

export default function PageFooter() {
  return (
    <footer className="border-t border-border-1 py-8">
      <div className="max-w-7xl mx-auto px-6 flex flex-wrap gap-4 items-center justify-between text-xs text-chrome-dim font-mono">
        <div className="flex items-center gap-2">
          <Zap size={12} className="text-plasma" />
          ops-pilot v0.1.0
        </div>
        <div className="flex items-center gap-4">
          <Link href="/help" className="hover:text-plasma transition-colors">
            Help
          </Link>
          <Link href="/contact" className="hover:text-plasma transition-colors">
            Contact
          </Link>
        </div>
      </div>
    </footer>
  );
}
