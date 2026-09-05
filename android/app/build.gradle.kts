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
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    buildTypes {
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
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
