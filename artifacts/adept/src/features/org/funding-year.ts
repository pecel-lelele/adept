/** Budget periods use Malaysia's calendar, including the UTC New Year boundary. */
export function currentBudgetYear(now = new Date()): number {
  return Number(new Intl.DateTimeFormat("en", {
    year: "numeric", timeZone: "Asia/Kuala_Lumpur",
  }).format(now));
}

export function fundingYear(value: string | undefined): number {
  const year = value && /^\d{4}$/.test(value) ? Number(value) : NaN;
  return Number.isInteger(year) && year >= 2020 && year <= 2200 ? year : currentBudgetYear();
}
