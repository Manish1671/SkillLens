import Link from "next/link";

export function LogoMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.15" opacity="0.22" />
      <circle cx="16" cy="16" r="9.25" stroke="currentColor" strokeWidth="1.35" opacity="0.55" />
      <circle cx="16" cy="16" r="4.1" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="1.55" fill="currentColor" />
      <circle cx="22.5" cy="9.5" r="1.15" fill="currentColor" opacity="0.7" />
    </svg>
  );
}

export function Logo({ href = "/", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="group inline-flex items-center gap-2.5 text-ink">
      <span className="text-accent">
        <LogoMark className="h-6 w-6" />
      </span>
      {!compact ? (
        <span className="text-[15px] font-semibold tracking-tight">
          Skill<span className="text-accent">Lens</span>
        </span>
      ) : null}
    </Link>
  );
}
