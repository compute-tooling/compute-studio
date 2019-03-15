import re


def title_fixup(title):
    return re.sub("[^a-zA-Z0-9]+", "-", title)
