package com.hexsecgpt.app;

import android.content.Context;
import android.net.Uri;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Creates safe, portable Android Studio project bundles. */
final class AppStudio {
    private AppStudio() {}

    static String create(Context context, String requestedName, String aiJson) throws Exception {
        String name = slug(requestedName);
        if (name.length() < 2) throw new IllegalArgumentException("Nome progetto non valido.");
        String json = stripFence(aiJson);
        JSONObject root = new JSONObject(json);
        JSONArray files = root.optJSONArray("files");
        if (files == null || files.length() < 2 || files.length() > 8)
            throw new IllegalArgumentException("Il progetto deve contenere da 2 a 8 file sorgente.");
        File base = new File(new File(context.getFilesDir(), "generated_android_projects"), name);
        if (base.exists()) throw new IllegalStateException("Esiste già un progetto con questo nome.");
        if (!base.mkdirs()) throw new IllegalStateException("Impossibile creare la cartella del progetto.");

        int total = 0;
        boolean hasMain = false;
        boolean hasLayout = false;
        try {
            for (int i = 0; i < files.length(); i++) {
                JSONObject item = files.getJSONObject(i);
                String path = item.optString("path", "");
                String body = item.optString("content", "");
                if (!safeSourcePath(path) || body.isEmpty() || body.length() > 30000)
                    throw new IllegalArgumentException("File sorgente non valido: " + path);
                if (path.endsWith("/MainActivity.java")) {
                    hasMain = true;
                    if (!body.matches("(?s).*package\\s+com\\.generated\\.app\\s*;.*"))
                        throw new IllegalArgumentException("MainActivity deve usare il package com.generated.app.");
                }
                if (path.equals("app/src/main/res/layout/activity_main.xml")) hasLayout = true;
                total += body.getBytes(StandardCharsets.UTF_8).length;
                if (total > 90000) throw new IllegalArgumentException("Il progetto supera il limite di 90 KB.");
                write(new File(base, path), body);
            }
            if (!hasMain || !hasLayout)
                throw new IllegalArgumentException("Servono MainActivity.java e res/layout/activity_main.xml.");
            write(new File(base, "settings.gradle"),
                "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n" +
                "dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }\n" +
                "rootProject.name = \"" + name + "\"\ninclude ':app'\n");
            write(new File(base, "build.gradle"),
                "plugins { id 'com.android.application' version '8.7.3' apply false }\n");
            String appIdSuffix = name.replaceAll("[^a-z0-9_]", "_");
            String applicationId = "com.hexsecgpt.generated." + appIdSuffix;
            write(new File(base, "app/build.gradle"),
                "plugins { id 'com.android.application' }\n\nandroid {\n" +
                "    namespace 'com.generated.app'\n    compileSdk 35\n" +
                "    defaultConfig { applicationId '" + applicationId + "'; minSdk 23; targetSdk 35; versionCode 1; versionName '1.0' }\n}\n");
            write(new File(base, "app/src/main/AndroidManifest.xml"),
                "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
                "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">\n" +
                "  <application android:label=\"" + xml(name) + "\" android:theme=\"@android:style/Theme.Material.Light.NoActionBar\" android:allowBackup=\"false\">\n" +
                "    <activity android:name=\".MainActivity\" android:exported=\"true\">\n" +
                "      <intent-filter><action android:name=\"android.intent.action.MAIN\"/><category android:name=\"android.intent.category.LAUNCHER\"/></intent-filter>\n" +
                "    </activity>\n  </application>\n</manifest>\n");
            write(new File(base, "README.md"),
                "# " + name + "\n\nProgetto Android generato con HexSecGPT App Studio.\n\n" +
                "Aprire la cartella in Android Studio e attendere la sincronizzazione Gradle.\n" +
                "Compilare con Build > Build Bundle(s) / APK(s) > Build APK(s).\n\n" +
                "I sorgenti generati dall'AI vanno revisionati e testati prima dell'installazione.\n");
            return base.getAbsolutePath();
        } catch (Exception e) {
            deleteTree(base);
            throw e;
        }
    }

    static JSONArray list(Context context) throws Exception {
        JSONArray result = new JSONArray();
        File root = new File(context.getFilesDir(), "generated_android_projects");
        File[] dirs = root.listFiles(File::isDirectory);
        if (dirs != null) for (File dir : dirs) result.put(dir.getName());
        return result;
    }

    static void export(Context context, String requestedName, Uri destination) throws Exception {
        String name = slug(requestedName);
        File base = new File(new File(context.getFilesDir(), "generated_android_projects"), name);
        if (!base.isDirectory()) throw new IllegalArgumentException("Progetto non trovato.");
        try (OutputStream raw = context.getContentResolver().openOutputStream(destination);
             ZipOutputStream zip = new ZipOutputStream(raw)) {
            addTree(base, base, zip);
            zip.finish();
        }
    }

    private static void addTree(File root, File current, ZipOutputStream zip) throws Exception {
        File[] children = current.listFiles();
        if (children == null) return;
        for (File child : children) {
            if (child.isDirectory()) addTree(root, child, zip);
            else {
                String path = root.toURI().relativize(child.toURI()).getPath();
                zip.putNextEntry(new ZipEntry(path));
                try (FileInputStream in = new FileInputStream(child)) {
                    byte[] buffer = new byte[8192];
                    int count;
                    while ((count = in.read(buffer)) != -1) zip.write(buffer, 0, count);
                }
                zip.closeEntry();
            }
        }
    }

    private static boolean safeSourcePath(String path) {
        if (path.contains("..") || path.startsWith("/") || path.contains("\\\\") || path.contains(":")) return false;
        if (!path.matches("app/src/main/java/com/generated/app/[A-Za-z0-9_]+\\.java") &&
            !path.matches("app/src/main/res/layout/[a-z0-9_]+\\.xml") &&
            !path.matches("app/src/main/res/values/[a-z0-9_]+\\.xml")) return false;
        return true;
    }

    private static String slug(String value) {
        String result = value == null ? "" : value.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_-]", "_");
        return result.length() > 32 ? result.substring(0, 32) : result;
    }

    private static String stripFence(String value) {
        String s = value == null ? "" : value.trim();
        if (s.startsWith("```")) {
            int first = s.indexOf('\n');
            int last = s.lastIndexOf("```");
            if (first >= 0 && last > first) s = s.substring(first + 1, last).trim();
        }
        int start = s.indexOf('{');
        int end = s.lastIndexOf('}');
        if (start < 0 || end <= start) throw new IllegalArgumentException("La risposta AI non contiene JSON valido.");
        return s.substring(start, end + 1);
    }

    private static void write(File file, String content) throws Exception {
        File parent = file.getParentFile();
        if (!parent.exists() && !parent.mkdirs()) throw new IllegalStateException("Impossibile creare " + parent.getName());
        try (java.io.FileOutputStream out = new java.io.FileOutputStream(file)) {
            out.write(content.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String xml(String value) {
        return value.replace("&", "&amp;").replace("\"", "&quot;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static void deleteTree(File file) {
        File[] children = file.listFiles();
        if (children != null) for (File child : children) deleteTree(child);
        file.delete();
    }
}
