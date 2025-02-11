from jinja2 import Environment, PackageLoader, select_autoescape
from .search_eng import Search, SearchResult, Match, TextBox
from app.config import Config as Cf
import re

package = PackageLoader("app")
env = Environment(loader=package, autoescape=select_autoescape())
config = Cf()


class TextBoxTemplate(TextBox):

    def __init__(self, textbox):
        self.box = textbox.box

    def __str__(self):
        return self.box

    def _highlight_search_term(self, search_term):
        self.box = re.sub(
            search_term,
            f"<span class='highlight'>{search_term}</span>",
            self.box,
            flags=re.IGNORECASE,
        )

    def _replace_linejump_br(self):
        self.box = self.box.replace("\n", "<br>")

    def get_render_obj(self, seach_term):
        self._highlight_search_term(seach_term)
        self._replace_linejump_br()
        return self


class SearchResultTemplate(SearchResult):
    def __init__(self, *args):
        super().__init__(*args)

    @property
    def path(self):
        prefix = config.prefix
        if prefix:
            return self.pdf_path.replace(prefix, "")
        else:
            return self.pdf_path

    @property
    def path_breadcrumbs(self):
        return self.path.split("/")


class Template:
    TEMPLATE_NAME = ""

    def __init__(self):
        self.template = env.get_template(self.TEMPLATE_NAME)
        self.context_data = {}

    def render(self):
        return self.template.render(**self.context_data)


class SearchTemplate(Template):
    """
    Renders SearchResults into html
    """

    TEMPLATE_NAME = "search.html"

    def __init__(self, search_term, force_cache):
        super().__init__()
        self.search_term: str | None = search_term
        self.force_cache: bool | None = force_cache
        self._buid_context()

    def process_textboxes(self, boxes: list[TextBox]):
        return [TextBoxTemplate(box).get_render_obj(self.search_term) for box in boxes]

    def _preprocess_results(self, results: list[SearchResult]) -> list[SearchResult]:

        new_results = []
        for search_result in results:
            highlighted_matches = [
                Match(match.page_num, self.process_textboxes(match.textboxes))
                for match in search_result.matches
            ]

            new_results.append(
                SearchResultTemplate(
                    search_result.filename,
                    search_result.pdf_path,
                    highlighted_matches,
                    search_result.occurrences,
                )
            )
        return new_results

    def _buid_context(self):
        self.context_data["search_term"] = self.search_term
        if self.search_term:
            s = Search(config.paths)
            preprocessed_results, total_occurrences = s.search(
                self.search_term, self.force_cache
            )
            results = self._preprocess_results(preprocessed_results)
            self.context_data["results"] = results
            self.context_data["total_occurrences"] = total_occurrences
