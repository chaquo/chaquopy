package com.chaquo.python.demo;

import android.content.*;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.util.*;
import android.webkit.*;
import android.widget.*;
import com.chaquo.python.*;
import java.io.*;

public class JavaDemoActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_java_demo);
        TextView tvCaption = (TextView) findViewById(R.id.tvCaption);
        tvCaption.setText(R.string.java_demo_caption);

        WebView wvSource = (WebView) findViewById(R.id.wvSource);
        try {
            viewSource(this, wvSource, "JavaDemoActivity.java");
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static final String ASSET_SOURCE_DIR = "source";
    private static final String EXTRA_CSS =
        "body { background-color: #eeeeee; font-size: 85%; }";

    // Compare with the equivalent Python code in chaquopy/demo/ui_demo.py
    private static void viewSource(Context context, WebView wv,
                                   String filename) throws IOException {
        InputStream stream = context.getAssets().open
            (ASSET_SOURCE_DIR + "/" + filename);
        BufferedReader reader =
            new BufferedReader(new InputStreamReader(stream));
        String text = "";
        String line;
        while ((line = reader.readLine()) != null) {
            text += line + "\n";
        }

        Python py = Python.getInstance();
        PyObject pygments = py.getModule("pygments");
        PyObject formatters = py.getModule("pygments.formatters");
        PyObject lexers = py.getModule("pygments.lexers");

        PyObject formatter = formatters.callAttr("HtmlFormatter");
        PyObject lexer = lexers.callAttr("get_lexer_for_filename", filename);
        String body = pygments.callAttr
            ("highlight", text, lexer, formatter).toJava(String.class);

        String html = String.format(
            "<html><head><style>%s\n%s</style></head><body>%s</body></html>",
            formatter.callAttr("get_style_defs"), EXTRA_CSS, body);
        wv.loadData(Base64.encodeToString(html.getBytes("ASCII"),
                                          Base64.DEFAULT),
                    "text/html", "base64");
    }
}
