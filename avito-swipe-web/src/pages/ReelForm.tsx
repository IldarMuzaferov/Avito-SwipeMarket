import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, asList } from '../api';
import { ApiError } from '../api/client';
import type { MyListing } from '../api/types';
import CropModal from '../components/CropModal';
import { CloseIcon, CropIcon, ImageIcon, PlusIcon, RetryIcon, SwipeIcon, VideoIcon } from '../components/Icons';
import PromotionModal from '../components/PromotionModal';
import { useToast } from '../components/Toast';
import { Spinner, Toggle } from '../components/ui';
import { MAX_PHOTOS, useMediaUpload } from '../lib/upload';
import { formatPrice, gradientFor, isVideoUrl } from '../lib/utils';

const MAX_DESC = 300;

function Preview({ src, title, price, description }: { src?: string; title: string; price: string; description: string }) {
  return (
    <div className="reel-preview">
      <p>Так увидят покупатели</p>
      <div className="rp-card" style={{ background: gradientFor(title || 'x') }}>
        {src && (isVideoUrl(src) ? <video src={src} muted loop autoPlay playsInline /> : <img src={src} alt="" />)}
        <div className="shade bottom" />
        <div className="rp-info">
          <h4>{title || 'Название товара'}</h4>
          {price && <b>{price}</b>}
          {description && <span>{description}</span>}
        </div>
      </div>
    </div>
  );
}

export default function ReelForm() {
  const nav = useNavigate();
  const toast = useToast();
  const [params] = useSearchParams();
  const { st, start, reset, addPhotos, removeFile, reorder, crop } = useMediaUpload();

  const [listings, setListings] = useState<MyListing[] | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [listingId, setListingId] = useState(params.get('listing') ?? '');
  const [enabled, setEnabled] = useState(true);
  const [showPrice, setShowPrice] = useState(true);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [cropOpen, setCropOpen] = useState(false);
  const [promoFor, setPromoFor] = useState<string | null>(null);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [over, setOver] = useState(false);
  const videoInput = useRef<HTMLInputElement>(null);
  const photoInput = useRef<HTMLInputElement>(null);
  const addInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.myListings().then((r) => setListings(asList(r))).catch((e) => {
      if (e instanceof ApiError && e.status === 403) setForbidden(true);
      else setListings([]);
    });
  }, []);

  const listing = listings?.find((l) => l.id === listingId);
  const isVideo = st.kind === 'video';
  const ready = st.phase === 'ready' && st.files.length > 0;
  const canPublish = enabled && ready && !!listing && !submitting;

  const pick = (kind: 'video' | 'photos', list: FileList | null) => {
    if (!list || list.length === 0) return;
    const files = Array.from(list);
    start(kind, kind === 'video' ? [files[0]] : files.slice(0, MAX_PHOTOS));
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (!files.length) return;
    if (files[0].type.startsWith('video/')) start('video', [files[0]]);
    else pick('photos', e.dataTransfer.files);
  };

  const publish = async () => {
    if (!listing || !st.uploadId) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const r = await api.createReel({ listing_id: listing.id, upload_id: st.uploadId, show_price: showPrice, description: description.trim() });
      toast({ text: r.status === 'published' ? 'Рилс опубликован в Свайпе' : 'Рилс отправлен на модерацию' });
      const id = r.reel_id ?? r.id;
      if (id) setPromoFor(id);
      else nav('/seller/listings');
    } catch (e: any) {
      setFormError(e?.message ?? 'Не удалось опубликовать рилс');
      setSubmitting(false);
    }
  };

  if (forbidden)
    return (
      <div className="container page">
        <h1>Рилс для Свайпа</h1>
        <p className="off-note">Эта страница для продавцов. В меню профиля (аватар справа вверху) выберите «Демо: войти как → Продавец».</p>
      </div>
    );
  if (!listings) return <div className="center-pad"><Spinner /></div>;

  const previewSrc = st.files[0]?.preview_url;
  return (
    <div className="container page">
      <h1>Рилс для Свайпа</h1>
      <div className="reel-layout">
        <div className="reel-main">
          <section className="card-box">
            <label className="field-label" htmlFor="listing">Объявление</label>
            <select id="listing" className="select" value={listingId} onChange={(e) => setListingId(e.target.value)}>
              <option value="">Выберите объявление</option>
              {listings.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.title} — {formatPrice({ amount: l.price, currency: 'RUB' })}
                </option>
              ))}
            </select>
            {listings.length === 0 && <p className="hint-text">У вас пока нет активных объявлений.</p>}
          </section>

          <section className="card-box">
            <div className="row-between">
              <div className="card-title"><SwipeIcon size={22} className="blue" /><b>Показывать в Свайпе</b></div>
              <Toggle checked={enabled} onChange={setEnabled} label="Показывать в Свайпе" />
            </div>
            <p className="hint-text">Покупатели листают товары как рилсы. Это шанс продать быстрее.</p>

            <div className={enabled ? '' : 'disabled-block'}>
              {st.phase === 'idle' && (
                <div className={`dropzone ${over ? 'over' : ''}`} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
                  <p>Перетащите файлы сюда или выберите способ загрузки</p>
                  <div className="dz-actions">
                    <button className="btn btn-primary" onClick={() => videoInput.current?.click()}><VideoIcon size={18} /> Видео до 60 сек</button>
                    <button className="btn btn-soft" onClick={() => photoInput.current?.click()}><ImageIcon size={18} /> Фото до {MAX_PHOTOS}</button>
                  </div>
                  <small>Видео — MP4/MOV до 200 МБ, фото — JPG/PNG/WebP до 10 МБ</small>
                </div>
              )}

              {st.phase === 'uploading' && (
                <div className="progress-box">
                  <p>Загружаем… {Math.round(st.progress * 100)}%</p>
                  <div className="bar"><i style={{ width: `${st.progress * 100}%` }} /></div>
                </div>
              )}
              {st.phase === 'processing' && (
                <div className="progress-box"><Spinner /><p>Обрабатываем {isVideo ? 'видео' : 'фото'}…</p></div>
              )}
              {st.phase === 'error' && (
                <div className="upload-error">
                  <p>{st.error}</p>
                  <button className="btn btn-secondary" onClick={reset}><RetryIcon size={16} /> Загрузить другой файл</button>
                </div>
              )}

              {ready && (
                <>
                  <div className="media-tiles">
                    {st.files.map((f, i) => (
                      <div
                        key={f.file_id}
                        className={`mtile ${isVideo ? 'single' : ''}`}
                        draggable={!isVideo}
                        onDragStart={() => setDragFrom(i)}
                        onDragOver={(e) => !isVideo && e.preventDefault()}
                        onDrop={async (e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (dragFrom !== null) {
                            const msg = await reorder(dragFrom, i);
                            if (msg) toast({ text: msg });
                          }
                          setDragFrom(null);
                        }}
                      >
                        {isVideoUrl(f.preview_url) ? <video src={f.preview_url} muted playsInline /> : <img src={f.preview_url} alt="" draggable={false} />}
                        {i === 0 && !isVideo && <span className="cover-label">Обложка</span>}
                        <button className="tile-x" aria-label="Удалить" onClick={async () => { const m = await removeFile(f.file_id); if (m) toast({ text: m }); }}>
                          <CloseIcon size={12} />
                        </button>
                      </div>
                    ))}
                    {!isVideo && st.files.length < MAX_PHOTOS && (
                      <button className="mtile add" onClick={() => addInput.current?.click()}><PlusIcon size={24} /><span>Добавить</span></button>
                    )}
                  </div>
                  <div className="media-tools">
                    <button className="link-btn inline" onClick={() => setCropOpen(true)}><CropIcon size={16} /> Кадрировать 9:16</button>
                    <button className="link-btn inline" onClick={reset}>Загрузить заново</button>
                  </div>
                  {!isVideo && <p className="hint-text">Перетаскивайте фото, чтобы поменять порядок. Первое станет обложкой</p>}
                </>
              )}
            </div>
            <input ref={videoInput} type="file" accept="video/*" hidden onChange={(e) => { pick('video', e.target.files); e.target.value = ''; }} />
            <input ref={photoInput} type="file" accept="image/*" multiple hidden onChange={(e) => { pick('photos', e.target.files); e.target.value = ''; }} />
            <input ref={addInput} type="file" accept="image/*" multiple hidden onChange={(e) => { if (e.target.files) addPhotos(Array.from(e.target.files)); e.target.value = ''; }} />
          </section>

          <section className="card-box">
            <div className="row-between">
              <div>
                <b>Показывать цену в рилсе</b>
                <p className="hint-text tight">Если выключить, цена будет только на странице товара</p>
              </div>
              <Toggle checked={showPrice} onChange={setShowPrice} label="Показывать цену в рилсе" />
            </div>
            <div className="textarea-box">
              <label htmlFor="desc">Описание для рилса</label>
              <textarea id="desc" value={description} maxLength={MAX_DESC} rows={3} onChange={(e) => setDescription(e.target.value)} placeholder="Расскажите о товаре коротко" />
              <span className="counter">{description.length} / {MAX_DESC}</span>
            </div>
            <p className="hint-text">Покупатель сразу видит первую строку, остальное раскроется по «ещё…»</p>
          </section>

          {formError && <div className="form-error">{formError}</div>}
          <button className="btn btn-primary btn-lg" disabled={!canPublish} onClick={publish}>{submitting ? 'Публикуем…' : 'Опубликовать'}</button>
          {!canPublish && !submitting && (
            <p className="hint-text">{!listing ? 'Выберите объявление' : !ready ? 'Загрузите видео или фото' : !enabled ? 'Включите показ в Свайпе' : ''}</p>
          )}
        </div>

        <Preview src={previewSrc} title={listing?.title ?? ''} price={showPrice && listing ? formatPrice({ amount: listing.price, currency: 'RUB' }) : ''} description={description} />
      </div>

      {cropOpen && previewSrc && (
        <CropModal src={previewSrc} onClose={() => setCropOpen(false)} onApply={(r) => { setCropOpen(false); crop(r); }} />
      )}
      {promoFor && <PromotionModal reelId={promoFor} onClose={() => nav('/seller/listings')} />}
    </div>
  );
}
