# HexSecGPT Android

Android application for the HexSecGPT project.

## Current Android edition

- Cyber HUD interface embedded in the APK.
- OpenRouter chat using the `openrouter/free` model route.
- API key entry inside the app; the key is encrypted with Android Keystore and is not committed to the repository.
- AI-assisted Python script generation. Generated files are stored in the app's private internal storage.

## Current limitations

- The original Python CLI and HTTP server under `hexsecgpt_source/` are preserved as source reference; they are not executed directly by the Android app.
- Generated Python scripts can be viewed but are not executed or syntax-checked by this Android edition.
- Nmap is not bundled. The Nmap panel is deliberately marked unavailable until a dedicated Android-native integration is implemented.
- An OpenRouter API key and network access are required for AI features. Model availability and free-route limits are controlled by OpenRouter.

## Build

GitHub Actions builds a debug APK with Java 17, Gradle 8.9, Android Gradle Plugin 8.7.3 and Android SDK 35.

After a successful run, download the artifact named **HexSecGPT-Android-APK**.
