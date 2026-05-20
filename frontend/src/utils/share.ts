/**
 * Share an invite link.
 *
 * On mobile we use the native Web Share sheet (navigator.share) — it lets
 * the user pick WhatsApp and attaches the URL as a real link. On desktop
 * we deliberately SKIP navigator.share: desktop browsers (especially on
 * Linux) open an empty/stuck OS "Share" panel. Desktop goes straight to
 * the WhatsApp Web intent instead.
 */
import apiClient from "@/api/client";

/** True for phones/tablets, where navigator.share is reliable. */
function isMobileDevice(): boolean {
  if (typeof navigator === "undefined") return false;
  const uaData = (navigator as Navigator & {
    userAgentData?: { mobile?: boolean };
  }).userAgentData;
  if (uaData && typeof uaData.mobile === "boolean") return uaData.mobile;
  return /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(
    navigator.userAgent || "",
  );
}

type ShareInviteInput = {
  title: string;
  /**
   * The shareable URL — already resolved by the caller. Components should
   * prefetch the short URL on mount and pass it here so the share-button
   * click stays synchronous (iOS Safari revokes the "user activation
   * context" if you await anything before calling navigator.share).
   */
  url: string;
  /** Message body used ONLY for the desktop fallback text=... URL. */
  text: string;
};

/** Best-effort short URL. Returns the fallback if shortening fails. */
export async function getShortInviteUrl(
  inviteToken: string,
  fallback: string,
): Promise<string> {
  try {
    const res = await apiClient.get(
      `/bets/invite/${inviteToken}/short-url`,
      { timeout: 4000 },
    );
    const u = res.data?.short_url;
    return typeof u === "string" && u ? u : fallback;
  } catch {
    return fallback;
  }
}

export type ShareOutcome = "native" | "whatsapp_intent" | "cancelled" | "error";

export async function shareInvite(input: ShareInviteInput): Promise<ShareOutcome> {
  const { title, url, text } = input;

  // Native share sheet — ONLY on mobile. On desktop navigator.share may
  // exist but opens a broken/empty OS panel, so we skip it there.
  // CRITICAL: do not `await` anything before navigator.share — iOS Safari
  // revokes the user-activation grant if any async work happens between
  // the click handler firing and the share call. The caller resolves the
  // share URL ahead of time and passes it in already-resolved.
  if (
    isMobileDevice() &&
    typeof navigator !== "undefined" &&
    typeof navigator.share === "function"
  ) {
    try {
      await navigator.share({ title, text, url });
      return "native";
    } catch (err) {
      if ((err as DOMException)?.name === "AbortError") return "cancelled";
      // Anything else: fall through to the WhatsApp web intent.
    }
  }

  try {
    const body = `${text}\n\n${url}`;
    const intent = `https://api.whatsapp.com/send?text=${encodeURIComponent(body)}`;
    window.open(intent, "_blank", "noopener,noreferrer");
    return "whatsapp_intent";
  } catch {
    return "error";
  }
}

/** Copy a string to the clipboard, with a legacy fallback for older browsers. */
export async function copyToClipboard(value: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    /* fall through */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = value;
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}
