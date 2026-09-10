# Agent IA — Revue d'architecture DevOps

Script Python autonome qui :

1. Lit le README d'un dépôt (n'importe lequel, passé en argument).
2. Construit un prompt demandant à un modèle Claude d'agir comme un
   ingénieur DevOps senior.
3. Affiche un résumé structuré de l'architecture du dépôt ainsi qu'une
   liste de risques (sévérité + recommandation).

## Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="ta-clé"
```

## Utilisation

```bash
python devops_review_agent.py /chemin/vers/le/repo
```

Options utiles :

- `--model claude-opus-5` : modèle à utiliser (défaut).
- `--output rapport.md` : sauvegarde le rapport en plus de l'affichage.
- `--tree-depth 3` : profondeur de l'arborescence donnée en contexte au modèle.
- `--effort xhigh` : niveau d'effort du modèle (low|medium|high|xhigh|max).

Sans argument, le script analyse le dépôt courant (`.`).
