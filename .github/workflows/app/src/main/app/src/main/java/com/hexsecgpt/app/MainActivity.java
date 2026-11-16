
package com.hexsecgpt.app;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Button;
import android.widget.Toast;

public class MainActivity extends Activity {

    private final String CYAN = "#00E5FF";
    private LinearLayout layout;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        layout.setPadding(30, 30, 30, 30);
        layout.setBackgroundColor(Color.rgb(3, 8, 19));

        TextView title = new TextView(this);
        title.setText("HEXSECGPT");
        title.setTextColor(Color.parseColor(CYAN));
        title.setTextSize(32);
        title.setTypeface(null, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);

        TextView subtitle = new TextView(this);
        subtitle.setText("\nCYBER SECURITY SYSTEM\n\nAndroid Edition 1.0");
        subtitle.setTextColor(Color.WHITE);
        subtitle.setTextSize(16);
        subtitle.setGravity(Gravity.CENTER);

        Button button = new Button(this);
        button.setText("AVVIA SISTEMA");
        button.setOnClickListener(v ->
            Toast.makeText(this,
                "HEXSECGPT ONLINE",
                Toast.LENGTH_LONG).show()
        );

        layout.addView(title);
        layout.addView(subtitle);

        LinearLayout.LayoutParams params =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        params.topMargin = 40;
        layout.addView(button, params);

        setContentView(layout);
    }
}
