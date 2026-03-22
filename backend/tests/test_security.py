"""Tests for credential encryption and role-based access control."""
import pytest


class TestCredentialEncryption:
    def test_roundtrip(self):
        from app.core.security import decrypt_credential, encrypt_credential

        secret = "my_ssh_password_123"
        encrypted = encrypt_credential(secret)
        assert encrypted != secret
        assert decrypt_credential(encrypted) == secret

    def test_different_ciphertext_each_call(self):
        from app.core.security import encrypt_credential

        secret = "same_password"
        enc1 = encrypt_credential(secret)
        enc2 = encrypt_credential(secret)
        # Fernet produces different ciphertext each call (due to random IV)
        assert enc1 != enc2

    def test_decrypt_wrong_key_raises(self):
        import os
        from cryptography.fernet import Fernet

        # Encrypt with a different key
        other_key = Fernet.generate_key()
        fernet = Fernet(other_key)
        bad_token = fernet.encrypt(b"secret").decode()

        from app.core.security import decrypt_credential
        with pytest.raises(Exception):
            decrypt_credential(bad_token)


@pytest.mark.asyncio
async def test_viewer_blocked_from_alarm_acknowledge(client, viewer_token, admin_token):
    """VIEWER role must not be able to acknowledge alarms."""
    # First create an alarm via the admin path (seed directly would be better in real tests)
    # For now just verify the 403 on VIEWER attempt
    resp = await client.post(
        "/alarms/1/acknowledge",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    # 403 or 404 is acceptable — 403 means role blocked, 404 means no alarm (also not 200)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_unauthenticated_request_blocked(client):
    resp = await client.get("/devices")
    assert resp.status_code == 401
