// Turns the raw warnings of a save into a short list: identical messages are merged across sources, and the same rule
// firing for several sounds becomes one entry ("same advice for: …"). Safety levels come first.
import type { Advice } from "./types";

export interface NoticeItem {
  level: Advice["level"];
  message: string;
  sources: string[];   // names of the sources it applies to, only filled when it is not all of the sources concerned
  also: string[];      // other sounds with the same advice (names)
}

const ORDER: Record<Advice["level"], number> = { danger: 0, warning: 1, info: 2 };

export function groupAdvice(
  advice: Advice[], sourceName: (id: string) => string, className: (mid: string) => string, allSources: string[],
): NoticeItem[] {
  // 1. same message on several sources -> one entry listing the sources
  const byMessage = new Map<string, { a: Advice; sources: string[] }>();
  for (const a of advice) {
    const g = byMessage.get(a.message);
    if (g) { if (!g.sources.includes(a.source)) g.sources.push(a.source); } else byMessage.set(a.message, { a, sources: [a.source] });
  }
  // 2. same rule on the same sources, one entry per sound -> one entry plus the other sounds
  const byRule = new Map<string, { a: Advice; sources: string[]; classes: string[] }>();
  for (const { a, sources } of byMessage.values()) {
    const key = `${a.rule}|${a.level}|${[...sources].sort().join(",")}`;
    const mid = a.classes[0];
    const g = byRule.get(key);
    if (g) { if (mid) g.classes.push(mid); } else byRule.set(key, { a, sources, classes: [] });
  }
  const items: NoticeItem[] = [...byRule.values()].map(({ a, sources, classes }) => ({
    level: a.level,
    message: a.message,
    sources: allSources.length > 1 && sources.length < allSources.length ? sources.map(sourceName) : [],
    also: classes.map(className),
  }));
  return items.sort((x, y) => ORDER[x.level] - ORDER[y.level]);
}
