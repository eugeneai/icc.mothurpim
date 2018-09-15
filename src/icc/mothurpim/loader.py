from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef, RDFS
from rdflib.namespace import DC, DCTERMS, FOAF, XSD
from icc.ngs.namespace import NGS, NGSP, SCHEMA, V, OSLC, CNT, NCO
from pkg_resources import resource_dir
import re
import glob
import os.path

CUR = Namespace("http://icc.ru/ontologies/NGS/mothur/")

# URL: https://github.com/eugeneai/icc.mothurpim


CPPEXT = ".cpp"
HEXT = ".h"


class Loader:
    """Loads Mothur commands from a directory of command
    sources to a graph.
    """

    def __init__(self, sourcedir):
        self.sourcedir = sourcedir
        self.loaded = False
        g = self.graph = Graph()

        self.spec = NGSP.spec

        g.add((self.spec, RDF.type, NGSP.Specification))

        g.bind('oslc', OSLC)
        g.bind('ngs', NGS)
        g.bind('ngsp', NGSP)
        g.bind('schema', SCHEMA)
        g.bind('dc', DC)
        g.bind('dcterms', DCTERMS)
        g.bind('v', V)
        g.bind('cnt', CNT)
        g.bind('mothur', CUR)
        g.bind('nco', NCO)

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

    def save(self, filename, format="rdf"):
        g = self.graph
        s = self.graph.serialize(format=format)
        o = open(filename, "wb")
        o.write(s)
        o.close()


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

RE_GOP_NAME = re.compile(
    r'getOutputPattern\s*\(\s*string\s+(\w+)\s*\)')
RE_GOP_RECORD = re.compile(
    r'if.+?==\s+"((\w|-)+)".+?pattern\s*=\s*"(.+?)"', re.MULTILINE | re.DOTALL)

RE_MOTUR_WIKI = re.compile(
    r'((https?|ftp)://www\.mothur\.org/wiki/(\w|\.|-)*)')

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

    opts = options
    if type == "Multiple":
        options = options.split("-")

    outputTypes = outputTypes.strip()
    if outputTypes:
        types = outputTypes.split("-")

    xsdbool = XSD.boolean
    d = {DC.title: Literal(name),
         NGSP.type: CUR[type],
         "optionsOrig": opts,
         "options": options,
         "optionsDefault": optionsDefault,
         "chooseOnlyOneGroup": chooseOnlyOneGroup,
         "chooseAtLeastOneGroup": chooseAtLeastOneGroup,
         "linkedGroup": linkedGroup,
         "outputTypesOrig": outputTypes,
         "multipleSelectionAllowed": Literal(multipleSelectionAllowed, datatype=xsdbool),
         "required": Literal(required, datatype=xsdbool),
         "important": Literal(important, datatype=xsdbool)}

    if outputTypes:
        d["outputTypes"] = types

    return d


CTX = {"true": True, "false": False, "compar": COMPAR}


RE_COMMENT = re.compile("(.*?)\s+//")


class CommandLoader:
    def __init__(self, loader, cpp, header):
        self.loader = loader
        self.graph = loader.graph
        self.cpp = cpp
        self.h = header

    def load(self):
        self.loadh()
        assert (self.command)
        self.loadcpp()

    def readfile(self, name, op="r"):
        i = open(name, op)
        s = []
        for l in i:
            m = RE_COMMENT.match(l)
            if m:
                l = m.group(1)
            s.append(l)
        return "".join(s)

    def loadh(self):
        self.text = self.readfile(self.h)
        name = self.find(RE_NAME, "name")
        category = self.find(RE_CAT, "category")
        citation = self.find(RE_CITE, "citation").replace(r"\n", "\n")
        description = self.find(RE_DESCR, "description")
        print(f"{name}:{category}\n {citation}\n {description}")
        g = self.graph
        #filename = os.path.split(self.h)[1].strip()
        # assert(filename)
        self.commandname = name
        res = CUR[self.commandname]
        self.command = res = URIRef(res)
        g.add((res, RDF.type, NGSP["Module"]))
        g.add((self.loader.spec, NGSP.module, res))
        g.add((res, DC.title, Literal(name)))
        g.add((res, DCTERMS.description, Literal(description)))
        g.add((res, SCHEMA.citation, Literal(citation)))
        g.add((res, V.category, Literal(category)))
        if citation:
            m = RE_MOTUR_WIKI.search(citation)
            if m:
                g.add((res, NCO.websiteURL, URIRef(m.group(1))))
            else:
                print("WARNING: Wiki page not found")

    def find(self, re, ent):
        m = re.search(self.text)
        if m is not None:
            value = m.group(1)
        else:
            raise ValueError(ent+" not found")
        return value

    def loadcpp(self):
        del self.text
        self.cpptext = self.readfile(self.cpp)

        g = self.loader.graph
        res = self.command

        self.params = {}
        for m in RE_COMPAR.finditer(self.cpptext):
            pname, params = m.groups()
            self.processparams(pname, params)

        help = ""
        for m in RE_HELP.finditer(self.cpptext):
            help += m.group(1)+r"\n"
        help = help.replace(r"\n\n", r"\n")
        help = help.replace(r"\n", "\n")
        self.help = help
        #self.help = help
        # print("HELP->", self.help)
        help = self.help = self.help.strip()
        if help:
            g.add((res, SCHEMA.softwareHelp, Literal(help)))

        m = RE_GOP.search(self.cpptext)
        self.gop = None
        if m:
            self.gop = m.group(1)
            # print(self.gop)
            gopr = BNode()
            g.add((gopr, RDF.type, CNT.Chars))
            g.add((res, NGSP.outputPattern, gopr))
            g.add((gopr, CNT.chars, Literal(self.gop)))
            m = RE_GOP_NAME.search(self.gop)
            if m:
                self.gopparam = m.group(1)
                g.add((gopr, NGSP.parameterName, Literal(self.gopparam)))
            else:
                raise ValueError("cannot recodgnize parameter name")
            self.process_gop(gopr)
        else:
            print("WARNING: getOutputPattern not found")

    def processparams(self, pname, defs):
        s = "compar("+defs+")"
        # print(s)
        defs = eval(s, CTX)
        g = self.graph
        name = defs[DC.title]
        self.params[name] = defs

        p = CUR["{}-{}-parameter".format(self.commandname, name)]
        g.add((p, RDF.type, NGSP["Parameter"]))
        g.add((self.command, NGSP.parameter, p))
        for k, v in defs.items():
            ko = k
            if type(k) == str:
                k = NGSP[k]
            if type(v) == str:
                if v == "none":
                    continue
                if v == "":
                    if ko != "optionsDefault":
                        continue
                v = Literal(v)
            if type(v) == list:
                pl = BNode()
                n = BNode()
                g.add((pl, RDF.type, OSLC.AllowedValues))
                g.add((p, k, pl))
                # g.add((p, OSLC.allowedValues, pl))
                for val in v:
                    g.add((pl, DC.identifier, Literal(val)))
            else:
                g.add((p, k, v))

    def process_gop(self, gopr):
        gop = self.gop
        patterns = []
        g = self.graph
        for m in RE_GOP_RECORD.finditer(gop):
            t, _, p = m.groups()
            patterns.append((t, p))
        if not patterns:
            print(gop)
            print("WARNING: there should be patterns of file names")

        print("GOPR:", gopr)
        for t, p in patterns:
            print("PATTERN:{}->{}".format(t, p))
            ptr = BNode()
            g.add((gopr, NGSP.pattern, ptr))
            g.add((ptr, DC.identifier, Literal(t)))
            g.add((ptr, NGSP.patternString, Literal(p)))


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
