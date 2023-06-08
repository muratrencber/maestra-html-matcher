from bs4 import BeautifulSoup as bs
from enum import Enum
from debug_print import log
import os
import json


class InstructionType(Enum):
    CONTEXT_CHANGE = 1
    ASSIGN = 2
    ASSIGN_REVERSE = 3
    CREATE = 4


class Expression():
    def __init__(self) -> None:
        self.islhs: bool = True

    def get_value(self, context):
        pass

    def set_value(self, context, other: "Expression"):
        pass


class Literal(Expression):
    def __init__(self, value) -> None:
        super().__init__()
        self.value = value

    def get_value(self, context):
        return self.value

    def set_value(self, context, other: Expression):
        self.value = other.get_value(context)

    def __str__(self) -> str:
        return f'"{self.value}"'


class DictionaryKey(Expression):
    def __init__(self, keys: list[str]) -> None:
        super().__init__()
        self.keys: list[str] = keys

    def get_value(self, context):
        root = context["dict"]
        for k in self.keys:
            root = root[k]
        return root

    def set_value(self, context, other: Expression):
        otherval = other.get_value()
        root = context["dict"]
        depth = len(self.keys)
        for i in range(len(self.keys)):
            if i == depth - 1:
                root[self.keys[i]] = otherval
                return
            root = root[self.keys[i]]

    def __str__(self) -> str:
        return "{"+".".join(self.keys)+"}"


class FormattedLiteral(Expression):
    def __init__(self, expressions) -> None:
        super().__init__()
        self.expressions = expressions

    def get_value(self, context):
        return "".join([e if isinstance(e, str) else e.get_value(context) for e in self.expressions])


class CSSSelector(Expression):
    def __init__(self, res) -> None:
        super().__init__()
        self.selectstr: str = res
        self.bounds: list[str] = []
        self.index: int = 0
        self.target: str = "innerHTML"

    def add_bounds(self, b1, b2):
        self.bounds.append(b1)
        self.bounds.append(b2)

    def get_elem_value(self, elem: bs):
        if self.target == "innerHTML":
            return elem.contents
        if self.target == "text":
            return "".join([c.text for c in elem.children if c.name is None])
        return elem.attrs[self.target]

    def set_elem_value(self, elem: bs, value):
        if self.target == "innerHTML":
            elem.contents = value
        elif self.target == "text":
            elemtexts = [
                c for c in elem.children if c.name is None and c.text.strip() != ""]
            if len(elemtexts) > 0:
                elemtexts[0].replace_with(value)
        else:
            elem.attrs[self.target] = value

    def get_value(self, context):
        return [self.get_elem_value(c) for c in self.get_elems(context)]

    def get_elems(self, context) -> list[bs]:
        root: bs = context["target"]
        if not self.islhs:
            root = context["reference"]
        children = [root]
        if self.selectstr.strip() != "":
            children = root.select(self.selectstr)
        startbound: int = self.index
        endbound: int = self.index + 1
        if len(self.bounds) == 2:
            if self.bounds[0] == "":
                startbound = 0
            else:
                startbound = int(self.bounds[0])
            if self.bounds[1] == "":
                endbound = len(children)
            else:
                endbound = int(self.bounds[1])
        return children[startbound:endbound]

    def set_value(self, context, other: Expression):
        elems = self.get_elems(context)
        log("CSSSelector, Elems:", elems)
        othervalues = other.get_value(context)
        if not isinstance(othervalues, list):
            othervalues = [othervalues]
        log("Other elems:", othervalues)
        thislen = len(elems)
        otherlen = len(othervalues)
        minlen = min(thislen, otherlen)
        if minlen == 0:
            log("MinLen is zero! (this:", thislen, "- other", otherlen, ")")
        for i in range(minlen):
            self.set_elem_value(elems[i], othervalues[i])

    def __str__(self) -> str:
        return f"CSSSelector: %{self.selectstr}%"


class Instruction():
    def __init__(self, type) -> None:
        self.type: InstructionType = type
        self.operands: list[Expression] = []
        self.depth: int = 0
        self.sub_instructions: list[Instruction] = []

    def add_operand(self, operand: Expression):
        self.operands.append(operand)

    def apply(self, context: dict):
        log(self.type, ":", [str(op) for op in self.operands])
        log("Subinstruction count:", len(self.sub_instructions))
        if self.type == InstructionType.ASSIGN or self.type == InstructionType.ASSIGN_REVERSE:
            receiver = self.operands[0] if self.type == InstructionType.ASSIGN else self.operands[1]
            sender = self.operands[1] if self.type == InstructionType.ASSIGN else self.operands[0]
            receiver.set_value(context, sender)
        if self.type == InstructionType.CONTEXT_CHANGE:
            lhs: CSSSelector = self.operands[0]
            rhs: CSSSelector = self.operands[1]
            rhs.islhs = False
            lhselems = lhs.get_elems(context)
            rhselems = rhs.get_elems(context)
            mincount = min(len(lhselems), len(rhselems))
            log("CTXCMinCount:", mincount, "lhscount:",
                len(lhselems), "rhscount:", len(rhselems))
            log("CTXStart:", context["target"])
            for i in range(mincount):
                new_context = context.copy()
                new_context["target"] = lhselems[i]
                new_context["reference"] = rhselems[i]
                for subins in self.sub_instructions:
                    subins.apply(new_context)
            log("CTXEnd:", context["target"])
        if self.type == InstructionType.CREATE:
            root: bs = context["target"]
            log(self.operands[0])
            elem = bs(self.operands[0], features="lxml")
            root.append(elem)
        return context

    def __str__(self) -> str:
        res = [str(self.type)]
        res += [str(op) for op in self.operands]
        resstr = "\t".join(["" for i in range(self.depth + 1)]
                           )+" - ".join(res) + "\n"

        if len(self.sub_instructions) > 0:
            resstr += "\t".join(["" for i in range(self.depth + 1)])+"CHILDREN"
            for ci in self.sub_instructions:
                resstr += "\n"+str(ci)
            resstr += "\t".join(["" for i in range(self.depth + 1)]
                                )+"CHILDRENEND"+"\n"
        return resstr


class Command:
    def __init__(self) -> None:
        pass

    def apply(self, context):
        pass


class ReplaceCommand(Command):
    def __init__(self, old: FormattedLiteral, new: FormattedLiteral, forTarget: bool) -> None:
        super().__init__()
        self.old: FormattedLiteral = old
        self.new: FormattedLiteral = new
        self.forTarget: bool = forTarget

    def apply(self, context):
        selectedKey = "reference"
        if self.forTarget:
            selectedKey = "target"
        res: str = str(context[selectedKey])
        log("REPLACOM, RES:\n", res)
        context[selectedKey] = bs(res.replace(self.old.get_value(
            context), self.new.get_value(context)), features="lxml")


class RemoveCommand(Command):
    def __init__(self, css_selector: CSSSelector, forTarget: bool) -> None:
        super().__init__()
        self.css_selector: CSSSelector = css_selector
        self.css_selector.islhs = forTarget

    def apply(self, context):
        elems: list[bs] = self.css_selector.get_elems(context)
        for e in elems:
            e.decompose()


class TranslateCommand(Command):
    def __init__(self, css_selector: CSSSelector) -> None:
        super().__init__()
        self.css_selector: CSSSelector = css_selector

    def apply(self, context):
        elems = self.css_selector.get_elems(context)
        for e in elems:
            self.translate_elem(e, context)

    def translate_elem(self, elem: bs, context):
        elemtexts = [
            c for c in elem.children if c.name is None and c.text.strip() != ""]
        if "alt" in elem.attrs:
            translated_attr = context["translator"].translate(
                elem.attrs["alt"])
            if translated_attr is None:
                log("translation for:", elem.attrs["alt"], "yields None!")
            else:
                elem.attrs["alt"] = translated_attr
        for txt in elemtexts:
            translated = context["translator"].translate(txt.text)
            if translated is None:
                log("translation for:", txt.text, "yields None!")
            else:
                txt.replace_with(translated)
        children = [c for c in elem.children if c.name is not None]
        for c in children:
            self.translate_elem(c, context)


class AddDictCommand(Command):
    def __init__(self, fl: FormattedLiteral) -> None:
        super().__init__()
        self.path: FormattedLiteral = fl

    def apply(self, context):
        pathval = self.path.get_value(context)
        abspath = os.path.abspath(os.path.join(context["absdir"], pathval))
        if os.path.exists(pathval):
            abspath = pathval
        dct = json.load(open(abspath, "r", encoding="utf8"))
        for key in dct:
            context["dict"][key] = dct[key]
