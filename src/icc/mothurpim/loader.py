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
        print(findnames)
        for f in files:
            name = f.replace(CPPEXT, "")
            header = name+HEXT
            print(f, header)

        self.loaded = True
        return self.graph


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
