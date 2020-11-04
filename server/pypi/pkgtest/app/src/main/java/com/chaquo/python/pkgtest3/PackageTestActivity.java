package com.chaquo.python.pkgtest3;

import android.app.*;
import android.text.*;
import com.chaquo.python.utils.*;


public class PackageTestActivity extends PythonTestActivity {

    @Override protected Class<? extends Task> getTaskClass() {
        return Task.class;
    }

    // =============================================================================================

    public static class Task extends PythonTestActivity.Task {
        // For interactive debugging using pdb. VISIBLE_PASSWORD is necessary to prevent some
        // versions of the Google keyboard from displaying the suggestion bar.
        public Task(Application app) {
            super(app, (InputType.TYPE_CLASS_TEXT +
                        InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS +
                        InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD));
        }
    }
}
