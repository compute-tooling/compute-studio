import os

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings

import markdown

DOCS = ["PUBLISH.md", "IOSCHEMA.md", "ENVIRONMENT.md", "FUNCTIONS.md"]


def md_to_html_name(mdname):
    return mdname.split(".")[0].lower() + ".html"


def basename(name_w_ext):
    return name_w_ext.split(".")[0].lower()


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        basedir = settings.BASE_DIR
        md = markdown.Markdown(extensions=["fenced_code", "toc"])
        for docname in DOCS:
            with open(os.path.join(basedir, "docs", docname), "r") as f:
                htmldoc = md.convert(f.read())
            page = render_to_string("docs/template.html", {"doc": htmldoc})

            for _docname in DOCS:
                page = page.replace(_docname, f"/docs/publish/{basename(_docname)}/")
            # print("bef", docname, "<code>" in page, "<pre><code>" in page)
            # page = page.replace("<code>", "<pre><code>")
            # print("aft", docname, "<code>" in page, "<pre><code>" in page)
            # page = page.replace("</code>", "</code></pre>")
            out = md_to_html_name(docname)
            with open(os.path.join(basedir, "templates", "docs", out), "w") as f:
                f.write(page)
