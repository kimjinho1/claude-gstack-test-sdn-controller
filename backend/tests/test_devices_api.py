"""Integration tests for /devices API endpoints."""
import pytest
from unittest.mock import patch


async def _seed_topology(client, token):
    """Helper: create group → site → building, return building_id."""
    headers = {"Authorization": f"Bearer {token}"}
    g = await client.post("/groups", json={"name": "Group A"}, headers=headers)
    assert g.status_code == 201
    s = await client.post("/sites", json={"group_id": g.json()["id"], "name": "Site 1"}, headers=headers)
    assert s.status_code == 201
    b = await client.post(
        "/buildings",
        json={"site_id": s.json()["id"], "name": "Main", "floors": 3},
        headers=headers,
    )
    assert b.status_code == 201
    return s.json()["id"], b.json()["id"]


@pytest.mark.asyncio
async def test_register_device_triggers_poll(client, admin_token):
    site_id, building_id = await _seed_topology(client, admin_token)

    with patch("app.api.devices.poll_device_task") as mock_task:
        resp = await client.post(
            "/devices",
            json={
                "name": "SW-01",
                "mac_addr": "AA:BB:CC:DD:EE:FF",
                "ip_addr": "10.0.1.1",
                "site_id": site_id,
                "building_id": building_id,
                "protocol": "SSH",
                "ssh_id": "admin",
                "ssh_password": "cisco123",
                "ssh_port": 22,
                "device_type": "cisco_ios",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["device_type"] == "cisco_ios"
    mock_task.delay.assert_called_once_with(data["id"])


@pytest.mark.asyncio
async def test_register_device_invalid_mac(client, admin_token):
    site_id, building_id = await _seed_topology(client, admin_token)
    resp = await client.post(
        "/devices",
        json={
            "name": "SW-01",
            "mac_addr": "AABBCCDDEEFF",  # missing colons
            "ip_addr": "10.0.1.1",
            "site_id": site_id,
            "building_id": building_id,
            "protocol": "SSH",
            "ssh_id": "admin",
            "ssh_password": "cisco123",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ports_returns_409_when_not_managed(client, admin_token):
    site_id, building_id = await _seed_topology(client, admin_token)

    with patch("app.api.devices.poll_device_task"):
        resp = await client.post(
            "/devices",
            json={
                "name": "SW-01",
                "mac_addr": "AA:BB:CC:DD:EE:FF",
                "ip_addr": "10.0.1.1",
                "site_id": site_id,
                "building_id": building_id,
                "protocol": "SSH",
                "ssh_id": "admin",
                "ssh_password": "cisco123",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    device_id = resp.json()["id"]

    ports_resp = await client.get(
        f"/devices/{device_id}/ports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ports_resp.status_code == 409


@pytest.mark.asyncio
async def test_viewer_cannot_register_device(client, viewer_token):
    resp = await client.post(
        "/devices",
        json={
            "name": "SW-01",
            "mac_addr": "AA:BB:CC:DD:EE:FF",
            "ip_addr": "10.0.1.1",
            "site_id": 1,
            "building_id": 1,
            "protocol": "SSH",
            "ssh_id": "admin",
            "ssh_password": "cisco123",
        },
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_device_not_found(client, admin_token):
    resp = await client.get(
        "/devices/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
