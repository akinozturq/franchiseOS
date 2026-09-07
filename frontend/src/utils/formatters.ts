export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "0,00 ₺";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0,00 ₺";
  
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "%0,00";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "%0,00";
  
  // If given as 0.35, show %35,00. If already given as 35, show %35,00
  const normalized = num <= 1 && num > 0 ? num * 100 : num;
  return `%${normalized.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  try {
    const parts = dateString.split("-");
    if (parts.length === 3) {
      return `${parts[2]}.${parts[1]}.${parts[0]}`;
    }
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString("tr-TR");
  } catch {
    return dateString;
  }
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "0";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0";
  return new Intl.NumberFormat("tr-TR").format(num);
}
