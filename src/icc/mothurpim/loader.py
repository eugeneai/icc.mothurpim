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
            # print(f, header)
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
        pass

# class CommandParameter {

# 	public:
#     CommandParameter() { name = ""; type = ""; options = ""; optionsDefault = ""; chooseOnlyOneGroup = ""; chooseAtLeastOneGroup = ""; linkedGroup = ""; multipleSelectionAllowed = false; required = false; important = false; outputTypes = ""; }
#     CommandParameter(string n, string t, string o, string d, string only, string atLeast, string linked, string opt, bool m, bool r, bool i) :
#         name(n), type(t), options(o), optionsDefault(d), chooseOnlyOneGroup(only), chooseAtLeastOneGroup(atLeast), linkedGroup(linked), outputTypes(opt),multipleSelectionAllowed(m), required(r), important(i) {}
#     CommandParameter(string n, string t, string o, string d, string only, string atLeast, string linked, string opt, bool m, bool r) : name(n), type(t), options(o), optionsDefault(d),
#             chooseOnlyOneGroup(only), chooseAtLeastOneGroup(atLeast), linkedGroup(linked), outputTypes(opt), multipleSelectionAllowed(m), required(r)  { important = false; }

# 		string name;		//something like fasta, processors, method
# 		string type;  //must be set to "Boolean", "Multiple", "Number", "String", "InputTypes" - InputTypes is for file inputs
# 		string options; //if the parameter has specific options allowed, used for parameters of type "Multiple", something like "furthest-nearest-average", or "sobs-chao...", leave blank for command that do not required specific options
# 		string optionsDefault;   //the default for this parameter, could be something like "F" for a boolean or "100" for a number or "sobs-chao" for multiple


# 		//for chooseOnlyOneGroup, chooseAtLeastOneGroup and linkedGroup if no group is needed set to "none".
# 		string chooseOnlyOneGroup; //for file inputs: if a command has several options for input files but you can only choose one then put them in a group
# 									//for instance in the read.dist command you can use a phylip or column file but not both so set chooseOnlyOneGroup for both parameters to something like "DistanceFileGroup"
# 		string chooseAtLeastOneGroup; //for file inputs: if a command has several options for input files and you want to make sure one is choosen then put them in a group
# 									//for instance in the read.dist command you must provide a phylip or column file so set chooseAtLeastOneGroup for both parameters to something like "DistanceFileGroup"
# 		string linkedGroup; //for file inputs: if a command has a file option were if you provide one you must provide another you can put them in a group
# 										//for instance in the cluster command if you provide a column file you must provide a name file so set linkedGroup for both parameters to something like "ColumnNameGroup"

# 		bool multipleSelectionAllowed; //for "Multiple" type to say whether you can select multiple options, for instance for calc parameter set to true, but for method set to false
# 		bool required; //is this parameter required

#         bool important; //is this parameter important.  The gui will put "important" parameters first in the option panel.

#         string outputTypes; //types on files created by the command if this parameter is given.  ie. get.seqs command fasta parameter makes a fasta file. can be multiple values split by dashes.

# 	private:
# };


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
