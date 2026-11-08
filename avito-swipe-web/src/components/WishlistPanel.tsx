import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { WishlistItem } from '../api/types';
import { gradientFor } from '../lib/utils';
import { ChevronRight, GiftIcon } from './Icons';

// Панель «Вишлист» справа от ленты: счётчик + до 6 миниатюр
export default function WishlistPanel({ count, refreshKey }: { count: number; refreshKey: number }) {
  const [items, setItems] = useState<WishlistItem[]>([]);
  useEffect(() => {
    let alive = true;
    api.wishlist({ limit: 6 }).then((r) => alive && setItems(r.items.slice(0, 6))).catch(() => {});
    return () => { alive = false; };
  }, [refreshKey]);

  return (
    <div className="wl-panel">
      <div className="wl-head">
        <GiftIcon size={22} className="blue" />
        <b>Вишлист</b>
        <span className="count-pill">{count > 99 ? '99+' : count}</span>
      </div>
      {items.length > 0 && (
        <div className="wl-thumbs">
          {items.map((it) => (
            <div
              key={it.listing_id}
              className="thumb"
              title={it.title}
              style={{ background: it.cover_url ? `center/cover url(${it.cover_url})` : gradientFor(it.listing_id) }}
            />
          ))}
        </div>
      )}
      {items.length === 0 && <p className="wl-empty">Свайпайте вправо — товары появятся здесь</p>}
      <Link to="/my/wishlist" className="wl-link">Открыть вишлист <ChevronRight size={16} /></Link>
    </div>
  );
}
