#!/usr/bin/env python3
"""Agent IA qui lit le README d'un repo et fait générer une revue d'architecture
et des risques par un modèle Claude, en lui faisant jouer le rôle d'un
ingénieur DevOps senior.

Usage:
    python devops_review_agent.py /chemin/vers/le/repo
    python devops_review_agent.py .  --model claude-opus-5 --output rapport.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import anthropic

README_CANDIDATES = [
    "README.md", "readme.md", "Readme.md",
    "README.rst", "README.txt", "README",
]

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".venv", "venv", ".terraform", ".vagrant", "dist", "build",
}

SYSTEM_PROMPT = """Tu es un ingénieur DevOps senior avec 15 ans d'expérience \
en infrastructure, conteneurisation, orchestration (Kubernetes), \
Infrastructure as Code (Terraform, Ansible) et CI/CD.

On te fournit le README et l'arborescence d'un dépôt git. À partir de ces \
seules informations, tu dois :

1. Résumer l'architecture du dépôt de façon structurée (composants, \
technologies utilisées, flux/dépendances entre les composants).
2. Lister les risques (sécurité, fiabilité, maintenabilité, scalabilité, \
processus) que tu identifies, chacun avec un niveau de sévérité \
(Élevé / Moyen / Faible) et une recommandation courte.

Réponds en français, au format Markdown, avec exactement ces deux sections :

## Résumé de l'architecture
## Liste des risques

Si une information est absente du README fourni, dis-le explicitement au \
lieu de l'inventer."""


def find_readme(repo_path: Path) -> Path:
    for name in README_CANDIDATES:
        candidate = repo_path / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Aucun README trouvé dans {repo_path}")


def build_repo_tree(repo_path: Path, max_depth: int = 2, max_lines: int = 300) -> str:
    lines: list[str] = []

    def walk(directory: Path, depth: int, prefix: str) -> None:
        if depth > max_depth or len(lines) >= max_lines:
            return
        try:
            entries = sorted(
                [e for e in directory.iterdir() if e.name not in EXCLUDED_DIRS and not e.name.startswith(".")],
                key=lambda e: (e.is_file(), e.name.lower()),
            )
        except PermissionError:
            return
        for entry in entries:
            if len(lines) >= max_lines:
                lines.append(f"{prefix}... (tronqué)")
                return
            lines.append(f"{prefix}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, depth + 1, prefix + "  ")

    walk(repo_path, 1, "")
    return "\n".join(lines)


def build_user_prompt(readme_content: str, tree: str) -> str:
    return f"""Arborescence du dépôt (profondeur limitée) :
```
{tree}
```

Contenu du README :
```
{readme_content}
```

Fais ta revue d'architecture et ta liste de risques en suivant le format demandé."""


def run_review(repo_path: Path, model: str, max_tokens: int, effort: str, tree_depth: int) -> str:
    readme_path = find_readme(repo_path)
    readme_content = readme_path.read_text(encoding="utf-8", errors="replace")
    tree = build_repo_tree(repo_path, max_depth=tree_depth)

    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": build_user_prompt(readme_content, tree)}],
        )
    except anthropic.AuthenticationError:
        print("Erreur : clé API invalide ou absente. Définis ANTHROPIC_API_KEY.", file=sys.stderr)
        sys.exit(1)
    except TypeError as e:
        if "authentication" in str(e).lower():
            print("Erreur : aucune méthode d'authentification trouvée. Définis ANTHROPIC_API_KEY "
                  "(ou connecte-toi avec `ant auth login`).", file=sys.stderr)
            sys.exit(1)
        raise
    except anthropic.PermissionDeniedError:
        print("Erreur : la clé API n'a pas les permissions nécessaires.", file=sys.stderr)
        sys.exit(1)
    except anthropic.NotFoundError:
        print(f"Erreur : modèle introuvable ({model}).", file=sys.stderr)
        sys.exit(1)
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "quelques secondes")
        print(f"Erreur : limite de débit atteinte, réessaie dans {retry_after}.", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIConnectionError:
        print("Erreur : impossible de joindre l'API Anthropic (réseau).", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"Erreur API ({e.status_code}) : {e.message}", file=sys.stderr)
        sys.exit(1)

    return "\n".join(block.text for block in response.content if block.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_path", nargs="?", default=".", help="Chemin vers le dépôt à analyser (défaut: .)")
    parser.add_argument("--model", default="claude-opus-5", help="Modèle Claude à utiliser (défaut: claude-opus-5)")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Nombre max de tokens en sortie")
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"], help="Niveau d'effort du modèle")
    parser.add_argument("--tree-depth", type=int, default=2, help="Profondeur de l'arborescence donnée en contexte")
    parser.add_argument("--output", type=Path, default=None, help="Fichier où sauvegarder le rapport (en plus de l'affichage)")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.is_dir():
        print(f"Erreur : {repo_path} n'est pas un dossier valide.", file=sys.stderr)
        sys.exit(1)

    try:
        report = run_review(repo_path, args.model, args.max_tokens, args.effort, args.tree_depth)
    except FileNotFoundError as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)

    print(report)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\n(Rapport sauvegardé dans {args.output})", file=sys.stderr)


if __name__ == "__main__":
    main()
