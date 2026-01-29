"""Manual TLE loader for debugging."""
import httpx
import asyncio

TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"

async def fetch_tle():
    print("Fetching TLE data from CelesTrak...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(TLE_URL)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            print(f"Got {len(lines)} lines ({len(lines)//3} satellites)")
            print("First satellite:")
            print(lines[0])
            print(lines[1])
            print(lines[2])
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(fetch_tle())
