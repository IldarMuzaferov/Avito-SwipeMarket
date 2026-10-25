from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import Category, Listing, User, WishlistItem
from app.main import app


@pytest.mark.asyncio
async def test_wishlist_and_public_sharing(client):
    async with app.state.test_session_factory() as session:
        owner = User(name="Владелец", is_guest=False)
        seller = User(name="Продавец", is_guest=False)
        category = Category(slug="guitar", name="Музыка")
        session.add_all([owner, seller, category])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            category_id=category.id,
            title="Гитара",
            price_amount=8900,
            city="Москва",
            status="active",
        )
        session.add(listing)
        await session.commit()
        listing_id = listing.id
        owner_id = owner.id

    from app.core.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(owner_id)})}"}
    added = await client.post(
        "/api/v1/wishlist/items",
        headers=headers,
        json={"listing_id": str(listing_id)},
    )
    duplicate = await client.post(
        "/api/v1/wishlist/items",
        headers=headers,
        json={"listing_id": str(listing_id)},
    )
    assert added.status_code == 201
    assert duplicate.status_code == 201

    enabled = await client.put(
        "/api/v1/wishlist/share",
        headers=headers,
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    token = enabled.json()["url"].rsplit("/", 1)[1]
    public = await client.get(f"/api/v1/public/wishlists/{token}")
    assert public.status_code == 200
    assert public.json()["count"] == 1
    assert public.json()["items"][0]["price"]["amount"] == 8900

    wishlist = await client.get("/api/v1/wishlist", headers=headers)
    assert wishlist.status_code == 200
    assert wishlist.json()["items"][0]["listing_id"] == str(listing_id)
    assert wishlist.json()["items"][0]["status"] == "available"

    disabled = await client.put(
        "/api/v1/wishlist/share",
        headers=headers,
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert (await client.get(f"/api/v1/public/wishlists/{token}")).status_code == 410

    rotated = await client.post("/api/v1/wishlist/share/rotate", headers=headers)
    assert rotated.status_code == 200
    new_token = rotated.json()["url"].rsplit("/", 1)[1]
    assert new_token != token
    assert (await client.get(f"/api/v1/public/wishlists/{new_token}")).status_code == 200

    deleted = await client.delete(f"/api/v1/wishlist/items/{listing_id}", headers=headers)
    assert deleted.status_code == 204
    async with app.state.test_session_factory() as session:
        assert await session.scalar(select(WishlistItem.id)) is None


@pytest.mark.asyncio
async def test_unknown_and_disabled_share_status_codes(client):
    unknown = await client.get("/api/v1/public/wishlists/unknown-token")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"
