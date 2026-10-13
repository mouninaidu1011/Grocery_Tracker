import requests


def find_food_image(name):
    """Item name tho Wikipedia lo photo vethukutundi. Dorikithe URL istundi, lekapote None."""
    api_url = "https://en.wikipedia.org/w/api.php"
    headers = {"User-Agent": "GroceryTrackerStudentProject/1.0"}

    for search_text in [f"{name} food", name]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_text,
            "gsrlimit": 5,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 300,
            "format": "json",
        }
        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=8)
            pages = response.json().get("query", {}).get("pages", {})
            ordered = sorted(pages.values(), key=lambda p: p.get("index", 99))
            for page in ordered:
                if "thumbnail" in page:
                    return page["thumbnail"]["source"]
        except Exception:
            pass
    return None