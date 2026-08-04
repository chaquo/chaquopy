package com.chaquo.python.utils;

import android.os.*;
import android.view.*;

import androidx.activity.*;
import androidx.appcompat.app.*;
import androidx.core.graphics.*;
import androidx.core.view.*;

import com.chaquo.python.*;

public class BaseActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(
            this, SystemBarStyle.dark(getColor(resId("color", "colorPrimaryDark")))
        );

        PyObject platform = Python.getInstance().getModule("platform");
        getSupportActionBar().setSubtitle(
            "Python " + platform.callAttr("python_version").toString()
        );
    }

    @Override
    public void setContentView(int layoutResID) {
        setContentView(LayoutInflater.from(this).inflate(layoutResID, null));
    }

    @Override
    public void setContentView(View view) {
        super.setContentView(view);

        // EdgeToEdge.enable calls Window.setStatusBarColor, but that has no effect when
        // targeting API level 35 and higher, so we need to manually draw the status bar
        // background (https://stackoverflow.com/q/78832208).
        View statusBarBackground = new View(this);
        statusBarBackground.setBackgroundColor(
            getColor(resId("color", "colorPrimaryDark"))
        );
        addContentView(
            statusBarBackground,
            new ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0)
        );

        // Based on the "Empty Views Activity" from Android Studio Quail 3.
        ViewCompat.setOnApplyWindowInsetsListener(
            view,
            (v, insets) -> {
                // systemBars includes the status bar, navigation bar (which may be on
                // the left or right on API level 28 and older), action bar, and display
                // cutouts.
                Insets systemBars =
                    insets.getInsets(WindowInsetsCompat.Type.systemBars());
                v.setPadding(
                    systemBars.left, systemBars.top, systemBars.right, systemBars.bottom
                );

                ViewGroup.MarginLayoutParams lp =
                    (ViewGroup.MarginLayoutParams) statusBarBackground.getLayoutParams();
                lp.height = systemBars.top;
                lp.leftMargin = systemBars.left;
                lp.rightMargin = systemBars.right;
                statusBarBackground.requestLayout();
                return insets;
            }
        );
    }

    public int resId(String type, String name) {
        return Utils.resId(this, type, name);
    }
}
