import type { ReactNode } from "react";

type IconKind =
  | "bets"
  | "leagues"
  | "wallet"
  | "ranking"
  | "chat"
  | "notifications"
  | "search";

interface EmptyStateProps {
  icon?: IconKind;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

function Icon({ kind }: { kind: IconKind }) {
  const common = {
    width: 72,
    height: 72,
    viewBox: "0 0 120 120",
    fill: "none" as const,
    "aria-hidden": true,
  };
  switch (kind) {
    case "bets":
      return (
        <svg {...common}>
          <rect x="20" y="36" width="80" height="56" rx="14" fill="#FFF3B0" />
          <path
            d="M32 66h56M32 82h36"
            stroke="#001F3F"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="88" cy="32" r="16" fill="#FFD10D" />
          <path d="M80 32l6 6 12-12" stroke="#001F3F" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
      );
    case "leagues":
      return (
        <svg {...common}>
          <rect x="18" y="30" width="84" height="64" rx="14" fill="#E5E7EB" />
          <circle cx="38" cy="54" r="10" fill="#FFD10D" />
          <circle cx="60" cy="54" r="10" fill="#9FE8A6" />
          <circle cx="82" cy="54" r="10" fill="#BEAEEA" />
          <path d="M28 78h64" stroke="#001F3F" strokeWidth="3" strokeLinecap="round" />
        </svg>
      );
    case "wallet":
      return (
        <svg {...common}>
          <rect x="16" y="38" width="88" height="56" rx="14" fill="#FFF3B0" />
          <circle cx="84" cy="66" r="8" fill="#FFD10D" stroke="#001F3F" strokeWidth="2" />
          <path d="M16 48c0-8 6-14 14-14h40l6 8H16z" fill="#FFD10D" />
        </svg>
      );
    case "ranking":
      return (
        <svg {...common}>
          <rect x="44" y="44" width="32" height="52" fill="#FFD10D" />
          <rect x="14" y="60" width="32" height="36" fill="#E5E7EB" />
          <rect x="74" y="68" width="32" height="28" fill="#FDE68A" />
          <circle cx="60" cy="30" r="14" fill="#FFD10D" stroke="#001F3F" strokeWidth="3" />
          <path d="M54 30l4 4 8-8" stroke="#001F3F" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
      );
    case "chat":
      return (
        <svg {...common}>
          <path d="M20 30h80v50H60l-16 14v-14H20z" fill="#E5E7EB" />
          <circle cx="44" cy="55" r="3" fill="#001F3F" />
          <circle cx="60" cy="55" r="3" fill="#001F3F" />
          <circle cx="76" cy="55" r="3" fill="#001F3F" />
        </svg>
      );
    case "notifications":
      return (
        <svg {...common}>
          <path d="M60 24c-11 0-20 9-20 20v14l-8 10h56l-8-10V44c0-11-9-20-20-20z" fill="#FFD10D" stroke="#001F3F" strokeWidth="3" strokeLinejoin="round" />
          <path d="M52 78c0 4 4 8 8 8s8-4 8-8" stroke="#001F3F" strokeWidth="3" strokeLinecap="round" fill="none" />
        </svg>
      );
    case "search":
    default:
      return (
        <svg {...common}>
          <circle cx="52" cy="52" r="24" stroke="#001F3F" strokeWidth="5" fill="#FFF3B0" />
          <path d="M70 70l22 22" stroke="#001F3F" strokeWidth="5" strokeLinecap="round" />
        </svg>
      );
  }
}

export function EmptyState({
  icon = "search",
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={`empty-state-card card ${className ?? ""}`.trim()} role="status">
      <Icon kind={icon} />
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-desc">{description}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

export default EmptyState;
