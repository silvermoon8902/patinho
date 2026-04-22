/**
 * Minimal i18n helper. Lookup keys in the pt-BR catalog, fall back to the
 * key itself so missing keys are visible in dev. Supports {{name}}
 * interpolation and a simple pluralization convention (`foo_one` vs
 * `foo_other` pair).
 *
 * This is a foundation — full i18n (locale switching, lazy-loaded
 * catalogs) becomes trivial later by swapping the import below for a
 * loader + adding a React context. For now every string lives in a
 * single file and the SPA is single-locale.
 */
import messages from "./messages.pt-BR.json";

type Dict = Record<string, unknown>;

function resolve(path: string, dict: Dict): string | undefined {
  const parts = path.split(".");
  let cur: unknown = dict;
  for (const p of parts) {
    if (cur && typeof cur === "object" && p in (cur as Dict)) {
      cur = (cur as Dict)[p];
    } else {
      return undefined;
    }
  }
  return typeof cur === "string" ? cur : undefined;
}

function interpolate(s: string, vars: Record<string, string | number> | undefined): string {
  if (!vars) return s;
  return s.replace(/\{\{(\w+)\}\}/g, (_, k) =>
    k in vars ? String(vars[k]) : `{{${k}}}`
  );
}

/** Get a translated string. Falls back to the key if missing. */
export function t(
  key: string,
  vars?: Record<string, string | number>
): string {
  const val = resolve(key, messages as Dict);
  return interpolate(val ?? key, vars);
}

/** Simple pluralization: picks `key_one` / `key_other` based on count. */
export function plural(
  baseKey: string,
  count: number,
  vars: Record<string, string | number> = {}
): string {
  const suffix = count === 1 ? "_one" : "_other";
  return t(`${baseKey}${suffix}`, { count, ...vars });
}

export default { t, plural };
