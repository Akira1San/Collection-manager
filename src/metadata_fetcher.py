import json
import os
import urllib.request
import urllib.parse
import urllib.error
import re
import html


def _json_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "CollectionManager/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _html_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "CollectionManager/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode()


def fetch_omdb(title, api_key, year=""):
    if not api_key:
        raise ValueError("OMDb API key is not configured.")
    url = f"http://www.omdbapi.com/?apikey={api_key}&t={urllib.parse.quote(title)}"
    if year:
        url += f"&y={urllib.parse.quote(year)}"
    data = _json_get(url)
    if data.get("Response") != "True":
        raise ValueError(data.get("Error", "No result found."))
    return _parse_omdb(data)


def _parse_omdb(data):
    genre = [g.strip() for g in data.get("Genre", "").split(",") if g.strip()]
    year = 0
    try:
        year = int(data.get("Year", "0").split("\u2013")[0].split("-")[0])
    except ValueError:
        pass
    return {
        "title": data.get("Title", ""),
        "year": year,
        "genre": genre,
        "description": data.get("Plot", ""),
        "cover": data.get("Poster", ""),
        "rating": data.get("imdbRating", ""),
        "director": data.get("Director", ""),
        "actors": data.get("Actors", ""),
    }


def fetch_wikipedia(title, year=""):
    if year:
        title += f" ({year})"
    search_url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&srsearch={urllib.parse.quote(title)}&format=json&srlimit=1"
    )
    search = _json_get(search_url)
    pages = search.get("query", {}).get("search", [])
    if not pages:
        raise ValueError("No Wikipedia page found.")

    page_title = pages[0]["title"]

    extract_url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&prop=extracts|pageprops|info&titles={urllib.parse.quote(page_title)}"
        f"&exintro=true&explaintext=true&format=json&redirects=1"
    )
    extract_data = _json_get(extract_url)
    pages_data = extract_data.get("query", {}).get("pages", {})
    page_id = list(pages_data.keys())[0]
    page = pages_data[page_id]
    description = page.get("extract", "").split("\n")[0] if page.get("extract") else ""

    infobox_url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&prop=pageprops&titles={urllib.parse.quote(page_title)}&format=json"
    )
    infobox_data = _json_get(infobox_url)
    pages_data2 = infobox_data.get("query", {}).get("pages", {})
    page_id2 = list(pages_data2.keys())[0]
    pageprops = pages_data2[page_id2].get("pageprops", {})

    wikibase = pageprops.get("wikibase_item", "")
    genre = []
    year = 0
    cover = ""
    if wikibase:
        claims_url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikibase}.json"
        claims_data = _json_get(claims_url)
        entity = claims_data.get("entities", {}).get(wikibase, {})
        claims = entity.get("claims", {})

        pub_date = claims.get("P577", [{}])[0].get("mainsnak", {}).get("datavalue", {})
        if pub_date:
            try:
                year = int(pub_date.get("value", {}).get("time", "")[:5])
            except (ValueError, IndexError):
                pass

        genre_claims = claims.get("P136", [])
        for g in genre_claims:
            gid = g.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "")
            if gid:
                label_url = f"https://www.wikidata.org/wiki/Special:EntityData/{gid}.json"
                label_data = _json_get(label_url)
                label_entity = label_data.get("entities", {}).get(gid, {})
                label = label_entity.get("labels", {}).get("en", {}).get("value", "")
                if label:
                    genre.append(label)

        for img_prop in ("P18", "P154"):
            image_claims = claims.get(img_prop, [])
            if image_claims:
                img_filename = image_claims[0].get("mainsnak", {}).get("datavalue", {}).get("value", "")
                if img_filename:
                    cover = (
                        "https://commons.wikimedia.org/wiki/Special:FilePath/"
                        f"{urllib.parse.quote(img_filename.replace(' ', '_'))}?width=500"
                    )
                    break

    if not cover:
        try:
            page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'))}"
            page_html = _html_get(page_url)
            m = re.search(
                r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>.*?'
                r'<img[^>]*src="(//upload\.wikimedia\.org[^"]+)"',
                page_html, re.DOTALL | re.IGNORECASE
            )
            if m:
                cover = "https:" + html.unescape(m.group(1))
        except Exception:
            pass

    return {
        "title": page_title,
        "year": year,
        "genre": genre,
        "description": description,
        "cover": cover,
        "source": "Wikipedia",
    }


def fetch_tmdb(title, api_key, year=""):
    if not api_key:
        raise ValueError("TMDB API key is not configured.")
    search_url = (
        f"https://api.themoviedb.org/3/search/movie?"
        f"api_key={api_key}&query={urllib.parse.quote(title)}"
    )
    if year:
        search_url += f"&year={urllib.parse.quote(year)}"
    search = _json_get(search_url)
    results = search.get("results", [])
    if not results:
        raise ValueError("No TMDB result found.")
    movie = results[0]
    movie_id = movie["id"]
    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    details = _json_get(details_url)
    genre = [g["name"] for g in details.get("genres", [])]
    poster = details.get("poster_path", "")
    cover = f"https://image.tmdb.org/t/p/w500{poster}" if poster else ""
    return {
        "title": details.get("title", ""),
        "year": details.get("release_date", "")[:4] if details.get("release_date") else 0,
        "genre": genre,
        "description": details.get("overview", ""),
        "cover": cover,
        "source": "TMDB",
    }


def download_cover(url, save_dir, filename):
    if not url or not url.startswith("http"):
        return ""
    os.makedirs(save_dir, exist_ok=True)
    ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        ext = ".jpg"
    filename = filename.replace(" ", "_")
    save_path = os.path.join(save_dir, f"{filename}{ext}")
    if os.path.exists(save_path):
        return save_path
    if os.path.isdir(save_dir):
        for f in os.listdir(save_dir):
            name, _ = os.path.splitext(f)
            if name == filename:
                return os.path.join(save_dir, f)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CollectionManager/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(save_path, "wb") as f:
            f.write(data)
        return save_path
    except Exception:
        return ""
