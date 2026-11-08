import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Onboarding from './pages/Onboarding';
import Feed from './pages/Feed';
import Wishlist from './pages/Wishlist';
import PublicWishlistPage from './pages/PublicWishlist';
import ReelForm from './pages/ReelForm';
import MyReels from './pages/MyReels';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="swipe" element={<Feed />} />
        <Route path="onboarding" element={<Onboarding />} />
        <Route path="my/wishlist" element={<Wishlist />} />
        {/* ссылка, которой делятся: avito.ru/wishlist/<token> */}
        <Route path="wishlist/:token" element={<PublicWishlistPage />} />
        <Route path="seller/reel" element={<ReelForm />} />
        <Route path="seller/listings" element={<MyReels />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
