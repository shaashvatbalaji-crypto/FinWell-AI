// ==========================================
// FINWELL AI — CURRENCY & FORMATTING HELPERS
// ==========================================

export function getCurrencySymbol(currency: string = 'INR'): string {
  const code = (currency || 'INR').trim().toUpperCase();
  switch (code) {
    case 'INR':
      return '₹';
    case 'USD':
      return '$';
    case 'EUR':
      return '€';
    case 'GBP':
      return '£';
    default:
      return '₹';
  }
}

export function formatCurrency(
  amount: number,
  currency: string = 'INR',
  options?: { minimumFractionDigits?: number; maximumFractionDigits?: number }
): string {
  const symbol = getCurrencySymbol(currency);
  const minDigits = options?.minimumFractionDigits ?? 2;
  const maxDigits = options?.maximumFractionDigits ?? 2;
  const val = typeof amount === 'number' && !isNaN(amount) ? amount : 0;
  
  return `${symbol}${val.toLocaleString('en-IN', {
    minimumFractionDigits: minDigits,
    maximumFractionDigits: maxDigits,
  })}`;
}
