
import os
import httpx

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

async def brave_search(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {"q": query, "count": 3}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        data = response.json()
        results = data.get("web", {}).get("results", [])
        if not results:
            return "Nessun risultato trovato da Brave."
        return "\n\n".join([f"{r['title']}\n{r['url']}" for r in results])

async def serpapi_search(query):
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "num": 3
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        results = data.get("organic_results", [])
        if not results:
            return "Nessun risultato trovato da SerpAPI."
        return "\n\n".join([f"{r['title']}\n{r['link']}" for r in results])
