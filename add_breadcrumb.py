import os
import json
from deep_translator import GoogleTranslator
from sys import argv
from unidecode import unidecode

DICT_PATH = "examples/langdata/"
LANG_MAP = {"zh": "zh-TW"}
KEEP_ENGLISH = ["ar", "ja", "ko", "sv", "zh"]

path = argv[1]


def get_paths(lang: str, pathstr: str, dct: dict, translator: GoogleTranslator):
    dirs = pathstr.split("/")
    dirs.reverse()
    rooti = len(dirs)
    for i, d in enumerate(dirs):
        if d in dct["breadcrumbs"]:
            rooti = i
            break
    print(dirs)
    print(rooti)
    rem_dir = dirs[:rooti]
    rem_dir.reverse()
    current_path = ""
    if rooti < len(dirs):
        current_path = dct["breadcrumbs"][dirs[rooti]]["path"]+"/"
    for i, d in enumerate(rem_dir):
        asword = d.replace("-", " ")
        translated = translator.translate(asword)
        traspath = unidecode(translated.lower().replace(" ", "-"))
        if lang in KEEP_ENGLISH:
            traspath = d
        current_path += traspath
        dct["breadcrumbs"][d] = {
            "path": current_path,
            "display": translated
        }
        current_path += "/"


for lfl in os.listdir(DICT_PATH):
    lng = lfl.split(".json")[0]
    dctfile = open(DICT_PATH+lfl, "r", encoding="utf8")
    dctcontent = dctfile.read()
    dctfile.close()
    lngdict = json.loads(dctcontent)
    lcode = lng
    if lng in LANG_MAP:
        lcode = LANG_MAP[lng]
    t = GoogleTranslator(target=lcode)
    get_paths(lng, path, lngdict, t)

    dctfile = open(DICT_PATH+lfl, "w", encoding="utf8")
    dctfile.write(json.dumps(
        lngdict, ensure_ascii=False, indent=2).encode("utf8").decode())
    dctfile.close()
