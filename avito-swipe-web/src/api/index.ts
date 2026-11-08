import { request } from './client';
import type {
  AuthResponse, Category, CropRect, DemoRole, FeedResponse, Listing, MyListing, MyReelsResponse,
  Onboarding, PromotionCreated, PromotionPlan, PublicWishlist, Reel, ShareState, SwipeRequest,
  SwipeResponse, TrackEvent, UploadInit, UploadKind, UploadStatus, User, WishlistResponse, FeedCard,
} from './types';

export const api = {
  // --- пользователь ---
  guest: (name?: string) => request<AuthResponse>('/auth/guest', { method: 'POST', body: name ? { name } : {}, auth: false }),
  demo: (role: DemoRole) => request<AuthResponse>('/auth/demo', { method: 'POST', body: { role }, auth: false }),
  me: () => request<User>('/users/me'),

  // --- онбординг ---
  categories: () => request<Category[] | { items: Category[] }>('/categories', { auth: false }),
  onboarding: () => request<Onboarding>('/users/me/onboarding'),
  setInterests: (body: { category_ids: string[] } | { skipped: true }) =>
    request<void>('/users/me/interests', { method: 'PUT', body }),
  interests: () => request<unknown>('/users/me/interests'),
  patchOnboarding: (hint_seen: boolean) => request<void>('/users/me/onboarding', { method: 'PATCH', body: { hint_seen } }),

  // --- лента и свайпы ---
  feed: (q: { limit?: number; cursor?: string | null; session_id?: string | null }) =>
    request<FeedResponse>('/feed', { query: q }),
  swipe: (body: SwipeRequest) => request<SwipeResponse>('/swipes', { method: 'POST', body }),
  undo: () => request<FeedCard>('/swipes/undo', { method: 'POST' }),
  listing: (id: string) => request<Listing>(`/listings/${id}`),
  events: (events: TrackEvent[]) => request<void>('/events', { method: 'POST', body: { events }, keepalive: true }),

  // --- вишлист ---
  wishlist: (q: { limit?: number; cursor?: string | null } = {}) => request<WishlistResponse>('/wishlist', { query: q }),
  addToWishlist: (listing_id: string) => request<unknown>('/wishlist/items', { method: 'POST', body: { listing_id } }),
  removeFromWishlist: (listing_id: string) => request<void>(`/wishlist/items/${listing_id}`, { method: 'DELETE' }),
  share: () => request<ShareState>('/wishlist/share'),
  setShare: (enabled: boolean) => request<ShareState>('/wishlist/share', { method: 'PUT', body: { enabled } }),
  publicWishlist: (token: string, q: { limit?: number; cursor?: string | null } = {}) =>
    request<PublicWishlist>(`/public/wishlists/${encodeURIComponent(token)}`, { query: q, auth: false }),

  // --- продавец ---
  createUpload: (body: { kind: UploadKind; files: { filename: string; content_type: string; size_bytes: number }[] }) =>
    request<UploadInit>('/media/uploads', { method: 'POST', body }),
  completeUpload: (id: string) => request<void>(`/media/uploads/${id}/complete`, { method: 'POST' }),
  uploadStatus: (id: string) => request<UploadStatus>(`/media/uploads/${id}`),
  cropUpload: (id: string, rect: CropRect) => request<void>(`/media/uploads/${id}/crop`, { method: 'POST', body: rect }),
  orderUpload: (id: string, file_ids: string[]) =>
    request<void>(`/media/uploads/${id}/order`, { method: 'PUT', body: { file_ids } }),
  deleteUploadFile: (id: string, fileId: string) => request<void>(`/media/uploads/${id}/files/${fileId}`, { method: 'DELETE' }),
  myListings: () => request<MyListing[] | { items: MyListing[] }>('/me/listings'),
  createReel: (body: { listing_id: string; upload_id: string; show_price: boolean; description: string }) =>
    request<Reel>('/reels', { method: 'POST', body }),
  patchReel: (id: string, body: { show_price?: boolean; description?: string; enabled?: boolean }) =>
    request<Reel>(`/reels/${id}`, { method: 'PATCH', body }),
  myReels: (q: { status?: string; limit?: number; cursor?: string | null } = {}) =>
    request<MyReelsResponse>('/me/reels', { query: q }),

  // --- продвижение ---
  plans: () => request<PromotionPlan[] | { items: PromotionPlan[] }>('/promotion/plans'),
  buyPromotion: (reelId: string, plan_id: string) =>
    request<PromotionCreated>(`/reels/${reelId}/promotions`, { method: 'POST', body: { plan_id } }),
  mockPay: (promotionId: string) => request<unknown>(`/promotions/${promotionId}/mock-pay`, { method: 'POST' }),
};

// API может вернуть и массив, и { items: [] } — приводим к массиву
export const asList = <T,>(v: T[] | { items: T[] } | undefined | null): T[] => (Array.isArray(v) ? v : v?.items ?? []);
