# ⚙️ STEP 3 — Configure .spec.config

**Goal:** Point `.spec.config` to sdd-harness (just 2 lines!)
**Duration:** 2 minutes
**Complexity:** Simple (edit 1 file)
**Prerequisites:** Step 2 complete (templates copied)
**Note:** You'll add `adoption_level` in STEP 6 after answering intention questions

---

## 📅 Where Are You?

You have:

- ✅ Project directories created (Step 1)
- ✅ Template files copied (Step 2)
- ❓ Need to edit `.spec.config` to point to sdd-harness

You're about to:

- Edit 1 file (`.spec.config`)
- Configure 2 variables (`spec_path` now, `adoption_level` in STEP 6)
- Move to Step 4 (validation)

---

## 🔍 Understanding .spec.config

`.spec.config` is a simple configuration file that tells your project where the SDD framework lives.

**Format:** INI (simple key=value)

**Now (STEP 3):**

```ini
[spec]
spec_path = ../sdd-harness
```

**Later (STEP 6):** You'll add:

```ini
[spec]
spec_path = ../sdd-harness
adoption_level = lite
```

(or `adoption_level = full`)

---

## ✏️ How to Edit (STEP 3 Only)

### Option A: From Command Line

```bash
cd /path/to/your-project

# Open with nano (easy text editor)
nano .spec.config
```

Then edit:

```ini
[spec]
spec_path = ../sdd-harness
```

Save: `Ctrl+O`, then `Enter`, then `Ctrl+X`

### Option B: From VS Code

```bash
# Open in VS Code
code .spec.config
```

Edit the file to:

```ini
[spec]
spec_path = ../sdd-harness
```

Save: `Ctrl+S` or `Cmd+S`

### Option C: From Any Editor

Open `.spec.config` in your favorite editor and edit to:

```ini
[spec]
spec_path = ../sdd-harness
```

---

## ⚙️ Choosing the Right spec_path

### Case 1: sdd-harness is a Sibling Directory (Recommended)

Your directory structure:

```
home/
├── sdd-harness/     ← SDD framework
└── your-project/        ← Your project
    └── .spec.config
```

**Use:** `spec_path = ../sdd-harness`

### Case 2: sdd-harness is Elsewhere

Your directory structure:

```
/home/username/
├── dev/
│   ├── sdd-harness/
│   └── your-project/
│       └── .spec.config
```

**Use:** `spec_path = ../sdd-harness` (still works!)

### Case 3: sdd-harness is Far Away

Your directory structure:

```
/home/username/work/projects/myapp/
└── .spec.config

/opt/frameworks/sdd-harness/
└── (SDD framework here)
```

**Use:** `spec_path = /opt/frameworks/sdd-harness` (absolute path)

### Case 4: sdd-harness is in a Different Location

```bash
# Find where sdd-harness actually is
find ~ -type d -name "sdd-harness" 2>/dev/null
# Shows: /home/username/frameworks/sdd-harness

# Then use relative path from your project
# If your project is /home/username/my-project
# and sdd-harness is /home/username/frameworks/sdd-harness
# Use: spec_path = ../frameworks/sdd-harness
```

---

## ✅ Verify Configuration

After editing, verify it's correct:

```bash
cat .spec.config
```

Should show:

```ini
[spec]
spec_path = ../sdd-harness
```

Or if you used absolute path:

```ini
[spec]
spec_path = /path/to/sdd-harness
```

### Test the Path

```bash
# This shows what the script will see
cat .spec.config | grep spec_path | cut -d' ' -f3

# Should output:
# ../sdd-harness
# (or your absolute path)

# Then verify the path actually exists
cd $(cat .spec.config | grep spec_path | cut -d' ' -f3)
ls
# Should show: INTEGRATION/, EXECUTION/, docs/, templates/, etc.
```

---

## 🆘 Troubleshooting

### Issue: "No such file or directory"

```bash
# The spec_path you entered doesn't exist

# Solution 1: Find where sdd-harness really is
find ~ -type d -name "sdd-harness" 2>/dev/null

# Solution 2: Update .spec.config with correct path
nano .spec.config
# Edit spec_path to correct location
```

### Issue: ".spec.config not found"

```bash
# Did Step 2 copy work?

# Check if file exists
ls -la .spec.config

# If not, copy it manually
cp ../sdd-harness/INTEGRATION/templates/.spec.config .

# Then edit it
nano .spec.config
```

### Issue: Can't Edit File (Permission Denied)

```bash
# You don't have permission

# Solution: Change permissions
chmod +w .spec.config

# Then try editing again
nano .spec.config
```

---

## 📝 Example .spec.config Files

### Example 1: Sibling Directories

```ini
[spec]
# Points to ../sdd-harness (one level up, then sdd-harness folder)
spec_path = ../sdd-harness

# Alternative: absolute path
# spec_path = /home/sergio/dev/sdd-harness
```

### Example 2: With Comments

```ini
[spec]
# Framework source: https://github.com/user/sdd-harness
# This tells your project where to find PHASE 0, AGENT_HARNESS, etc.
spec_path = ../sdd-harness

# You can also use absolute path:
# spec_path = /opt/sdd-harness
```

---

## ✅ Ready for Step 4?

Once `.spec.config` is configured, proceed to:

**→ [STEP_4.md](./STEP_4.md)**

Run validation script to verify everything works.

---

## 🚀 What Happens Next

In Step 4, the validation script will:

1. Read `.spec.config`
2. Find sdd-harness at the specified `spec_path`
3. Create `.sdd/` infrastructure
4. Run VALIDATION_QUIZ to verify knowledge

---

**Estimated time:** 2 minutes
**Difficulty:** Very easy
**Next step:** Validate setup
