import os
import sys

from collections import defaultdict

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
if len(sys.argv) == 1:
    raise ValueError("No project name specified")

project_name = sys.argv[1]

FILES = [
    "admin.py",
    "apps.py",
    "constants.py",
    "displayer.py",
    "forms.py",
    "meta_parameters.py",
    "models.py",
    "parser.py",
    "submit.py",
    "urls.py",
    "views.py",
    "migrations/__init__.py",
    "tests/__init__.py",
    "tests/test_views.py",
    "tests/outputs.json",
]

new_files = defaultdict(str)
for basename in FILES:
    with open(os.path.join(CURRENT_PATH, "project", basename)) as f:
        template = f.read()
    print("__________________________________________________")
    print(template)
    template = template.replace("{project}", project_name.lower())
    template = template.replace("{Project}", project_name.title())
    template = template.replace("{PROJECT}", project_name.upper())
    print(template)
    new_files[basename] = template

destination_dir = os.path.join(CURRENT_PATH, "..", "webapp", "apps",
                               "projects", project_name.lower())
os.mkdir(destination_dir)
os.mkdir(os.path.join(destination_dir, "tests"))
os.mkdir(os.path.join(destination_dir, "migrations"))


for basename, text in new_files.items():
    with open(os.path.join(destination_dir, basename), "w") as f:
        f.write(text)

