import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.panelist.app"
    compileSdk = 35

    val keystoreProperties = Properties()
    val keystorePropertiesFile = rootProject.file("keystore.properties")
    if (keystorePropertiesFile.exists()) {
        keystorePropertiesFile.inputStream().use(keystoreProperties::load)
    }

    val configuredVersionCode = providers.gradleProperty("versionCode").orNull?.toIntOrNull() ?: 1
    val configuredVersionName = providers.gradleProperty("versionName").orNull ?: "0.1.0"

    signingConfigs {
        create("release") {
            keystoreProperties["storeFile"]?.toString()?.let { storeFile = rootProject.file(it) }
            storePassword = keystoreProperties["storePassword"]?.toString()
            keyAlias = keystoreProperties["keyAlias"]?.toString()
            keyPassword = keystoreProperties["keyPassword"]?.toString()
        }
    }

    defaultConfig {
        applicationId = "com.panelist.app"
        minSdk = 28
        targetSdk = 35
        versionCode = configuredVersionCode
        versionName = configuredVersionName
        manifestPlaceholders["usesCleartextTraffic"] = "false"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    buildTypes {
        debug {
            manifestPlaceholders["usesCleartextTraffic"] = "true"
        }
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }

    val configuredBaseUrl = providers.gradleProperty("panelistBaseUrl").orNull ?: "http://10.0.2.2:8080/"
    defaultConfig.buildConfigField("String", "PANELIST_BASE_URL", "\"$configuredBaseUrl\"")

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.ui:ui:1.7.5")
    implementation("androidx.compose.material3:material3:1.3.1")
    implementation("androidx.compose.material:material-icons-core:1.7.5")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
    debugImplementation("androidx.compose.ui:ui-test-manifest:1.7.5")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4:1.7.5")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
}
