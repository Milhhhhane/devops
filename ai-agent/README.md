# Agent IA — Revue d'architecture DevOps

Script Python autonome qui :

1. Lit le README d'un dépôt (n'importe lequel, passé en argument).
2. Construit un prompt demandant à un modèle IA open source d'agir comme
   un ingénieur DevOps senior.
3. Affiche un résumé structuré de l'architecture du dépôt ainsi qu'une
   liste de risques (sévérité + recommandation).

Utilise [OpenRouter](https://openrouter.ai) par défaut (même API que celle
utilisée par opencode), qui expose des modèles open source (Llama, Mistral,
Qwen, ...) via une API compatible OpenAI. Le `--base-url` reste modifiable
si tu préfères pointer vers un autre serveur compatible OpenAI plus tard.

## Installation

```bash
pip install -r requirements.txt
```

Récupère une clé API sur https://openrouter.ai/keys puis :

```bash
export OPENROUTER_API_KEY="ta-clé"
```

## Utilisation

```bash
python devops_review_agent.py /chemin/vers/le/repo
```

Le modèle par défaut est `meta-llama/llama-3.3-70b-instruct:free` (gratuit
sur OpenRouter). Pour en choisir un autre, vois la liste sur
https://openrouter.ai/models :

```bash
python devops_review_agent.py . --model mistralai/mistral-7b-instruct:free
```

Options utiles :

- `--model` : slug du modèle OpenRouter à utiliser.
- `--base-url` : URL de l'API compatible OpenAI (défaut: OpenRouter).
- `--api-key` : clé API (défaut: `$OPENROUTER_API_KEY`).
- `--output rapport.md` : sauvegarde le rapport en plus de l'affichage.
- `--tree-depth 3` : profondeur de l'arborescence donnée en contexte au modèle.

Sans argument, le script analyse le dépôt courant (`.`).
