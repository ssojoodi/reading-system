from html.parser import HTMLParser

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {"strong", "b", "em", "i"}


class SimpleFormattingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ALLOWED_TAGS:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(conditional_escape(data))

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")

    def render(self) -> str:
        return "".join(self.parts)


@register.filter
def simple_note_html(value):
    parser = SimpleFormattingParser()
    parser.feed(value or "")
    parser.close()
    html = parser.render().replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        line.replace("\n", "<br>")
        for line in html.split("\n\n")
        if line.strip()
    ]
    return mark_safe("".join(f"<p>{paragraph}</p>" for paragraph in paragraphs))
