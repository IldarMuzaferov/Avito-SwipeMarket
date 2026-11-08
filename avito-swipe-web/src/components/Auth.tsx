import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api';
import { ApiError, getToken, onUnauthorized, setToken } from '../api/client';
import type { DemoRole, User } from '../api/types';
import { Spinner, NetworkError } from './ui';

type AuthCtx = {
  user: User;
  wishlistCount: number;
  setWishlistCount: (n: number) => void;
  refreshUser: () => Promise<void>;
  loginDemo: (role: DemoRole | 'guest') => Promise<void>;
};
const Ctx = createContext<AuthCtx | null>(null);
export const useAuth = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth вне AuthProvider');
  return v;
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [wishlistCount, setWishlistCount] = useState(0);
  const [failed, setFailed] = useState(false);

  const apply = useCallback((u: User) => {
    setUser(u);
    setWishlistCount(u.wishlist_count ?? 0);
  }, []);

  const newGuest = useCallback(async () => {
    const r = await api.guest();
    setToken(r.access_token);
    apply(r.user);
  }, [apply]);

  const boot = useCallback(async () => {
    setFailed(false);
    try {
      if (getToken()) {
        try {
          apply(await api.me());
          return;
        } catch (e) {
          if (!(e instanceof ApiError) || e.status === 0) throw e;
        }
      }
      await newGuest();
    } catch {
      setFailed(true);
    }
  }, [apply, newGuest]);

  useEffect(() => {
    onUnauthorized(newGuest);
    boot();
  }, [boot, newGuest]);

  const refreshUser = useCallback(async () => {
    try {
      apply(await api.me());
    } catch {
      /* ignore */
    }
  }, [apply]);

  const loginDemo = useCallback(
    async (role: DemoRole | 'guest') => {
      const r = role === 'guest' ? await api.guest() : await api.demo(role);
      setToken(r.access_token);
      // чистим состояние, зависящее от пользователя, проще всего перезагрузкой
      window.location.assign('/swipe');
    },
    [],
  );

  if (failed)
    return (
      <div className="boot">
        <NetworkError onRetry={boot} text="Не удалось подключиться к серверу. Проверьте, что бэкенд запущен на http://localhost:8000" />
      </div>
    );
  if (!user)
    return (
      <div className="boot">
        <Spinner />
      </div>
    );

  return <Ctx.Provider value={{ user, wishlistCount, setWishlistCount, refreshUser, loginDemo }}>{children}</Ctx.Provider>;
}
