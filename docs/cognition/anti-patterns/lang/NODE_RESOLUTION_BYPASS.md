# Resolution Bypass — Node.js / TypeScript
> Parent: [`RESOLUTION_BYPASS.md`](../RESOLUTION_BYPASS.md)

---

## ❌ Node-Specific Hacks
### 1. Relative Import Hell```typescript
// ❌ Navigating the tree with deep relative paths
import { DB } from "../../../../../config/database";
```
**Why:** The project has grown but the directory structure wasn't modularized. Moving any file breaks the entire system.

---

### 2. `module-alias` or `NODE_PATH` Runtime Hacks```javascript
// ❌ Overriding resolution logic at startup
require('module-alias/register');
// OR
process.env.NODE_PATH = './src';
```
**Why:** Developer wants "cleaner" imports but doesn't want to configure the build tool or package manager correctly. This is invisible to static analysis.

---

### 3. Manual `node_modules` Manipulation```bash
# ❌ Manually deleting/editing files inside node_modules# and expecting the build to persist those changes.```
**Why:** "I just need to change this one line in the lib."

---

### 4. Symlink Magic (Manual)```bash
# ❌ Manually creating ln -s inside the source tree# to make imports "easier".```
**Why:** Avoids configuring proper workspaces or aliases. Breaks on Windows or in different CI environments.

---

## ✅ Node/TS Cures
### Cure 1: TSConfig Paths (TypeScript)```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": "src",
    "paths": {
      "@core/*": ["core/*"],
      "@shared/*": ["shared/*"]
    }
  }
}
```
```typescript
import { DB } from "@core/database"; // ✅ Safe and statically typed
```

### Cure 2: NPM/Yarn/Pnpm WorkspacesFor monorepos:
```json
// package.json
{
  "workspaces": [
    "packages/*"
  ]
}
```
Then import packages by their real names: `import { helper } from "@my-org/shared"`.

### Cure 3: `patch-package`If you MUST modify a library, use `patch-package` to create a deterministic `.patch` file that is applied during `npm install`.

---

## 🔍 Detection```bash
# Search for process.env.NODE_PATHgrep -rn "NODE_PATH" .

# Search for module-aliasgrep -rn "module-alias" .
```

---

## 📏 Rule> If your IDE (VSCode/WebStorm) shows a "Module not found" error or red squiggly lines on an import that actually works when you run the app, you are using a Resolution Bypass.
