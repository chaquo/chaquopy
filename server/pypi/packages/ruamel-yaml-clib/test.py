import unittest


class TestRuamelYamlClib(unittest.TestCase):

    # See https://yaml.readthedocs.io/en/latest/example.html
    def test_basic(self):
        import ruamel.yaml
        from ruamel.yaml import YAML
        from io import StringIO
        from textwrap import dedent

        self.assertTrue(ruamel.yaml.__with_libyaml__)

        inp = dedent("""\
            # example
            name:
              # details
              family: Smith   # very common
              given: Alice    # one of the siblings
            """)

        yaml = YAML()
        code = yaml.load(inp)
        self.assertEqual("Alice", code['name']['given'])

        sio = StringIO()
        yaml.dump(code, sio)
        self.assertEqual(inp, sio.getvalue())
