from app.security import decrypt_secret, encrypt_secret


def test_token_encryption_round_trip():
    token = "super-secret-token"
    encrypted = encrypt_secret(token)
    assert encrypted != token
    assert decrypt_secret(encrypted) == token
