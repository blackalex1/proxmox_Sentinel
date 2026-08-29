"""Git Repository & Branch Manager for Sentinel Controller."""

from __future__ import annotations

import os
from typing import Optional

from .common import (
    BOLD,
    CYAN,
    GREEN,
    RESET,
    YELLOW,
    log_error,
    log_info,
    log_success,
    log_warn,
    run_command,
)


class GitManager:
    """Manages Git updates, commit pulls, branch resolution and changelog display."""

    def __init__(self, project_dir: str, proxy_url: Optional[str] = None) -> None:
        self.project_dir = project_dir
        self.proxy_url = proxy_url

    def update_codebase(self, branch: str = "main", silent_if_uptodate: bool = False) -> bool:
        """Updates local Git repository with stashing, conflict protection and changelog output."""
        if not os.path.isdir(os.path.join(self.project_dir, ".git")):
            if not silent_if_uptodate:
                log_warn("Каталог .git не найден. Пропуск обновления через Git.")
            return False

        if not silent_if_uptodate:
            log_info(f"Проверка обновлений кодовой базы Git (ветка: {branch})...")

        # Stash local uncommitted changes if any
        stashed = False
        status_proc = run_command(["git", "status", "--porcelain"], cwd=self.project_dir, capture=True, check=False)
        if status_proc.stdout.strip():
            log_info("Сохранение локальных изменений во временный стек (git stash)...")
            stash_res = run_command(["git", "stash"], cwd=self.project_dir, check=False)
            if stash_res.returncode == 0:
                stashed = True

        git_env = {}
        if self.proxy_url:
            git_env["http_proxy"] = self.proxy_url
            git_env["https_proxy"] = self.proxy_url
            git_env["HTTP_PROXY"] = self.proxy_url
            git_env["HTTPS_PROXY"] = self.proxy_url

        old_commit = ""
        try:
            old_commit = run_command(["git", "rev-parse", "HEAD"], cwd=self.project_dir, capture=True, check=False).stdout.strip()
        except Exception:
            pass

        # Try updating from origin
        pull_success = False
        try:
            fetch_cmd = ["git", "-c", "http.connectTimeout=6", "-c", "http.timeout=15", "fetch", "origin", branch]
            res = run_command(fetch_cmd, cwd=self.project_dir, env=git_env, capture=True, check=False, timeout=20.0)
            if res.returncode == 0:
                merge_res = run_command(["git", "reset", "--hard", "FETCH_HEAD"], cwd=self.project_dir, capture=True, check=False, timeout=10.0)
                if merge_res.returncode == 0:
                    pull_success = True
        except Exception:
            pass

        if not pull_success:
            log_warn("Не удалось получить обновления из Git-репозитория.")
            if stashed:
                try:
                    run_command(["git", "stash", "pop"], cwd=self.project_dir, check=False)
                except Exception:
                    pass
            return False

        # Drop stash on clean reset so old local files do not overwrite fresh code
        if stashed:
            try:
                run_command(["git", "stash", "drop"], cwd=self.project_dir, check=False)
            except Exception:
                pass

        new_commit = ""
        try:
            new_commit = run_command(["git", "rev-parse", "HEAD"], cwd=self.project_dir, capture=True, check=False).stdout.strip()
        except Exception:
            pass

        if old_commit and new_commit and old_commit != new_commit:
            log_success(f"Кодовая база успешно обновлена: {BOLD}{old_commit[:7]} -> {new_commit[:7]}{RESET}")
            try:
                log_commits = run_command(["git", "log", "--color=always", "--pretty=format:  %C(yellow)•%C(reset) %C(bold yellow)%h%C(reset) %C(bold white)%s%C(reset) %C(cyan)(%cr)%C(reset)", f"{old_commit}..{new_commit}"], cwd=self.project_dir, capture=True, check=False).stdout.strip()
                if log_commits:
                    print("\n" + "=" * 60)
                    print(f"{BOLD}📝 СПИСОК ИЗМЕНЕНИЙ (CHANGELOG {old_commit[:7]}..{new_commit[:7]}):{RESET}")
                    print("=" * 60)
                    print(log_commits)
                    print("=" * 60)
                log_diff = run_command(["git", "diff", "--stat", "--color=always", f"{old_commit}..{new_commit}"], cwd=self.project_dir, capture=True, check=False).stdout.strip()
                if log_diff:
                    print(f"\n{log_diff}\n")
            except Exception:
                pass
            return True
        else:
            if not silent_if_uptodate:
                log_success("Кодовая база уже актуальна (Already up to date).")
            return False
