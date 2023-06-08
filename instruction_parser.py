import pyparsing as pp
import insobjects as io
import re
import os
from debug_print import log
from insobjects import FormattedLiteral, Literal, DictionaryKey, CSSSelector, Instruction, Command, RemoveCommand, ReplaceCommand, TranslateCommand, InstructionType

        
def parse_c3s(line, lineno, res: pp.ParseResults):
    selector = CSSSelector(res[0])
    log("pc3ss:")
    res.clear()
    res.append(selector)
    #print("pc3s:",res,"\n",selector.selectstr)

def parse_c3si(line, lineno, res: pp.ParseResults):
    log("c3sis:",res)
    selector, index = res[0]
    selector.index = index
    res.clear()
    res.append(selector)
    #print("c3sie:",res)

def parse_c3sb(line, lineno, res: pp.ParseResults):
    log("c3sbs:",res)
    selector, bs, be = res[0]
    selector.add_bounds(bs, be)
    res.clear()
    res.append(selector)
    #print("c3sbe:",res)

def parse_c3sm(line, lineno, res: pp.ParseResults):
    log("c3sm:",res)
    pass

def parse_c3sa(line, lineno, res: pp.ParseResults):
    log("c3sa:",res)
    selector, dot, attrname = res
    selector.target = attrname
    res.clear()
    res.append(selector)

def parse_iselect(line, lineno, res: pp.ParseResults):
    log("is",res)
    index = int(res[0][1])
    res.clear()
    res.append(index)
    #print("ie:",res)

def parse_bselect(line, lineno, res: pp.ParseResults):
    log("bs", res)
    b1 = res[0][1]
    b2 = res[0][3]
    res.clear()
    res.append(b1)
    res.append(b2)
    #print("be:",res)

def parse_expr(line, lineno, res: pp.ParseResults):
    log("es", res)
    #print("ee", res)

def parse_ctxchange(line, lineno, res: pp.ParseResults):
    #print("ctxcs", res)
    selectorlhs, op, selectorrhs, scolon = res
    ins = Instruction(InstructionType.CONTEXT_CHANGE)
    ins.add_operand(selectorlhs)
    ins.add_operand(selectorrhs)
    res.clear()
    res.append(ins)
    #print("ctxce", res)

def parse_creat(line, lineno, res: pp.ParseResults):
    #print("creats", res)
    htmlStr = res[0]
    ins = Instruction(InstructionType.CREATE)
    ins.add_operand(htmlStr)
    res.clear()
    res.append(ins)
    #print("create", res)

def parse_assign(line, lineno, res: pp.ParseResults):
    log("assigns", res)
    lhs, op, rhs = res
    instype = InstructionType.ASSIGN
    if op == "=>":
        instype = InstructionType.ASSIGN_REVERSE
    ins = Instruction(instype)
    rhs.islhs = False
    ins.add_operand(lhs)
    ins.add_operand(rhs)
    res.clear()
    res.append(ins)
    #print("assigne", res)

def parse_instr(line, lineno, res: pp.ParseResults):
    log("instrs", line)
    space_count = 0
    for c in line:
        if c == " ":
            space_count += 1
        elif c == "\t":
            space_count += 4
        else:
            break
    ins = res[0]
    if type(ins) == Instruction:
        #print("new depth:",space_count//4)
        ins.depth = space_count // 4
    #print("instre", res)

def parse_replace(line, lineno, res: pp.ParseResults):
    log("replaces", res)
    cmdstr, old, new = res
    cmd = ReplaceCommand(old, new, cmdstr.startswith("t"))
    res.clear()
    res.append(cmd)
    #print("replacee", res)

def parse_remove(line, lineno, res: pp.ParseResults):
    log("removes", res)
    cmdstr, selector = res
    cmd = RemoveCommand(selector, cmdstr.startswith("t"))
    res.clear()
    res.append(cmd)
    #print("remove", res)

def parse_translate(line, lineno, res: pp.ParseResults):
    log("translates", res)
    cmdstr, selector = res
    cmd = TranslateCommand(selector)
    res.clear()
    res.append(cmd)

def parse_cmd(line, lineno, res: pp.ParseResults):
    log("cmds",res)
    _, com = res
    res.clear()
    res.append(com)
    #print("cmde",res)

def parse_formatted_literal(line, lineno, res: pp.ParseResults):
    log("fr", res)
    expressions = []
    dictliteral = pp.QuotedString("{",end_quote_char="}").add_parse_action(parse_dict_literal)
    matcher = pp.ZeroOrMore(pp.CharsNotIn('{')) + pp.ZeroOrMore(dictliteral+pp.ZeroOrMore(pp.CharsNotIn("{")))
    expressions = matcher.parse_string(res[0])
    log("EXPR:",expressions)
    fsl = FormattedLiteral(expressions)
    res.clear()
    res.append(fsl)

def parse_dict_literal(line, lineno, res: pp.ParseResults):
    keys = res[0].split(".")
    replace_pr(DictionaryKey(keys), res)

def replace_pr(value, res: pp.ParseResults):
    res.clear()
    res.append(value)

def apply_includes(current_abspath: str, content: str)-> str:
    dirpath = os.path.dirname(current_abspath)
    matches: list[re.Match] = re.finditer("#include <(.*?)>(\n|\Z)", content)
    new_content = ""
    last_index = 0
    for m in matches:
        relpath = m.group(1)
        starti, endi = m.span()
        fullpath = os.path.abspath(os.path.join(dirpath, relpath))
        include_file = open(fullpath, "r", encoding="utf8")
        include_content = include_file.read()
        include_file.close()
        new_content += content[last_index:starti] + apply_includes(fullpath, include_content) + "\n"
        last_index = endi
    new_content += content[last_index:]
    return new_content

def parse_file(path: str) -> tuple[list[Command], list[Instruction]]:
    num = pp.Or([pp.Regex("-[0-9]+"), pp.Regex("[0-9]*")])
    index = pp.Or([pp.Regex("-[0-9]+"), pp.Regex("[0-9]+")])
    bound = num
    dictliteral = pp.QuotedString("{",end_quote_char="}").add_parse_action(parse_dict_literal)
    stringliteral = pp.QuotedString('"', esc_char="\\").add_parse_action(lambda l,ln,r: replace_pr(Literal(r[0]), r))
    formattedliteral = pp.QuotedString('f"', end_quote_char='"', esc_char="\\").add_parse_action(parse_formatted_literal)
    literal = formattedliteral ^ stringliteral ^ dictliteral
    c3s = pp.QuotedString("%").add_parse_action(parse_c3s)
    iselect = pp.Group("["+index+"]").add_parse_action(parse_iselect)
    bselect = pp.Group("["+bound+":"+bound+"]").add_parse_action(parse_bselect)
    attrib = pp.Or(["text", "alt", "content", "lang", "href", "src", "data-src", "innerHTML"])
    c3si = pp.Group(c3s + iselect).add_parse_action(parse_c3si)
    c3sb = pp.Group(c3s + bselect).add_parse_action(parse_c3sb)
    c3sm = pp.Or([c3sb, c3si, c3s]).add_parse_action(parse_c3sm)
    c3sa = (c3sm+"."+attrib).add_parse_action(parse_c3sa)
    expr = (c3sa ^ c3sm ^ literal).add_parse_action(parse_expr)
    ctxins = (c3sm+"<->"+c3sm+":").add_parse_action(parse_ctxchange)
    creatins = pp.QuotedString("+","+").add_parse_action(parse_creat)
    revassnins = (expr +"=>"+expr).add_parse_action(parse_assign)
    assnins = pp.Or([expr+"="+expr, expr+"<="+expr]).add_parse_action(parse_assign)
    ins = pp.Or([assnins, revassnins, creatins, ctxins]).add_parse_action(parse_instr)
    replacecmd = pp.Or([("rreplace"+literal+literal), ("treplace"+literal+literal)]).add_parse_action(parse_replace)
    translatecmd = ("translate"+c3sm).add_parse_action(parse_translate)
    removecmd = pp.Or([("rremove"+c3sm), ("tremove"+c3sm)]).add_parse_action(parse_remove)
    dictcmd = ("addict" + formattedliteral).add_parse_action(lambda l,ln,r: replace_pr(io.AddDictCommand(r[1]), r))
    cmd = pp.Or([replacecmd, removecmd, dictcmd, translatecmd])
    cmdins = ("#"+cmd).add_parse_action(parse_cmd)
    line = pp.Or([cmdins, ins])

    f = open(path, "r", encoding="utf8")
    content = f.read()
    f.close()
    full_contents = apply_includes(os.path.abspath(path), content)
    res = open("combined_instructions.mstr", "w", encoding="utf8")
    res.write(full_contents)
    res.close()
    lines = full_contents.splitlines()
    total_results = []
    for l in lines:
        if l.strip() == "": continue
        log("[INSTRUCTION START]",l,"[INSTRUCTION END]")
        res = line.parse_string(l)
        total_results.append(res.as_list()[0])
    depths: list[Instruction] = {}
    commands = []
    instructions = []
    for res in total_results:
        if issubclass(type(res), Command):
            commands.append(res)
        else:
            asinstr: Instruction = res
            parent_depth = asinstr.depth - 1
            #print("ins:",str(asinstr))
            if parent_depth == -1:
                #print("add ass ins")
                instructions.append(asinstr)
            elif len(depths) > parent_depth:
                #print("add as child")
                depths[parent_depth].sub_instructions.append(asinstr)
            if asinstr.type == InstructionType.CONTEXT_CHANGE:
                depths[asinstr.depth] = asinstr
    return (commands, instructions)