/**
 * Share an invite link.
 *
 * Why this helper exists: WhatsApp does NOT auto-linkify URLs that use raw
 * IPv4 addresses (e.g. http://187.127.25.239/invite/abc). It treats them
 * as plain text. To make the link clickable in the recipient's WhatsApp
 * we route through the backend's is.gd shortener which returns an HTTPS
 * short URL that WhatsApp WILL linkify even when the underlying app is on
 * plain HTTP. Once the app moves to HTTPS + a real domain this hop can
 * be retired.
 */
import apiClient from "@/api/client";

type ShareInviteInput = {
  title: string;
  url: string;
  /** Bet invite token, used to fetch the cached short URL. */
  inviteToken?: string;
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
  const { title, url, text, inviteToken } = input;

  const linkUrl = inviteToken ? await getShortInviteUrl(inviteToken, url) : url;

  // Prefer the native share sheet on mobile — passing `url` separately is
  // what makes WhatsApp render a link preview instead of plain text.
  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share({ title, text, url: linkUrl });
      return "native";
    } catch (err) {
      // User dismissed the sheet — AbortError is expected, no toast.
      if ((err as DOMException)?.name === "AbortError") return "cancelled";
      // Anything else: fall through to the WhatsApp web intent.
    }
  }

  try {
    const body = `${text}\n\n${linkUrl}`;
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
