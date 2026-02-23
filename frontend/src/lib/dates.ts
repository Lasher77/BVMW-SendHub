const BERLIN = "Europe/Berlin";

/** ISO-String → "DD.MM.YYYY, HH:mm" in Berliner Zeit */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "–";
  return new Date(isoString).toLocaleString("de-DE", {
    timeZone: BERLIN,
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** ISO-String → "DD.MM.YYYY" in Berliner Zeit */
export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return "–";
  return new Date(isoString).toLocaleDateString("de-DE", {
    timeZone: BERLIN,
    day: "2-digit", month: "2-digit", year: "numeric",
  });
}

/**
 * ISO-String → "YYYY-MM-DDTHH:mm" in Berliner Zeit
 * Für datetime-local Inputs: zeigt dem User die korrekte Berliner Ortszeit.
 */
export function toDatetimeLocalBerlin(isoString: string | null | undefined): string {
  if (!isoString) return "";
  return new Date(isoString)
    .toLocaleString("sv-SE", { timeZone: BERLIN })
    .replace(" ", "T")
    .slice(0, 16);
}

/**
 * "YYYY-MM-DDTHH:mm" (Berliner Ortszeit aus datetime-local Input) → UTC ISO-String
 * Berücksichtigt Sommer-/Winterzeit automatisch.
 */
export function berlinToISO(localStr: string): string {
  if (!localStr) return "";
  // Parse als wäre es UTC, dann Berlin-Offset bestimmen und korrigieren
  const assumedUTC = new Date(localStr + "Z");
  const berlinStr = assumedUTC
    .toLocaleString("sv-SE", { timeZone: BERLIN })
    .replace(" ", "T")
    .slice(0, 16);
  const offsetMs = assumedUTC.getTime() - new Date(berlinStr + "Z").getTime();
  return new Date(assumedUTC.getTime() + offsetMs).toISOString();
}
