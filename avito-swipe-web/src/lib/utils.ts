import { api } from '../api';
import type { Price } from '../api/types';

export function formatPrice(p: Price | null | undefined): string {
  if (!p) return '';
  const n = new Intl.NumberFormat('ru-RU').format(p.amount).replace(/\u00a0|\u202f/g, '\u00a0');
  const cur = p.currency === 'RUB' ? '₽' : p.currency;
  return `${n}\u00a0${cur}`;
}

export function formatRating(r?: number | null): string {
  return r == null ? '' : r.toFixed(1).replace('.', ',');
}

export function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

// Градиенты-заглушки как в макете, когда у товара нет картинки
const GRADIENTS = [
  ['#ffb86b', '#ff5c8c'], ['#33c7bd', '#1a66d9'], ['#9973f2', '#404dd9'], ['#8cd980', '#1a9980'],
  ['#ffd959', '#ff8c40'], ['#f299b2', '#994db2'], ['#6bb4ff', '#4d6be8'], ['#e8806b', '#994d4d'],
];
export function gradientFor(key: string): string {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  const [a, b] = GRADIENTS[h % GRADIENTS.length];
  return `linear-gradient(135deg, ${a} 7%, ${b} 79%)`;
}

export function shortDate(iso?: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }).replace('.', '');
}

export function isVideoUrl(url: string): boolean {
  return /\.(mp4|mov|webm|m4v)(\?|$)/i.test(url);
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }
}

// «Открыть товар»: страница объявления на Авито. Окно открываем сразу (иначе блокирует браузер),
// а адрес подставляем, когда придёт ответ GET /listings/{id}.
export async function openListing(listingId: string): Promise<void> {
  const w = window.open('about:blank', '_blank');
  try {
    const l = await api.listing(listingId);
    if (w) {
      w.opener = null;
      w.location.href = l.listing_url;
    } else {
      window.location.href = l.listing_url;
    }
  } catch (e) {
    w?.close();
    throw e;
  }
}

export function videoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const v = document.createElement('video');
    v.preload = 'metadata';
    v.onloadedmetadata = () => {
      URL.revokeObjectURL(v.src);
      resolve(v.duration);
    };
    v.onerror = () => reject(new Error('bad video'));
    v.src = URL.createObjectURL(file);
  });
}

export function plural(n: number, forms: [string, string, string]): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return forms[0];
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return forms[1];
  return forms[2];
}
