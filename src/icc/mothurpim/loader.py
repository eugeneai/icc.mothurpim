from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef
from rdflib.namespace import DC, DCTERMS, FOAF
from pkg_resources import resource_dir
import re
import glob
import os.path

CPPEXT = ".cpp"
HEXT = ".h"


class Loader:
    """Loads Mothur commands from a directory of command
    sources to a graph.
    """

    def __init__(self, sourcedir):
        self.sourcedir = sourcedir
        self.loaded = False
        self.graph = Graph()

    def load(self):
        if self.loaded:
            return self.graph
        # Traverse all .h and .cpp files
        # with searching command definitions.

        findnames = self.sourcedir+"/*"+CPPEXT
        files = glob.glob(findnames)
        for f in files:
            name = f.replace(CPPEXT, "")
            header = glob.glob(name+HEXT+"*")[0]
            print("Processing -----: ", f, header)
            fl = CommandLoader(self, f, header)
            fl.load()

        self.loaded = True
        return self.graph


# NAME = "[a-zA-Z.]+"
NAME = ".+?"


def re_simple(methodname):
    s = 'get'+methodname+r'\(\s*\)\s*{\s*return\s+"('+NAME+r')"\s*;\s*}'
    return re.compile(s)


RE_NAME = re_simple("CommandName")
RE_CITE = re_simple("Citation")
RE_CAT = re_simple("CommandCategory")
RE_DESCR = re_simple("Description")

RE_COMPAR = re.compile(
    r'CommandParameter\s+p(\w+)\s*\((.+?)\)\s*;')
RE_HELP = re.compile(r'helpString\s*\+?=\s*"(.*?)"')

RE_GOP = re.compile(
    r'(getOutputPattern\s*\(\s*string.+?catch.+?\}.+?\})', re.DOTALL)

RE_GOP_NAME = re.compile(r'getOutputPattern\s*\(\s*string\s+(\w+)\s*\)')
# RE_GOP_NAME = re.compile(r'(getOutputPattern\s*\(\s*string\s+)')

CP_TYPES = {'InputTypes', 'Boolean', 'Number', 'Multiple', 'String'}


def COMPAR(name="",
           type="",
           options="",
           optionsDefault="",
           chooseOnlyOneGroup="",
           chooseAtLeastOneGroup="",
           linkedGroup="",
           outputTypes="",
           multipleSelectionAllowed=False,
           required=False,
           important=False):

    if type == "Multiple":
        options = options.split("-")

    d = {"name": name,
         "type": type,
         "options": options,
         "optionsDefault": optionsDefault,
         "chooseOnlyOneGroup": chooseOnlyOneGroup,
         "chooseAtLeastOneGroup": chooseAtLeastOneGroup,
         "linkedGroup": linkedGroup,
         "outputTypes": outputTypes,
         "multipleSelectionAllowed": multipleSelectionAllowed,
         "required": required,
         "important": important}

    return d


CTX = {"true": True, "false": False, "compar": COMPAR}


class CommandLoader:
    def __init__(self, loader, cpp, header):
        self.loader = loader
        self.cpp = cpp
        self.h = header

    def load(self):
        self.loadh()
        self.loadcpp()

    def loadh(self):
        self.text = open(self.h).read()
        name = self.find(RE_NAME, "name")
        category = self.find(RE_CAT, "category")
        citation = self.find(RE_CITE, "citation")
        description = self.find(RE_DESCR, "description")
        print(f"{name}:{category}\n {citation}\n {description}")

    def find(self, re, ent):
        m = re.search(self.text)
        if m is not None:
            value = m.group(1)
        else:
            raise ValueError(ent+" not found")
        return value

    def loadcpp(self):
        del self.text
        self.cpptext = open(self.cpp).read()
        self.params = {}
        for m in RE_COMPAR.finditer(self.cpptext):
            pname, params = m.groups()
            self.processparams(pname, params)

        help = ""
        for m in RE_HELP.finditer(self.cpptext):
            help += m.group(1)
        self.help = help.replace(r"\n", "\n")
        print("HELP->", self.help)
        m = RE_GOP.search(self.cpptext)
        self.gop = None
        if m:
            self.gop = m.group(1)
            print(self.gop)
            m = RE_GOP_NAME.search(self.gop)
            if m:
                self.gopparam = m.group(1)
                print("---> ", self.gopparam)
            else:
                raise ValueError("cannot recodgnize parameter name")
        else:
            print("WARNING: getOutputPattern not found")

    def processparams(self, pname, defs):
        s = "compar("+defs+")"
        # print(s)
        defs = eval(s, CTX)
        self.params[defs["name"]] = defs


def rdflib_example():
    g = Graph()

    # Create an identifier to use as the subject for Donna.
    donna = BNode()

    # Add triples using store's add method.
    g.add((donna, RDF.type, FOAF.Person))
    g.add((donna, FOAF.nick, Literal("donna", lang="foo")))
    g.add((donna, FOAF.name, Literal("Donna Fales")))
    g.add((donna, FOAF.mbox, URIRef("mailto:donna@example.org")))

    # Iterate over triples in store and print them out.
    print("--- printing raw triples ---")
    for s, p, o in g:
        print((s, p, o))

    # For each foaf:Person in the store print out its mbox property.
    print("--- printing mboxes ---")
    for person in g.subjects(RDF.type, FOAF.Person):
        for mbox in g.objects(person, FOAF.mbox):
            print(mbox)

    # Bind a few prefix, namespace pairs for more readable output
    g.bind("dc", DC)
    g.bind("foaf", FOAF)

    print(g.serialize(format='n3'))

    return True
