import io

import pytest
from sqlalchemy import func, select

from service_app.database import FollowerORM, LikeORM, MediaORM, TweetORM, UserORM


class TestTweets:
    @pytest.mark.asyncio
    async def test_create_tweet(self, client, db_session, test_user):
        """Общий тест проверки создания tweet"""
        payload = {"tweet_data": "Test tweet data", "tweet_media_ids": []}
        headers = {"api-key": test_user.api_key}

        resp = await client.post("/api/tweets", json=payload, headers=headers)
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["result"] is True

        tweet = await db_session.get(TweetORM, body["tweet_id"])
        assert tweet is not None
        assert tweet.author_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_media(self, client, db_session, test_user):
        """Общий тест проверки загрузки media"""
        file_content = b"fake_image"
        files = {"file": ("image.png", io.BytesIO(file_content), "image/png")}
        headers = {"api-key": test_user.api_key}

        resp = await client.post("/api/medias", files=files, headers=headers)

        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["result"] is True
        media = await db_session.get(MediaORM, body["media_id"])
        assert media is not None
        assert media.owner_id == test_user.id

    @pytest.mark.asyncio
    async def test_delete_own_tweet(
        self, client, db_session, test_user, session_factory
    ):
        """Общий тест проверки удаление своего твита"""
        headers = {"api-key": test_user.api_key}

        # твит текущего пользователя
        my_tweet = TweetORM(author_id=test_user.id, content="my tweet")
        db_session.add(my_tweet)
        await db_session.commit()

        # твит другого пользователя (чтобы проверить, что он не удалился)
        other_user = UserORM(name="Other", api_key="other_key")
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_tweet = TweetORM(author_id=other_user.id, content="other tweet")
        db_session.add(other_tweet)

        await db_session.commit()
        await db_session.refresh(my_tweet)
        await db_session.refresh(other_tweet)

        resp = await client.delete(f"/api/tweets/{my_tweet.id}", headers=headers)

        assert resp.status_code in (200, 204)
        body = resp.json()
        assert body["result"] is True

        # проверяем: мой твит удалён
        async with session_factory() as session:
            deleted = await session.get(TweetORM, my_tweet.id)
            assert deleted is None

        # проверяем: чужой твит остался
        still_there = await db_session.get(TweetORM, other_tweet.id)
        assert still_there is not None
        assert still_there.author_id == other_user.id

        resp2 = await client.delete(f"/api/tweets/{other_tweet.id}", headers=headers)
        assert resp2.json()["result"] is False

    @pytest.mark.asyncio
    async def test_like_tweet(self, client, db_session, test_user, session_factory):
        """Общий тест проверки простановки like"""
        headers = {"api-key": test_user.api_key}

        other_user = UserORM(name="Other", api_key="other_key")
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_tweet = TweetORM(author_id=other_user.id, content="other tweet")
        db_session.add(other_tweet)

        await db_session.commit()
        await db_session.refresh(other_tweet)

        response = await client.post(
            f"/api/tweets/{other_tweet.id}/likes", headers=headers
        )

        assert response.status_code in (200, 201)
        body = response.json()
        assert body["result"] is True

        async with session_factory() as s:
            res = await s.execute(
                select(LikeORM).where(
                    LikeORM.tweet_id == other_tweet.id,
                    LikeORM.user_id == test_user.id,
                )
            )
            like = res.scalar_one_or_none()

        assert like is not None

    @pytest.mark.asyncio
    async def test_like_own_tweet_forbidden(self, client, db_session, test_user):
        """Тест проверки like на свой tweet"""
        tweet = TweetORM(author_id=test_user.id, content="mine")
        db_session.add(tweet)
        await db_session.commit()
        await db_session.refresh(tweet)

        resp = await client.post(
            f"/api/tweets/{tweet.id}/likes", headers={"api-key": test_user.api_key}
        )
        body = resp.json()

        assert body["result"] is False

    @pytest.mark.asyncio
    async def test_like_twice_not_allowed(
        self, client, db_session, test_user, session_factory
    ):
        """Тест проверки повторного like"""
        other = UserORM(name="Other", api_key="other_key")
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        tweet = TweetORM(author_id=other.id, content="tweet")
        db_session.add(tweet)
        await db_session.commit()
        await db_session.refresh(tweet)

        headers = {"api-key": test_user.api_key}

        r1 = await client.post(f"/api/tweets/{tweet.id}/likes", headers=headers)
        assert r1.json()["result"] is True

        r2 = await client.post(f"/api/tweets/{tweet.id}/likes", headers=headers)
        assert r2.json()["result"] is False

        # проверяем, что лайк остался один
        async with session_factory() as s:
            res = await s.execute(
                select(func.count())
                .select_from(LikeORM)
                .where(
                    LikeORM.tweet_id == tweet.id,
                    LikeORM.user_id == test_user.id,
                )
            )
            assert res.scalar_one() == 1

    @pytest.mark.asyncio
    async def test_delete_like_tweet(
        self, client, db_session, test_user, session_factory
    ):
        """Общий тест проверки, убрать like с tweet"""
        headers = {"api-key": test_user.api_key}

        other_user = UserORM(name="Other", api_key="other_key")
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        other_tweet = TweetORM(author_id=other_user.id, content="other tweet")
        db_session.add(other_tweet)

        await db_session.commit()
        await db_session.refresh(other_tweet)

        like_tweet = LikeORM(user_id=test_user.id, tweet_id=other_tweet.id)
        db_session.add(like_tweet)
        await db_session.commit()
        await db_session.refresh(like_tweet)

        resp = await client.delete(
            f"/api/tweets/{other_tweet.id}/likes", headers=headers
        )
        assert resp.json()["result"] is True

        resp2 = await client.delete(
            f"/api/tweets/{other_tweet.id}/likes", headers=headers
        )
        assert resp2.json()["result"] is False

    @pytest.mark.asyncio
    async def test_follow_user(self, client, db_session, test_user, session_factory):
        """Общий тест проверки, пользователь
        подписывается на другого пользователя"""
        headers = {"api-key": test_user.api_key}

        other_user = UserORM(name="Other", api_key="other_key")
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        resp = await client.post(f"/api/users/{other_user.id}/follow", headers=headers)
        assert resp.json()["result"] is True

        resp2 = await client.post(f"/api/users/{other_user.id}/follow", headers=headers)
        assert resp2.json()["result"] is False

        resp3 = await client.post(f"/api/users/{test_user.id}/follow", headers=headers)
        assert resp3.json()["result"] is False

        user_id_not_exist = 9999
        resp4 = await client.post(
            f"/api/users/{user_id_not_exist}/follow", headers=headers
        )
        assert resp4.json()["result"] is False

    @pytest.mark.asyncio
    async def test_unfollow_user(self, client, db_session, test_user, session_factory):
        """Общий тест проверки,
        пользователь отписывается от другого пользователя"""
        headers = {"api-key": test_user.api_key}

        other_user = UserORM(name="Other", api_key="other_key")
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        unfollow = FollowerORM(follower_id=test_user.id, followed_id=other_user.id)
        db_session.add(unfollow)
        await db_session.commit()
        await db_session.refresh(unfollow)

        resp = await client.delete(
            f"/api/users/{other_user.id}/follow", headers=headers
        )
        assert resp.json()["result"] is True

        # проверка если подписки нет
        resp2 = await client.delete(
            f"/api/users/{other_user.id}/follow", headers=headers
        )
        assert resp2.json()["result"] is False

        # отписка пользователя на себя
        resp3 = await client.delete(
            f"/api/users/{test_user.id}/follow", headers=headers
        )
        assert resp3.json()["result"] is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("url", ["/api/tweets", "/api/users/me", "/api/users/1"])
    async def test_get_requires_api_key(self, client, url):
        resp = await client.get(url)

        assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        ["/api/tweets", "/api/users/me", "/api/users/1"],
    )
    async def test_get_rejects_bad_api_key(self, client, url):
        resp = await client.get(url, headers={"api-key": "bad"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_users_me(self, client, test_user):
        resp = await client.get("/api/users/me", headers={"api-key": test_user.api_key})
        assert resp.status_code == 200

        body = resp.json()
        assert body["result"] is True
        assert body["user"]["id"] == test_user.id
        assert body["user"]["name"] == test_user.name
        assert "followers" in body["user"]
        assert "following" in body["user"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url_builder",
        [
            lambda u: "/api/users/me",
            lambda u: f"/api/users/{u.id}",
        ],
    )
    async def test_get_user_profile_same_schema(self, client, test_user, url_builder):
        url = url_builder(test_user)

        resp = await client.get(url, headers={"api-key": test_user.api_key})
        assert resp.status_code == 200

        body = resp.json()
        assert body["result"] is True

        user = body["user"]
        assert set(user.keys()) >= {"id", "name", "followers", "following"}
        assert user["id"] == test_user.id
        assert user["name"] == test_user.name

    @pytest.mark.asyncio
    async def test_get_tweets_feed(self, client, test_user):
        resp = await client.get("/api/tweets", headers={"api-key": test_user.api_key})
        assert resp.status_code == 200

        body = resp.json()
        assert body["result"] is True
        assert "tweets" in body
        assert isinstance(body["tweets"], list)
