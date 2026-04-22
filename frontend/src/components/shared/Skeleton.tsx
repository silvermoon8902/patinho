import type { CSSProperties } from "react";

type SkeletonShape = "text" | "card" | "avatar" | "rect";

interface SkeletonProps {
  shape?: SkeletonShape;
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  className?: string;
  style?: CSSProperties;
  /** Stack multiple identical lines when shape="text". */
  lines?: number;
}

export function Skeleton({
  shape = "text",
  width,
  height,
  radius,
  className,
  style,
  lines = 1,
}: SkeletonProps) {
  const resolved: CSSProperties = {
    width:
      width ??
      (shape === "avatar"
        ? 44
        : shape === "card"
        ? "100%"
        : shape === "rect"
        ? "100%"
        : undefined),
    height:
      height ??
      (shape === "avatar"
        ? 44
        : shape === "card"
        ? 120
        : shape === "rect"
        ? 16
        : 14),
    borderRadius:
      radius ?? (shape === "avatar" ? "50%" : shape === "card" ? 12 : 6),
    ...style,
  };

  if (shape === "text" && lines > 1) {
    return (
      <div className={`skeleton-group ${className ?? ""}`.trim()}>
        {Array.from({ length: lines }).map((_, i) => (
          <span
            key={i}
            className="skeleton"
            aria-hidden="true"
            style={{
              ...resolved,
              width: i === lines - 1 ? "70%" : resolved.width,
            }}
          />
        ))}
      </div>
    );
  }

  return <span className={`skeleton ${className ?? ""}`.trim()} aria-hidden="true" style={resolved} />;
}

export function SkeletonBetCard() {
  return (
    <div className="card skeleton-bet-card" aria-busy="true">
      <div className="skeleton-bet-card-head">
        <Skeleton width={80} height={22} radius={999} />
        <Skeleton width={64} height={22} radius={999} />
      </div>
      <Skeleton width="80%" height={22} />
      <Skeleton width="60%" height={16} />
      <div className="skeleton-bet-card-meta">
        <Skeleton width={100} height={14} />
        <Skeleton width={80} height={14} />
      </div>
    </div>
  );
}

export function SkeletonListRow() {
  return (
    <div className="skeleton-list-row" aria-busy="true">
      <Skeleton shape="avatar" />
      <div className="skeleton-list-row-body">
        <Skeleton width="50%" height={16} />
        <Skeleton width="30%" height={12} />
      </div>
      <Skeleton width={60} height={18} />
    </div>
  );
}

export default Skeleton;
