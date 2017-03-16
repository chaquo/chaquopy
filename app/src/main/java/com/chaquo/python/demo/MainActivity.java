package com.chaquo.python.demo;

import android.os.*;
import android.support.v7.app.*;
import android.view.*;
import android.widget.*;

public class MainActivity extends AppCompatActivity {

    private Repl repl = Repl.getInstance();

    private TextView tvBuffer;
    private EditText etInput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvBuffer = (TextView) findViewById(R.id.tvBuffer);
        etInput = (EditText) findViewById(R.id.etInput);
        etInput.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                String input = etInput.getText().toString().trim();
                if (! input.isEmpty()) {
                    tvBuffer.append(">>> ");
                    tvBuffer.append(etInput.getText());
                    tvBuffer.append("\n");
                    etInput.setText("");

                    String result = repl.eval(input);
                    tvBuffer.append(result);
                    if (! result.endsWith("\n")) {
                        tvBuffer.append("\n");
                    }
                }
                return true;
            }
        });

        repl.start();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    protected void onDestroy() {
        repl.stop();
        super.onDestroy();
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();

        //noinspection SimplifiableIfStatement
        if (id == R.id.action_settings) {
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}
