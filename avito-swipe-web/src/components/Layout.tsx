import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './Auth';
import { Avatar } from './ui';
import { AvitoMark, GiftIcon, GridIcon, HeartIcon, HomeIcon, PinIcon, SearchIcon, SwipeIcon, UserIcon, CloseIcon } from './Icons';
import type { DemoRole } from '../api/types';

const ROLES: { id: DemoRole | 'guest'; label: string }[] = [
  { id: 'guest', label: 'Гость' },
  { id: 'buyer', label: 'Покупатель' },
  { id: 'friend', label: 'Друг' },
  { id: 'seller', label: 'Продавец' },
];

function Header({ isHome, onAvatar }: { isHome: boolean; onAvatar: () => void }) {
  const { user } = useAuth();
  return (
    <header className="header">
      <div className="container header-in">
        <Link to="/" className="logo" aria-label="Авито">
          <AvitoMark />
          <span>Avito</span>
        </Link>
        <Link to="/" className="cat-btn">
          <GridIcon />
          <span>Все категории</span>
        </Link>
        <div className="search">
          <SearchIcon size={18} />
          <input placeholder="Поиск по объявлениям" aria-label="Поиск по объявлениям" />
          <span className="region">
            <PinIcon size={16} />
            <span>Во всех регионах</span>
          </span>
        </div>
        <NavLink to="/swipe" className={({ isActive }) => `swipe-btn ${isActive ? 'active' : ''}`}>
          <SwipeIcon size={22} />
          <span>Свайп</span>
          {isHome && <em className="new">NEW</em>}
        </NavLink>
        <Link to="/" className="fav" aria-label="Избранное">
          <HeartIcon size={26} />
        </Link>
        <button className="avatar-btn" onClick={onAvatar} aria-label="Меню пользователя">
          <Avatar name={user.name} url={user.avatar_url} size={30} />
        </button>
      </div>
    </header>
  );
}

function UserMenu({ onClose }: { onClose: () => void }) {
  const { user, loginDemo } = useAuth();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node) && !(e.target as HTMLElement).closest('.avatar-btn,.tab-profile')) onClose();
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [onClose]);
  return (
    <div className="user-menu" ref={ref}>
      <div className="um-head">
        <Avatar name={user.name} url={user.avatar_url} size={36} />
        <div>
          <b>{user.name}</b>
          <small>{user.is_guest ? 'Гость' : 'Тестовый пользователь'}</small>
        </div>
        <button className="icon-btn ghost mobile-only" onClick={onClose} aria-label="Закрыть"><CloseIcon size={20} /></button>
      </div>
      <Link to="/my/wishlist" onClick={onClose}>Мой вишлист</Link>
      <Link to="/seller/reel" onClick={onClose}>Создать рилс для Свайпа</Link>
      <Link to="/seller/listings" onClick={onClose}>Мои объявления</Link>
      <Link to="/onboarding?edit=1" onClick={onClose}>Изменить интересы</Link>
      <div className="um-demo">
        <small>Демо: войти как</small>
        <div>
          {ROLES.map((r) => (
            <button key={r.id} className="chip" onClick={() => loginDemo(r.id)}>{r.label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

function BottomNav({ onProfile }: { onProfile: () => void }) {
  const { wishlistCount } = useAuth();
  return (
    <nav className="bottom-nav" aria-label="Навигация">
      <NavLink to="/" end><span className="pill"><HomeIcon size={24} /></span>Главная</NavLink>
      <NavLink to="/swipe"><span className="pill"><SwipeIcon size={24} /></span>Свайп</NavLink>
      <NavLink to="/my/wishlist">
        <span className="pill"><GiftIcon size={24} />{wishlistCount > 0 && <i className="dot" />}</span>Вишлист
      </NavLink>
      <button className="tab-profile" onClick={onProfile}><span className="pill"><UserIcon size={24} /></span>Профиль</button>
    </nav>
  );
}

function Banner() {
  return (
    <div className="promo-banner">
      <span>Хватамба уже здесь: ловите скидки до 90% до 30 ноября</span>
      <button>За покупками</button>
    </div>
  );
}

export default function Layout() {
  const { pathname } = useLocation();
  const [menu, setMenu] = useState(false);
  useEffect(() => setMenu(false), [pathname]);
  const isHome = pathname === '/';
  return (
    <div className={`app ${pathname.startsWith('/swipe') ? 'is-feed' : ''}`}>
      {isHome && <Banner />}
      <Header isHome={isHome} onAvatar={() => setMenu((m) => !m)} />
      {menu && <UserMenu onClose={() => setMenu(false)} />}
      <main>
        <Outlet />
      </main>
      <BottomNav onProfile={() => setMenu((m) => !m)} />
    </div>
  );
}
