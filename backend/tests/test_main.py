import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health") # Adjust endpoint if necessary
    assert response.status_code == 200
    # assert response.json() == {"status": "ok"} # Adjust expected response if necessary 