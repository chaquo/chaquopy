from os.path import join
from six import StringIO


class ForwardingOutputStream(StringIO):
    def __init__(self, obj, method):
        StringIO.__init__(self)
        self.func = getattr(obj, method)

    def write(self, s):
        StringIO.write(self, s)
        self.func(self.getvalue())
        self.seek(0)
        self.truncate(0)


ASSET_SOURCE_DIR = "source"
DEFAULT_CSS = "body { background-color: #eeeeee; font-size: 85%; }"

def load_source(context, web_view, filename, extra_css=""):
    from base64 import b64encode
    from java.io import BufferedReader, InputStreamReader
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_for_filename

    stream = context.getAssets().open(join(ASSET_SOURCE_DIR, filename))
    reader = BufferedReader(InputStreamReader(stream))
    text = "\n".join(iter(reader.readLine, None))

    formatter = HtmlFormatter()
    body = highlight(text, get_lexer_for_filename(filename), formatter)
    html = ('<html><head><style>{}\n{}\n{}</style></head><body>{}</body></html>"'
            .format(formatter.get_style_defs(), DEFAULT_CSS, extra_css, body))
    web_view.loadData(b64encode(html), "text/html", "base64")
