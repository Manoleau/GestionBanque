# Bot de gestion de budget (Python + SQLite)

Ce dépôt contient un bot Discord en Python pour gérer manuellement un budget avec abonnements, dépenses, solde bancaire,
et un rappel quotidien à 8h dans un salon spécifique. Toutes les commandes sont des slash commands (/).

## Fonctionnalités

- Gestion des abonnements (montant, jour du mois)
- Gestion des dépenses manuelles (montant, date d’échéance, marquer payé)
- Gestion du solde bancaire par utilisateur (définir, ajouter, retirer, afficher)
- Rappel quotidien à 8h configurable avec `REMINDER_CHANNEL_ID`
- Persistance SQLite asynchrone (aiosqlite)

## Quickstart

1. Créez et activez un environnement virtuel (recommandé).
2. Installez les dépendances:
   ```bash
   pip install -r requirements.txt
   ```
3. Créez un fichier `.env` à la racine du projet:
   ```env
   DISCORD_TOKEN=VOTRE_TOKEN_BOT
   DATABASE_PATH=bot.db
   # ID du salon texte pour le rappel quotidien à 8h (facultatif)
   REMINDER_CHANNEL_ID=
   ```
4. Démarrez le bot:
   ```bash
   python -m bot
   ```

## Project Structure

- `bot/__main__.py`: Entry point for running `python -m bot`
- `bot/config.py`: Charge la configuration depuis les variables d'environnement
- `bot/db.py`: Connexion SQLite et initialisation simple
- `bot/bot.py`: Client bot et enregistrement des événements/commandes (slash)
- `bot/cogs/budget.py`: Gestion du budget (abonnements, dépenses, banque) avec rappel quotidien à 8h
- `bot/services/budget_service.py`: Logique métier et accès aux données (CRUD, calculs)
- `bot/utils/money.py`: Utilitaires de formatage/parsing des montants

## Commandes (slash)

- Abonnements:
    - `/sub add name:<nom> amount:<montant> day_of_month:<1..28>`: ajoute un abonnement. Ex:
      `/sub add name:Netflix amount:12.99 day_of_month:15`
    - `/sub list`: liste vos abonnements
    - `/sub del sub_id:<id>`: supprime un abonnement
- Dépenses:
    - `/pay add name:<nom> amount:<montant> due_date:<AAAA-MM-JJ>`: ajoute une dépense à payer
    - `/pay list`: liste vos dépenses non payées
    - `/pay done expense_id:<id>`: marque une dépense comme payée
    - `/pay del expense_id:<id>`: supprime une dépense
- Banque:
    - `/bank show`: affiche votre solde actuel
    - `/bank set amount:<montant>`: définit votre solde
    - `/bank add amount:<montant>`: ajoute au solde
    - `/bank sub amount:<montant>`: retire du solde
- Synthèse:
    - `/reste`: montre le total restant à payer ce mois depuis aujourd'hui (abonnements à venir + dépenses non payées)

## Reminders

- Chaque utilisateur peut paramétrer son rappel quotidien à 8h:
    - `/reminder set mode:dm` pour recevoir un MP.
    - `/reminder set mode:channel channel:#salon` pour recevoir une mention dans un salon spécifique.
    - `/reminder show` pour afficher votre configuration actuelle.
- Si aucune préférence n'est définie pour aucun utilisateur, et que `REMINDER_CHANNEL_ID` est configuré dans `.env`, un
  rappel générique sera posté dans ce salon.

## Notes

- Assurez-vous d'activer les intents requis pour votre bot dans le Developer Portal Discord et adaptez `bot.py` si
  besoin.
