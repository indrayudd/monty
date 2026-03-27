import os
import time
import pathlib
import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any, Dict, Optional


OPENALEX_API_BASE = "https://api.openalex.org"
OPENALEX_CONTENT_BASE = "https://content.openalex.org"


@dataclass
class _SimpleResponse:
    body: bytes

    def json(self) -> Dict[str, Any]:
        return json.loads(self.body.decode("utf-8"))


class _StreamingResponse:
    def __init__(self, response: Any):
        self._response = response

    def __enter__(self) -> "_StreamingResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._response.close()

    def iter_content(self, chunk_size: int = 1024 * 64):
        while True:
            chunk = self._response.read(chunk_size)
            if not chunk:
                break
            yield chunk


class OpenAlexClient:
    def __init__(self, api_key: str, user_agent: Optional[str] = None, timeout: int = 30):
        if not api_key:
            raise ValueError("OPENALEX_API_KEY is required")
        self.api_key = api_key
        self.timeout = timeout
        self.headers: Dict[str, str] = {}
        if user_agent:
            self.headers["User-Agent"] = user_agent

    def build_url(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        params = dict(params or {})
        params["api_key"] = self.api_key
        query = urlencode(params)
        return f"{url}?{query}" if query else url

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None, stream: bool = False) -> Any:
        full_url = self.build_url(url, params=params)
        req = Request(full_url, headers=self.headers)
        if stream:
            resp = urlopen(req, timeout=self.timeout)
            return _StreamingResponse(resp)
        with urlopen(req, timeout=self.timeout) as resp:
            body = resp.read()
        return _SimpleResponse(body)

    def search_works(
        self,
        topic_query: str,
        per_page: int = 10,
        extra_filter: Optional[str] = None,
        sort: Optional[str] = None,
        select: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search OpenAlex works.

        Example query:
            search="violence in montessori children"

        Example filters:
            open_access.is_oa:true
        """
        params: Dict[str, Any] = {
            "search": topic_query,
            "per_page": per_page,
        }
        if extra_filter:
            params["filter"] = extra_filter
        if sort:
            params["sort"] = sort
        if select:
            params["select"] = select

        return self._get(f"{OPENALEX_API_BASE}/works", params=params).json()

    def get_work(self, work_id: str) -> Dict[str, Any]:
        """
        work_id can be:
        - 'W1234567890'
        - full OpenAlex URL
        - DOI form like 'doi:10.xxxx/....'
        """
        normalized = work_id.rstrip("/").split("/")[-1] if work_id.startswith("http") else work_id
        return self._get(f"{OPENALEX_API_BASE}/works/{normalized}").json()

    def download_xml(self, work_id: str, out_path: pathlib.Path) -> bool:
        """
        Attempts to download cached TEI XML from the OpenAlex content API.
        Returns True on success, False if unavailable.
        """
        normalized = work_id.rstrip("/").split("/")[-1] if work_id.startswith("http") else work_id
        url = f"{OPENALEX_CONTENT_BASE}/works/{normalized}.grobid-xml"

        try:
            with self._get(url, stream=True) as resp:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)
            return True
        except HTTPError:
            return False


def extract_basic_metadata(work: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull a compact metadata view from an OpenAlex work object.
    """
    primary_location = work.get("primary_location") or {}
    best_oa_location = work.get("best_oa_location") or {}
    open_access = work.get("open_access") or {}

    authorships = work.get("authorships") or []
    authors = []
    for a in authorships[:5]:
        author_obj = a.get("author") or {}
        name = author_obj.get("display_name")
        if name:
            authors.append(name)

    return {
        "id": work.get("id"),
        "openalex_id": (work.get("id") or "").rstrip("/").split("/")[-1] if work.get("id") else None,
        "title": work.get("display_name") or work.get("title"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "cited_by_count": work.get("cited_by_count", 0),
        "doi": (work.get("ids") or {}).get("doi"),
        "authors": authors,
        "is_oa": open_access.get("is_oa"),
        "oa_status": open_access.get("oa_status"),
        "has_content_pdf": (work.get("has_content") or {}).get("pdf"),
        "landing_page_url": (
            best_oa_location.get("landing_page_url")
            or primary_location.get("landing_page_url")
        ),
        "source": (
            ((primary_location.get("source") or {}).get("display_name"))
            or ((best_oa_location.get("source") or {}).get("display_name"))
        ),
        "abstract_inverted_index": work.get("abstract_inverted_index"),
    }


def reconstruct_abstract(abstract_inverted_index: Optional[Dict[str, Any]]) -> str:
    if not abstract_inverted_index:
        return ""

    positions: Dict[int, str] = {}
    for word, indexes in abstract_inverted_index.items():
        if not isinstance(indexes, list):
            continue
        for index in indexes:
            if isinstance(index, int):
                positions[index] = word

    if not positions:
        return ""

    return " ".join(positions[index] for index in sorted(positions))


def extract_abstract_text(work: Dict[str, Any]) -> str:
    abstract_text = work.get("abstract")
    if isinstance(abstract_text, str) and abstract_text.strip():
        return abstract_text.strip()

    return reconstruct_abstract(work.get("abstract_inverted_index"))


def score_work_for_selection(work: Dict[str, Any]) -> float:
    """
    Simple local ranking heuristic.
    You can replace this with embeddings, reranking, or LLM scoring later.
    """
    cited_by = work.get("cited_by_count", 0) or 0
    year = work.get("publication_year", 0) or 0
    open_access = (work.get("open_access") or {}).get("is_oa", False)
    has_pdf = ((work.get("has_content") or {}).get("pdf", False))

    score = 0.0
    score += min(cited_by, 300) * 0.05
    score += max(year - 2018, 0) * 0.5
    score += 10.0 if open_access else 0.0
    score += 15.0 if has_pdf else 0.0
    return score


def retrieve_topic_papers(
    topic: str,
    api_key: str,
    n_candidates: int = 10,
    n_select: int = 3,
    download_dir: str = "downloads",
    require_oa: bool = True,
) -> Dict[str, Any]:
    """
    Retrieval-only pipeline:
    1. Search topic
    2. Get top N candidate works
    3. Choose top K locally
    4. Fetch full metadata
    5. Optionally download TEI XML files
    """
    client = OpenAlexClient(
        api_key=api_key,
        user_agent="my-retriever/0.1 (contact: you@example.com)"
    )

    filters = []
    if require_oa:
        filters.append("open_access.is_oa:true")

    search_resp = client.search_works(
        topic_query=topic,
        per_page=n_candidates,
        extra_filter=",".join(filters) if filters else None,
        select=(
            "id,display_name,publication_year,publication_date,cited_by_count,ids,"
            "open_access,has_content,primary_location,best_oa_location,authorships"
        ),
    )

    candidates = search_resp.get("results", [])
    if not candidates:
        return {
            "topic": topic,
            "candidates_found": 0,
            "selected": [],
        }

    ranked = sorted(candidates, key=score_work_for_selection, reverse=True)
    selected = ranked[:n_select]

    output = {
        "topic": topic,
        "candidates_found": len(candidates),
        "selected": [],
    }

    for work in selected:
        work_id = (work.get("id") or "").rstrip("/").split("/")[-1]
        full_work = client.get_work(work_id)
        meta = extract_basic_metadata(full_work)

        xml_path = None
        xml_downloaded = False

        if work_id:
            safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in work_id)
            xml_path_obj = pathlib.Path(download_dir) / f"{safe_name}.xml"
            xml_downloaded = client.download_xml(work_id, xml_path_obj)
            if xml_downloaded:
                xml_path = str(xml_path_obj.resolve())

        output["selected"].append({
            "metadata": meta,
            "xml_downloaded": xml_downloaded,
            "xml_path": xml_path,
        })

        time.sleep(0.2)

    return output


if __name__ == "__main__":
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    topic = "violence in montessori children"

    result = retrieve_topic_papers(
        topic=topic,
        api_key=api_key,
        n_candidates=10,
        n_select=3,
        download_dir="openalex_xml",
        require_oa=True,
    )

    import json
    print(json.dumps(result, indent=2))
