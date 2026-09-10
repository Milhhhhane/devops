#!/usr/bin/env python3
"""Agent IA qui lit le README d'un repo et fait générer une revue d'architecture
et des risques par un modèle IA local, en lui faisant jouer le rôle d'un
ingénieur DevOps senior.

Fonctionne avec n'importe quel serveur de modèle local exposant une API
compatible OpenAI (Ollama, LM Studio, llama.cpp server, text-generation-webui,
vLLM, ...).

Usage:
    python devops_review_agent.py /chemin/vers/le/repo --model llama3
    python devops_review_agent.py . --model mistral --base-url http://localhost:1234/v1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from openai import OpenAI, APIConnectionError, APIStatusError, AuthenticationError, NotFoundError, RateLimitError

README_CANDIDATES = [
    "README.md", "readme.md", "Readme.md",
    "README.rst", "README.txt", "README",
]

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".venv", "venv", ".terraform", ".vagrant", "dist", "build",
}

DEFAULT_BASE_URL = "http://localhost:11434/v1"  # Ollama par défaut

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


def run_review(repo_path: Path, model: str, base_url: str, api_key: str, max_tokens: int, tree_depth: int) -> str:
    readme_path = find_readme(repo_path)
    readme_content = readme_path.read_text(encoding="utf-8", errors="replace")
    tree = build_repo_tree(repo_path, max_depth=tree_depth)

    client = OpenAI(base_url=base_url, api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(readme_content, tree)},
            ],
        )
    except AuthenticationError:
        print("Erreur : authentification refusée par le serveur local (clé API attendue ?).", file=sys.stderr)
        sys.exit(1)
    except NotFoundError:
        print(f"Erreur : modèle introuvable sur le serveur ({model}). "
              f"Vérifie qu'il est bien chargé/installé.", file=sys.stderr)
        sys.exit(1)
    except RateLimitError:
        print("Erreur : le serveur local est surchargé, réessaie dans quelques instants.", file=sys.stderr)
        sys.exit(1)
    except APIConnectionError:
        print(f"Erreur : impossible de joindre le serveur IA local à {base_url}. "
              f"Vérifie qu'il est bien démarré.", file=sys.stderr)
        sys.exit(1)
    except APIStatusError as e:
        print(f"Erreur API ({e.status_code}) : {e.message}", file=sys.stderr)
        sys.exit(1)

    return response.choices[0].message.content or ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_path", nargs="?", default=".", help="Chemin vers le dépôt à analyser (défaut: .)")
    parser.add_argument(
        "--model",
        default=os.environ.get("LOCAL_AI_MODEL", "llama3"),
        help="Nom du modèle tel que connu par ton serveur local (défaut: llama3, ou $LOCAL_AI_MODEL)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LOCAL_AI_BASE_URL", DEFAULT_BASE_URL),
        help=f"URL de l'API compatible OpenAI de ton serveur local (défaut: {DEFAULT_BASE_URL}, ou $LOCAL_AI_BASE_URL). "
             "Ollama: http://localhost:11434/v1 — LM Studio: http://localhost:1234/v1",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LOCAL_AI_API_KEY", "not-needed"),
        help="Clé API si ton serveur local en exige une (défaut: 'not-needed', ou $LOCAL_AI_API_KEY)",
    )
    parser.add_argument("--max-tokens", type=int, default=4096, help="Nombre max de tokens en sortie")
    parser.add_argument("--tree-depth", type=int, default=2, help="Profondeur de l'arborescence donnée en contexte")
    parser.add_argument("--output", type=Path, default=None, help="Fichier où sauvegarder le rapport (en plus de l'affichage)")
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.is_dir():
        print(f"Erreur : {repo_path} n'est pas un dossier valide.", file=sys.stderr)
        sys.exit(1)

    try:
        report = run_review(repo_path, args.model, args.base_url, args.api_key, args.max_tokens, args.tree_depth)
    except FileNotFoundError as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)

    print(report)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"\n(Rapport sauvegardé dans {args.output})", file=sys.stderr)


if __name__ == "__main__":
    main()
