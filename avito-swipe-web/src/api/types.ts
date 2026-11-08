// Типы строго по спецификации API (раздел 5 и 6)

export type Price = { amount: number; currency: string };

export type MediaItem = {
  url: string;
  poster?: string | null;
  duration_sec?: number | null;
  width?: number | null;
  height?: number | null;
};
export type ReelMedia = { type: 'video' | 'photo' | 'album'; items: MediaItem[] };
export type Seller = { id: string; name: string; avatar_url?: string | null; rating?: number | null };

export type FeedCard = {
  reel_id: string;
  listing_id: string;
  media: ReelMedia;
  title: string;
  price: Price | null; // null, если продавец скрыл цену в рилсе
  description: string;
  seller: Seller;
  is_promoted: boolean;
  in_wishlist: boolean;
};
export type FeedResponse = { items: FeedCard[]; next_cursor: string | null; session_id: string };

export type SwipeAction = 'like' | 'dislike' | 'skip';
export type SwipeRequest = {
  reel_id: string;
  action: SwipeAction;
  client_id: string;
  session_id: string;
  dwell_ms: number;
  position: number;
};
export type SwipeResponse = { in_wishlist: boolean; wishlist_count: number; swipes_total: number };

export type User = {
  id: string;
  name: string;
  avatar_url?: string | null;
  city?: string | null;
  is_guest: boolean;
  wishlist_count: number;
};
export type AuthResponse = { access_token: string; refresh_token?: string; user: User };
export type DemoRole = 'buyer' | 'friend' | 'seller';

export type Category = { id: string; name: string; image_url?: string | null; color?: string | null };
export type Onboarding = { interests_done: boolean; hint_seen: boolean };

export type ItemStatus = 'available' | 'sold' | 'removed';
export type WishlistItem = {
  listing_id: string;
  reel_id?: string;
  title: string;
  price: Price;
  cover_url?: string | null;
  city?: string | null;
  status: ItemStatus;
  added_at?: string;
};
export type ShareState = { enabled: boolean; url: string | null };
export type WishlistResponse = {
  count: number;
  items: WishlistItem[];
  next_cursor?: string | null;
  share: ShareState;
};
export type PublicWishlist = {
  owner: { display_name: string; avatar_url?: string | null };
  count: number;
  items: WishlistItem[];
  next_cursor?: string | null;
};

export type Listing = {
  id?: string;
  title: string;
  description?: string;
  price: Price;
  city?: string;
  images?: string[];
  seller?: Seller;
  status: ItemStatus;
  listing_url: string;
};

export type UploadKind = 'video' | 'photos';
export type UploadInit = {
  upload_id: string;
  files: { file_id: string; put_url: string; headers?: Record<string, string> }[];
  expires_in: number;
};
export type UploadStatusValue = 'created' | 'uploaded' | 'processing' | 'ready' | 'failed';
export type UploadStatus = {
  status: UploadStatusValue;
  error?: string | null;
  duration_sec?: number | null;
  files: { file_id?: string; preview_url: string }[];
};
export type CropRect = { x: number; y: number; width: number; height: number };

export type MyListing = { id: string; title: string; price: number; has_reel: boolean };

export type ReelStatus = 'draft' | 'processing' | 'moderation' | 'published' | 'rejected' | 'disabled';
export type Reel = { id?: string; reel_id?: string; status: ReelStatus };
export type MyReel = {
  reel_id: string;
  listing_id: string;
  title: string;
  price: Price;
  cover_url?: string | null;
  status: ReelStatus;
  reject_reason?: string | null;
  stats?: { views?: number; likes?: number; promotion?: { active_until?: string | null } | null };
  promotion?: { active_until?: string | null } | null;
};
export type MyReelsResponse = { items: MyReel[]; next_cursor?: string | null };

export type PromotionPlan = {
  id: string;
  days: number;
  estimated_reach: number;
  price: Price;
  is_best_value: boolean;
};
export type PromotionCreated = { promotion_id: string; status: string; payment_url?: string };

export type TrackEvent = {
  type: 'view' | 'watch' | 'expand_description' | 'open_listing' | 'sound_toggle';
  reel_id: string;
  value_ms?: number;
  ts: string;
};
