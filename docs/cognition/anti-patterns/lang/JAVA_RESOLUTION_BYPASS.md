# Resolution Bypass — Java
> Parent: [`RESOLUTION_BYPASS.md`](../RESOLUTION_BYPASS.md)

---

## ❌ Java-Specific Hacks
### 1. Fat Jar / Uber Jar Manual Merging```bash
# ❌ Manually unzipping and re-zipping JAR files# to resolve version conflicts instead of using exclusions.```
**Why:** Handling "Dependency Hell" by brute force.

---

### 2. Reflection-based Class Loading```java
// ❌ Loading classes from dynamic paths outside the classpath
URLClassLoader child = new URLClassLoader(
    new URL[] {new URL("file:/ext/lib/plugin.jar")},
    this.getClass().getClassLoader()
);
```
**Why:** Implementing a plugin system without a proper framework (like SPI or OSGi).

---

### 3. System Classpath Injection```bash
# ❌ Running the app with a massive -cp /lib/*:./bin# where files are placed manually by a script.```
**Why:** Bypassing Maven/Gradle's artifact management for "simplicity".

---

### 4. `provided` Scope for Local Hacks```xml
<!-- ❌ Marking a dependency as provided and then placing
     a modified version of that JAR in the server's lib folder -->
<dependency>
    <groupId>com.external</groupId>
    <artifactId>broken-lib</artifactId>
    <scope>provided</scope>
</dependency>
```
**Why:** Changing behavior without updating the code.

---

## ✅ Java Cures
### Cure 1: Maven/Gradle ExclusionsResolve version conflicts correctly in the manifest.
```xml
<dependency>
    <groupId>com.foo</groupId>
    <artifactId>bar</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.bad</groupId>
            <artifactId>lib</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

### Cure 2: Java Service Provider Interface (SPI)Use the standard `ServiceLoader` for plugin architectures.

### Cure 3: Modular Java (Project Jigsaw)Use `module-info.java` to explicitly declare what is exported and what is required.

---

## 🔍 Detection```bash
# Check for custom ClassLoadersgrep -rn "ClassLoader" .

# Check start scripts for hardcoded absolute paths in -cpgrep -rn "\-cp" scripts/
```

---

## 📏 Rule> The `mvn clean install` or `./gradlew build` command should be the ONLY source of truth for how the application's classpath is constructed.
