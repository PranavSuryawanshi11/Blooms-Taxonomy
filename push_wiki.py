"""
BloomCraft AI - GitHub Wiki Automated Synchronization Tool
Uploads all documentation in the wiki/ directory directly to the GitHub Wiki git repository.
"""

import os
import sys
import shutil
import subprocess
import tempfile

WIKI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki")
WIKI_REPO_URL = "https://github.com/PranavSuryawanshi11/Blooms-Taxonomy.wiki.git"

def main():
    print("=" * 70)
    print(" BloomCraft AI - GitHub Wiki Deployer")
    print("=" * 70)

    if not os.path.exists(WIKI_DIR):
        print(f"Error: Wiki directory '{WIKI_DIR}' does not exist.")
        sys.exit(1)

    wiki_files = [f for f in os.listdir(WIKI_DIR) if f.endswith(".md")]
    print(f"Found {len(wiki_files)} Wiki pages in 'wiki/' directory:")
    for f in wiki_files:
        print(f"  - {f}")

    print(f"\nChecking connection to GitHub Wiki ({WIKI_REPO_URL})...")
    check_cmd = subprocess.run(["git", "ls-remote", WIKI_REPO_URL], capture_output=True, text=True)

    if check_cmd.returncode != 0:
        print("\n" + "!" * 70)
        print(" GitHub Wiki is not initialized yet!")
        print("!" * 70)
        print("GitHub creates the '.wiki.git' repository only AFTER you click")
        print("'Create the first page' once on the GitHub website.\n")
        print("To initialize it:")
        print("  1. Open your browser and go to:")
        print("     https://github.com/PranavSuryawanshi11/Blooms-Taxonomy/wiki")
        print("  2. Click the green 'Create the first page' button.")
        print("  3. Click 'Save page' (any title/content is fine).")
        print("  4. Re-run: python push_wiki.py\n")
        print("As soon as you do this, running 'python push_wiki.py' will automatically")
        print("upload all 8 complete documentation pages, sidebar, and footer to GitHub!")
        print("=" * 70)
        sys.exit(1)

    # Wiki repo exists on GitHub! Let's clone, sync, commit, and push.
    temp_dir = tempfile.mkdtemp(prefix="bloomcraft_wiki_")
    try:
        print(f"\nCloning GitHub Wiki into temporary staging area...")
        subprocess.run(["git", "clone", WIKI_REPO_URL, temp_dir], check=True)

        # Copy all wiki files to clone
        for f in wiki_files:
            src = os.path.join(WIKI_DIR, f)
            dst = os.path.join(temp_dir, f)
            shutil.copy2(src, dst)
            print(f"  Synced: {f}")

        # Git add, commit, push
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        status_check = subprocess.run(["git", "status", "--porcelain"], cwd=temp_dir, capture_output=True, text=True)

        if not status_check.stdout.strip():
            print("\nGitHub Wiki is already up-to-date with all local pages!")
            return

        subprocess.run(["git", "commit", "-m", "docs: update complete BloomCraft AI technical wiki"], cwd=temp_dir, check=True)
        print("\nPushing updated pages to GitHub Wiki...")
        push_res = subprocess.run(["git", "push", "origin", "master"], cwd=temp_dir, capture_output=True, text=True)

        if push_res.returncode != 0:
            # Try main branch if master failed
            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=temp_dir, capture_output=True, text=True)

        if push_res.returncode == 0:
            print("\n" + "=" * 70)
            print(" SUCCESS! GitHub Wiki has been updated successfully!")
            print(" Visit your wiki live at:")
            print(" https://github.com/PranavSuryawanshi11/Blooms-Taxonomy/wiki")
            print("=" * 70)
        else:
            print("Failed to push to wiki repository:", push_res.stderr)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
