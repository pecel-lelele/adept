/** Presentation names mirror taxonomy/skills.csv. IDs remain unchanged in requests. */
export const SKILL_NAMES: Readonly<Record<string, string>> = {
  excel: "Spreadsheet analysis",
  sql: "SQL",
  python: "Python programming",
  "data-visualisation": "Data visualisation",
  "process-mapping": "Business process mapping",
  rpa: "Robotic process automation",
  "prompt-engineering": "Prompt engineering",
  "ai-literacy": "AI literacy & responsible AI",
  "risk-compliance": "Risk & compliance",
  "customer-service": "Customer service",
  "logistics-planning": "Logistics planning",
  "manual-data-entry": "Manual data entry",
};

/** Prefer the API label; use a readable fallback while independently owned APIs evolve. */
export function skillName(id: string, label?: string): string {
  return label || SKILL_NAMES[id] || entityName(id);
}

export function entityName(id: string): string {
  return id.split(/[-_ ]+/).map(word =>
    ["ai", "sql", "rpa", "hr", "hrd", "sdg", "tvet"].includes(word.toLowerCase())
      ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1),
  ).join(" ");
}
