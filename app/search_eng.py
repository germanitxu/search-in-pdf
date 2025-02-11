import os
from dataclasses import dataclass
from pymupdf import open, Page, Rect
from pymupdf.utils import search_for
import logging
import pickle
import redis

REDIS_PORT = 6379
HOST = "localhost"
r = redis.StrictRedis(host=HOST, port=REDIS_PORT, db=0)

logger = logging.getLogger(__name__)
FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)


@dataclass
class TextBox:
    box: str


@dataclass
class Match:
    page_num: str
    textboxes: list[TextBox]


@dataclass
class SearchResult:
    filename: str
    pdf_path: str
    matches: list[Match]
    occurrences: int

    @property
    def path_no_filename(self):
        return self.pdf_path.replace("/" + self.filename, "")


class SearchCache:
    def __init__(
        self,
        search_term: str,
        results: list[SearchResult],
        pdf_name_paths: list[tuple[str, str]],
    ):
        self.search_term = search_term
        self.results = results
        self.pdf_name_paths = pdf_name_paths


class Search:
    # Number of lines UP or down to define the textbox
    LINES_UP = 3
    LINES_DOWN = 3

    def __init__(self, paths):
        self.paths = paths

    @staticmethod
    def get_result_from_cached_search(path, search_obj: SearchCache) -> SearchResult:
        if path in search_obj.pdf_name_paths:
            _, pdf_path = path
            for res in search_obj.results:
                if res.pdf_path == pdf_path:
                    return res

    @staticmethod
    def cache_search_results(search_term, results, pdf_name_paths):
        logger.info("Caching results")
        to_cache_obj = SearchCache(search_term, results, pdf_name_paths)
        picked_obj = pickle.dumps(to_cache_obj)
        r.set(search_term, picked_obj)

    @staticmethod
    def uncache_search_results(search_term):
        logger.info(f"Uncaching by {search_term}")
        cached_search = r.get(search_term)
        uncached_search: SearchCache | None = None
        if cached_search:
            uncached_search = pickle.loads(cached_search)  # type: ignore
        return uncached_search

    @staticmethod
    def _extract_page_from_pdf(pdf_path) -> list[Page]:
        logger.info("Extracting doc")
        doc = open(pdf_path)
        # pdf[2].get_textbox(pdf[2].search_for("En", flags=1)[6])
        logger.info("Doc created")
        return doc.pages()

    def _extract_text_boxes_from_page(
        self, page: Page, search_term
    ) -> tuple[Match, int] | None:
        logger.info(f"Extracting text from page {page.number + 1}")
        try:
            p_rect = page.bound()
            p_width = p_rect.width
            matches: list[Rect] = search_for(page, search_term)
            textboxes = []
            if not len(matches):
                logger.info("No matches found in page")
                return
            logger.info("Finding TextBoxes")
            for match in matches:
                tl, br = match.top_left, match.bottom_right
                match_height = match.height
                y0 = tl.y - (match_height * self.LINES_UP)
                x0 = 0
                y1 = br.y + (match_height * self.LINES_DOWN)
                x1 = p_width
                new_rect = Rect(x0, y0, x1, y1)
                textboxes.append(TextBox(page.get_textbox(new_rect)))
            return Match((page.number + 1), textboxes), len(matches)
        except AssertionError:  # Raised by Page.bound
            logger.error("Page is None")
            return

    def process_pdf(self, pdf_name_path, search_term) -> SearchResult:
        filename, pdf_path = pdf_name_path
        logger.info(f"Processing PDF {pdf_name_path}")
        pages = self._extract_page_from_pdf(pdf_path)
        matches = []
        occurrences = 0
        for page in pages:
            tb_occurrences = self._extract_text_boxes_from_page(page, search_term)
            if tb_occurrences:
                match, occ = tb_occurrences
                matches.append(match)
                occurrences += occ

        if occurrences:
            logger.info(f"Found {occurrences} of {search_term} in {pdf_name_path}")
            matches = sorted(matches, key=lambda m: m.page_num)
            return SearchResult(filename, pdf_path, matches, occurrences)

    def _search(
        self, search_term: str, reload_cache: bool
    ) -> tuple[list[SearchResult], int]:
        """
        Search for a string in the pdfs under paths.
        :param search_term: String to search in paths
        :return:
        Returns a list of SearchResults
        """

        pdf_name_paths: list[tuple[str, str]] = []  # type: ignore

        uncached_search = self.uncache_search_results(search_term)
        if reload_cache:
            uncached_search = None
        logger.info("Searching PDFs in paths")
        for path in self.paths:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".pdf"):
                        logger.info(f"Found PDF {path}/{file}")
                        pdf_name_paths.append((file, os.path.join(root, file)))
        results = []
        total_occurences = 0
        if uncached_search and uncached_search.pdf_name_paths == pdf_name_paths:
            # It means we already searched for that term and on the paths that we want to look for
            logger.info("Results found in cache.")
            results = uncached_search.results
            total_occurences += sum((x.occurrences for x in uncached_search.results))
        else:
            for path in pdf_name_paths:
                cached_result: SearchResult | None = (
                    self.get_result_from_cached_search(path, uncached_search)
                    if uncached_search
                    else None
                )
                result = cached_result or self.process_pdf(path, search_term)
                if result:
                    logger.info(f"Finished searching in {path}")
                    results.append(result)

        self.cache_search_results(search_term, results, pdf_name_paths)
        results = sorted(results, key=lambda rs: self.paths.index(rs.path_no_filename))
        logger.info("Returning results.")
        return results, total_occurences

    def search(self, search_term: str, reload_cache=False):
        logger.info(f"Searching PDFs for {search_term}")
        return self._search(search_term, reload_cache)
