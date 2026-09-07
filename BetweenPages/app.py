from flask import Flask, render_template, request, redirect, url_for, session
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
import json
import os
import re
import unicodedata

import requests

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "between-pages-secret")

HEADERS = {"User-Agent": "BetweenPagesApp/1.0"}
MAX_RESULTS = 12
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY and OpenAI else None
print("OpenAI key loaded:", bool(OPENAI_API_KEY))


def safe_get(url, params=None, timeout=15):
    try:
        response = requests.get(url, params=params or {}, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        print("API ERROR:", error)
        return {}


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    value = str(value).strip()
    return [value] if value else []


def normalise(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def meaningful_tokens(value):
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "in", "into", "is", "of", "on", "or", "the", "to", "with", "what",
        "which", "where", "when", "that", "this", "these", "those", "book",
        "books", "teach", "about", "does", "should", "could", "would", "have",
        "will", "people", "their", "they", "your", "us"
    }
    return {token for token in normalise(value).split() if len(token) > 2 and token not in stop_words}


def openlibrary_book(item):
    authors = as_list(item.get("author_name")) or ["Unknown Author"]
    cover_id = item.get("cover_i")
    return {
        "title": item.get("title", "Unknown Title"),
        "author": ", ".join(authors),
        "authors": authors,
        "subjects": as_list(item.get("subject")),
        "series": as_list(item.get("series")),
        "description": item.get("first_sentence", "") if isinstance(item.get("first_sentence"), str) else "",
        "cover": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
        "source": "Open Library"
    }


def gutendex_book(item):
    authors = [a.get("name") for a in item.get("authors", []) if isinstance(a, dict) and a.get("name")]
    authors = authors or ["Unknown Author"]
    formats = item.get("formats", {}) or {}
    text_url = formats.get("text/plain; charset=utf-8") or formats.get("text/plain")
    html_url = formats.get("text/html; charset=utf-8") or formats.get("text/html")
    subjects = as_list(item.get("subjects")) + as_list(item.get("bookshelves"))
    return {
        "id": item.get("id"), "title": item.get("title", "Unknown Title"),
        "author": ", ".join(authors), "authors": authors, "subjects": subjects,
        "description": " ".join(subjects), "cover": formats.get("image/jpeg"),
        "text_url": text_url, "html_url": html_url,
        "full_text_url": html_url or text_url, "has_full_text": bool(text_url or html_url),
        "source": "Project Gutenberg"
    }


def search_books(query, language=""):
    params = {"q": query, "limit": MAX_RESULTS, "fields": "key,title,author_name,cover_i,subject,series"}
    if language:
        params["language"] = language
    data = safe_get(OPEN_LIBRARY_URL, params)
    return [openlibrary_book(item) for item in data.get("docs", [])[:MAX_RESULTS]]


def find_original(book_title):
    # Use "q" (general search) instead of "title" — the title field does a
    # stricter match and was failing on common queries like "harry potter".
    data = safe_get(OPEN_LIBRARY_URL, {"q": book_title, "limit": 20})
    books = [openlibrary_book(item) for item in data.get("docs", [])]
    if not books:
        return None
    requested = normalise(book_title)
    def score(book):
        title = normalise(book.get("title", ""))
        if title == requested:
            return 100
        if requested in title:
            return 70
        return len(meaningful_tokens(title) & meaningful_tokens(requested))
    return max(books, key=score)


def analyse_book(book, preferences=""):
    empty = {"genres": [], "themes": [], "vibes": [], "search_terms": []}
    if not ai_client:
        return empty
    prompt = f"""Return only valid JSON with arrays named genres, themes, vibes, and search_terms.
Suggest other books with a similar reading experience. Do not recommend the same book.
User preferences: {preferences}
Title: {book.get('title')}
Author: {book.get('author')}
Subjects: {book.get('subjects', [])}"""
    try:
        response = ai_client.responses.create(model=OPENAI_MODEL, input=prompt)
        value = json.loads(response.output_text.strip())
        return value if isinstance(value, dict) else empty
    except Exception as error:
        print("AI ANALYSIS ERROR:", error)
        return empty


def build_alternatives(book_title, preferences="", language="", author=""):
    original = find_original(book_title)
    if not original:
        return [book for book in search_books(book_title, language) if normalise(book["title"]) != normalise(book_title)]

    analysis = analyse_book(original, preferences)
    terms = []
    for key in ("search_terms", "genres", "themes", "vibes"):
        terms.extend(as_list(analysis.get(key)))
    terms.extend([part.strip() for part in preferences.split(",") if part.strip()])
    terms.extend(original.get("subjects", [])[:10])
    if not terms:
        terms.extend(["fantasy", "friendship", "adventure", "classic fiction"])

    original_title = normalise(original.get("title", ""))
    original_subjects = set().union(*(meaningful_tokens(x) for x in original.get("subjects", [])))
    unique = {}
    for term in dict.fromkeys(terms):
        params = {"q": term, "limit": 30}
        if language:
            params["language"] = language
        data = safe_get(OPEN_LIBRARY_URL, params)
        for item in data.get("docs", []):
            candidate = openlibrary_book(item)
            candidate_title = normalise(candidate.get("title", ""))
            if not candidate_title or candidate_title == original_title or original_title in candidate_title or candidate_title in original_title:
                continue
            candidate_subjects = set().union(*(meaningful_tokens(x) for x in candidate.get("subjects", [])))
            score = 1 + 3 * len(original_subjects & candidate_subjects) + 4 * len(meaningful_tokens(preferences) & candidate_subjects)
            key = (candidate_title, normalise(candidate.get("author", "")))
            if key not in unique or score > unique[key].get("score", 0):
                candidate["score"] = score
                unique[key] = candidate
    results = sorted(unique.values(), key=lambda book: book.get("score", 0), reverse=True)
    if results:
        return results[:MAX_RESULTS]

    fallback = []
    for term in original.get("subjects", [])[:4] or ["fiction", "adventure", "friendship"]:
        fallback.extend(search_books(term, language)[:5])
    return [book for book in fallback if normalise(book["title"]) != original_title][:MAX_RESULTS]


@app.route("/")
def home():
    return render_template("BetweenPages.html", active_page="home")


@app.route("/search")
def search():
    mode = request.args.get("mode", "search")
    query = request.args.get("q", "").strip()
    author = request.args.get("author", "").strip()
    language = request.args.get("language", "").strip()
    preferences = request.args.get("preferences", "").strip()
    books = []
    if mode == "search" and query:
        books = search_books(query, language)
    elif mode == "alternative" and query:
        books = build_alternatives(query, preferences, language, author)
    saved_shelves = session.get("shelves", {})
    saved_favorites = session.get("favorites", [])
    for book in books:
        book["is_favorite"] = any(x.get("title") == book["title"] and x.get("author") == book["author"] for x in saved_favorites)
        book["saved_on"] = next((name for name, items in saved_shelves.items() if any(x.get("title") == book["title"] and x.get("author") == book["author"] for x in items)), "")
    return render_template("search.html", books=books, query=query, author=author, preferences=preferences, mode=mode, active_page="search")


@app.route("/shelves")
def shelves():
    return render_template("shelves.html", shelves=session.get("shelves", {}), active_page="shelves")


@app.route("/shelf", methods=["POST"])
def shelf():
    title, author = request.form.get("title", ""), request.form.get("author", "")
    cover, shelf_name = request.form.get("cover", ""), request.form.get("shelf", "")
    action, shelves_data = request.form.get("action", "add"), session.get("shelves", {})
    if shelf_name:
        shelves_data.setdefault(shelf_name, [])
        book = {"title": title, "author": author, "cover": cover}
        if action == "remove":
            shelves_data[shelf_name] = [x for x in shelves_data[shelf_name] if x != book]
        elif book not in shelves_data[shelf_name]:
            shelves_data[shelf_name].append(book)
        session["shelves"] = shelves_data
        session.modified = True
    return redirect(request.referrer or url_for("search"))


@app.route("/favorites")
def favorites():
    return render_template("favorites.html", books=session.get("favorites", []), active_page="favorites")


@app.route("/favorite", methods=["POST"])
def favorite():
    book = {"title": request.form.get("title", ""), "author": request.form.get("author", ""), "cover": request.form.get("cover", "")}
    favorites_data = session.get("favorites", [])
    existing = next((x for x in favorites_data if x.get("title") == book["title"] and x.get("author") == book["author"]), None)
    if existing:
        favorites_data.remove(existing)
    else:
        favorites_data.append(book)
    session["favorites"], session.modified = favorites_data, True
    return redirect(request.referrer or url_for("favorites"))


def extract_book_title(question):
    """Extract a likely book title from common Book Buddy questions."""
    patterns = [
        r"(?:what\s+is\s+the\s+moral\s+of)\s+[\"']?(.+?)[\"']?\??$",
        r"(?:what\s+did|what\s+does)\s+(.+?)\s+(?:teach|teach us|show us|tell us)\s+about\s+.+?\??$",
        r"(?:friendship|courage|love|identity|moral|lesson|themes?)\s+(?:of|in|from)\s+[\"']?(.+?)[\"']?\??$",
    ]
    for pattern in patterns:
        match = re.search(pattern, question.strip(), re.IGNORECASE)
        if match:
            title = match.group(1).strip(" ?.!\"'")
            if normalise(title) in {"this book", "the book", "this story", "the story", "it"}:
                continue
            if len(title.split()) >= 1:
                return title
    return ""


TITLE_LENSES = {
    "harry potter": "friendship as loyalty, trust, and standing by someone through hard choices",
    "harry potter and the philosophers stone": "friendship as loyalty, trust, and standing by someone through hard choices",
    "harry potter and the sorcerers stone": "friendship as loyalty, trust, and standing by someone through hard choices",
    "the little prince": "care, responsibility, and how meaningful relationships change the way people see the world",
    "pride and prejudice": "pride, first impressions, and the willingness to revise one's judgment",
    "the great gatsby": "ambition, longing, and how pursuing an ideal can distort a person's view of reality",
}

TOPIC_LENSES = {
    "friendship": "friendship as loyalty, trust, and the way relationships shape difficult choices",
    "moral": "the moral as an interpretation — compare characters' choices, consequences, and values rather than expecting one official answer",
    "courage": "courage as how people respond to fear, responsibility, and difficult choices",
    "love": "love as care, loyalty, sacrifice, and the tension between desire and responsibility",
    "identity": "identity as belonging, self-understanding, and how other people shape a person's sense of self",
}


def metadata_book_buddy_answer(question, title_query=None):
    """Give a warm, honest discussion starter without requiring an OpenAI key."""
    title_query = title_query or extract_book_title(question)
    if not title_query:
        return (
            "Tell me which book you're thinking about and I'll dig into it with you — "
            "e.g. “What did Harry Potter teach us about friendship?”"
        )

    book = find_original(title_query)
    if not book:
        return (
            f"I couldn't find ‘{title_query}’ — try searching for it in Discover first, "
            "then come back and ask me about it."
        )

    subjects = [s for s in book.get("subjects", []) if len(s) < 80][:8]
    subject_text = ", ".join(subjects)
    title_key = normalise(book.get("title", ""))
    question_terms = meaningful_tokens(question)

    lens = next((text for key, text in TITLE_LENSES.items() if key in title_key), None)
    if not lens:
        lens = next((text for term, text in TOPIC_LENSES.items() if term in question_terms), TOPIC_LENSES["moral"])

    opener = (
        f"{book['title']} by {book['author']} touches on {subject_text} — "
        if subject_text else
        f"{book['title']} by {book['author']} — "
    )

    return (
        f"{opener}one way to think about it is {lens}.\n\n"
        "That's just a starting point — dig into the book itself for the full picture."
    )


def ask_book_buddy(question, title_query=None):
    if not ai_client:
        return metadata_book_buddy_answer(question, title_query)

    context_line = f"The user is discussing: {title_query}\n" if title_query else ""
    prompt = f"""
You are Book Buddy, a literary discussion companion.
Help the user discuss a specific book’s themes, morals, lessons, friendships,
character development, and important choices. Do not recommend books; Discover
handles recommendations. Do not invent plot details or quotes. Separate
interpretation from factual information. If the title is unclear, ask for it.
{context_line}
User question:
{question}
"""
    try:
        response = ai_client.responses.create(model=OPENAI_MODEL, input=prompt)
        return response.output_text.strip()
    except Exception as error:
        print("BOOK BUDDY ERROR:", error)
        return metadata_book_buddy_answer(question, title_query)


@app.route("/book_buddy", methods=["GET", "POST"])
def book_buddy():
    question = request.form.get("question", "").strip() if request.method == "POST" else ""
    answer = None
    if question:
        title_query = extract_book_title(question) or session.get("book_buddy_last_title", "")
        if title_query:
            session["book_buddy_last_title"] = title_query
            session.modified = True
        answer = ask_book_buddy(question, title_query)
    return render_template("book_buddy.html", answer=answer, question=question, active_page="book_buddy")


@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings")


if __name__ == "__main__":
    app.run(debug=True)
