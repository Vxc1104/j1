import os
from notion_client import Client


def get_client() -> Client:
    return Client(auth=os.getenv("NOTION_API_KEY"))


def search_notion(query: str, max_results: int = 5) -> list[dict]:
    client = get_client()
    result = client.search(query=query, page_size=max_results)
    pages = []
    for item in result.get("results", []):
        title = ""
        if item["object"] == "page":
            props = item.get("properties", {})
            for prop in props.values():
                if prop["type"] == "title" and prop["title"]:
                    title = prop["title"][0]["plain_text"]
                    break
        pages.append({
            "id": item["id"],
            "title": title or "Ohne Titel",
            "url": item.get("url", ""),
            "type": item["object"],
        })
    return pages


def get_page_content(page_id: str) -> str:
    client = get_client()
    blocks = client.blocks.children.list(block_id=page_id)
    text_parts = []
    for block in blocks.get("results", []):
        btype = block["type"]
        if btype in block and "rich_text" in block[btype]:
            for rt in block[btype]["rich_text"]:
                text_parts.append(rt.get("plain_text", ""))
    return "\n".join(text_parts)


def get_database_entries(database_id: str, max_results: int = 10) -> list[dict]:
    client = get_client()
    result = client.databases.query(database_id=database_id, page_size=max_results)
    entries = []
    for page in result.get("results", []):
        entry = {"id": page["id"]}
        for name, prop in page.get("properties", {}).items():
            ptype = prop["type"]
            if ptype == "title" and prop["title"]:
                entry[name] = prop["title"][0]["plain_text"]
            elif ptype == "rich_text" and prop["rich_text"]:
                entry[name] = prop["rich_text"][0]["plain_text"]
            elif ptype == "number":
                entry[name] = prop["number"]
            elif ptype == "select" and prop["select"]:
                entry[name] = prop["select"]["name"]
            elif ptype == "date" and prop["date"]:
                entry[name] = prop["date"]["start"]
        entries.append(entry)
    return entries
