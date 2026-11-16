package com.hexsecgpt.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.graphics.Color;
import android.text.InputType;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.security.KeyStore;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import java.security.SecureRandom;
import javax.crypto.spec.GCMParameterSpec;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

public class MainActivity extends Activity {
    private static final String KEY_ALIAS = "HexSecGPT.ApiKey.AES";
    private static final String PREFS = "hexsec_secure_settings";
    private static final String PREF_API = "openrouter_key";
    private static final String API_URL = "https://openrouter.ai/api/v1/chat/completions";
    private static final String MODEL = "openrouter/free";
    private static final String SYSTEM_PROMPT =
        "Sei HexSecGPT, assistente tecnico specializzato in cybersecurity difensiva, " +
        "Linux, Android, Termux, Python, reti, OSINT pubblico e programmazione. " +
        "Rispondi in italiano quando l'utente scrive in italiano. " +
        "Distingui fatti verificati e ipotesi; non inventare risultati. " +
        "Supporta esclusivamente test su sistemi propri o esplicitamente autorizzati. " +
        "Per richieste rischiose privilegia spiegazioni difensive e ambienti di laboratorio.";

    private WebView webView;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final List<JSONObject> history = new ArrayList<>();
    private volatile boolean busy = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(3, 8, 19));
        getWindow().setNavigationBarColor(Color.rgb(3, 8, 19));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(3, 8, 19));
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(true);
        webView.getSettings().setAllowContentAccess(false);
        webView.getSettings().setAllowFileAccessFromFileURLs(false);
        webView.getSettings().setAllowUniversalAccessFromFileURLs(false);
        webView.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !request.getUrl().toString().startsWith("file:///android_asset/");
            }
        });
        webView.addJavascriptInterface(new AndroidBridge(), "HexSecGPT");
        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
        resetHistory();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.removeJavascriptInterface("HexSecGPT");
            webView.destroy();
        }
        executor.shutdownNow();
        super.onDestroy();
    }

    private synchronized void resetHistory() {
        history.clear();
        try {
            JSONObject system = new JSONObject();
            system.put("role", "system");
            system.put("content", SYSTEM_PROMPT);
            history.add(system);
        } catch (Exception ignored) { }
    }

    private void js(String function, String... values) {
        if (webView == null) return;
        StringBuilder call = new StringBuilder("window.").append(function).append("(");
        for (int i = 0; i < values.length; i++) {
            if (i > 0) call.append(",");
            call.append(JSONObject.quote(values[i] == null ? "" : values[i]));
        }
        call.append(");");
        final String script = call.toString();
        runOnUiThread(() -> {
            if (webView != null) webView.evaluateJavascript(script, null);
        });
    }

    private String storedKey() {
        try {
            String packed = getSharedPreferences(PREFS, MODE_PRIVATE).getString(PREF_API, null);
            if (packed == null) return null;
            String[] parts = packed.split("\\.", 2);
            if (parts.length != 2) return null;
            byte[] iv = Base64.decode(parts[0], Base64.NO_WRAP);
            byte[] ciphertext = Base64.decode(parts[1], Base64.NO_WRAP);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, getSecretKey(), new GCMParameterSpec(128, iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (Exception e) {
            return null;
        }
    }

    private void saveKey(String value) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, getSecretKey());
        byte[] encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        String packed = Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP) + "." +
                        Base64.encodeToString(encrypted, Base64.NO_WRAP);
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(PREF_API, packed).apply();
    }

    private Key getSecretKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
        keyStore.load(null);
        if (keyStore.containsAlias(KEY_ALIAS)) return keyStore.getKey(KEY_ALIAS, null);
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build());
        return generator.generateKey();
    }

    private void showKeyDialog() {
        runOnUiThread(() -> {
            EditText input = new EditText(this);
            input.setSingleLine(true);
            input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
            input.setHint("sk-or-v1-…");
            new AlertDialog.Builder(this)
                .setTitle("Chiave API OpenRouter")
                .setMessage("La chiave viene cifrata con Android Keystore e resta sul dispositivo.")
                .setView(input)
                .setNegativeButton("Annulla", (d, w) -> js("onKeySaved", "Configurazione annullata", ""))
                .setNeutralButton("Rimuovi", (d, w) -> {
                    getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(PREF_API).apply();
                    js("onKeySaved", "Chiave rimossa dal dispositivo", "");
                })
                .setPositiveButton("Salva", (d, w) -> {
                    String value = input.getText().toString().trim();
                    if (value.length() < 12) {
                        js("onKeySaved", "", "La chiave inserita non sembra valida.");
                        return;
                    }
                    try {
                        saveKey(value);
                        js("onKeySaved", "Chiave salvata in modo cifrato", "");
                    } catch (Exception e) {
                        js("onKeySaved", "", "Impossibile proteggere la chiave: " + safeMessage(e));
                    }
                })
                .show();
        });
    }

    private String safeMessage(Exception e) {
        String message = e.getMessage();
        return message == null ? e.getClass().getSimpleName() : message;
    }

    private String requestCompletion(JSONArray messages) throws Exception {
        String key = storedKey();
        if (key == null || key.trim().isEmpty()) throw new IllegalStateException("Configura prima la chiave API OpenRouter.");

        JSONObject payload = new JSONObject();
        payload.put("model", MODEL);
        payload.put("messages", messages);
        payload.put("temperature", 0.7);
        payload.put("stream", false);

        HttpURLConnection connection = (HttpURLConnection) new URL(API_URL).openConnection();
        try {
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(20000);
            connection.setReadTimeout(90000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + key);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("HTTP-Referer", "https://github.com/codexgigas79/HexSecGPT-Android-Builder");
            connection.setRequestProperty("X-Title", "HexSecGPT Android");
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream out = connection.getOutputStream()) { out.write(body); }

            int status = connection.getResponseCode();
            InputStream stream = status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream();
            String responseText = readAll(stream);
            JSONObject response = new JSONObject(responseText);
            if (status < 200 || status >= 300) {
                JSONObject error = response.optJSONObject("error");
                String detail = error == null ? ("HTTP " + status) : error.optString("message", "HTTP " + status);
                throw new IllegalStateException(detail);
            }
            JSONArray choices = response.optJSONArray("choices");
            if (choices == null || choices.length() == 0) throw new IllegalStateException("Il servizio AI non ha restituito una risposta.");
            JSONObject message = choices.getJSONObject(0).optJSONObject("message");
            String content = message == null ? "" : message.optString("content", "");
            if (content.trim().isEmpty()) throw new IllegalStateException("Risposta AI vuota.");
            return content.trim();
        } finally {
            connection.disconnect();
        }
    }

    private String readAll(InputStream stream) throws Exception {
        if (stream == null) return "";
        try (InputStream in = stream; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = in.read(buffer)) != -1) {
                out.write(buffer, 0, count);
                if (out.size() > 1_000_000) throw new IllegalStateException("Risposta del server troppo grande.");
            }
            return out.toString("UTF-8");
        }
    }

    private JSONArray historySnapshot() throws Exception {
        JSONArray messages = new JSONArray();
        synchronized (history) {
            for (JSONObject item : history) messages.put(new JSONObject(item.toString()));
        }
        return messages;
    }

    private class AndroidBridge {
        @JavascriptInterface
        public void openApiKeyDialog() { showKeyDialog(); }

        @JavascriptInterface
        public String getStatus() {
            return storedKey() == null ? "CHIAVE NON CONFIGURATA" : "CHIAVE CONFIGURATA";
        }

        @JavascriptInterface
        public void clearChat() { resetHistory(); }

        @JavascriptInterface
        public void sendMessage(String text) {
            final String prompt = text == null ? "" : text.trim();
            if (prompt.isEmpty() || prompt.length() > 8000) {
                js("onHexSecReply", "", "Messaggio vuoto o troppo lungo.");
                return;
            }
            if (busy) {
                js("onHexSecReply", "", "Attendere il completamento della richiesta precedente.");
                return;
            }
            busy = true;
            executor.execute(() -> {
                try {
                    JSONObject user = new JSONObject();
                    user.put("role", "user");
                    user.put("content", prompt);
                    synchronized (history) { history.add(user); }
                    String answer = requestCompletion(historySnapshot());
                    JSONObject assistant = new JSONObject();
                    assistant.put("role", "assistant");
                    assistant.put("content", answer);
                    synchronized (history) {
                        history.add(assistant);
                        while (history.size() > 21) history.remove(1);
                    }
                    js("onHexSecReply", answer, "");
                } catch (Exception e) {
                    js("onHexSecReply", "", safeMessage(e));
                } finally {
                    busy = false;
                }
            });
        }

        @JavascriptInterface
        public void generateScript(String name, String request) {
            final String safeName = name == null ? "" : name.trim();
            final String description = request == null ? "" : request.trim();
            if (!safeName.matches("[A-Za-z0-9_-]{1,40}") || description.isEmpty() || description.length() > 4000) {
                js("onScriptGenerated", "", "", "Nome o descrizione non validi.");
                return;
            }
            if (busy) {
                js("onScriptGenerated", "", "", "Attendere il completamento della richiesta precedente.");
                return;
            }
            busy = true;
            executor.execute(() -> {
                try {
                    JSONArray messages = new JSONArray();
                    JSONObject system = new JSONObject();
                    system.put("role", "system");
                    system.put("content", "Sei un programmatore Python. Genera solo script Python 3 per automazioni locali legittime e non distruttive. Non creare malware, furto di credenziali, persistenza, evasione, attacchi o esfiltrazione. Non includere installazioni automatiche o comandi distruttivi. Restituisci un unico blocco di codice Python delimitato da tre backtick.");
                    messages.put(system);
                    JSONObject user = new JSONObject();
                    user.put("role", "user");
                    user.put("content", "Nome: " + safeName + "\nRichiesta: " + description);
                    messages.put(user);
                    String answer = requestCompletion(messages);
                    Matcher matcher = Pattern.compile("(?is)\\x60\\x60\\x60(?:python|py)?\\s*(.*?)\\x60\\x60\\x60").matcher(answer);
                    if (!matcher.find()) throw new IllegalStateException("L'AI non ha restituito un blocco Python riconoscibile.");
                    String code = matcher.group(1).trim();
                    File directory = new File(getFilesDir(), "generated_scripts");
                    if (!directory.exists() && !directory.mkdirs()) throw new IllegalStateException("Impossibile creare la cartella degli script.");
                    File output = new File(directory, safeName + ".py");
                    if (output.exists()) throw new IllegalStateException("Esiste già uno script con questo nome.");
                    try (OutputStreamWriter writer = new OutputStreamWriter(new FileOutputStream(output), StandardCharsets.UTF_8)) {
                        writer.write(code);
                        writer.write("\n");
                    }
                    js("onScriptGenerated", output.getName(), code, "");
                } catch (Exception e) {
                    js("onScriptGenerated", "", "", safeMessage(e));
                } finally {
                    busy = false;
                }
            });
        }

        @JavascriptInterface
        public String listScripts() {
            JSONArray result = new JSONArray();
            File directory = new File(getFilesDir(), "generated_scripts");
            File[] files = directory.listFiles((dir, name) -> name.endsWith(".py"));
            if (files != null) for (File file : files) result.put(file.getName());
            return result.toString();
        }

        @JavascriptInterface
        public String readScript(String name) {
            if (name == null || !name.matches("[A-Za-z0-9_-]{1,40}\\.py")) return "";
            File file = new File(new File(getFilesDir(), "generated_scripts"), name);
            if (!file.isFile()) return "";
            try (FileInputStream in = new FileInputStream(file)) { return readAll(in); }
            catch (Exception e) { return ""; }
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
