export const AADHAAR = /\b([2-9][0-9]{3})[\s\-]?([0-9]{4})[\s\-]?([0-9]{4})\b/g;
export const AADHAAR_MASKED = /\b[Xx*]{4}[\s\-]?[Xx*]{4}[\s\-]?[0-9]{4}\b/g;
export const PAN = /\b([A-Z]{3}[ABCFGHLJPTF][A-Z][0-9]{4}[A-Z])\b/g;

const UPI_PROVIDERS = [
  'paytm','gpay','phonepe','okicici','okhdfcbank','oksbi','okaxis','ybl',
  'axl','apl','ibl','icici','hdfcbank','sbi','upi','freecharge','airtel',
  'jio','amazon','indus','boi','cnrb','psb','aubank','dbs','federal',
  'idfc','kbl','kvb','rbl','scb','tjsb','uco','uboi','unionbank','kotak',
  'pnb','bob','barb','nkgsb','saraswat','mahb','nsdl','hsbc','cub','paribas',
].join('|');

export const UPI = new RegExp(`\\b[\\w.\\-]{2,256}@(?:${UPI_PROVIDERS})\\b`, 'gi');
export const IFSC = /\b([A-Z]{4}0[A-Z0-9]{6})\b/g;
export const MOBILE_IN = /(?<!\d)(?:\+91[\s\-]?|91[\s\-]?|0)?([6-9][0-9]{9})(?!\d)/g;
export const GST = /\b([0-3][0-9][A-Z]{3}[ABCFGHLJPTF][A-Z][0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z])\b/g;
export const BANK_ACCOUNT = /(?:account\s*(?:number|no\.?|#)|a\/?c\s*(?:no\.?|#)|bank\s*a\/?c)[\s:]*([0-9]{9,18})/gi;
export const EMAIL = /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b/g;
export const IPV4 = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;
