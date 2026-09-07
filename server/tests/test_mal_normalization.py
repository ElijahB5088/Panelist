from app.providers.mal import MALProvider


def test_mal_authorization_uses_pkce():
    authorization = MALProvider().create_authorization("client", "https://panelist.example/callback")

    assert "code_challenge=" in authorization.authorization_url
    assert "code_challenge_method=plain" in authorization.authorization_url
    assert authorization.state
    assert authorization.code_verifier


def test_mal_token_bundle_preserves_refresh_token():
    from app.providers.mal import encode_token_bundle

    assert '"refresh_token": "old-refresh"' in encode_token_bundle(
        {"access_token": "new-access"}, {"refresh_token": "old-refresh"}
    )


def test_mal_normalization_maps_manga_list_status():
    normalized = MALProvider().normalize_library([
        {
            "node": {
                "id": 2,
                "title": "Berserk",
                "synopsis": "A dark fantasy manga.",
                "mean": 9.2,
                "genres": [{"name": "Fantasy"}],
                "authors": [{"node": {"first_name": "Kentaro", "last_name": "Miura"}}],
                "serialization": [{"node": {"name": "Young Animal"}}],
            },
            "list_status": {"status": "reading", "num_chapters_read": 30, "score": 10},
        }
    ])

    media, library = normalized[0]
    assert media.id == "mal:2"
    assert media.creator == "Kentaro Miura"
    assert media.publisher == "Young Animal"
    assert library == {"status": "reading", "progress": 30, "user_rating": 10.0}


def test_mal_statuses_are_manga_statuses():
    provider = MALProvider()

    assert provider._normalize_status("completed") == "completed"
    assert provider._normalize_status("on_hold") == "planned"
    assert provider._normalize_status("plan_to_read") == "planned"
