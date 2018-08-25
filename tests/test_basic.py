from nose.plugins.skip import SkipTest
from nose.tools import assert_raises, nottest
from icc.mothurpim.loader import Loader, main_test

# @SkipTest


class TestBasic:

    def setUp(self):
        pass

    def test_something(self):
        assert main_test()

    def tearDown(self):
        pass
