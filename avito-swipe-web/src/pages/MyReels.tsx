import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ApiError } from '../api/client';
import type { MyReel } from '../api/types';
import PromotionModal from '../components/PromotionModal';
import { useToast } from '../components/Toast';
import { EmptyState, NetworkError, Spinner } from '../components/ui';
import { SwipeIcon } from '../components/Icons';
import { formatPrice, gradientFor, shortDate } from '../lib/utils';

function statusView(r: MyReel): { label: string; cls: string } {
  const until = (r.stats?.promotion ?? r.promotion)?.active_until;
  if (r.status === 'published' && until) return { label: `Продвигается до ${shortDate(until)}`, cls: 'promo' };
  switch (r.status) {
    case 'published': return { label: 'Опубликован в Свайпе', cls: 'pub' };
    case 'moderation': return { label: 'На модерации', cls: 'mod' };
    case 'processing': return { label: 'Обрабатывается', cls: 'mod' };
    case 'rejected': return { label: `Отклонён${r.reject_reason ? `: ${r.reject_reason}` : ''}`, cls: 'rej' };
    case 'draft': return { label: 'Черновик', cls: 'off' };
    default: return { label: 'Выключен', cls: 'off' };
  }
}

export default function MyReels() {
  const toast = useToast();
  const [items, setItems] = useState<MyReel[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error' | 'forbidden'>('loading');
  const [promoFor, setPromoFor] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState('loading');
    try {
      const r = await api.myReels({ limit: 30 });
      setItems(r.items);
      setCursor(r.next_cursor ?? null);
      setState('ready');
    } catch (e) {
      setState(e instanceof ApiError && e.status === 403 ? 'forbidden' : 'error');
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const loadMore = async () => {
    if (!cursor) return;
    try {
      const r = await api.myReels({ limit: 30, cursor });
      setItems((l) => [...l, ...r.items]);
      setCursor(r.next_cursor ?? null);
    } catch {
      toast({ text: 'Не удалось загрузить ещё' });
    }
  };

  const toggle = async (r: MyReel) => {
    try {
      await api.patchReel(r.reel_id, { enabled: r.status === 'disabled' });
      load();
    } catch (e: any) {
      toast({ text: e?.message ?? 'Не удалось изменить статус' });
    }
  };

  if (state === 'loading') return <div className="center-pad"><Spinner /></div>;
  if (state === 'error') return <NetworkError onRetry={load} />;
  if (state === 'forbidden')
    return (
      <div className="container page">
        <h1>Мои объявления</h1>
        <p className="off-note">Эта страница для продавцов. В меню профиля (аватар справа вверху) выберите «Демо: войти как → Продавец».</p>
      </div>
    );

  return (
    <div className="container page">
      <div className="page-head">
        <h1>Мои объявления</h1>
        <Link to="/seller/reel" className="btn btn-primary"><SwipeIcon size={18} /> Создать рилс</Link>
      </div>

      {items.length === 0 ? (
        <EmptyState icon={<SwipeIcon size={44} />} title="Пока нет рилсов" text="Добавьте видео или фото к объявлению — покупатели увидят его в Свайпе">
          <Link to="/seller/reel" className="btn btn-primary">Создать рилс</Link>
        </EmptyState>
      ) : (
        <div className="reel-rows">
          {items.map((r) => {
            const sv = statusView(r);
            const hasPromo = !!(r.stats?.promotion ?? r.promotion)?.active_until;
            return (
              <div className="reel-row" key={r.reel_id}>
                <div className="rr-cover" style={{ background: r.cover_url ? `center/cover url(${r.cover_url})` : gradientFor(r.listing_id) }} />
                <div className="rr-main">
                  <b className="rr-title">{r.title}</b>
                  <b>{formatPrice(r.price)}</b>
                  {r.stats && (r.stats.views != null || r.stats.likes != null) && (
                    <small>В Свайпе: {r.stats.views ?? 0} показов · {r.stats.likes ?? 0} в вишлисте</small>
                  )}
                </div>
                <div className="rr-side">
                  <span className={`status ${sv.cls}`}>{sv.label}</span>
                  {r.status === 'rejected' && <Link className="link-btn inline" to={`/seller/reel?listing=${r.listing_id}`}>Исправить</Link>}
                  {r.status === 'published' && !hasPromo && <button className="link-btn inline" onClick={() => setPromoFor(r.reel_id)}>Продвинуть</button>}
                  {(r.status === 'published' || r.status === 'disabled') && (
                    <button className="link-btn inline muted-link" onClick={() => toggle(r)}>{r.status === 'disabled' ? 'Включить' : 'Выключить'}</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {cursor && <div className="more-row"><button className="btn btn-secondary" onClick={loadMore}>Показать ещё</button></div>}
      {promoFor && <PromotionModal reelId={promoFor} onClose={(b) => { setPromoFor(null); if (b) load(); }} />}
    </div>
  );
}
