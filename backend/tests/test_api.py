import pytest


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Olympiad Archive API is live"}


@pytest.mark.asyncio
async def test_competitions_and_problems(client):
    # create a competition
    comp_data = {"name": "IMO", "country": "International", "url": "https://imo-official.org"}
    r = await client.post("/competitions/", json=comp_data)
    assert r.status_code == 200
    comp = r.json()
    assert comp["name"] == "IMO"
    comp_id = comp["id"]

    # fetch competitions list
    r = await client.get("/competitions/")
    assert r.status_code == 200
    assert any(c["id"] == comp_id for c in r.json())

    # create a tag then a problem linked to competition
    tag = await client.post("/tags/", json={"name": "Number Theory"})
    tag_id = tag.json()["id"]

    prob_data = {
        "competition_id": comp_id,
        "year": 2024,
        "problem_number": 1,
        "statement": "Sample statement",
        "difficulty": 5,
        "source_url": "http://example.com",
        "tag_ids": [tag_id],
    }
    r = await client.post("/problems/", json=prob_data)
    assert r.status_code == 200
    prob = r.json()
    assert prob["competition_id"] == comp_id
    assert prob["year"] == 2024
    assert tag_id in [t["id"] for t in prob.get("tags", [])]
    problem_id = prob["id"]

    # retrieve by id and ensure solutions list present
    r = await client.get(f"/problems/{problem_id}")
    assert r.status_code == 200
    assert r.json()["id"] == problem_id

    # update problem (change year + tags)
    new_tag = await client.post("/tags/", json={"name": "Geometry"})
    new_tag_id = new_tag.json()["id"]
    update_data = {**prob_data, "statement": "Updated", "year": 2025, "tag_ids": [new_tag_id]}
    r = await client.put(f"/problems/{problem_id}", json=update_data)
    assert r.status_code == 200
    assert r.json()["statement"] == "Updated"
    assert r.json()["year"] == 2025
    assert new_tag_id in [t["id"] for t in r.json().get("tags", [])]

    # delete problem
    r = await client.delete(f"/problems/{problem_id}")
    assert r.status_code == 204

    # ensure not found afterwards
    r = await client.get(f"/problems/{problem_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tags_and_solutions(client):
    # create a tag
    tag_data = {"name": "Algebra"}
    r = await client.post("/tags/", json=tag_data)
    assert r.status_code == 200
    tag = r.json()
    assert tag["name"] == "Algebra"
    tag_id = tag["id"]

    # duplicate tag should return 400
    r = await client.post("/tags/", json=tag_data)
    assert r.status_code == 400

    # create another competition and problem for solution
    comp = await client.post("/competitions/", json={"name": "USAMO"})
    comp_id = comp.json()["id"]
    prob = await client.post(
        "/problems/",
        json={
            "competition_id": comp_id,
            "year": 2023,
            "problem_number": 2,
            "statement": "Another",
        },
    )
    problem_id = prob.json()["id"]

    # add a solution to that problem
    sol_data = {"problem_id": problem_id, "content": "Solution text", "author": "Test"}
    r = await client.post("/solutions/", json=sol_data)
    assert r.status_code == 200
    sol = r.json()
    assert sol["problem_id"] == problem_id
    assert sol["author"] == "Test"

    # retrieve problem with solutions via problems endpoint
    r = await client.get(f"/problems/{problem_id}")
    assert r.status_code == 200
    data = r.json()
    assert "solutions" in data
    assert len(data["solutions"]) == 1
