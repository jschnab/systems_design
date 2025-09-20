import re

from bs4 import BeautifulSoup

HTML_TAG_REGEX = re.compile(r"<.*?>")


def remove_html_tags(text):
    return re.sub(HTML_TAG_REGEX, "", text)


def remove_html_tags_except_em(text):
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup.find_all():
        if tag.name != "em":
            tag.unwrap()
    return str(soup)
