package com.zicore.system;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Shader;
import android.view.View;

/**
 * Custom spectrum visualizer. Draws FFT frequency bars in the ZICORE
 * palette (cyan / purple / green) using only the Android framework.
 */
public class VisualizerView extends View {

    private static final int BARS = 48;

    private final Paint[] paints;
    private final byte[] fft = new byte[128];
    private final float[] levels = new float[BARS];
    private int captureSize = 0;

    public VisualizerView(Context context) {
        super(context);
        paints = new Paint[BARS];
        for (int i = 0; i < BARS; i++) {
            paints[i] = new Paint();
            paints[i].setStyle(Paint.Style.FILL);
            paints[i].setColor(colorFor(i));
        }
        setMinimumHeight(220);
    }

    public void setCaptureSize(int size) {
        captureSize = Math.max(size, 2);
    }

    /** Feed raw FFT bytes from {@code android.media.audiofx.Visualizer}. */
    public void update(byte[] data) {
        int n = data == null ? 0 : data.length;
        if (n > fft.length) n = fft.length;
        System.arraycopy(data, 0, fft, 0, n);
        postInvalidateOnAnimation();
    }

    public void reset() {
        java.util.Arrays.fill(levels, 0f);
        postInvalidate();
    }

    private int colorFor(int i) {
        float t = (float) i / (BARS - 1);
        if (t < 0.5f) {
            // cyan -> purple
            return lerp(Color.parseColor("#00e5ff"), Color.parseColor("#7c4dff"), t * 2f);
        }
        // purple -> green
        return lerp(Color.parseColor("#7c4dff"), Color.parseColor("#00ff88"), (t - 0.5f) * 2f);
    }

    private int lerp(int from, int to, float t) {
        int r1 = Color.red(from), g1 = Color.green(from), b1 = Color.blue(from);
        int r2 = Color.red(to), g2 = Color.green(to), b2 = Color.blue(to);
        return Color.rgb(
            (int) (r1 + (r2 - r1) * t),
            (int) (g1 + (g2 - g1) * t),
            (int) (b1 + (b2 - b1) * t)
        );
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth();
        int h = getHeight();
        if (w == 0 || h == 0) return;

        // Background
        canvas.drawColor(Color.parseColor("#060a12"));

        // Track grid lines
        Paint grid = new Paint();
        grid.setColor(Color.parseColor("#0d1117"));
        grid.setStrokeWidth(1);
        for (int i = 0; i < 4; i++) {
            float y = h * (i + 1) / 5f;
            canvas.drawLine(0, y, w, y, grid);
        }

        // Fall back to a gentle idle wave when no FFT data is available yet.
        int n = captureSize > 0 ? Math.min(captureSize, 256) / 2 : 64;
        float barW = (float) w / BARS;
        float gap = Math.max(barW * 0.18f, 1f);

        for (int i = 0; i < BARS; i++) {
            float val;
            if (n > 0) {
                int idx = Math.min(i * n / BARS, n - 1);
                val = (fft[idx] & 0xFF) / 255f;
            } else {
                val = 0f;
            }
            float target = Math.max(val * 1.15f, 0.015f);
            // smooth
            levels[i] = levels[i] + (target - levels[i]) * 0.35f;
            float barH = h * Math.min(levels[i], 1f) * 0.92f;

            float left = i * barW + gap / 2f;
            float right = (i + 1) * barW - gap / 2f;
            float top = h - barH;
            if (right > left + 1 && top < h - 1) {
                paints[i].setShader(new LinearGradient(
                    0, top, 0, h, colorFor(i), Color.parseColor("#0d1117"), Shader.TileMode.CLAMP));
                canvas.drawRect(left, top, right, h - 2, paints[i]);
                paints[i].setShader(null);
            }
        }
    }
}
