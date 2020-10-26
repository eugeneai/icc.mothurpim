from nose.plugins.skip import SkipTest
from nose.tools import assert_raises, nottest
from icc.mothurpim.loader import Loader, rdflib_example
from pkg_resources import resource_filename
import os.path

# @SkipTest

SRCDIR = os.path.abspath(resource_filename(
    "icc.mothurpim", "../../../mothur-src/source/commands/"))

print(SRCDIR)


class TestBasic:

    def setUp(self):
        pass

    # def test_something(self):
    #     assert rdflib_example()

    def tearDown(self):
        pass

    def test_loader(self):
        l = Loader(SRCDIR)
        l.load()
        l.save("result.ttl", format="ttl")
