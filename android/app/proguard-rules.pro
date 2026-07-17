# ZICORE ProGuard Rules
-keepattributes JavascriptInterface
-keepclassmembers class com.zicore.system.MainActivity$* {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class com.zicore.system.** { *; }
