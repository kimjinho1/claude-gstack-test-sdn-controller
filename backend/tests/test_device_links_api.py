"""Integration tests for /device-links API endpoints."""
import uuid
import pytest
from unittest.mock import patch


async def _seed_topology(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    g = await client.post("/groups", json={"name": "Group A"}, headers=headers)
    s = await client.post("/sites", json={"group_id": g.json()["id"], "name": "Site 1"}, headers=headers)
    b = await client.post(
        "/buildings",
        json={"site_id": s.json()["id"], "name": "Main", "floors": 3},
        headers=headers,
    )
    return s.json()["id"], b.json()["id"]


async def _create_device(client, token, name, ip, site_id, building_id):
    # Generate a unique MAC per call — avoids global counter pollution across test runs
    uid = uuid.uuid4().hex[:12].upper()
    mac = ":".join(uid[i:i+2] for i in range(0, 12, 2))
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.api.devices.poll_device_task"):
        resp = await client.post(
            "/devices",
            json={
                "name": name,
                "mac_addr": mac,
                "ip_addr": ip,
                "site_id": site_id,
                "building_id": building_id,
                "protocol": "SSH",
                "ssh_id": "admin",
                "ssh_password": "cisco123",
                "ssh_port": 22,
                "device_type": "cisco_ios",
            },
            headers=headers,
        )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_get_topology_graph_empty(client, admin_token):
    """Graph endpoint returns empty lists when no devices exist."""
    resp = await client.get(
        "/device-links/graph",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["devices"] == []
    assert data["links"] == []


@pytest.mark.asyncio
async def test_get_topology_graph_with_data(client, admin_token):
    """Graph includes devices and links."""
    site_id, building_id = await _seed_topology(client, admin_token)
    p_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)
    c_id = await _create_device(client, admin_token, "SW-02", "10.0.1.2", site_id, building_id)

    # Create link
    await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/device-links/graph",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["devices"]) == 2
    assert len(data["links"]) == 1
    assert data["links"][0]["parent_id"] == p_id
    assert data["links"][0]["child_id"] == c_id


@pytest.mark.asyncio
async def test_create_link_success(client, admin_token):
    """Successfully create a parent→child device link."""
    site_id, building_id = await _seed_topology(client, admin_token)
    p_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)
    c_id = await _create_device(client, admin_token, "SW-02", "10.0.1.2", site_id, building_id)

    resp = await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_id"] == p_id
    assert data["child_id"] == c_id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_link_self_loop_rejected(client, admin_token):
    """A device cannot be linked to itself."""
    site_id, building_id = await _seed_topology(client, admin_token)
    d_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)

    resp = await client.post(
        "/device-links",
        json={"parent_id": d_id, "child_id": d_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_link_missing_device_rejected(client, admin_token):
    """Link creation fails if parent or child device does not exist."""
    resp = await client.post(
        "/device-links",
        json={"parent_id": 9999, "child_id": 9998},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_link_duplicate_rejected(client, admin_token):
    """Creating the same link twice returns 409 Conflict."""
    site_id, building_id = await _seed_topology(client, admin_token)
    p_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)
    c_id = await _create_device(client, admin_token, "SW-02", "10.0.1.2", site_id, building_id)

    await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_link_success(client, admin_token):
    """Delete an existing link — returns 204 No Content."""
    site_id, building_id = await _seed_topology(client, admin_token)
    p_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)
    c_id = await _create_device(client, admin_token, "SW-02", "10.0.1.2", site_id, building_id)

    link_resp = await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    link_id = link_resp.json()["id"]

    resp = await client.delete(
        f"/device-links/{link_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204

    # Verify the link is gone
    list_resp = await client.get(
        "/device-links",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert all(link["id"] != link_id for link in list_resp.json())


@pytest.mark.asyncio
async def test_delete_link_not_found(client, admin_token):
    """Deleting a non-existent link returns 404."""
    resp = await client.delete(
        "/device-links/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_links(client, admin_token):
    """List all links returns correct results."""
    site_id, building_id = await _seed_topology(client, admin_token)
    p_id = await _create_device(client, admin_token, "SW-01", "10.0.1.1", site_id, building_id)
    c_id = await _create_device(client, admin_token, "SW-02", "10.0.1.2", site_id, building_id)
    c2_id = await _create_device(client, admin_token, "SW-03", "10.0.1.3", site_id, building_id)

    await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/device-links",
        json={"parent_id": p_id, "child_id": c2_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/device-links",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
