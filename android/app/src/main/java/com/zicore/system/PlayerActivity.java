package com.zicore.system;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.audiofx.Visualizer;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.SeekBar;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Native modular media player (Winamp-style):
 *  - large video surface + audio visualizer panel
 *  - collapsible playlist loaded from the ZICORE server
 *  - transport controls, seek, shuffle, repeat
 *  - reliable continuous playback (framework MediaPlayer, no cutoffs)
 */
public class PlayerActivity extends AppCompatActivity {

    private static final String PREFS_NAME = "zicore_prefs";
    private static final String KEY_SERVER = "server_url";
    private static final String EXTRA_URL = "start_url";
    private static final String EXTRA_TITLE = "start_title";

    private MediaPlayer player;
    private Visualizer visualizer;

    private LinearLayout videoPanel;
    private FrameLayout videoFrame;
    private android.view.SurfaceView videoSurface;
    private VisualizerView vizView;
    private ListView playlistView;
    private TextView titleView, timeView, durView, playlistHeader;
    private SeekBar seekBar;
    private Button btnPlay, btnPrev, btnNext, btnShuffle, btnRepeat, btnVizToggle, btnListToggle;
    private TextView btnClose;

    private Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            updateProgress();
            handler.postDelayed(this, 250);
        }
    };

    private final List<MediaItem> playlist = new ArrayList<>();
    private int current = -1;
    private boolean shuffle = false;
    private boolean repeat = false;
    private boolean vizExpanded = true;
    private boolean listExpanded = true;
    private String serverUrl;

    private static final String CLOUD_URL = "https://zcs.zicore.space";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        serverUrl = prefs.getString(KEY_SERVER, CLOUD_URL);

        ensureAudioPermission();
        buildLayout();
        loadPlaylist();
    }

    private void ensureAudioPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.RECORD_AUDIO}, 100);
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 100 && current >= 0) startVisualizer();
    }

    // ── Layout ──────────────────────────────────────────────

    @SuppressLint("DefaultLocale")
    private void buildLayout() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#060a12"));

        // ── Header bar ──
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(12), dp(8), dp(8), dp(8));
        header.setBackgroundColor(Color.parseColor("#0d1117"));

        TextView logo = new TextView(this);
        logo.setText("◈  PLAYER");
        logo.setTextColor(Color.parseColor("#00e5ff"));
        logo.setTextSize(15);
        logo.setTypeface(android.graphics.Typeface.MONOSPACE);
        header.addView(logo, lpWrap(dp(0), dp(0), 1f));

        btnClose = new TextView(this);
        btnClose.setText("✕");
        btnClose.setTextSize(18);
        btnClose.setTextColor(Color.parseColor("#607080"));
        btnClose.setPadding(dp(12), dp(4), dp(12), dp(4));
        btnClose.setOnClickListener(v -> finish());
        header.addView(btnClose, lpWrap(0, 0, 0f));
        root.addView(header, lpMatch(dp(44)));

        // ── Video monitor (large, modular panel) ──
        videoPanel = new LinearLayout(this);
        videoPanel.setOrientation(LinearLayout.VERTICAL);
        videoPanel.setBackgroundColor(Color.parseColor("#0d1117"));

        TextView vidHeader = panelHeader("▸  VIDEO MONITOR", 0);
        videoPanel.addView(vidHeader, lpMatch(dp(30)));

        videoFrame = new FrameLayout(this);
        videoFrame.setBackgroundColor(Color.BLACK);
        videoSurface = new android.view.SurfaceView(this);
        videoSurface.getHolder().addCallback(new android.view.SurfaceHolder.Callback() {
            @Override public void surfaceCreated(android.view.SurfaceHolder holder) {
                if (player != null) player.setDisplay(holder);
            }
            @Override public void surfaceChanged(android.view.SurfaceHolder holder, int fmt, int w, int h) {}
            @Override public void surfaceDestroyed(android.view.SurfaceHolder holder) {}
        });
        videoFrame.addView(videoSurface, new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        videoPanel.addView(videoFrame, lpMatch(dp(240)));
        root.addView(videoPanel, lpWeight(1f));

        // ── Visualizer panel (collapsible) ──
        LinearLayout vizPanel = new LinearLayout(this);
        vizPanel.setOrientation(LinearLayout.VERTICAL);
        vizPanel.setBackgroundColor(Color.parseColor("#0d1117"));

        LinearLayout vizHead = new LinearLayout(this);
        vizHead.setOrientation(LinearLayout.HORIZONTAL);
        vizHead.setGravity(Gravity.CENTER_VERTICAL);
        vizHead.setPadding(dp(12), 0, dp(8), 0);

        TextView vizTitle = new TextView(this);
        vizTitle.setText("▸  SPECTRUM ANALYZER");
        vizTitle.setTextColor(Color.parseColor("#7c4dff"));
        vizTitle.setTextSize(12);
        vizTitle.setTypeface(android.graphics.Typeface.MONOSPACE);
        vizHead.addView(vizTitle, lpWrap(0, 0, 1f));

        btnVizToggle = new Button(this);
        btnVizToggle.setText("—");
        styleMini(btnVizToggle);
        btnVizToggle.setOnClickListener(v -> toggleViz());
        vizHead.addView(btnVizToggle, lpWrap(dp(40), dp(26), 0f));

        vizPanel.addView(vizHead, lpMatch(dp(30)));

        vizView = new VisualizerView(this);
        vizPanel.addView(vizView, lpMatch(dp(150)));
        root.addView(vizPanel, lpMatch(dp(180)));

        // ── Playlist panel (collapsible) ──
        LinearLayout listPanel = new LinearLayout(this);
        listPanel.setOrientation(LinearLayout.VERTICAL);
        listPanel.setBackgroundColor(Color.parseColor("#0d1117"));

        LinearLayout listHead = new LinearLayout(this);
        listHead.setOrientation(LinearLayout.HORIZONTAL);
        listHead.setGravity(Gravity.CENTER_VERTICAL);
        listHead.setPadding(dp(12), 0, dp(8), 0);

        playlistHeader = new TextView(this);
        playlistHeader.setText("▸  PLAYLIST  (0)");
        playlistHeader.setTextColor(Color.parseColor("#00ff88"));
        playlistHeader.setTextSize(12);
        playlistHeader.setTypeface(android.graphics.Typeface.MONOSPACE);
        listHead.addView(playlistHeader, lpWrap(0, 0, 1f));

        btnListToggle = new Button(this);
        btnListToggle.setText("—");
        styleMini(btnListToggle);
        btnListToggle.setOnClickListener(v -> toggleList());
        listHead.addView(btnListToggle, lpWrap(dp(40), dp(26), 0f));

        listPanel.addView(listHead, lpMatch(dp(30)));

        playlistView = new ListView(this);
        playlistView.setBackgroundColor(Color.parseColor("#0a0f18"));
        playlistView.setDivider(null);
        playlistView.setDividerHeight(dp(1));
        playlistView.setOnItemClickListener((parent, view, pos, id) -> playAt(pos));
        listPanel.addView(playlistView, lpWeight(1f));
        root.addView(listPanel, lpWeight(1f));

        // ── Transport controls ──
        LinearLayout transport = new LinearLayout(this);
        transport.setOrientation(LinearLayout.VERTICAL);
        transport.setPadding(dp(12), dp(6), dp(12), dp(8));
        transport.setBackgroundColor(Color.parseColor("#0d1117"));

        // seek row
        LinearLayout seekRow = new LinearLayout(this);
        seekRow.setOrientation(LinearLayout.HORIZONTAL);
        seekRow.setGravity(Gravity.CENTER_VERTICAL);

        timeView = monoText("0:00");
        durView = monoText("0:00");
        seekRow.addView(timeView, lpWrap(0, 0, 0f));

        seekBar = new SeekBar(this);
        seekBar.setPadding(dp(8), 0, dp(8), 0);
        seekBar.setProgressTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#00e5ff")));
        seekBar.setThumbTintList(android.content.res.ColorStateList.valueOf(Color.parseColor("#00e5ff")));
        seekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar sb, int progress, boolean fromUser) {
                if (fromUser && player != null) {
                    player.seekTo(progress);
                    timeView.setText(formatTime(progress));
                }
            }
            @Override public void onStartTrackingTouch(SeekBar seekBar) {}
            @Override public void onStopTrackingTouch(SeekBar seekBar) {}
        });
        seekRow.addView(seekBar, lpWrap(0, 0, 1f));

        seekRow.addView(durView, lpWrap(0, 0, 0f));
        transport.addView(seekRow, lpMatch(dp(44)));

        // buttons row
        LinearLayout btnRow = new LinearLayout(this);
        btnRow.setOrientation(LinearLayout.HORIZONTAL);
        btnRow.setGravity(Gravity.CENTER);

        btnShuffle = styleBtn("⤨");
        btnShuffle.setOnClickListener(v -> {
            shuffle = !shuffle;
            btnShuffle.setText(shuffle ? "●" : "⤨");
            btnShuffle.setTextColor(Color.parseColor(shuffle ? "#00ff88" : "#00e5ff"));
        });

        btnPrev = styleBtn("⏮");
        btnPrev.setOnClickListener(v -> playAt(prevIndex()));

        btnPlay = styleBtn("▶");
        btnPlay.setTextSize(20);
        btnPlay.setOnClickListener(v -> togglePlay());

        btnNext = styleBtn("⏭");
        btnNext.setOnClickListener(v -> playAt(nextIndex()));

        btnRepeat = styleBtn("↻");
        btnRepeat.setOnClickListener(v -> {
            repeat = !repeat;
            btnRepeat.setTextColor(Color.parseColor(repeat ? "#00ff88" : "#00e5ff"));
        });

        btnRow.addView(btnShuffle, lpWrap(dp(52), dp(48), 1f));
        btnRow.addView(btnPrev, lpWrap(dp(52), dp(48), 1f));
        btnRow.addView(btnPlay, lpWrap(dp(64), dp(52), 1f));
        btnRow.addView(btnNext, lpWrap(dp(52), dp(48), 1f));
        btnRow.addView(btnRepeat, lpWrap(dp(52), dp(48), 1f));
        transport.addView(btnRow, lpMatch(dp(58)));

        root.addView(transport, lpMatch(dp(108)));

        setContentView(root);

        String startUrl = getIntent().getStringExtra(EXTRA_URL);
        String startTitle = getIntent().getStringExtra(EXTRA_TITLE);
        if (startUrl != null) {
            MediaItem first = new MediaItem(startTitle != null ? startTitle : "Now playing", startUrl, startUrl.endsWith(".mp4") || startUrl.endsWith(".webm") || startUrl.endsWith(".m4v") || startUrl.endsWith(".mkv") || startUrl.endsWith(".mov"));
            playlist.add(0, first);
            current = 0;
            updatePlaylist();
            if (isVideo(first.url)) showVideo(true);
            else showVideo(false);
            playAt(0);
        }
    }

    private void toggleViz() {
        vizExpanded = !vizExpanded;
        vizView.setVisibility(vizExpanded ? View.VISIBLE : View.GONE);
        btnVizToggle.setText(vizExpanded ? "—" : "+");
    }

    private void toggleList() {
        listExpanded = !listExpanded;
        playlistView.setVisibility(listExpanded ? View.VISIBLE : View.GONE);
        btnListToggle.setText(listExpanded ? "—" : "+");
    }

    private void showVideo(boolean show) {
        videoFrame.setVisibility(show ? View.VISIBLE : View.GONE);
        videoPanel.setVisibility(show ? View.VISIBLE : View.GONE);
    }

    // ── Playlist loading ────────────────────────────────────

    private void loadPlaylist() {
        new Thread(() -> {
            List<MediaItem> items = new ArrayList<>();
            try {
                items.addAll(fetch("/api/zmmx/browse?category=music&source=zicore_fs&limit=100&order=asc"));
                items.addAll(fetch("/api/zmmx/browse?category=audio&source=zicore_fs&limit=100&order=asc"));
                items.addAll(fetch("/api/zmmx/browse?category=video&source=zicore_fs&limit=100&order=asc"));
            } catch (Exception e) {
                e.printStackTrace();
            }
            runOnUiThread(() -> {
                playlist.clear();
                playlist.addAll(items);
                updatePlaylist();
            });
        }).start();
    }

    private List<MediaItem> fetch(String apiPath) throws Exception {
        List<MediaItem> out = new ArrayList<>();
        URL url = new URL(serverUrl + apiPath);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(10000);
        conn.setRequestProperty("Accept", "application/json");
        int code = conn.getResponseCode();
        if (code != 200) {
            conn.disconnect();
            return out;
        }
        BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line);
        br.close();
        conn.disconnect();

        JSONObject root = new JSONObject(sb.toString());
        JSONArray arr = root.optJSONArray("items");
        if (arr == null) arr = root.optJSONArray("results");
        if (arr == null) return out;

        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.getJSONObject(i);
            String name = o.optString("name");
            String u = o.optString("url");
            if (name.isEmpty() || u.isEmpty()) continue;
            // skip macOS dot-files and hidden files
            String base = name.substring(name.lastIndexOf('/') + 1);
            if (base.startsWith("._") || base.startsWith(".~") || base.startsWith(".")) continue;
            String full;
            if (u.startsWith("http")) full = u;
            else full = serverUrl + encodeUrlPath(u);
            boolean video = isVideo(u);
            out.add(new MediaItem(name, full, video));
        }
        return out;
    }

    private static boolean isVideo(String url) {
        String s = url.toLowerCase();
        return s.endsWith(".mp4") || s.endsWith(".webm") || s.endsWith(".mkv")
                || s.endsWith(".mov") || s.endsWith(".m4v") || s.endsWith(".3gp");
    }

    /** Encode URL path segments while preserving slashes and query params. */
    private static String encodeUrlPath(String url) {
        try {
            int q = url.indexOf('?');
            String path = q >= 0 ? url.substring(0, q) : url;
            String query = q >= 0 ? url.substring(q) : "";
            String[] segs = path.split("/");
            StringBuilder sb = new StringBuilder();
            for (String seg : segs) {
                if (sb.length() > 0) sb.append('/');
                sb.append(java.net.URLEncoder.encode(seg, "UTF-8").replace("+", "%20"));
            }
            return sb.toString() + query;
        } catch (Exception e) {
            return url;
        }
    }

    /** Auth headers for protected media endpoints (/media-fs requires SSO). */
    private static java.util.Map<String, String> buildHeaders(SharedPreferences prefs) {
        String token = prefs.getString("sso_token", "");
        java.util.Map<String, String> h = new java.util.HashMap<>();
        if (!token.isEmpty()) h.put("Authorization", "Bearer " + token);
        return h;
    }

    // ── Playback ────────────────────────────────────────────

    private void playAt(int index) {
        if (playlist.isEmpty() || index < 0) return;
        current = ((index % playlist.size()) + playlist.size()) % playlist.size();
        MediaItem item = playlist.get(current);

        releasePlayer();

        try {
            player = new MediaPlayer();
            player.setAudioAttributes(new android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build());

            if (item.video) {
                showVideo(true);
                android.view.SurfaceHolder holder = videoSurface.getHolder();
                if (holder.getSurface().isValid()) player.setDisplay(holder);
                else player.setDisplay(null);
            } else {
                showVideo(false);
            }

            player.setDataSource(this, Uri.parse(item.url),
                    buildHeaders(getSharedPreferences(PREFS_NAME, MODE_PRIVATE)));
            player.setOnPreparedListener(mp -> {
                if (item.video) {
                    android.view.SurfaceHolder holder = videoSurface.getHolder();
                    if (holder.getSurface().isValid()) mp.setDisplay(holder);
                }
                mp.start();
                seekBar.setMax(mp.getDuration());
                durView.setText(formatTime(mp.getDuration()));
                startVisualizer();
            });
            player.setOnCompletionListener(mp -> {
                if (repeat) {
                    playAt(current);
                } else {
                    playAt(nextIndex());
                }
            });
            player.setOnErrorListener((mp, what, extra) -> {
                runOnUiThread(() -> {
                    Toast("Error de reproducción (" + what + "/" + extra + "). Saltando...");
                    btnPlay.setText("▶");
                    if (repeat) {
                        playAt(current);
                    } else {
                        playAt(nextIndex());
                    }
                });
                return true;
            });
            player.prepareAsync();

            titleView = monoText(item.title);
            // ensure a header shows current item
            runOnUiThread(() -> {
                if (playlistHeader != null) {
                    playlistHeader.setText("▶  " + item.title);
                }
            });
            btnPlay.setText("⏸");
            seekBar.setProgress(0);
            handler.removeCallbacks(ticker);
            handler.post(ticker);
            updatePlaylist();
        } catch (Exception e) {
            e.printStackTrace();
            Toast("No se pudo reproducir: " + e.getMessage());
        }
    }

    private void togglePlay() {
        if (player == null || current < 0) {
            if (!playlist.isEmpty()) playAt(0);
            return;
        }
        if (player.isPlaying()) {
            player.pause();
            btnPlay.setText("▶");
        } else {
            player.start();
            btnPlay.setText("⏸");
        }
    }

    private int nextIndex() {
        if (playlist.isEmpty()) return -1;
        if (shuffle) {
            return (int) (Math.random() * playlist.size());
        }
        return current + 1 >= playlist.size() ? 0 : current + 1;
    }

    private int prevIndex() {
        if (playlist.isEmpty()) return -1;
        if (current <= 0) return playlist.size() - 1;
        return current - 1;
    }

    private void startVisualizer() {
        if (player == null) return;
        try {
            stopVisualizer();
            visualizer = new Visualizer(player.getAudioSessionId());
            visualizer.setCaptureSize(Visualizer.getCaptureSizeRange()[1]);
            vizView.setCaptureSize(visualizer.getCaptureSize());
            visualizer.setDataCaptureListener(new Visualizer.OnDataCaptureListener() {
                @Override
                public void onWaveFormDataCapture(Visualizer visualizer, byte[] waveform, int samplingRate) {
                }

                @Override
                public void onFftDataCapture(Visualizer visualizer, byte[] fft, int samplingRate) {
                    vizView.update(fft);
                }
            }, Visualizer.getMaxCaptureRate() / 2, false, true);
            visualizer.setEnabled(true);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void stopVisualizer() {
        if (visualizer != null) {
            try {
                visualizer.setEnabled(false);
                visualizer.release();
            } catch (Exception ignored) {
            }
            visualizer = null;
        }
    }

    private void releasePlayer() {
        stopVisualizer();
        if (player != null) {
            try {
                player.stop();
            } catch (Exception ignored) {
            }
            player.release();
            player = null;
        }
        handler.removeCallbacks(ticker);
        vizView.reset();
    }

    private void updateProgress() {
        if (player != null && current >= 0) {
            try {
                int pos = player.getCurrentPosition();
                seekBar.setMax(player.getDuration());
                if (!seekBar.isPressed()) {
                    seekBar.setProgress(pos);
                    timeView.setText(formatTime(pos));
                }
            } catch (Exception ignored) {
            }
        }
    }

    // ── Playlist UI ─────────────────────────────────────────

    private void updatePlaylist() {
        if (playlistHeader != null && current < 0) {
            playlistHeader.setText("▸  PLAYLIST  (" + playlist.size() + ")");
        }
        List<String> labels = new ArrayList<>();
        for (int i = 0; i < playlist.size(); i++) {
            MediaItem m = playlist.get(i);
            String mark = (i == current) ? "▶  " : "   ";
            labels.add(mark + (m.video ? "🎬 " : "♪ ") + m.title);
        }
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(this,
                android.R.layout.simple_list_item_1, labels) {
            @Override
            public android.view.View getView(int position, android.view.View convertView,
                                             ViewGroup parent) {
                android.view.View v = super.getView(position, convertView, parent);
                TextView tv = v instanceof TextView ? (TextView) v : null;
                if (tv != null) {
                    tv.setTextColor(Color.parseColor("#c8d8e8"));
                    tv.setTextSize(12);
                    tv.setPadding(dp(12), dp(8), dp(8), dp(8));
                    tv.setTypeface(android.graphics.Typeface.MONOSPACE);
                    if (position == current) {
                        tv.setTextColor(Color.parseColor("#00ff88"));
                    }
                }
                v.setBackgroundColor(Color.parseColor(position == current ? "#12202f" : "#0a0f18"));
                return v;
            }
        };
        playlistView.setAdapter(adapter);
        if (current >= 0) {
            try {
                playlistView.smoothScrollToPosition(current);
            } catch (Exception ignored) {
            }
        }
    }

    // ── Helpers ─────────────────────────────────────────────

    private static class MediaItem {
        final String title;
        final String url;
        final boolean video;

        MediaItem(String title, String url, boolean video) {
            this.title = title;
            this.url = url;
            this.video = video;
        }
    }

    private TextView monoText(String s) {
        TextView tv = new TextView(this);
        tv.setText(s);
        tv.setTextColor(Color.parseColor("#00e5ff"));
        tv.setTextSize(12);
        tv.setTypeface(android.graphics.Typeface.MONOSPACE);
        tv.setGravity(Gravity.CENTER_VERTICAL);
        return tv;
    }

    private Button styleBtn(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(16);
        b.setTextColor(Color.parseColor("#00e5ff"));
        b.setTypeface(android.graphics.Typeface.MONOSPACE);
        b.setBackgroundColor(Color.parseColor("#16213e"));
        b.setAllCaps(false);
        b.setPadding(0, 0, 0, 0);
        return b;
    }

    private void styleMini(Button b) {
        b.setTextSize(12);
        b.setTextColor(Color.parseColor("#00e5ff"));
        b.setTypeface(android.graphics.Typeface.MONOSPACE);
        b.setBackgroundColor(Color.parseColor("#16213e"));
        b.setAllCaps(false);
        b.setPadding(0, 0, 0, 0);
    }

    private TextView panelHeader(String text, int color) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextColor(color != 0 ? color : Color.parseColor("#00e5ff"));
        tv.setTextSize(11);
        tv.setTypeface(android.graphics.Typeface.MONOSPACE);
        tv.setPadding(dp(12), 0, 0, 0);
        tv.setGravity(Gravity.CENTER_VERTICAL);
        tv.setBackgroundColor(Color.parseColor("#16213e"));
        return tv;
    }

    private String formatTime(int ms) {
        if (ms < 0) return "0:00";
        int s = ms / 1000;
        return String.format(Locale.US, "%d:%02d", s / 60, s % 60);
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density);
    }

    private LinearLayout.LayoutParams lpWrap(int w, int h, float weight) {
        int ww = w == 0 ? LinearLayout.LayoutParams.WRAP_CONTENT : w;
        int wh = h == 0 ? LinearLayout.LayoutParams.WRAP_CONTENT : h;
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ww, wh, weight);
        return lp;
    }

    private LinearLayout.LayoutParams lpWeight(float weight) {
        return new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 0, weight);
    }

    private LinearLayout.LayoutParams lpMatch(int h) {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, h);
    }

    private LinearLayout.LayoutParams lpMatch(int w, int h) {
        return new LinearLayout.LayoutParams(w, h);
    }

    private void Toast(String msg) {
        android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (player != null && player.isPlaying()) {
            // keep playing in background; visualizer needs UI so stop it
            stopVisualizer();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (player != null && current >= 0 && !vizView.isShown()) {
            startVisualizer();
        }
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(ticker);
        releasePlayer();
        super.onDestroy();
    }
}
