package com.hexsecgpt.app;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Remote APK builds through the private HexSecGPT BuildServer repository. */
final class RemoteBuildManager {
    private static final String OWNER = "codexgigas79";
    private static final String REPO = "HexSecGPT-BuildServer";
    private static final String API = "https://api.github.com/repos/" + OWNER + "/" + REPO;
    private static final String WORKFLOW = ".github/workflows/build-generated-app.yml";
    private static final int CONNECT_TIMEOUT = 20000;
    private static final int READ_TIMEOUT = 30000;

    static final class Result {
        final long runId;
        final String runUrl;
        final String artifactName;
        final File apk;
        Result(long id, String url, String artifact, File file) {
            runId = id; runUrl = url; artifactName = artifact; apk = file;
        }
    }

    private RemoteBuildManager() {}

    static Result build(Context context, String projectName, String token) throws Exception {
        if (projectName == null || !projectName.matches("[A-Za-z0-9_-]{2,32}"))
            throw new IllegalArgumentException("Nome progetto non valido.");
        if (token == null || token.trim().length() < 20)
            throw new IllegalStateException("Token GitHub non configurato.");

        JSONArray files = collectSources(context, projectName);
        JSONObject clientPayload = new JSONObject();
        clientPayload.put("project_name", projectName);
        clientPayload.put("files", files);
        JSONObject dispatch = new JSONObject();
        dispatch.put("event_type", "build-android");
        dispatch.put("client_payload", clientPayload);

        long startedAt = System.currentTimeMillis();
        apiJson("POST", API + "/dispatches", token, dispatch.toString());
        JSONObject run = waitForRun(token, startedAt);
        long runId = run.optLong("id", 0);
        String runUrl = run.optString("html_url", "https://github.com/" + OWNER + "/" + REPO + "/actions");
        if (runId == 0) throw new IllegalStateException("GitHub ha ricevuto la richiesta ma non ha restituito una run identificabile.");

        String status = run.optString("status", "");
        String conclusion = run.optString("conclusion", "");
        if (!"completed".equals(status) || !"success".equals(conclusion)) {
            String details = failedSteps(token, runId);
            throw new IllegalStateException("Compilazione non riuscita (" + status + "/" + conclusion + "). " +
                    (details.isEmpty() ? "Consultare la run GitHub." : details) + " Run: " + runUrl);
        }

        String artifactName = "HexSecGPT-" + projectName + "-APK";
        JSONObject artifactsResponse = apiJson("GET", API + "/actions/runs/" + runId + "/artifacts", token, null);
        JSONArray artifacts = artifactsResponse.optJSONArray("artifacts");
        long artifactId = 0;
        if (artifacts != null) {
            for (int i = 0; i < artifacts.length(); i++) {
                JSONObject item = artifacts.getJSONObject(i);
                if (artifactName.equals(item.optString("name")) && !item.optBoolean("expired", true)) {
                    artifactId = item.optLong("id", 0);
                    break;
                }
            }
        }
        if (artifactId == 0)
            throw new IllegalStateException("Build riuscita, ma l'artifact APK non risulta pubblicato o è scaduto. Run: " + runUrl);

        File apk = downloadAndExtractApk(context, token, artifactId, projectName, runId);
        return new Result(runId, runUrl, artifactName, apk);
    }

    private static JSONArray collectSources(Context context, String projectName) throws Exception {
        File base = new File(new File(context.getFilesDir(), "generated_android_projects"), projectName);
        if (!base.isDirectory()) throw new IllegalArgumentException("Progetto non trovato nell'archivio locale.");
        JSONArray files = new JSONArray();
        collectDirectory(base, new File(base, "app/src/main/java/com/generated/app"), "app/src/main/java/com/generated/app", files);
        collectDirectory(base, new File(base, "app/src/main/res/layout"), "app/src/main/res/layout", files);
        if (files.length() < 2 || files.length() > 8)
            throw new IllegalStateException("Il BuildServer accetta da 2 a 8 file Java/XML. Il progetto contiene " + files.length() + ".");
        boolean main = false, layout = false;
        int total = 0;
        for (int i = 0; i < files.length(); i++) {
            JSONObject item = files.getJSONObject(i);
            String path = item.getString("path");
            String body = item.getString("content");
            total += body.getBytes(StandardCharsets.UTF_8).length;
            if (body.getBytes(StandardCharsets.UTF_8).length > 30000)
                throw new IllegalStateException("File troppo grande: " + path);
            if (path.endsWith("/MainActivity.java")) main = true;
            if ("app/src/main/res/layout/activity_main.xml".equals(path)) layout = true;
        }
        if (total > 90000) throw new IllegalStateException("Il progetto supera il limite totale di 90 KB.");
        if (!main || !layout) throw new IllegalStateException("Servono MainActivity.java e activity_main.xml.");
        return files;
    }

    private static void collectDirectory(File root, File directory, String prefix, JSONArray output) throws Exception {
        File[] children = directory.listFiles();
        if (children == null) return;
        for (File file : children) {
            if (file.isDirectory()) throw new IllegalStateException("Sottocartelle non previste nel progetto generato.");
            String name = file.getName();
            boolean java = prefix.endsWith("/java/com/generated/app") && name.matches("[A-Za-z0-9_]+\\.java");
            boolean xml = prefix.endsWith("/res/layout") && name.matches("[a-z0-9_]+\\.xml");
            if (!java && !xml) continue;
            if (output.length() >= 8) throw new IllegalStateException("Il progetto supera il limite di 8 file.");
            byte[] bytes;
            try (InputStream in = new FileInputStream(file); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[4096]; int n;
                while ((n = in.read(buffer)) != -1) { out.write(buffer, 0, n); if (out.size() > 30000) break; }
                bytes = out.toByteArray();
            }
            JSONObject item = new JSONObject();
            item.put("path", prefix + "/" + name);
            item.put("content", new String(bytes, StandardCharsets.UTF_8));
            output.put(item);
        }
    }

    private static JSONObject waitForRun(String token, long startedAt) throws Exception {
        for (int attempt = 0; attempt < 60; attempt++) {
            JSONObject response = apiJson("GET", API + "/actions/runs?event=repository_dispatch&per_page=20", token, null);
            JSONArray runs = response.optJSONArray("workflow_runs");
            JSONObject candidate = null;
            if (runs != null) {
                for (int i = 0; i < runs.length(); i++) {
                    JSONObject item = runs.getJSONObject(i);
                    if (!WORKFLOW.equals(item.optString("path"))) continue;
                    if (!"repository_dispatch".equals(item.optString("event"))) continue;
                    long created = parseGitHubDate(item.optString("created_at"));
                    if (created >= startedAt - 15000) {
                        if (candidate == null || created > parseGitHubDate(candidate.optString("created_at"))) candidate = item;
                    }
                }
            }
            if (candidate != null && "completed".equals(candidate.optString("status"))) return candidate;
            if (candidate != null && ("queued".equals(candidate.optString("status")) ||
                    "in_progress".equals(candidate.optString("status")) || "waiting".equals(candidate.optString("status")))) {
                Thread.sleep(5000);
                continue;
            }
            Thread.sleep(5000);
        }
        throw new IllegalStateException("Timeout: GitHub non ha completato la compilazione entro 5 minuti. Controllare GitHub Actions nel BuildServer.");
    }

    private static long parseGitHubDate(String value) {
        try {
            SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
            format.setTimeZone(TimeZone.getTimeZone("UTC"));
            Date date = format.parse(value);
            return date == null ? 0 : date.getTime();
        } catch (Exception e) { return 0; }
    }

    private static String failedSteps(String token, long runId) {
        try {
            JSONObject response = apiJson("GET", API + "/actions/runs/" + runId + "/jobs", token, null);
            JSONArray jobs = response.optJSONArray("jobs");
            StringBuilder detail = new StringBuilder();
            if (jobs != null) for (int i = 0; i < jobs.length(); i++) {
                JSONObject job = jobs.getJSONObject(i);
                JSONArray steps = job.optJSONArray("steps");
                if (steps == null) continue;
                for (int j = 0; j < steps.length(); j++) {
                    JSONObject step = steps.getJSONObject(j);
                    String result = step.optString("conclusion", "");
                    if ("failure".equals(result) || "cancelled".equals(result)) {
                        if (detail.length() > 0) detail.append("; ");
                        detail.append(job.optString("name", "Job")).append(": ")
                              .append(step.optString("name", "step")).append(" (").append(result).append(")");
                    }
                }
            }
            return detail.toString();
        } catch (Exception ignored) { return ""; }
    }

    private static JSONObject apiJson(String method, String address, String token, String body) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(address).openConnection();
        try {
            connection.setRequestMethod(method);
            connection.setConnectTimeout(CONNECT_TIMEOUT);
            connection.setReadTimeout(READ_TIMEOUT);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            connection.setRequestProperty("X-GitHub-Api-Version", "2022-11-28");
            if (body != null) {
                byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setFixedLengthStreamingMode(bytes.length);
                try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            }
            int code = connection.getResponseCode();
            if (code == 204) return new JSONObject();
            InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            String text = readText(stream, 1000000);
            if (code < 200 || code >= 300) {
                String message = "GitHub API HTTP " + code;
                try { message = new JSONObject(text).optString("message", message); } catch (Exception ignored) {}
                throw new IllegalStateException(message);
            }
            return text.trim().isEmpty() ? new JSONObject() : new JSONObject(text);
        } finally { connection.disconnect(); }
    }

    private static File downloadAndExtractApk(Context context, String token, long artifactId, String projectName, long runId) throws Exception {
        String address = API + "/actions/artifacts/" + artifactId + "/zip";
        HttpURLConnection connection = (HttpURLConnection) new URL(address).openConnection();
        InputStream input = null;
        try {
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(CONNECT_TIMEOUT);
            connection.setReadTimeout(60000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            int code = connection.getResponseCode();
            if (code == 301 || code == 302 || code == 303 || code == 307 || code == 308) {
                String location = connection.getHeaderField("Location");
                if (location == null || !location.startsWith("https://"))
                    throw new IllegalStateException("GitHub non ha fornito un collegamento sicuro per l'artifact.");
                connection.disconnect();
                connection = (HttpURLConnection) new URL(location).openConnection();
                connection.setConnectTimeout(CONNECT_TIMEOUT);
                connection.setReadTimeout(60000);
                code = connection.getResponseCode();
            }
            if (code != 200) throw new IllegalStateException("Download artifact non riuscito (HTTP " + code + ").");
            input = connection.getInputStream();
            File targetDir = new File(context.getCacheDir(), "built_apks");
            if (!targetDir.exists() && !targetDir.mkdirs()) throw new IllegalStateException("Impossibile preparare la cartella APK.");
            File apk = new File(targetDir, projectName + "-" + runId + ".apk");
            boolean found = false;
            try (ZipInputStream zip = new ZipInputStream(input)) {
                ZipEntry entry;
                while ((entry = zip.getNextEntry()) != null) {
                    String entryName = new File(entry.getName()).getName();
                    if ("app-debug.apk".equals(entryName) || entryName.endsWith(".apk")) {
                        try (FileOutputStream out = new FileOutputStream(apk)) {
                            byte[] buffer = new byte[8192]; int n; long total = 0;
                            while ((n = zip.read(buffer)) != -1) {
                                total += n;
                                if (total > 100L * 1024L * 1024L) throw new IllegalStateException("APK oltre il limite di 100 MB.");
                                out.write(buffer, 0, n);
                            }
                        }
                        found = apk.isFile() && apk.length() > 10000;
                        break;
                    }
                    zip.closeEntry();
                }
            }
            if (!found) {
                apk.delete();
                throw new IllegalStateException("L'artifact è stato scaricato, ma non contiene un APK valido.");
            }
            return apk;
        } finally {
            if (input != null) try { input.close(); } catch (Exception ignored) {}
            connection.disconnect();
        }
    }

    private static String readText(InputStream input, int limit) throws Exception {
        if (input == null) return "";
        try (InputStream in = input; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) != -1) {
                out.write(buffer, 0, n);
                if (out.size() > limit) throw new IllegalStateException("Risposta GitHub troppo grande.");
            }
            return out.toString("UTF-8");
        }
    }
}
