package com.zicore.system;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.GeolocationPermissions;
import android.webkit.JsResult;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Collections;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout loadingScreen;
    private TextView statusText;
    private SharedPreferences prefs;
    private boolean vrMode = false;
    private WebView leftEyeView;
    private WebView rightEyeView;
    private LinearLayout vrContainer;

    // Server URLs
    private static final String CLOUD_URL = "https://zcs.zicore.space";
    private static final String LOCAL_URL = "http://localhost:4000";
    private static final String PREFS_NAME = "zicore_prefs";
    private static final String KEY_SERVER = "server_url";
    private static final String KEY_FIRST_RUN = "first_run";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Fullscreen immersive
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            getWindow().getAttributes().layoutInDisplayCutoutMode =
                WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

        // Create loading screen
        loadingScreen = new LinearLayout(this);
        loadingScreen.setOrientation(LinearLayout.VERTICAL);
        loadingScreen.setGravity(android.view.Gravity.CENTER);
        loadingScreen.setBackgroundColor(Color.parseColor("#060a12"));
        loadingScreen.setPadding(40, 40, 40, 40);

        TextView logo = new TextView(this);
        logo.setText("◈");
        logo.setTextSize(64);
        logo.setTextColor(Color.parseColor("#00e5ff"));
        logo.setGravity(android.view.Gravity.CENTER);
        loadingScreen.addView(logo);

        TextView title = new TextView(this);
        title.setText("ZICORE SYSTEM");
        title.setTextSize(20);
        title.setTextColor(Color.parseColor("#00e5ff"));
        title.setGravity(android.view.Gravity.CENTER);
        title.setPadding(0, 20, 0, 8);
        loadingScreen.addView(title);

        statusText = new TextView(this);
        statusText.setText("Iniciando...");
        statusText.setTextSize(12);
        statusText.setTextColor(Color.parseColor("#607080"));
        statusText.setGravity(android.view.Gravity.CENTER);
        loadingScreen.addView(statusText);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setIndeterminate(true);
        LinearLayout.LayoutParams barParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        );
        barParams.setMargins(0, 30, 0, 0);
        progressBar.setLayoutParams(barParams);
        progressBar.setVisibility(View.VISIBLE);
        loadingScreen.addView(progressBar);

        setContentView(loadingScreen);

        // First run: ask for server URL
        if (prefs.getBoolean(KEY_FIRST_RUN, true)) {
            showServerDialog();
        } else {
            connectToServer();
        }
    }

    private void showServerDialog() {
        String[] options = {
            "☁ ZICORE Cloud (zcs.zicore.space)",
            "📱 Termux Local (localhost:4000)",
            "🌐 Custom URL"
        };

        new AlertDialog.Builder(this, R.style.ZICOREDialog)
            .setTitle("Conectar a ZICORE")
            .setItems(options, (dialog, which) -> {
                switch (which) {
                    case 0:
                        prefs.edit().putString(KEY_SERVER, CLOUD_URL).apply();
                        break;
                    case 1:
                        prefs.edit().putString(KEY_SERVER, LOCAL_URL).apply();
                        break;
                    case 2:
                        showCustomUrlDialog();
                        return;
                }
                prefs.edit().putBoolean(KEY_FIRST_RUN, false).apply();
                connectToServer();
            })
            .setCancelable(false)
            .show();
    }

    private void showCustomUrlDialog() {
        EditText input = new EditText(this);
        input.setHint("http://192.168.1.x:4000");
        input.setTextColor(Color.WHITE);
        input.setHintTextColor(Color.GRAY);

        new AlertDialog.Builder(this, R.style.ZICOREDialog)
            .setTitle("URL del servidor")
            .setView(input)
            .setPositiveButton("Conectar", (dialog, which) -> {
                String url = input.getText().toString().trim();
                if (!url.isEmpty()) {
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        url = "http://" + url;
                    }
                    prefs.edit().putString(KEY_SERVER, url).apply();
                    prefs.edit().putBoolean(KEY_FIRST_RUN, false).apply();
                    connectToServer();
                }
            })
            .setNegativeButton("Cancelar", (dialog, which) -> dialog.dismiss())
            .show();
    }

    private void connectToServer() {
        String serverUrl = prefs.getString(KEY_SERVER, CLOUD_URL);
        statusText.setText("Conectando a " + serverUrl + "...");

        // Check network
        if (!isNetworkAvailable()) {
            statusText.setText("Sin conexion. Verifica tu WiFi.");
            progressBar.setVisibility(View.GONE);
            return;
        }

        setupWebView(serverUrl);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView(String serverUrl) {
        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#060a12"));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setDatabaseEnabled(true);

        // Enable geolocation
        settings.setGeolocationEnabled(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE);
                statusText.setText("Cargando...");
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                statusText.setText("");
                // Inject SSO token from shared preferences
                String token = prefs.getString("sso_token", "");
                if (!token.isEmpty()) {
                    view.evaluateJavascript(
                        "localStorage.setItem('zicore_sso_token','" + token + "')", null
                    );
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    statusText.setText("Error de conexion. Reintentando...");
                    // Auto-retry in 3 seconds
                    new Handler(Looper.getMainLooper()).postDelayed(() -> {
                        String url = prefs.getString(KEY_SERVER, CLOUD_URL);
                        webView.loadUrl(url);
                    }, 3000);
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage msg) {
                return true;
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this, R.style.ZICOREDialog)
                    .setTitle("ZICORE")
                    .setMessage(message)
                    .setPositiveButton("OK", (d, w) -> result.confirm())
                    .show();
                return true;
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                return true;
            }
        });

        // Save SSO token when changed + VR controls
        webView.addJavascriptInterface(new Object() {
            @android.webkit.JavascriptInterface
            public void saveToken(String token) {
                prefs.edit().putString("sso_token", token).apply();
            }

            @android.webkit.JavascriptInterface
            public void enterVR() {
                runOnUiThread(() -> enterVRMode());
            }

            @android.webkit.JavascriptInterface
            public void exitVR() {
                runOnUiThread(() -> exitVRMode());
            }

            @android.webkit.JavascriptInterface
            public void toggleVR() {
                runOnUiThread(() -> toggleVRMode());
            }

            @android.webkit.JavascriptInterface
            public boolean isVRMode() {
                return vrMode;
            }

            @android.webkit.JavascriptInterface
            public void setBrightness(int level) {
                runOnUiThread(() -> {
                    WindowManager.LayoutParams params = getWindow().getAttributes();
                    params.screenBrightness = level / 100.0f;
                    getWindow().setAttributes(params);
                });
            }

            @android.webkit.JavascriptInterface
            public void vibrate(int ms) {
                android.os.Vibrator v = (android.os.Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null) v.vibrate(ms);
            }
        }, "ZICORE");

        // Replace loading screen with webview
        setContentView(webView);
        webView.loadUrl(serverUrl);

        // Handle back button
        webView.setOnKeyListener((v, keyCode, event) -> {
            if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
                webView.goBack();
                return true;
            }
            return false;
        });
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm != null) {
            NetworkInfo info = cm.getActiveNetworkInfo();
            return info != null && info.isConnected();
        }
        return false;
    }

    public static String getLocalIpAddress(Context context) {
        try {
            List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
            for (NetworkInterface iface : interfaces) {
                List<InetAddress> addrs = Collections.list(iface.getInetAddresses());
                for (InetAddress addr : addrs) {
                    if (!addr.isLoopbackAddress() && addr instanceof java.net.Inet4Address) {
                        return addr.getHostAddress();
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "127.0.0.1";
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            new AlertDialog.Builder(this, R.style.ZICOREDialog)
                .setTitle("Salir de ZICORE?")
                .setPositiveButton("Salir", (d, w) -> finish())
                .setNegativeButton("Cancelar", null)
                .show();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    // ── VR Stereo Mode ──────────────────────────────────────
    public void toggleVRMode() {
        if (!vrMode) {
            enterVRMode();
        } else {
            exitVRMode();
        }
    }

    private void enterVRMode() {
        vrMode = true;

        // Create VR container with split-screen
        vrContainer = new LinearLayout(this);
        vrContainer.setOrientation(LinearLayout.HORIZONTAL);
        vrContainer.setBackgroundColor(Color.BLACK);

        // Left eye
        leftEyeView = createStereoWebView("left");
        LinearLayout.LayoutParams leftParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1.0f);
        leftEyeView.setLayoutParams(leftParams);

        // Divider
        View divider = new View(this);
        divider.setBackgroundColor(Color.parseColor("#333333"));
        LinearLayout.LayoutParams dividerParams = new LinearLayout.LayoutParams(2, LinearLayout.LayoutParams.MATCH_PARENT);
        divider.setLayoutParams(dividerParams);

        // Right eye
        rightEyeView = createStereoWebView("right");
        LinearLayout.LayoutParams rightParams = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1.0f);
        rightEyeView.setLayoutParams(rightParams);

        vrContainer.addView(leftEyeView);
        vrContainer.addView(divider);
        vrContainer.addView(rightEyeView);

        // Hide main webview, show VR
        webView.setVisibility(View.GONE);
        setContentView(vrContainer);

        // Load Materializer VR stream
        String serverUrl = prefs.getString(KEY_SERVER, CLOUD_URL);
        String token = prefs.getString("sso_token", "");
        String vrUrl = serverUrl + "/materializer?vr=stereo&eye=";
        String leftUrl = vrUrl + "left";
        String rightUrl = vrUrl + "right";
        if (!token.isEmpty()) {
            leftUrl += "&token=" + token;
            rightUrl += "&token=" + token;
        }
        leftEyeView.loadUrl(leftUrl);
        rightEyeView.loadUrl(rightUrl);

        // Full screen immersive
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );

        Toast.makeText(this, "VR Mode ON — Split Stereo", Toast.LENGTH_SHORT).show();
    }

    private WebView createStereoWebView(String eye) {
        WebView wv = new WebView(this);
        wv.setBackgroundColor(Color.BLACK);
        WebSettings settings = wv.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);

        wv.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                // Inject VR mode flag
                view.evaluateJavascript("window.ZICORE_VR_MODE=true; window.ZICORE_EYE='" + eye + "';", null);
            }
        });

        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }
        });

        return wv;
    }

    private void exitVRMode() {
        vrMode = false;

        // Destroy VR views
        if (leftEyeView != null) leftEyeView.destroy();
        if (rightEyeView != null) rightEyeView.destroy();

        // Restore main webview
        setContentView(webView);
        webView.setVisibility(View.VISIBLE);

        // Exit immersive
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);

        Toast.makeText(this, "VR Mode OFF", Toast.LENGTH_SHORT).show();
    }

    // ── Materializer Stream ─────────────────────────────────
    public void loadMaterializerStream() {
        String serverUrl = prefs.getString(KEY_SERVER, CLOUD_URL);
        String token = prefs.getString("sso_token", "");
        String streamUrl = serverUrl + "/materializer";
        if (!token.isEmpty()) streamUrl += "?token=" + token;
        webView.loadUrl(streamUrl);
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) webView.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) webView.destroy();
        super.onDestroy();
    }
}
