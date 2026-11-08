import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import { ApiError } from '../api/client';
import type { PublicWishlist } from '../api/types';
import { GiftIcon } from '../components/Icons';
import { Avatar, EmptyState, NetworkError, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';
import WishCard from '../components/WishCard';
import { plural } from '../lib/utils';

export default function PublicWishlistPage() {
  const { token = '' } = useParams();
  const toast = useToast();
  const [data, setData] = useState<PublicWishlist | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'network' | 'notfound' | 'disabled'>('loading');
  const [more, setMore] = useState(false);

  const load = useCallback(async () => {
    setState('loading');
    try {
      const r = await api.publicWishlist(token, { limit: 24 });
      setData(r);
      setCursor(r.next_cursor ?? null);
      setState('ready');
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setState('notfound');
      else if (e instanceof ApiError && e.status === 410) setState('disabled');
      else setState('network');
    }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const loadMore = async () => {
    if (!cursor || !data) return;
    setMore(true);
    try {
      const r = await api.publicWishlist(token, { limit: 24, cursor });
      setData({ ...data, items: [...data.items, ...r.items] });
      setCursor(r.next_cursor ?? null);
    } catch {
      toast({ text: 'Не удалось загрузить ещё' });
    } finally {
      setMore(false);
    }
  };

  if (state === 'loading') return <div className="center-pad"><Spinner /></div>;
  if (state === 'network') return <NetworkError onRetry={load} />;
  if (state === 'notfound' || state === 'disabled' || !data)
    return (
      <EmptyState
        icon={<GiftIcon size={44} />}
        title="Вишлист недоступен"
        text={state === 'disabled' ? 'Владелец отключил доступ по ссылке' : 'Ссылка недействительна или устарела'}
      >
        <Link to="/swipe" className="btn btn-primary">Открыть Свайп</Link>
      </EmptyState>
    );

  return (
    <div className="container page">
      <div className="page-head">
        <div className="owner">
          <Avatar name={data.owner.display_name} url={data.owner.avatar_url} size={48} />
          <div>
            <h1>Вишлист: {data.owner.display_name}</h1>
            <p className="muted">{data.count} {plural(data.count, ['товар', 'товара', 'товаров'])} · купите на Авито и подарите лично</p>
          </div>
        </div>
      </div>
      {data.items.length === 0 ? (
        <EmptyState icon={<GiftIcon size={44} />} title="Здесь пока пусто" text="Владелец ещё не добавил товары в вишлист" />
      ) : (
        <>
          <div className="wl-grid">
            {data.items.map((it) => (
              <WishCard key={it.listing_id} item={it} mode="public" />
            ))}
          </div>
          {cursor && (
            <div className="more-row">
              <button className="btn btn-secondary" onClick={loadMore} disabled={more}>{more ? 'Загрузка…' : 'Показать ещё'}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
