import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { ApiError } from '../api/client';
import type { CropRect, UploadKind } from '../api/types';
import { videoDuration } from './utils';

// Лимиты из спецификации
export const MAX_VIDEO_SEC = 60;
export const MAX_VIDEO_BYTES = 200 * 1024 * 1024;
export const MAX_PHOTOS = 10;
export const MAX_PHOTO_BYTES = 10 * 1024 * 1024;

export type UploadPhase = 'idle' | 'uploading' | 'processing' | 'ready' | 'error';
export type UploadFileView = { file_id: string; preview_url: string };
export type UploadState = {
  phase: UploadPhase;
  kind?: UploadKind;
  progress: number;
  uploadId?: string;
  files: UploadFileView[];
  error?: string;
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const MESSAGES: Record<string, string> = {
  video_too_long: 'Видео длиннее 60 секунд. Обрежьте его',
  bad_format: 'Неподдерживаемый формат. Загрузите видео MP4/MOV или фото JPG/PNG/WebP',
  too_large: 'Файл слишком большой. Видео — до 200 МБ, фото — до 10 МБ',
};
export function uploadErrorMessage(e: unknown): string {
  if (e instanceof ApiError) return MESSAGES[e.code] ?? e.message;
  return 'Не удалось загрузить файл. Попробуйте ещё раз';
}

function put(url: string, file: File, headers: Record<string, string> | undefined, onLoaded: (n: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    const h = headers ?? {};
    if (!Object.keys(h).some((k) => k.toLowerCase() === 'content-type') && file.type) xhr.setRequestHeader('Content-Type', file.type);
    for (const [k, v] of Object.entries(h)) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => e.lengthComputable && onLoaded(e.loaded);
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new ApiError(xhr.status, 'upload_failed', 'Не удалось загрузить файл в хранилище'));
    xhr.onerror = () => reject(new ApiError(0, 'network', 'Нет соединения во время загрузки файла'));
    xhr.send(file);
  });
}

async function validate(kind: UploadKind, files: File[]) {
  if (kind === 'video') {
    const f = files[0];
    if (!f.type.startsWith('video/')) throw new ApiError(415, 'bad_format', '');
    if (f.size > MAX_VIDEO_BYTES) throw new ApiError(413, 'too_large', '');
    try {
      if ((await videoDuration(f)) > MAX_VIDEO_SEC + 0.5) throw new ApiError(422, 'video_too_long', '');
    } catch (e) {
      if (e instanceof ApiError) throw e; // если браузер не прочитал метаданные — пусть проверит сервер
    }
  } else {
    if (files.length > MAX_PHOTOS) throw new ApiError(422, 'validation_error', `Можно загрузить до ${MAX_PHOTOS} фото`);
    for (const f of files) {
      if (!f.type.startsWith('image/')) throw new ApiError(415, 'bad_format', '');
      if (f.size > MAX_PHOTO_BYTES) throw new ApiError(413, 'too_large', '');
    }
  }
}

export function useMediaUpload() {
  const [st, setSt] = useState<UploadState>({ phase: 'idle', progress: 0, files: [] });
  const alive = useRef(true);
  const sources = useRef<File[]>([]); // исходные файлы в том же порядке, что и st.files
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  const poll = useCallback(async (uploadId: string) => {
    const t0 = Date.now();
    while (alive.current) {
      const s = await api.uploadStatus(uploadId);
      if (s.status === 'ready') {
        setSt((p) => ({
          ...p,
          phase: 'ready',
          files: s.files.map((f, i) => ({ file_id: f.file_id ?? String(i), preview_url: f.preview_url })),
        }));
        return;
      }
      if (s.status === 'failed') throw new ApiError(422, s.error ?? 'processing_failed', s.error && MESSAGES[s.error] ? '' : 'Не удалось обработать файл. Попробуйте другой');
      if (Date.now() - t0 > 180_000) throw new ApiError(0, 'timeout', 'Обработка заняла слишком много времени');
      await sleep(1500);
    }
  }, []);

  const start = useCallback(
    async (kind: UploadKind, files: File[]) => {
      sources.current = files;
      setSt({ phase: 'uploading', kind, progress: 0, files: [] });
      try {
        await validate(kind, files);
        const init = await api.createUpload({
          kind,
          files: files.map((f) => ({ filename: f.name, content_type: f.type, size_bytes: f.size })),
        });
        const loaded = files.map(() => 0);
        const total = files.reduce((a, f) => a + f.size, 0) || 1;
        await Promise.all(
          init.files.map((fi, i) =>
            put(fi.put_url, files[i], fi.headers, (n) => {
              loaded[i] = n;
              if (alive.current) setSt((p) => ({ ...p, progress: loaded.reduce((a, b) => a + b, 0) / total }));
            }),
          ),
        );
        await api.completeUpload(init.upload_id);
        if (alive.current) setSt((p) => ({ ...p, phase: 'processing', uploadId: init.upload_id, progress: 1 }));
        await poll(init.upload_id);
      } catch (e) {
        if (alive.current) setSt((p) => ({ ...p, phase: 'error', error: uploadErrorMessage(e) }));
      }
    },
    [poll],
  );

  const reset = useCallback(() => {
    sources.current = [];
    setSt({ phase: 'idle', progress: 0, files: [] });
  }, []);

  // Добавить фото = загрузить набор заново (API создаёт одну загрузку на пачку файлов)
  const addPhotos = useCallback((more: File[]) => start('photos', [...sources.current, ...more].slice(0, MAX_PHOTOS)), [start]);

  const removeFile = useCallback(
    async (fileId: string) => {
      if (!st.uploadId) return;
      const i = st.files.findIndex((f) => f.file_id === fileId);
      try {
        await api.deleteUploadFile(st.uploadId, fileId);
      } catch (e) {
        return uploadErrorMessage(e);
      }
      sources.current = sources.current.filter((_, k) => k !== i);
      if (st.files.length <= 1) return reset();
      setSt((p) => ({ ...p, files: p.files.filter((f) => f.file_id !== fileId) }));
    },
    [st.uploadId, st.files, reset],
  );

  const reorder = useCallback(
    async (from: number, to: number) => {
      if (!st.uploadId || from === to) return;
      const files = [...st.files];
      const [m] = files.splice(from, 1);
      files.splice(to, 0, m);
      const src = [...sources.current];
      const [ms] = src.splice(from, 1);
      src.splice(to, 0, ms);
      const prevFiles = st.files;
      const prevSrc = sources.current;
      sources.current = src;
      setSt((p) => ({ ...p, files })); // сразу показываем новый порядок
      try {
        await api.orderUpload(st.uploadId, files.map((f) => f.file_id));
      } catch {
        sources.current = prevSrc;
        setSt((p) => ({ ...p, files: prevFiles }));
        return 'Не удалось изменить порядок';
      }
    },
    [st.uploadId, st.files],
  );

  const crop = useCallback(
    async (rect: CropRect) => {
      if (!st.uploadId) return;
      const id = st.uploadId;
      setSt((p) => ({ ...p, phase: 'processing' }));
      try {
        await api.cropUpload(id, rect);
        await poll(id);
      } catch (e) {
        if (alive.current) setSt((p) => ({ ...p, phase: 'error', error: uploadErrorMessage(e) }));
      }
    },
    [st.uploadId, poll],
  );

  return { st, start, reset, addPhotos, removeFile, reorder, crop };
}
