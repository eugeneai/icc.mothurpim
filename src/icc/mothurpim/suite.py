#from mercurial import commands, ui, hg
import hglib
import hglib.util
import pkg_resources
import os.path
import shutil
from collections import namedtuple
from lxml import etree
from rdflib import Graph, Literal, BNode, Namespace, RDF, URIRef, RDFS
from rdflib.namespace import DC, DCTERMS, FOAF, XSD
from icc.ngs.namespace import NGS, NGSP, NGSS, SCHEMA, V, OSLC, CNT, NCO, CUR

GAL = Namespace("http://galaxyproject.org/ontologies/shed/")

REPOS = "https://toolshed.g2.bx.psu.edu/repos/"
USER = "iuc"
SUITE = "suite_mothur"
HGROOT = os.path.abspath(pkg_resources.resource_filename(
    "icc.mothurpim", "../../../tmp"))
OUTDIR = os.path.abspath(os.path.join(HGROOT, "../output"))

G = Graph()


def graph_save(filename, format="rdf"):
    print("# Output filename:{}".format(filename))
    g = G
    s = g.serialize(format=format)
    o = open(filename, "wb")
    o.write(s)
    o.close()


def namespaces():
    g = G
    g.bind('oslc', OSLC)
    g.bind('ngs', NGS)
    g.bind('ngsp', NGSP)
    g.bind('ngss', NGSS)
    g.bind('schema', SCHEMA)
    g.bind('dc', DC)
    g.bind('dcterms', DCTERMS)
    g.bind('v', V)
    g.bind('cnt', CNT)
    g.bind('mothur', CUR)
    g.bind('nco', NCO)
    g.bind('gal', GAL)
    g.bind('rdfs', RDFS)


DT = DCTERMS


def hg_url(name):
    return REPOS+USER+"/"+name


def hg_clone(name):
    # remove all first
    TARGET = os.path.join(HGROOT, name)
    branch = os.path.join(TARGET, '.hg', 'branch')
    if not os.path.exists(branch):
        print("# Clearing dir: {}".format(TARGET))
        try:
            shutil.rmtree(TARGET)
        except FileNotFoundError:
            pass
        url = hg_url(name)
        print("# Cloning {} to {}".format(url, TARGET))
        src = hglib.util.b(url)
        dst = hglib.util.b(TARGET)
        return hglib.clone(src, dst)
    return None


Suite = namedtuple('Suite', ("owner", "name", "shed", "rev"))


def enumerate_suites(repo):
    with open(os.path.join(HGROOT, SUITE, 'repository_dependencies.xml')) as i:
        xml = etree.parse(i)
        # print(etree.tostring(xml))
        for el in xml.xpath("//repository"):
            a = el.attrib
            yield(Suite(owner=a["owner"],
                        name=a["name"],
                        shed=a["toolshed"],
                        rev=a["changeset_revision"]))


INDEX = 0

REPL = {
    GAL['name']: DC['title'],
    GAL['id']: DC['identifier'],
    GAL['description']: DC['description'],

    GAL['type']: RDFS['range'],
    GAL['label']: DC['description'],
    GAL['format']: DT['format'],
    GAL['source']: DC['source'],
}


def q(URI):
    return REPL.get(URI, URI)


def process_shed(shed, root=None):
    global INDEX
    INDEX += 1
    assert(root)
    hg_clone(shed.name)
    real_name = shed.name.replace("mothur_", "").replace("_", ".")
    HG = os.path.join(HGROOT, shed.name)
    try:
        with open(os.path.join(HG, real_name+'.xml')) as i:
            xml = etree.parse(i)
            mc = open(os.path.join(HG, 'macros.xml'))
            macros = etree.parse(mc)
            print("# ROOT: {}".format(xml))
            print("# MACROS: {}".format(macros))
    except FileNotFoundError:
        print("#### Not found: {}".format(real_name))
        return
    tk = {}
    mc = {}
    for xel in macros.xpath("/macros/xml"):
        k = xel.attrib["name"]
        mc[k] = xel
    for t in macros.xpath("/macros/token"):
        k = t.attrib['name']
        tk[k] = t
    m = BNode()
    r = root
    G.add((r, NGSP.module, m))
    G.add((r, NGSP.module, m))
    G.add((m, RDF.type, NGSP["Module"]))
    G.add((m, RDF.type, GAL["Module"]))
    G.add((m, SCHEMA.sku, Literal(INDEX)))  # Stock Keeping Unit
    G.add((m, DC.title, Literal(real_name)))

    def macroexp(t):
        if t:
            for k, v in tk.items():
                t = t.replace(k, v.text)
        return t

    def texttest(t):
        t1 = t
        if isinstance(t, str):
            t1 = t.replace("\n", '').replace('\r', '').strip()
            # print('`{}`'.format(t1))
            t1 = macroexp(t1)
        return t1

    def indepth(curr, element, parent=None):
        if parent is None:
            parent = curr
        if element.tag in ['macros', 'tests']:  # TODO: Tests might useful
            return
        if element.tag == "expand":
            name = element.attrib["macro"]
            m = mc[name]
            for child in m:
                # print(">>>", child.tag)
                indepth(parent, child, parent=parent)
            return
        if 'text' in element.attrib and len(element.attrib) == 1 and len(element) == 0:
            t = texttest(element.attrib['text'])
            G.add((parent, q(GAL[element.tag]), Literal(t)))
            return

        for ak, av in element.attrib.iteritems():
            G.add((curr, q(GAL[ak]), Literal(texttest(av))))

        tt = texttest(element.text)
        if tt:
            if len(element.attrib) == 0 and len(element) == 0:
                G.add((parent, q(GAL[element.tag]),
                       Literal(macroexp(element.text))))
                return
            else:
                G.add((curr, DC["description"],
                       Literal(macroexp(element.text))))

        for child in element:
            # print("<%s %s %s>" % (curr, child.tag, child.attrib))
            # print(element.tail)
            eb = BNode()
            indepth(eb, child, parent=curr)
            ll = list(G.predicate_objects(subject=eb))
            # if child.tag == 'expand':
            #     print("----", ll)
            if len(ll) > 0:  # If any relations with eb constructed
                G.add((curr, q(GAL[child.tag]), eb))

    xroot = xml.getroot()
    print(">>R>>", xroot.tag)
    indepth(m, xroot)
    # for element in xml.iter():
    #     print(element.text)


def main():
    namespaces()
    print("# Tmp dir:{}".format(HGROOT))
    root = hg_clone(SUITE)
    # client = hglib.open(HGROOT)
    # print("## {}".format(list(client.manifest())))
    r = BNode()
    G.add((r, RDF.type, GAL["Suite"]))
    G.add((r, DC.title, Literal("Mothur")))
    for shed in enumerate_suites(root):
        print("# Toolshed: {} rev {}".format(shed.name, shed.rev))
        process_shed(shed, root=r)
        # break
    graph_save(OUTDIR+"/suite_mothur.ttl", format='n3')
    graph_save(OUTDIR+"/suite_mothur-ntr.ttl", format='ntriples')
    # graph_save(OUTDIR+"/suite_mothur.ttl", format='ttl')


if __name__ == "__main__":
    main()
