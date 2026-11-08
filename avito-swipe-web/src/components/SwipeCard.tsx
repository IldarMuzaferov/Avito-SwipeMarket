import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, type CSSProperties, type PointerEvent as RPE } from 'react';
import type { FeedCard, SwipeAction } from '../api/types';
import { track } from '../lib/track';
import { clamp, formatPrice, formatRating, gradientFor, openListing } from '../lib/utils';
import { SoundOff, StarIcon, RetryIcon } from './Icons';
import { Avatar } from './ui';
import { useToast } from './Toast';

export type SwipeCardHandle = { fling: (a: SwipeAction) => void };
export type Glow = { dir: SwipeAction | null; level: number };

type Props = {
  card: FeedCard;
  soundOn: boolean;
  onSound: () => void;
  onCommit: (a: SwipeAction) => void;
  onGlow: (g: Glow) => void;
};

const DEG_PER_PX = 0.09; // 140px ≈ 12.6°
const ANGLE_THRESHOLD = 12; // порог «улетает» из макета
const SKIP_DISTANCE = 100;

const SwipeCard = forwardRef<SwipeCardHandle, Props>(function SwipeCard({ card, soundOn, onSound, onCommit, onGlow }, ref) {
  const toast = useToast();
  const [drag, setDrag] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [fly, setFly] = useState<SwipeAction | null>(null);
  const [idx, setIdx] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [overflow, setOverflow] = useState(false);
  const [mediaErr, setMediaErr] = useState(false);
  const [progress, setProgress] = useState(0);

  const start = useRef<{ x: number; y: number; type: string } | null>(null);
  const moved = useRef(false);
  const committed = useRef(false);
  const dragRef = useRef({ x: 0, y: 0 });
  const skipUp = useRef(false);
  const descRef = useRef<HTMLParagraphElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const items = card.media.items;
  const isVideo = card.media.type === 'video';
  const cur = items[Math.min(idx, items.length - 1)];

  // события для рекомендаций: показ и время просмотра
  useEffect(() => {
    const t0 = Date.now();
    track('view', card.reel_id);
    return () => {
      const ms = Date.now() - t0;
      if (ms > 500) track('watch', card.reel_id, ms);
    };
  }, [card.reel_id]);

  useEffect(() => {
    if (videoRef.current) videoRef.current.muted = !soundOn;
  }, [soundOn]);

  useLayoutEffect(() => {
    const el = descRef.current;
    if (el && !expanded) setOverflow(el.scrollHeight > el.clientHeight + 1);
  }, [card.description, expanded]);

  const finish = (action: SwipeAction) => {
    if (committed.current) return;
    committed.current = true;
    setFly(action);
    setDragging(false);
    onGlow({ dir: action, level: 1 });
    window.setTimeout(() => onCommit(action), 240);
  };
  useImperativeHandle(ref, () => ({
    fling: (a) => {
      skipUp.current = false;
      finish(a);
    },
  }));

  const levelFor = (x: number, y: number, touch: boolean): Glow => {
    const h = clamp(Math.abs(x * DEG_PER_PX) / ANGLE_THRESHOLD, 0, 1);
    const v = clamp((touch ? Math.abs(y) : Math.max(0, y)) / SKIP_DISTANCE, 0, 1);
    if (h >= v && h > 0.02) return { dir: x > 0 ? 'like' : 'dislike', level: h };
    if (v > 0.02) return { dir: 'skip', level: v };
    return { dir: null, level: 0 };
  };

  const down = (e: RPE) => {
    if (committed.current) return;
    if ((e.target as HTMLElement).closest('[data-nodrag]')) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    start.current = { x: e.clientX, y: e.clientY, type: e.pointerType };
    moved.current = false;
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
    if (!soundOn) onSound(); // звук включается после первого касания
  };
  const move = (e: RPE) => {
    const s = start.current;
    if (!s) return;
    const x = e.clientX - s.x;
    const y = e.clientY - s.y;
    if (Math.abs(x) + Math.abs(y) > 6) moved.current = true;
    dragRef.current = { x, y };
    setDrag({ x, y });
    onGlow(levelFor(x, y, s.type !== 'mouse'));
  };
  const up = () => {
    const s = start.current;
    start.current = null;
    if (!s) return;
    const { x, y } = dragRef.current;
    dragRef.current = { x: 0, y: 0 };
    const touch = s.type !== 'mouse';
    const skipDist = touch ? Math.abs(y) : y;
    if (Math.abs(x * DEG_PER_PX) >= ANGLE_THRESHOLD) {
      finish(x > 0 ? 'like' : 'dislike');
    } else if (skipDist >= SKIP_DISTANCE && skipDist > Math.abs(x)) {
      skipUp.current = touch && y < 0;
      finish('skip');
    } else {
      setDragging(false);
      setDrag({ x: 0, y: 0 });
      onGlow({ dir: null, level: 0 });
    }
  };

  const tapMedia = (e: React.MouseEvent<HTMLDivElement>) => {
    if (moved.current) return;
    if (expanded) return setExpanded(false);
    if (items.length < 2) return;
    const r = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - r.left) / r.width;
    setIdx((i) => clamp(i + (ratio < 0.35 ? -1 : 1), 0, items.length - 1));
  };

  const open = async () => {
    track('open_listing', card.reel_id);
    try {
      await openListing(card.listing_id);
    } catch {
      toast({ text: 'Не удалось открыть товар. Попробуйте ещё раз' });
    }
  };

  const retryMedia = () => {
    setMediaErr(false);
    videoRef.current?.load();
    videoRef.current?.play().catch(() => {});
  };

  const angle = drag.x * DEG_PER_PX;
  const g = fly ? { dir: fly, level: 1 } : levelFor(drag.x, drag.y, start.current ? start.current.type !== 'mouse' : false);
  let transform = `translate(${drag.x}px, ${drag.y}px) rotate(${angle}deg)`;
  if (fly === 'like') transform = `translate(130%, ${drag.y}px) rotate(22deg)`;
  if (fly === 'dislike') transform = `translate(-130%, ${drag.y}px) rotate(-22deg)`;
  if (fly === 'skip') transform = `translate(0, ${skipUp.current ? '-' : ''}110%)`;
  const style: CSSProperties & Record<string, string | number> = {
    transform,
    transition: dragging ? 'none' : fly ? 'transform .24s ease-in' : 'transform .25s cubic-bezier(.2,.8,.2,1)',
    '--glow': g.level,
  };

  const price = formatPrice(card.price);
  const sellerInfo = (
    <div className="seller-row">
      <Avatar name={card.seller.name} url={card.seller.avatar_url} size={28} />
      <b>{card.seller.name}</b>
      {card.seller.rating != null && (
        <>
          <StarIcon size={13} />
          <span>{formatRating(card.seller.rating)}</span>
        </>
      )}
    </div>
  );

  return (
    <div
      className={`swipe-card glow-${g.dir ?? 'none'}`}
      style={style}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
    >
      <div className="media" style={{ background: gradientFor(card.reel_id) }} onClick={tapMedia}>
        {isVideo ? (
          <video
            ref={videoRef}
            key={cur.url}
            src={cur.url}
            poster={cur.poster ?? undefined}
            autoPlay
            loop
            muted={!soundOn}
            playsInline
            preload="auto"
            onTimeUpdate={(e) => setProgress(e.currentTarget.currentTime / (e.currentTarget.duration || 1))}
            onError={() => setMediaErr(true)}
          />
        ) : (
          <img key={cur.url} src={cur.url} alt="" draggable={false} onError={() => setMediaErr(true)} />
        )}
        <div className="shade top" />
        <div className="shade bottom" />
      </div>

      {mediaErr && (
        <div className="media-error" data-nodrag>
          <p>{isVideo ? 'Видео не загрузилось' : 'Фото не загрузилось'}</p>
          <button className="btn btn-light" onClick={retryMedia}><RetryIcon size={16} /> Повторить</button>
        </div>
      )}

      {items.length > 1 && (
        <div className="segments">
          {items.map((_, i) => (
            <i key={i} className={i <= idx ? 'on' : ''} />
          ))}
        </div>
      )}
      {card.is_promoted && <span className="ad-label" style={{ top: items.length > 1 ? 26 : 14 }}>Реклама</span>}
      {isVideo && !soundOn && (
        <button
          className="sound-chip"
          data-nodrag
          onClick={() => {
            track('sound_toggle', card.reel_id);
            onSound();
          }}
        >
          <SoundOff size={14} /> Включить звук
        </button>
      )}

      {!expanded && (
        <div className="info">
          {sellerInfo}
          <h3>{card.title}</h3>
          {price && <div className="price">{price}</div>}
          {card.description && (
            <div className="desc-wrap">
              <p className="desc clamp" ref={descRef}>{card.description}</p>
              {overflow && (
                <button
                  className="more"
                  data-nodrag
                  onClick={() => {
                    setExpanded(true);
                    track('expand_description', card.reel_id);
                  }}
                >
                  ещё...
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {isVideo && !expanded && (
        <div className="vprogress"><i style={{ width: `${progress * 100}%` }} /></div>
      )}

      {expanded && (
        <div className="sheet" data-nodrag>
          <span className="grip" />
          {sellerInfo}
          <h3>{card.title}</h3>
          {price && <div className="price">{price}</div>}
          <p className="desc">{card.description}</p>
          <button className="collapse" onClick={() => setExpanded(false)}>Свернуть</button>
          <button className="btn btn-primary btn-wide" onClick={open}>Открыть товар</button>
        </div>
      )}
    </div>
  );
});

export default SwipeCard;
