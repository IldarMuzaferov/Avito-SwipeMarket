import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, asList } from '../api';
import type { Category } from '../api/types';
import { CheckIcon } from '../components/Icons';
import { NetworkError, Spinner } from '../components/ui';
import { useToast } from '../components/Toast';

// Пастельные цвета плиток из макета — запасной вариант, если бэкенд не прислал color
const PALETTE = ['#e9e6ff', '#daf0ff', '#e3f3d3', '#ffe1cc', '#ffdde8', '#ffe1e1', '#d3f1ef', '#fff3c4', '#e6dcf9', '#ffe8d6'];
const MIN = 3;

export default function Onboarding() {
  const nav = useNavigate();
  const toast = useToast();
  const [params] = useSearchParams();
  const edit = params.get('edit') === '1';
  const [cats, setCats] = useState<Category[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setFailed(false);
    try {
      setCats(asList(await api.categories()));
    } catch {
      setFailed(true);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  // «Изменить интересы»: подставляем уже выбранные
  useEffect(() => {
    if (!edit) return;
    api.interests().then((r) => {
      const raw: any = r;
      const arr: any[] = Array.isArray(raw) ? raw : raw?.category_ids ?? raw?.items ?? [];
      setSelected(arr.map((x) => (typeof x === 'string' ? x : x.id)));
    }).catch(() => {});
  }, [edit]);

  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const submit = async (skip: boolean) => {
    setSaving(true);
    try {
      await api.setInterests(skip ? { skipped: true } : { category_ids: selected });
      nav('/swipe', { replace: true });
    } catch (e: any) {
      toast({ text: e?.message ?? 'Не удалось сохранить интересы' });
      setSaving(false);
    }
  };

  if (failed) return <NetworkError onRetry={load} />;
  if (!cats) return <div className="center-pad"><Spinner /></div>;

  const ok = selected.length >= MIN;
  return (
    <div className="onb-wrap">
      <div className="onb-card">
        <h1>Что вам интересно?</h1>
        <p className="sub">Выберите хотя бы {MIN} — подберём ленту под вас</p>
        <div className="tiles-onb">
          {cats.map((c, i) => {
            const on = selected.includes(c.id);
            return (
              <button key={c.id} className={`cat-tile ${on ? 'on' : ''}`} style={{ background: c.color || PALETTE[i % PALETTE.length] }} onClick={() => toggle(c.id)} aria-pressed={on}>
                {c.image_url && <img src={c.image_url} alt="" />}
                <span className="deco" />
                <b>{c.name}</b>
                {on && <span className="check"><CheckIcon size={14} /></span>}
              </button>
            );
          })}
        </div>
        <p className="count">Выбрано: {selected.length}</p>
        <button className="btn btn-primary btn-wide" disabled={!ok || saving} onClick={() => submit(false)}>
          {ok ? 'Продолжить' : `Выберите ещё ${MIN - selected.length}`}
        </button>
        <button className="link-btn" disabled={saving} onClick={() => submit(true)}>Пропустить</button>
      </div>
    </div>
  );
}
