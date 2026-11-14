plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val uploadKeystore = providers.environmentVariable("VM_UPLOAD_KEYSTORE").orNull
val uploadStorePassword = providers.environmentVariable("VM_UPLOAD_STORE_PASSWORD").orNull
val uploadKeyAlias = providers.environmentVariable("VM_UPLOAD_KEY_ALIAS").orNull
val uploadKeyPassword = providers.environmentVariable("VM_UPLOAD_KEY_PASSWORD").orNull
val uploadSigningConfigured = listOf(
    uploadKeystore, uploadStorePassword, uploadKeyAlias, uploadKeyPassword
).all { !it.isNullOrBlank() }

android {
    namespace = "org.visionmachine.agriclinic"
    compileSdk = 36

    defaultConfig {
        applicationId = "org.visionmachine.agriclinic"
        minSdk = 26
        targetSdk = 36
        versionCode = 6
        versionName = "0.6.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (uploadSigningConfigured) {
            create("upload") {
                storeFile = file(uploadKeystore!!)
                storePassword = uploadStorePassword
                keyAlias = uploadKeyAlias
                keyPassword = uploadKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (uploadSigningConfigured) {
                signingConfig = signingConfigs.getByName("upload")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation("com.github.mik3y:usb-serial-for-android:3.9.0")
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("androidx.exifinterface:exifinterface:1.4.1")
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.31.1")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.1")
}

tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    doFirst {
        check(file("src/main/assets/vision_rgb_cseed42.onnx").exists()) {
            "Verified local RGB model asset is required for a release. See docs/ANDROID_RGB.md."
        }
    }
}
