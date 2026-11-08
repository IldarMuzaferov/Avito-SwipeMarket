import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ShareState, WishlistItem } from '../api/types';
import { useAuth } from '../components/Auth';
import { ChevronRight, GiftIcon, ShareIcon } from '../components/Icons';
import ShareModal from '../components/ShareModal';
import { useToast } from '../components/Toast';
import { EmptyState, NetworkError, Spinner } from '../components/ui';
import WishCard from '../components/WishCard';
import { plural } from '../lib/utils';

export default function Wishlist() {
  const toast = useToast();
  const { setWishlistCount } = useAuth();
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [count, setCount] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [share, setShare] = useState<ShareState>({ enabled: false, url: null });
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [more, setMore] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  const load = useCallback(async () => {
    setState('loading');
    try {
      const r = await api.wishlist({ limit: 24 });
      setItems(r.items);
      setCount(r.count);
      setCursor(r.next_cursor ?? null);
      setShare(r.share ?? { enabled: false, url: null });
      setWishlistCount(r.count);
      setState('ready');
    } catch {
      setState('error');
    }
  }, [setWishlistCount]);
  useEffect(() => { load(); }, [load]);

  const loadMore = async () => {
    if (!cursor) return;
    setMore(true);
    try {
      const r = await api.wishlist({ limit: 24, cursor });
      setItems((l) => [...l, ...r.items.filter((x) => !l.some((y) => y.listing_id === x.listing_id))]);
      setCursor(r.next_cursor ?? null);
    } catch {
      toast({ text: 'Не удалось загрузить ещё' });
    } finally {
      setMore(false);
    }
  };

  const remove = async (it: WishlistItem) => {
    const idx = items.findIndex((x) => x.listing_id === it.listing_id);
    setItems((l) => l.filter((x) => x.listing_id !== it.listing_id));
    setCount((c) => c - 1);
    setWishlistCount(Math.max(0, count - 1));
    try {
      await api.removeFromWishlist(it.listing_id);
      toast({
        text: 'Товар убран из вишлиста',
        actionLabel: 'Вернуть',
        duration: 6000,
        onAction: async () => {
          try {
            await api.addToWishlist(it.listing_id);
            setItems((l) => {
              const copy = [...l];
              copy.splice(Math.min(idx, copy.length), 0, it);
              return copy;
            });
            setCount((c) => c + 1);
            setWishlistCount(count);
          } catch {
            toast({ text: 'Не удалось вернуть товар' });
          }
        },
      });
    } catch {
      setItems((l) => {
        const copy = [...l];
        copy.splice(Math.min(idx, copy.length), 0, it);
        return copy;
      });
      setCount((c) => c + 1);
      setWishlistCount(count);
      toast({ text: 'Не удалось убрать товар. Попробуйте ещё раз' });
    }
  };

  if (state === 'loading') return <div className="center-pad"><Spinner /></div>;
  if (state === 'error') return <NetworkError onRetry={load} />;

  return (
    <div className="container page">
      <div className="page-head">
        <div>
          <h1>Вишлист</h1>
          <p className="muted">{count} {plural(count, ['товар', 'товара', 'товаров'])}</p>
        </div>
        <button className="btn btn-soft" onClick={() => setShareOpen(true)}><ShareIcon size={18} /> Поделиться</button>
      </div>

      <button className="access-bar" onClick={() => setShareOpen(true)}>
        <i className={`dot ${share.enabled ? 'on' : ''}`} />
        <span>Доступ по ссылке: {share.enabled ? 'включён' : 'выключен'}</span>
        <ChevronRight size={16} />
      </button>

      {items.length === 0 ? (
        <EmptyState icon={<GiftIcon size={44} />} title="В вишлисте пока пусто" text="Свайпайте товары вправо — они появятся здесь, и друзья смогут выбрать подарок">
          <Link to="/swipe" className="btn btn-primary">Перейти в Свайп</Link>
        </EmptyState>
      ) : (
        <>
          <div className="wl-grid">
            {items.map((it) => (
              <WishCard key={it.listing_id} item={it} mode="own" onRemove={remove} />
            ))}
          </div>
          {cursor && (
            <div className="more-row">
              <button className="btn btn-secondary" onClick={loadMore} disabled={more}>{more ? 'Загрузка…' : 'Показать ещё'}</button>
            </div>
          )}
        </>
      )}

      {shareOpen && <ShareModal share={share} onChange={setShare} onClose={() => setShareOpen(false)} />}
    </div>
  );
}
