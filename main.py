from instruction_parser import Command, Instruction, CSSSelector, parse_file
from bs4 import BeautifulSoup as bs
from sys import argv
from deep_translator import GoogleTranslator
from debug_print import log, set_debug
import re
import os

ctx = {"target": None, "reference": None, "dict": {"environ": {}}}
google_translate_map = {"zh": "zh-TW"}

OUTPUT_PATH = "output.html"


def parse_environment_variable(arg: str):
    key, value = arg.split("=")
    ctx["dict"]["environ"][key] = value


def parse_output_path(arg: str):
    global OUTPUT_PATH
    OUTPUT_PATH = arg


def map_lang(lang: str) -> str:
    if lang in google_translate_map:
        return google_translate_map[lang]
    return lang


FLAG_PARSERS = {
    "e": parse_environment_variable,
    "o": parse_output_path
}

if len(argv) < 4:
    log("Invalid argument count!")
    exit()

target_html_path = argv[1]
reference_html_path = argv[2]
instructions_path = argv[3]

if len(argv) > 4:
    last_flag = ""
    splitted_args = argv[4:]
    for arg in splitted_args:
        strarg = arg.strip()
        if strarg.startswith("-"):
            if strarg == "-d":
                set_debug(True)
            else:
                last_flag = strarg[1:]
            continue
        FLAG_PARSERS[last_flag](strarg)


commands, instructions = parse_file(instructions_path)

targetfile = open(target_html_path, "r", encoding="utf-8")
target_html_contents = targetfile.read()
targetfile.close()

referencefile = open(reference_html_path, "r", encoding="utf-8")
reference_html_contents = referencefile.read()
reference_html_contents = reference_html_contents.replace(
    "</br></br>", "</p><p>")
log(reference_html_contents)
log("======END======")
referencefile.close()

# fromstring(target_html_contens)
target = bs(target_html_contents, features="lxml")
# fromstring(reference_html_contens)
reference = bs(reference_html_contents, features="lxml")

ctx["target"] = target
ctx["reference"] = reference
ctx["translator"] = GoogleTranslator(
    "auto", target=map_lang(ctx["dict"]["environ"]["lang"]))
ctx["absdir"] = os.path.dirname(instructions_path)
log("TARGET TYPE", type(ctx["target"]))
for c in commands:
    c.apply(ctx)
for i in instructions:
    i.apply(ctx)
prettyHTML = ctx["target"].prettify(
    encoding="utf8").decode("utf8")  # prettify the html
log(re.search("\n\s*<span(.*?)class=\"path", prettyHTML))
prettyHTML = re.sub("\n\s*</span>", "</span>", prettyHTML)
prettyHTML = re.sub("\n\s*<span(.*?)class=\"path",
                    "<span\\1class=\"path", prettyHTML)
outfile = open(OUTPUT_PATH, "w", encoding="utf8")
outfile.write(prettyHTML)
outfile.close()

comout = open("comout.txt", "w", encoding="utf8")
comres = ""
for i in instructions:
    comres += str(i) + "\n"
comout.write(comres)
comout.close()
