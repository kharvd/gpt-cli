# gpt-cli

Votre interface en ligne de commande pour ChatGPT, Claude et Bard. Plus besoin de jongler avec les onglets, tout se passe ici, dans votre terminal !

![screenshot](https://github.com/kharvd/gpt-cli/assets/466920/ecbcccc4-7cfa-4c04-83c3-a822b6596f01)

## Fonctionnalités Magiques

### **Bientôt disponible** - Support de l'Interpréteur de Code https://github.com/kharvd/gpt-cli/pull/37

- **Interface en Ligne de Commande**: Discutez avec ChatGPT ou Claude directement depuis votre terminal. C'est comme avoir un génie dans une bouteille, mais la bouteille, c'est votre console !
- **Personnalisation du Modèle**: Modifiez le modèle par défaut, la température et les valeurs top_p pour chaque assistant. Prenez les rênes de l'IA !
- **Suivi de l'Utilisation**: Gardez un œil sur votre consommation d'API avec le comptage des jetons et les informations sur les prix. Pas de mauvaises surprises !
- **Raccourcis Clavier**: Utilisez Ctrl-C, Ctrl-D et Ctrl-R pour une gestion de conversation et une saisie facilitées. Vos doigts vous remercieront !
- **Saisie Multi-Ligne**: Passez en mode multi-ligne pour les requêtes ou conversations plus complexes. Exprimez-vous sans limites !
- **Support Markdown**: Activez ou désactivez le formatage markdown pour les sessions de chat. À vous de choisir le look !
- **Messages Prédéfinis**: Configurez des messages prédéfinis pour vos assistants personnalisés afin d'établir un contexte ou des scénarios de jeu de rôle. Donnez une personnalité à votre IA !
- **Assistants Multiples**: Basculez facilement entre différents assistants, y compris les assistants généraux, de développement et personnalisés définis dans le fichier de configuration. Un assistant pour chaque humeur !
- **Configuration Flexible**: Définissez vos assistants, les paramètres du modèle et votre clé API dans un fichier de configuration YAML. La personnalisation à son apogée !

## Installation

Cette installation suppose que vous avez une machine Linux/OSX avec Python et pip prêts à l'emploi.
```bash
pip install gpt-command-line
```

Installez la dernière version depuis la source (pour les aventuriers !) :
```bash
pip install git+https://github.com/kharvd/gpt-cli.git
```

Ou installez en clonant manuellement le dépôt (pour les puristes !) :
```bash
git clone https://github.com/kharvd/gpt-cli.git
cd gpt-cli
pip install .
```

Ajoutez la clé API OpenAI à votre fichier `.bashrc` (à la racine de votre dossier personnel).
Dans cet exemple, nous utilisons nano, mais votre éditeur de texte préféré fera aussi l'affaire.

```
nano ~/.bashrc
export OPENAI_API_KEY=<votre_clé_ici>
```

Lancez l'outil et que la magie opère !

```
gpt
```

Vous pouvez également utiliser un fichier `gpt.yml` pour la configuration. Consultez la section [Configuration](README.fr.md#Configuration) ci-dessous pour en savoir plus.

## Utilisation

Assurez-vous de définir la variable d'environnement `OPENAI_API_KEY` avec votre clé API OpenAI (ou placez-la dans le fichier `~/.config/gpt-cli/gpt.yml` comme décrit ci-dessous).

```
usage: gpt [-h] [--no_markdown] [--model MODEL] [--temperature TEMPERATURE] [--top_p TOP_P]
              [--log_file LOG_FILE] [--log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
              [--prompt PROMPT] [--execute EXECUTE] [--no_stream]
              [{dev,general,bash}]

Lancez une session de chat avec ChatGPT. Consultez https://github.com/kharvd/gpt-cli pour plus d'informations.

arguments positionnels:
  {dev,general,bash}
                        Le nom de l'assistant à utiliser. `general` (par défaut) est un assistant
                        généralement utile, `dev` est un assistant de développement logiciel avec des
                        réponses plus courtes. Vous pouvez spécifier vos propres assistants dans le
                        fichier de configuration ~/.config/gpt-cli/gpt.yml. Consultez le README pour
                        plus d'informations.

arguments optionnels:
  -h, --help            afficher ce message d'aide et quitter
  --no_markdown         Désactiver le formatage markdown dans la session de chat.
  --model MODEL         Le modèle à utiliser pour la session de chat. Remplace le modèle par défaut
                        défini pour l'assistant.
  --temperature TEMPERATURE
                        La température à utiliser pour la session de chat. Remplace la température
                        par défaut définie pour l'assistant.
  --top_p TOP_P         Le top_p à utiliser pour la session de chat. Remplace le top_p par défaut
                        défini pour l'assistant.
  --log_file LOG_FILE   Le fichier dans lequel écrire les logs. Supporte les codes de format strftime.
  --log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Le niveau de log à utiliser
  --prompt PROMPT, -p PROMPT
                        Si spécifié, ne démarrera pas de session de chat interactive et affichera
                        plutôt la réponse sur la sortie standard avant de quitter. Peut être spécifié
                        plusieurs fois. Utilisez `-` pour lire le prompt depuis l'entrée standard.
                        Implique --no_markdown.
  --execute EXECUTE, -e EXECUTE
                        Si spécifié, transmet le prompt à l'assistant et permet à l'utilisateur de
                        modifier la commande shell produite avant de l'exécuter. Implique --no_stream.
                        Utilisez `-` pour lire le prompt depuis l'entrée standard.
  --no_stream           Si spécifié, ne diffusera pas la réponse sur la sortie standard. Ceci est
                        utile si vous souhaitez utiliser la réponse dans un script. Ignoré lorsque
                        l'option --prompt n'est pas spécifiée.
  --no_price            Désactiver l'enregistrement des prix.
```

Tapez `:q` ou Ctrl-D pour quitter, `:c` ou Ctrl-C pour effacer la conversation, `:r` ou Ctrl-R pour régénérer la dernière réponse.
Pour entrer en mode multi-ligne, tapez une barre oblique inversée `\` suivie d'une nouvelle ligne. Quittez le mode multi-ligne en appuyant sur ESC puis Entrée. C'est un peu comme un code secret !

Vous pouvez remplacer les paramètres du modèle en utilisant les arguments `--model`, `--temperature` et `--top_p` à la fin de votre prompt. Par exemple :

```
> Quelle est le sens de la vie ? --model gpt-4 --temperature 2.0
Le sens de la vie est subjectif et peut être différent pour diverses êtres humains et unique-phil ethics.org/cultuties-/ it that reson/bdstals89im3_jrf334;mvs-bread99ef=g22me
```

L'assistant `dev` est instruit pour être un expert en développement logiciel et fournir des réponses courtes et précises. Direct au but !

```bash
$ gpt dev
```

L'assistant `bash` est instruit pour être un expert en script bash et ne fournir que des commandes bash. Utilisez l'option `--execute` pour exécuter les commandes. Il fonctionne mieux avec le modèle `gpt-4`. Demandez et vous recevrez... une commande bash !

```bash
gpt bash -e "Comment lister les fichiers dans un répertoire ?"
```

Cela vous invitera à modifier la commande dans votre `$EDITOR` avant de l'exécuter. Vous gardez le contrôle !

## Configuration

Vous pouvez configurer les assistants dans le fichier de configuration `~/.config/gpt-cli/gpt.yml`. Le fichier est un fichier YAML avec la structure suivante (voir aussi [config.py](./gptcli/config.py)) :

```yaml
default_assistant: <nom_assistant>
markdown: False
openai_api_key: <clé_api_openai>
anthropic_api_key: <clé_api_anthropic>
log_file: <chemin>
log_level: <DEBUG|INFO|WARNING|ERROR|CRITICAL>
assistants:
  <nom_assistant>:
    model: <nom_modèle>
    temperature: <température>
    top_p: <top_p>
    messages:
      - { role: <rôle>, content: <message> }
      - ...
  <nom_assistant>:
    ...
```

Vous pouvez également remplacer les paramètres des assistants prédéfinis. Faites comme chez vous !

Vous pouvez spécifier l'assistant par défaut à utiliser en définissant le champ `default_assistant`. Si vous ne le spécifiez pas, l'assistant par défaut est `general`. Vous pouvez également spécifier le `model`, la `temperature` et le `top_p` à utiliser pour l'assistant. Si vous ne les spécifiez pas, les valeurs par défaut sont utilisées. Ces paramètres peuvent également être remplacés par les arguments de la ligne de commande. Flexibilité, on vous dit !

Exemple :

```yaml
default_assistant: dev
markdown: True
openai_api_key: <votre_clé_openai_ici>
assistants:
  pirate:
    model: gpt-4
    temperature: 1.0
    messages:
      - { role: system, content: "Tu es un pirate." }
```

```
$ gpt pirate

> Yo ho ho !
À l'abordage, matelot ! Qu'est-ce qui t'amène par chez nous ? Que tu cherches un trésor ou l'aventure, nous voguerons ensemble sur les sept mers. Prépare ta carte et ta boussole, car un long voyage nous attend !
```

## Autres Chatbots (Amis de l'IA)

### Anthropic Claude

Pour utiliser Claude, vous devez avoir une clé API d'[Anthropic](https://console.anthropic.com/) (il y a actuellement une liste d'attente pour l'accès à l'API). Après avoir obtenu la clé API, vous pouvez ajouter une variable d'environnement :

```bash
export ANTHROPIC_API_KEY=<votre_clé_ici>
```

ou une ligne de configuration dans `~/.config/gpt-cli/gpt.yml` :

```yaml
anthropic_api_key: <votre_clé_ici>
```

Maintenant, vous devriez pouvoir exécuter `gpt` avec `--model claude-v1` ou `--model claude-instant-v1`. Claude, à votre service !

```bash
gpt --model claude-v1
```

### Google Bard (PaLM 2)
Comme pour Claude, définissez la clé API Google :

```bash
export GOOGLE_API_KEY=<votre_clé_ici>
```
ou une ligne de configuration :
```yaml
google_api_key: <votre_clé_ici>
```

Exécutez `gpt` avec le bon modèle. Bard est dans la place !
```bash
gpt --model chat-bison-001
```
