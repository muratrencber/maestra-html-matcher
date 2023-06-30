from sys import argv
import json
import os
from pathlib import Path

DICT_PATH = "examples/langdata/"
org_path_dict = {}
full_paths = []
lines = []

web_rel_paths = {}
flags = {}
lang_names = {}

org_paths = argv[1]
root = argv[2]
page = argv[3]

is_index = False
is_index_inp = input("Is index? [y/n]")
if is_index_inp.lower() == "y":
    is_index = True

opf = open(org_paths, "r", encoding="utf8")
for l in opf.readlines():
    code, path = l.split(",")
    org_path_dict[code] = path.strip()

for lfl in os.listdir(DICT_PATH):
    lng = lfl.split(".json")[0]
    dctfile = open(DICT_PATH+lfl, "r", encoding="utf8")
    dctcontent = dctfile.read()
    dctfile.close()
    lngdict = json.loads(dctcontent)
    rel_path = lngdict["breadcrumbs"][page]["path"]
    web_rel_paths[lng] = rel_path
    flags[lng] = lngdict["flag"]
    lang_names[lng] = lngdict["name"]
    full_path = os.path.abspath(os.path.join(root, rel_path))
    full_path = full_path.replace("/", "\\")
    if is_index:
        if not full_path.endswith("\\"):
            full_path += "\\"
        Path(full_path).mkdir(parents=True, exist_ok=True)
        full_path += "index.html"
    else:
        elems = full_path.split("\\")
        Path("\\".join(elems[:-1])).mkdir(parents=True, exist_ok=True)
        full_path += ".html"

    l = f"python main.py examples\\{page}\\target_index.html {org_path_dict[lng]} examples\\{page}\\instructions.match -e lang={lng} -o {full_path}"
    lines.append(l)
    full_paths.append(full_path)

prtcom = "npx prettier --write "+" ".join(full_paths)
lines.append(prtcom)

finalfile = open(f"run-{page}.bat", "w", encoding="utf8")
finalfile.write(str("\n".join(lines)))

flags["en"] = "us"
web_rel_paths["en"] = web_rel_paths["ja"].split("ja/")[1]
web_rel_paths["x-default"] = web_rel_paths["en"]
lang_names["en"] = "English"

sorted_keys = sorted(list(web_rel_paths.keys()))
web_rel_paths = {i: web_rel_paths[i] for i in sorted_keys}
for key in web_rel_paths:
    print(
        f'<link rel="alternate" hreflang="{key}" href="https://maestra.ai/{web_rel_paths[key]}" />')

del web_rel_paths["x-default"]
print("\n")
for key in web_rel_paths:
    print(
        f'<li><a href="/{web_rel_paths[key]}"><img alt="{flags[key]}" data-src="/assets/template/img/svg/flags/{flags[key]}.svg"> {lang_names[key]}</a></li>')
