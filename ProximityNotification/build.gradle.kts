plugins {
    kotlin("android") version "1.9.10" apply false
    id("com.android.application") version "8.2.2" apply false
}

tasks.register<Delete>("clean") {
    delete(rootProject.buildDir)
}
