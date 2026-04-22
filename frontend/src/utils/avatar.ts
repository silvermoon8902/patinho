/** Deterministic color + initial from a username, for avatar fallbacks. */

// Ten distinct high-contrast palette colors (navy text on all).
const PALETTE = [
  "#FFE58F", "#FFD10D", "#FFB347", "#FF8A65",
  "#9FE8A6", "#7DCFB6", "#90CAF9", "#BEAEEA",
  "#F48FB1", "#FFAB91",
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return h;
}

export function avatarColor(username: string | null | undefined): string {
  if (!username) return PALETTE[0];
  return PALETTE[hash(username) % PALETTE.length];
}

export function avatarInitial(username: string | null | undefined): string {
  const u = (username || "").trim();
  if (!u) return "?";
  return u[0].toUpperCase();
}
