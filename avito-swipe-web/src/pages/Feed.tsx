import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { ApiError } from '../api/client';
import type { FeedCard, SwipeAction } from '../api/types';
import { useAuth } from '../components/Auth';
import { ArrowDown, ArrowUp, CloseIcon, GiftIcon } from '../components/Icons';
import SwipeCard, { type Glow, type SwipeCardHandle } from '../components/SwipeCard';
import { useToast } from '../components/Toast';
import { EmptyState, NetworkError, Spinner } from '../components/ui';
import WishlistPanel from '../components/WishlistPanel';
import { gradientFor, uuid } from '../lib/utils';

type Done = { card: FeedCard; action: SwipeAction };

function ActionButton(p: { kind: 'dislike' | 'like' | 'back' | 'skip'; onClick: () => void; disabled?: boolean }) {
  const map = {
    dislike: { icon: <CloseIcon size={29} />, label: 'Не то', cls: 'a-dislike' },
    like: { icon: <GiftIcon size={32} />, label: 'Хочу', cls: 'a-like' },
    back: { icon: <ArrowUp size={22} />, label: 'Назад', cls: 'a-back' },
    skip: { icon: <ArrowDown size={22} />, label: 'Пропустить', cls: 'a-skip' },
  }[p.kind];
  return (
    <div className={`action ${map.cls}`}>
      <button onClick={p.onClick} disabled={p.disabled} aria-label={map.label}>{map.icon}</button>
      <span>{map.label}</span>
    </div>
  );
}

function Hint({ onClose }: { onClose: () => void }) {
  return (
    <div className="hint" role="dialog" aria-label="Подсказка по управлению">
      <div className="hint-box">
        <h2>Как листать</h2>
        <ul>
          <li><kbd>→</kbd><span>Свайп вправо — <b>Хочу</b>, товар попадёт в вишлист</span></li>
          <li><kbd>←</kbd><span>Свайп влево — <b>Не то</b>, больше не покажем</span></li>
          <li><kbd>↓</kbd><span>Свайп вниз или колесо мыши — <b>Пропустить</b> (на телефоне — вверх)</span></li>
          <li><kbd>↑</kbd><span><b>Назад</b> — вернуться к предыдущей карточке</span></li>
        </ul>
        <button className="btn btn-primary btn-wide" onClick={onClose}>Понятно</button>
      </div>
    </div>
  );
}

function FeedStage({ showHint, onHintClose }: { showHint: boolean; onHintClose: () => void }) {
  const toast = useToast();
  const { wishlistCount, setWishlistCount } = useAuth();

  const [cards, setCards] = useState<FeedCard[]>([]);
  const [history, setHistory] = useState<Done[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [ended, setEnded] = useState(false);
  const [glow, setGlow] = useState<Glow>({ dir: null, level: 0 });
  const [soundOn, setSoundOn] = useState(false);
  const [panelKey, setPanelKey] = useState(0);

  const cardsRef = useRef<FeedCard[]>([]);
  const cursor = useRef<string | null>(null);
  const session = useRef<string | null>(null);
  const fetching = useRef(false);
  const endedRef = useRef(false);
  const seen = useRef(new Set<string>());
  const swiped = useRef(0);
  const shownAt = useRef(Date.now());
  const undoing = useRef(false);
  const lastWheel = useRef(0);
  const front = useRef<SwipeCardHandle>(null);

  useEffect(() => { cardsRef.current = cards; }, [cards]);
  const frontId = cards[0]?.reel_id;
  useEffect(() => { shownAt.current = Date.now(); }, [frontId]);

  const fetchMore = useCallback(async () => {
    if (fetching.current || endedRef.current) return;
    fetching.current = true;
    try {
      const res = await api.feed({ limit: 10, cursor: cursor.current, session_id: session.current });
      session.current = res.session_id ?? session.current;
      cursor.current = res.next_cursor;
      if (!res.next_cursor || res.items.length === 0) {
        endedRef.current = true;
        setEnded(true);
      }
      const fresh = res.items.filter((c) => !seen.current.has(c.reel_id));
      fresh.forEach((c) => seen.current.add(c.reel_id));
      setCards((prev) => [...prev, ...fresh]);
      setStatus('ready');
    } catch {
      if (cardsRef.current.length === 0) setStatus('error');
    } finally {
      fetching.current = false;
    }
  }, []);

  useEffect(() => { fetchMore(); }, [fetchMore]);
  // подгружаем заранее, когда осталось меньше 4 карточек
  useEffect(() => {
    if (status === 'ready' && cards.length <= 3 && !ended) fetchMore();
  }, [cards.length, status, ended, fetchMore]);

  const sendSwipe = useCallback(
    async (card: FeedCard, action: SwipeAction, clientId: string, dwell: number, position: number) => {
      try {
        const res = await api.swipe({
          reel_id: card.reel_id, action, client_id: clientId, session_id: session.current ?? '', dwell_ms: dwell, position,
        });
        setWishlistCount(res.wishlist_count);
        if (action === 'like') setPanelKey((k) => k + 1);
      } catch (e) {
        if (e instanceof ApiError && e.code === 'listing_unavailable') {
          toast({ text: 'Этот товар уже продан или снят с продажи' });
        } else if (action === 'like') {
          // client_id тот же — повтор безопасен (POST /swipes идемпотентен)
          toast({ text: 'Лайк не сохранился', actionLabel: 'Повторить', duration: 9000, onAction: () => sendSwipe(card, action, clientId, dwell, position) });
        }
      }
    },
    [setWishlistCount, toast],
  );

  const commit = useCallback(
    (action: SwipeAction) => {
      const card = cardsRef.current[0];
      if (!card) return;
      const position = swiped.current++;
      const dwell = Date.now() - shownAt.current;
      setCards((c) => c.slice(1));
      setHistory((h) => [...h, { card, action }].slice(-30));
      setGlow({ dir: null, level: 0 });
      sendSwipe(card, action, uuid(), dwell, position);
    },
    [sendSwipe],
  );

  const undo = useCallback(async () => {
    if (undoing.current) return;
    const last = history[history.length - 1];
    if (!last) return;
    undoing.current = true;
    try {
      const card = (await api.undo()) ?? last.card;
      setCards((c) => [card, ...c.filter((x) => x.reel_id !== card.reel_id)]);
      setHistory((h) => h.slice(0, -1));
      swiped.current = Math.max(0, swiped.current - 1);
      if (last.action === 'like') {
        api.me().then((u) => setWishlistCount(u.wishlist_count)).catch(() => {});
        setPanelKey((k) => k + 1);
      }
    } catch (e) {
      toast({ text: e instanceof ApiError && e.status === 404 ? 'Нечего отменять' : 'Не удалось вернуться назад' });
    } finally {
      undoing.current = false;
    }
  }, [history, setWishlistCount, toast]);

  const blocked = showHint;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (blocked || e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const map: Record<string, () => void> = {
        ArrowRight: () => front.current?.fling('like'),
        ArrowLeft: () => front.current?.fling('dislike'),
        ArrowDown: () => front.current?.fling('skip'),
        ArrowUp: () => undo(),
      };
      const fn = map[e.key];
      if (fn) {
        e.preventDefault();
        fn();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [blocked, undo]);

  const onWheel = (e: React.WheelEvent) => {
    if (blocked || Math.abs(e.deltaY) < 25) return;
    const now = Date.now();
    if (now - lastWheel.current < 700) return;
    lastWheel.current = now;
    front.current?.fling('skip');
  };

  const retry = () => {
    setStatus('loading');
    fetchMore();
  };

  const current = cards[0];
  const next = cards[1];
  const isLoading = status === 'loading' || (!current && !ended && status !== 'error');
  const isEmpty = status === 'ready' && !current && ended;
  const nextImg = next && (next.media.items[0]?.poster ?? (next.media.type !== 'video' ? next.media.items[0]?.url : undefined));

  let center;
  if (status === 'error' && !current) center = <NetworkError onRetry={retry} text="Не удалось загрузить ленту" />;
  else if (isEmpty)
    center = (
      <EmptyState
        icon={<GiftIcon size={44} />}
        title={swiped.current === 0 ? 'Пока нет товаров по вашим интересам' : 'Карточки закончились'}
        text={swiped.current === 0 ? 'Попробуйте выбрать другие категории' : 'Загляните позже — мы подберём новые товары'}
      >
        <Link to="/onboarding?edit=1" className="btn btn-primary">Изменить интересы</Link>
        <Link to="/my/wishlist" className="btn btn-secondary">Открыть вишлист</Link>
      </EmptyState>
    );
  else if (isLoading) center = <div className="card-skel"><Spinner /></div>;

  return (
    <div className="feed" onWheel={onWheel} style={{ '--glow': glow.level } as CSSProperties}>
      <div className={`edge edge-${glow.dir ?? 'none'}`} />
      <div className="feed-grid">
        <aside className="side left">
          {current && <ActionButton kind="dislike" onClick={() => front.current?.fling('dislike')} />}
        </aside>

        <section className="stage">
          {center ? (
            <div className="stage-center">{center}</div>
          ) : (
            <div className="card-slot">
              {next && (
                <div className="back-card" style={{ background: nextImg ? `center/cover url(${nextImg})` : gradientFor(next.reel_id) }} />
              )}
              {current && (
                <SwipeCard
                  key={current.reel_id}
                  ref={front}
                  card={current}
                  soundOn={soundOn}
                  onSound={() => setSoundOn(true)}
                  onCommit={commit}
                  onGlow={setGlow}
                />
              )}
            </div>
          )}
          {/* на телефоне вместо панели — чип со счётчиком */}
          <Link to="/my/wishlist" className="m-wish-chip" aria-label="Вишлист">
            <GiftIcon size={20} /> <b>{wishlistCount > 99 ? '99+' : wishlistCount}</b>
          </Link>
        </section>

        <aside className="side right">
          <WishlistPanel count={wishlistCount} refreshKey={panelKey} />
          {current && (
            <div className="actions">
              <ActionButton kind="like" onClick={() => front.current?.fling('like')} />
              <ActionButton kind="back" onClick={undo} disabled={history.length === 0} />
              <ActionButton kind="skip" onClick={() => front.current?.fling('skip')} />
            </div>
          )}
        </aside>
      </div>
      {showHint && current && <Hint onClose={onHintClose} />}
    </div>
  );
}

export default function Feed() {
  const nav = useNavigate();
  const [gate, setGate] = useState<'check' | 'ok' | 'error'>('check');
  const [hint, setHint] = useState(false);

  const check = useCallback(async () => {
    setGate('check');
    try {
      const o = await api.onboarding();
      if (!o.interests_done) {
        nav('/onboarding', { replace: true });
        return;
      }
      setHint(!o.hint_seen);
      setGate('ok');
    } catch {
      setGate('error');
    }
  }, [nav]);
  useEffect(() => { check(); }, [check]);

  if (gate === 'error') return <NetworkError onRetry={check} />;
  if (gate === 'check') return <div className="center-pad"><Spinner /></div>;
  return (
    <FeedStage
      showHint={hint}
      onHintClose={() => {
        setHint(false);
        api.patchOnboarding(true).catch(() => {});
      }}
    />
  );
}
