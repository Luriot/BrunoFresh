# Guide de Déploiement : De GitHub à Unraid

Ce guide détaille l'intégralité du processus pour compiler, publier et déployer BrunoFresh sur un serveur Unraid en utilisant GitHub Actions et le GitHub Container Registry (GHCR).

---

## 1. Déclenchement du Build (GitHub Actions)

L'application est configurée pour se "builder" et se publier automatiquement à chaque modification sur la branche principale.

1. Commit et push tes derniers changements sur la branche `main`.
2. Sur ton dépôt GitHub, va dans l'onglet **Actions**.
3. Tu verras le workflow **Build and Publish Container** s'exécuter.
4. Ce workflow réalise les actions suivantes :
   - Construit le frontend (React/Vite).
   - Construit le backend (Python/FastAPI) et y injecte le frontend.
   - Scanne l'image Docker pour trouver d'éventuelles vulnérabilités (Trivy).
   - Pousse l'image finale sur le registre Docker de GitHub : `ghcr.io`.

---

## 2. Rendre l'image publique sur GHCR (Très important)

Par défaut, GitHub rend les images Docker privées. Pour éviter de devoir configurer l'authentification Docker (Personal Access Token) dans Unraid, il est beaucoup plus simple de rendre le paquet public (ton application reste sécurisée par ton `APP_PASSCODE`).

1. Sur GitHub, va sur ton profil ou l'accueil de ton dépôt, puis clique sur **Packages** (généralement en bas à droite sur la page d'accueil du repo, ou dans l'onglet Packages de ton profil).
2. Sélectionne le package `brunofresh`.
3. Va dans **Package settings** (colonne de droite).
4. Dans la section *Danger Zone*, trouve **Change visibility** et passe le package en **Public**.

*Note: L'URL de ton image sera désormais `ghcr.io/TonNomDutilisateurGitHub/brunofresh:latest` (en minuscules).*

---

## 3. Configuration dans Unraid

Maintenant que l'image est disponible, on peut la déployer sur Unraid.

1. Ouvre l'interface web de ton Unraid.
2. Va dans l'onglet **Docker**.
3. Tout en bas de la page, clique sur le bouton **Add Container**.
4. Remplis les informations principales de la Template :
   - **Name:** `BrunoFresh`
   - **Repository:** `ghcr.io/TonNomDutilisateurGitHub/brunofresh:latest` *(N'oublie pas de remplacer par ton nom d'utilisateur, tout en minuscules).*
   - **Network Type:** `Bridge`

### Ajouter les Mappings (Ports, Volumes, Variables)

Pour chaque élément ci-dessous, clique sur **"Add another Path, Port, Variable, Label or Device"** en bas de la page.

#### A. Le Port Web (Config Type: Port)
- **Name:** `WebUI`
- **Container Port:** `8000`
- **Host Port:** `8000` *(Ou un autre port libre sur ton Unraid, par exemple 8080. C'est le port que tu utiliseras pour accéder à l'app).*
- **Connection Type:** `TCP`

#### B. La Persistance des Données (Config Type: Path)
C'est indispensable pour ne pas perdre ta base de données SQLite et tes images au redémarrage !
- **Name:** `Appdata Storage`
- **Container Path:** `/app/backend/data`
- **Host Path:** `/mnt/user/appdata/brunofresh/data` *(C'est là qu'Unraid va stocker ton `database.db` et le dossier `images/`).*

#### C. Les Variables d'Environnement (Config Type: Variable)

Ajoute une variable pour chaque ligne suivante :

1. **Le Mot de Passe de l'App (Requis)**
   - **Name:** `Admin Passcode`
   - **Key:** `APP_PASSCODE`
   - **Value:** *Ton mot de passe secret pour te connecter à BrunoFresh.*

2. **La Clé de Signature des Cookies (Requis pour la stabilité)**
   - **Name:** `Cookie Secret`
   - **Key:** `AUTH_SECRET`
   - **Value:** *Une longue suite de lettres et chiffres générée au hasard (ex: `a8b2c3...`). Si tu ne mets rien, l'app déconnectera tout le monde à chaque redémarrage d'Unraid.*

3. **L'URL d'Ollama (Si utilisé)**
   - **Name:** `Ollama IP`
   - **Key:** `OLLAMA_BASE_URL`
   - **Value:** `http://192.168.X.X:11434` *(⚠️ Remplace par l'adresse IP de la machine physique hébergeant Ollama. NE METS JAMAIS `localhost` ou `127.0.0.1` sinon le conteneur cherchera Ollama à l'intérieur de lui-même !).*

4. **Sécurité des Cookies (Optionnel)**
   - **Name:** `Secure Cookies`
   - **Key:** `AUTH_COOKIE_SECURE`
   - **Value:** `false` *(Si tu accèdes via HTTP localement). Met à `true` uniquement si tu places BrunoFresh derrière un reverse proxy HTTPS comme Nginx Proxy Manager ou Traefik.*

---

## 4. Démarrage et Mises à jour

1. Une fois tout configuré, clique sur **Apply** dans Unraid.
2. Unraid va télécharger l'image depuis GitHub.
3. Lors du démarrage du conteneur, le script `docker-entrypoint.sh` qu'on a codé va s'exécuter automatiquement : il créera ou mettra à jour la base de données (`alembic upgrade head`) dans ton dossier `appdata`.
4. L'application démarrera ensuite. Tu pourras y accéder via `http://IP_DE_TON_UNRAID:8000`.

**Pour mettre à jour l'application plus tard :**
- Pousse tes modifications de code sur GitHub.
- Attends 2-3 minutes que l'Action GitHub se termine.
- Dans Unraid, clique sur l'icône de BrunoFresh -> **Force Update** (ou utilise un outil comme Watchtower). Le conteneur se mettra à jour et migrera la base de données tout seul si nécessaire !
