# Agent IA — Revue d'architecture DevOps

Script Python autonome qui :

1. Lit le README d'un dépôt (n'importe lequel, passé en argument).
2. Construit un prompt demandant à un modèle IA d'agir comme un
   ingénieur DevOps senior.
3. Affiche un résumé structuré de l'architecture du dépôt ainsi qu'une
   liste de risques (sévérité + recommandation).

Le script parle à n'importe quel serveur de modèle **local** exposant une
API compatible OpenAI : [Ollama](https://ollama.com), [LM Studio](https://lmstudio.ai),
`llama.cpp server`, `text-generation-webui`, vLLM, etc.

## Installation

```bash
pip install -r requirements.txt
```

Démarre ton serveur local (exemple avec Ollama) :

```bash
ollama run llama3
```

## Utilisation

```bash
python devops_review_agent.py /chemin/vers/le/repo --model llama3
```

Par défaut, le script tape sur `http://localhost:11434/v1` (API Ollama).
Pour un autre serveur, précise l'URL :

```bash
# LM Studio
python devops_review_agent.py . --model mon-modele --base-url http://localhost:1234/v1

# ou via variables d'environnement
export LOCAL_AI_BASE_URL="http://localhost:1234/v1"
export LOCAL_AI_MODEL="mon-modele"
python devops_review_agent.py .
```

Options utiles :

- `--model` : nom du modèle tel que connu par ton serveur local (défaut: `llama3`).
- `--base-url` : URL de l'API compatible OpenAI de ton serveur (défaut: Ollama).
- `--api-key` : clé API si ton serveur local en exige une.
- `--output rapport.md` : sauvegarde le rapport en plus de l'affichage.
- `--tree-depth 3` : profondeur de l'arborescence donnée en contexte au modèle.

Sans argument, le script analyse le dépôt courant (`.`).
