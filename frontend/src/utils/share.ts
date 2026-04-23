/**
 * Share an invite link.
 *
 * Why this helper exists: WhatsApp does NOT auto-linkify URLs that use raw
 * IPv4 addresses (e.g. http://187.127.25.239/invite/abc). It treats them as
 * plain text, forcing the recipient to select → copy → open browser.
 *
 * Fix: use the native Web Share API on mobile. When `url` is passed as its
 * own field, WhatsApp receives it as a first-class link attachment and
 * renders a preview card — regardless of whether it's an IP or a domain.
 *
 * Desktop falls back to `api.whatsapp.com/send`, which still suffers the
 * IP-linkify limitation; once the app has a real domain behind HTTPS, both
 * paths will produce clickable links.
 */

type ShareInviteInput = {
  title: string;
  url: string;
  /** Message body used ONLY for the desktop fallback text=... URL. */
  text: string;
};

export type ShareOutcome = "native" | "whatsapp_intent" | "cancelled" | "error";

export async function shareInvite(input: ShareInviteInput): Promise<ShareOutcome> {
  const { title, url, text } = input;

  // Prefer the native share sheet on mobile — passing `url` separately is
  // what makes WhatsApp render a link preview instead of plain text.
  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share({ title, text, url });
      return "native";
    } catch (err) {
      // User dismissed the sheet — AbortError is expected, no toast.
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
