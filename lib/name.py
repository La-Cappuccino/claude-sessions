#!/usr/bin/env python3
"""Auto-name unnamed Claude Code sessions based on their content."""

import json
import os
import re
import sys
import glob


def extract_name_from_messages(messages):
    """Generate a descriptive name from user messages using heuristics."""
    if not messages:
        return None

    combined = " ".join(messages[:3])  # First 3 user messages
    combined_lower = combined.lower()

    # Extract action verbs
    verbs = []
    verb_patterns = [
        (r'\b(fix|fixing|fixed)\b', 'Fix'),
        (r'\b(build|building|built)\b', 'Build'),
        (r'\b(deploy|deploying|deployed)\b', 'Deploy'),
        (r'\b(create|creating|created)\b', 'Create'),
        (r'\b(add|adding|added)\b', 'Add'),
        (r'\b(update|updating|updated)\b', 'Update'),
        (r'\b(refactor|refactoring|refactored)\b', 'Refactor'),
        (r'\b(debug|debugging|debugged)\b', 'Debug'),
        (r'\b(test|testing|tested)\b', 'Test'),
        (r'\b(install|installing|installed)\b', 'Install'),
        (r'\b(configure|configuring|configured|config|setup|set up)\b', 'Configure'),
        (r'\b(migrate|migrating|migrated|migration)\b', 'Migrate'),
        (r'\b(implement|implementing|implemented)\b', 'Implement'),
        (r'\b(remove|removing|removed|delete|deleting|deleted)\b', 'Remove'),
        (r'\b(research|researching|researched|explore|exploring)\b', 'Research'),
        (r'\b(review|reviewing|reviewed)\b', 'Review'),
        (r'\b(download|downloading|downloaded)\b', 'Download'),
        (r'\b(write|writing|wrote)\b', 'Write'),
        (r'\b(design|designing|designed)\b', 'Design'),
        (r'\b(optimize|optimizing|optimized)\b', 'Optimize'),
        (r'\b(clean|cleaning|cleaned|cleanup)\b', 'Cleanup'),
    ]

    for pattern, verb in verb_patterns:
        if re.search(pattern, combined_lower):
            verbs.append(verb)
            break  # Take the first matching verb

    # Extract file paths / extensions
    file_matches = re.findall(r'[\w/.-]+\.\w{1,5}', combined)
    file_context = ""
    if file_matches:
        # Get the most interesting file
        for f in file_matches:
            base = os.path.basename(f)
            if base not in ('.md', '.json', '.txt'):
                file_context = base
                break

    # Extract tech keywords
    tech_keywords = []
    tech_patterns = [
        (r'\b(react|nextjs|next\.js|next js)\b', 'Next.js'),
        (r'\b(tailwind|tailwindcss)\b', 'Tailwind'),
        (r'\b(supabase)\b', 'Supabase'),
        (r'\b(docker|container)\b', 'Docker'),
        (r'\b(api|endpoint|route)\b', 'API'),
        (r'\b(database|db|sql|postgres|postgresql)\b', 'Database'),
        (r'\b(auth|authentication|login|oauth)\b', 'Auth'),
        (r'\b(css|styles?|styling)\b', 'Styles'),
        (r'\b(i18n|translation|intl|locale)\b', 'i18n'),
        (r'\b(seo|meta|sitemap)\b', 'SEO'),
        (r'\b(gdpr|privacy|cookie)\b', 'GDPR'),
        (r'\b(ci|cd|pipeline|github actions)\b', 'CI/CD'),
        (r'\b(typescript|ts)\b', 'TypeScript'),
        (r'\b(python|py)\b', 'Python'),
        (r'\b(bash|shell|script)\b', 'Shell'),
        (r'\b(git|github|pr|pull request)\b', 'Git'),
        (r'\b(vps|server|deploy|coolify)\b', 'Server'),
        (r'\b(email|smtp|newsletter)\b', 'Email'),
        (r'\b(ui|ux|component|layout|design)\b', 'UI'),
        (r'\b(cron|schedule|job)\b', 'Cron'),
    ]

    for pattern, keyword in tech_patterns:
        if re.search(pattern, combined_lower):
            tech_keywords.append(keyword)
            if len(tech_keywords) >= 2:
                break

    # Build name
    parts = []
    if verbs:
        parts.append(verbs[0])
    if tech_keywords:
        parts.extend(tech_keywords[:2])
    if file_context and len(parts) < 3:
        parts.append(file_context)

    # Fallback: use first ~5 words of first message
    if not parts:
        words = messages[0].split()[:6]
        name = " ".join(words)
        if len(name) > 50:
            name = name[:47] + "..."
        return name

    return " ".join(parts)


def get_user_messages(jsonl_path):
    """Get first N user text messages from a session."""
    messages = []
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "user":
                        msg = data.get("message", {})
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            text = None
                            if isinstance(content, str) and content.strip():
                                text = content.strip()
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        text = c["text"].strip()
                                        break
                            if text:
                                messages.append(text)
                                if len(messages) >= 3:
                                    return messages
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception:
        pass
    return messages


def has_custom_title(jsonl_path):
    """Check if session already has a custom title."""
    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                if '"custom-title"' in line:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "custom-title":
                            return True
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return False


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    home = os.path.expanduser("~")
    base = os.path.join(home, ".claude", "projects")

    unnamed = []
    named_count = 0
    skipped_count = 0

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    for proj_dir in glob.glob(f"{base}/*/"):
        for jsonl_path in glob.glob(f"{proj_dir}*.jsonl"):
            if has_custom_title(jsonl_path):
                skipped_count += 1
                continue

            messages = get_user_messages(jsonl_path)
            if not messages:
                continue

            name = extract_name_from_messages(messages)
            if not name:
                continue

            session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
            unnamed.append({
                "path": jsonl_path,
                "id": session_id,
                "name": name,
                "preview": messages[0][:80],
            })

    if not unnamed:
        print(f"\n{GREEN}All sessions already have names.{RESET} ({skipped_count} named)")
        return

    print(f"\n{BOLD}Auto-naming sessions{RESET}")
    print(f"  Already named: {skipped_count}")
    print(f"  To name: {len(unnamed)}")
    print()

    if dry_run or not force:
        for s in unnamed[:30]:  # Show first 30
            print(f"  {CYAN}{s['id'][:8]}...{RESET} -> {GREEN}{s['name']}{RESET}")
            print(f"           {DIM}{s['preview'][:60]}{RESET}")
        if len(unnamed) > 30:
            print(f"  {DIM}... and {len(unnamed) - 30} more{RESET}")
        print()

        if not force:
            print(f"{YELLOW}Dry run.{RESET} Run with {BOLD}--force{RESET} to write names.")
            return

    # Write names
    for s in unnamed:
        try:
            entry = json.dumps({
                "type": "custom-title",
                "customTitle": s["name"],
            })
            with open(s["path"], "a") as f:
                f.write("\n" + entry)
            named_count += 1
        except Exception as e:
            print(f"  Error naming {s['id']}: {e}")

    print(f"\n{GREEN}Named {named_count} sessions.{RESET}")


if __name__ == "__main__":
    main()
