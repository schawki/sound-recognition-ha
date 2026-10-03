# -*- coding: utf-8 -*-
"""Writes custom_components/sound_recognition/{strings.json, translations/en.json, translations/fr.json}.
English is the reference; add a language by adding a dict to LANGS (same keys) and re-running."""
import json
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "custom_components", "sound_recognition")

EN = {
    "config": {
        "step": {
            "user": {
                "title": "Connect to the sound recognition service",
                "description": "Enter the address of the service (the container that runs the classifier) and its token. The token is generated at the first start and written in the service's config.yaml (api.token).",
                "data": {"host": "Host", "port": "Port", "token": "Token"},
            },
            "reauth_confirm": {"title": "Token refused", "description": "The service refused the token. Enter the current token.", "data": {"token": "Token"}},
        },
        "error": {"cannot_connect": "Cannot reach the service. Check the address, the port and that the service is running.",
                  "invalid_auth": "The token was refused.", "unknown": "Unexpected error."},
        "abort": {"already_configured": "This service is already configured.", "reauth_successful": "Token updated."},
    },
    "options": {
        "step": {
            "init": {"title": "Sound recognition", "menu_options": {
                "sources": "Audio sources", "classes": "Which sounds to listen for", "class_settings": "Settings of one sound",
                "defaults": "Global defaults", "advice": "Advice and warnings", "advice_rule": "Adjust an advice", "finish": "Done (apply to Home Assistant)"}},
            "advice": {"title": "Advice and warnings", "description": "{advice}"},
            "advice_none": {"title": "Advice and warnings", "description": "Nothing to report for the current configuration."},
            "advice_rule": {
                "title": "Adjust an advice",
                "description": "{errors}\nChoose an advice, the level you want, and optionally one source (empty = all sources). “Ignore” hides it; for advice about safety sounds (fire, baby, security) also tick the confirmation.",
                "data": {"rule": "Advice", "source": "Only for this source", "level": "Level", "confirm": "I understand this concerns a safety sound"},
            },
            "sources": {"title": "Audio sources", "menu_options": {"add_source": "Add a source", "edit_source": "Edit a source", "remove_source": "Remove a source", "init": "Back"}},
            "add_source": {
                "title": "Add a source",
                "description": "{errors}\nCamera or Raspberry Pi through go2rtc: use its RTSP address (rtsp://host:8554/name).",
                "data": {"name": "Name", "type": "Type", "url": "Address (URL)", "enabled": "Enabled", "threshold_offset": "Threshold offset",
                         "min_volume_dbfs": "Minimum volume", "schedule_mode": "Listening", "window_days": "Days", "window_from": "From", "window_to": "Until",
                         "clips_allowed": "Allow audio clips", "clips_max_days": "Keep clips at most (days)"},
                "data_description": {"threshold_offset": "Added to every threshold of this source (positive = less sensitive, for a noisy room).",
                                     "min_volume_dbfs": "Sounds quieter than this are ignored. Leave empty to use the global default.",
                                     "schedule_mode": "Continuous listens all the time. Scheduled listens only during the window below.",
                                     "clips_allowed": "Turn off to never store audio from this source."},
            },
            "edit_source": {"title": "Edit a source", "description": "Choose the source to edit.", "data": {"source": "Source"}},
            "edit_source_form": {
                "title": "Edit {source}",
                "description": "{errors}\nAdditional time windows kept: {extra_windows} (edit them in the YAML file).",
                "data": {"name": "Name", "type": "Type", "url": "Address (URL)", "enabled": "Enabled", "threshold_offset": "Threshold offset",
                         "min_volume_dbfs": "Minimum volume", "schedule_mode": "Listening", "window_days": "Days", "window_from": "From", "window_to": "Until",
                         "clips_allowed": "Allow audio clips", "clips_max_days": "Keep clips at most (days)"},
            },
            "remove_source": {"title": "Remove a source", "description": "{errors}", "data": {"source": "Source", "confirm": "Yes, remove it"}},
            "scope": {"title": "Where should this apply?", "menu_options": {"scope_global": "All sources", "scope_source": "One source only"}},
            "scope_source": {"title": "Choose the source", "data": {"source": "Source"}},
            "classes_pick": {
                "title": "Sounds to listen for",
                "description": "{errors}\nStarred sounds (★) are the ones recommended as alerts. Sounds that are not listed are ignored. Applies to: {scope}",
                "data": {"classes": "Sounds"},
            },
            "class_pick": {"title": "Choose a sound", "description": "Applies to: {scope}", "data": {"class": "Sound"}},
            "class_form": {
                "title": "{class}",
                "description": "{errors}\n{forbidden} {note}\nSuggested threshold / duration / cooldown: {suggested}. Applies to: {scope}",
                "data": {"threshold": "Threshold", "min_duration_s": "Minimum duration", "cooldown_s": "Cooldown", "pre_roll_s": "Clip: seconds before",
                         "post_roll_s": "Clip: seconds after", "clip_retention_days": "Keep clips (days, 0 = none)", "min_volume_dbfs": "Minimum volume",
                         "always_on": "Always listen for this sound (ignore schedules)"},
                "data_description": {"threshold": "Score from 0 to 1 above which the sound counts.", "min_duration_s": "The sound must last at least this long.",
                                     "cooldown_s": "Delay before the same sound is reported again.", "min_volume_dbfs": "Leave empty to use the source or global value."},
            },
            "defaults": {
                "title": "Global defaults",
                "description": "{errors}",
                "data": {"min_volume_dbfs": "Minimum volume", "context_boost": "Threshold raise when television, radio or music is detected",
                         "clips_allowed": "Allow audio clips", "clips_max_days": "Keep clips at most (days)"},
            },
        },
        "error": {"invalid_config": "The service refused this configuration: {errors}", "no_sources": "There is no source yet. Add one first.", "confirm_required": "This advice concerns a safety sound: tick the confirmation to hide it.",
                  "no_classes": "No sound is enabled here yet.", "not_confirmed": "Tick the box to confirm."},
        "abort": {"cannot_connect": "Cannot reach the service."},
    },
    "entity": {
        "binary_sensor": {"connection": {"name": "Connected"}, "detected": {"name": "{class_name}"}},
        "event": {"sound": {"name": "Sound detection", "state_attributes": {"event_type": {"state": {"detection": "Detection", "clip_ready": "Clip ready"}}}}},
        "sensor": {"level": {"name": "Sound level"}, "advice": {"name": "Advice and warnings"}},
    },
    "issues": {"advice": {"title": "Sound recognition advice", "description": "**{source}**: {message}"}},
    "selector": {
        "advice_level": {"options": {"default": "Catalog default", "info": "Information", "warning": "Warning", "danger": "Danger", "ignore": "Ignore (hide)"}},
        "source_type": {"options": {"rtsp": "RTSP stream", "go2rtc": "go2rtc / camera", "alsa_rpi": "Raspberry Pi microphone", "esphome": "ESPHome (not available yet)", "file": "Audio file (tests)"}},
        "schedule_mode": {"options": {"continuous": "Continuous (all the time)", "scheduled": "Scheduled (time window)"}},
        "weekday": {"options": {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}},
    },
}

FR = {
    "config": {
        "step": {
            "user": {
                "title": "Connexion au service de reconnaissance de sons",
                "description": "Indiquez l'adresse du service (le conteneur qui exécute le classifieur) et son jeton. Le jeton est généré au premier démarrage et écrit dans le config.yaml du service (api.token).",
                "data": {"host": "Hôte", "port": "Port", "token": "Jeton"},
            },
            "reauth_confirm": {"title": "Jeton refusé", "description": "Le service a refusé le jeton. Saisissez le jeton actuel.", "data": {"token": "Jeton"}},
        },
        "error": {"cannot_connect": "Impossible de joindre le service. Vérifiez l'adresse, le port et que le service tourne.",
                  "invalid_auth": "Le jeton a été refusé.", "unknown": "Erreur inattendue."},
        "abort": {"already_configured": "Ce service est déjà configuré.", "reauth_successful": "Jeton mis à jour."},
    },
    "options": {
        "step": {
            "init": {"title": "Reconnaissance de sons", "menu_options": {
                "sources": "Sources audio", "classes": "Quels sons écouter", "class_settings": "Réglages d'un son",
                "defaults": "Valeurs par défaut", "advice": "Conseils et avertissements", "advice_rule": "Ajuster un conseil", "finish": "Terminer (appliquer dans Home Assistant)"}},
            "advice": {"title": "Conseils et avertissements", "description": "{advice}"},
            "advice_none": {"title": "Conseils et avertissements", "description": "Rien à signaler pour la configuration actuelle."},
            "advice_rule": {
                "title": "Ajuster un conseil",
                "description": "{errors}\nChoisissez un conseil, le niveau voulu et, au besoin, une seule source (vide = toutes les sources). « Ignorer » le masque ; pour un conseil concernant des sons de sécurité (incendie, bébé, intrusion), cochez aussi la confirmation.",
                "data": {"rule": "Conseil", "source": "Seulement pour cette source", "level": "Niveau", "confirm": "Je comprends que cela concerne un son de sécurité"},
            },
            "sources": {"title": "Sources audio", "menu_options": {"add_source": "Ajouter une source", "edit_source": "Modifier une source", "remove_source": "Supprimer une source", "init": "Retour"}},
            "add_source": {
                "title": "Ajouter une source",
                "description": "{errors}\nCaméra ou Raspberry Pi via go2rtc : utilisez son adresse RTSP (rtsp://hôte:8554/nom).",
                "data": {"name": "Nom", "type": "Type", "url": "Adresse (URL)", "enabled": "Activée", "threshold_offset": "Décalage de seuil",
                         "min_volume_dbfs": "Volume minimum", "schedule_mode": "Écoute", "window_days": "Jours", "window_from": "De", "window_to": "Jusqu'à",
                         "clips_allowed": "Autoriser les clips audio", "clips_max_days": "Conserver les clips au plus (jours)"},
                "data_description": {"threshold_offset": "Ajouté à tous les seuils de cette source (positif = moins sensible, pour une pièce bruyante).",
                                     "min_volume_dbfs": "Les sons plus faibles sont ignorés. Laissez vide pour utiliser la valeur globale.",
                                     "schedule_mode": "Continue : écoute en permanence. Planifiée : écoute seulement pendant la plage ci-dessous.",
                                     "clips_allowed": "Désactivez pour ne jamais enregistrer d'audio depuis cette source."},
            },
            "edit_source": {"title": "Modifier une source", "description": "Choisissez la source à modifier.", "data": {"source": "Source"}},
            "edit_source_form": {
                "title": "Modifier {source}",
                "description": "{errors}\nPlages horaires supplémentaires conservées : {extra_windows} (à modifier dans le fichier YAML).",
                "data": {"name": "Nom", "type": "Type", "url": "Adresse (URL)", "enabled": "Activée", "threshold_offset": "Décalage de seuil",
                         "min_volume_dbfs": "Volume minimum", "schedule_mode": "Écoute", "window_days": "Jours", "window_from": "De", "window_to": "Jusqu'à",
                         "clips_allowed": "Autoriser les clips audio", "clips_max_days": "Conserver les clips au plus (jours)"},
            },
            "remove_source": {"title": "Supprimer une source", "description": "{errors}", "data": {"source": "Source", "confirm": "Oui, la supprimer"}},
            "scope": {"title": "Où cela doit-il s'appliquer ?", "menu_options": {"scope_global": "Toutes les sources", "scope_source": "Une seule source"}},
            "scope_source": {"title": "Choisir la source", "data": {"source": "Source"}},
            "classes_pick": {
                "title": "Sons à écouter",
                "description": "{errors}\nLes sons marqués d'une étoile (★) sont ceux recommandés comme alertes. Les sons absents de la liste sont ignorés. S'applique à : {scope}",
                "data": {"classes": "Sons"},
            },
            "class_pick": {"title": "Choisir un son", "description": "S'applique à : {scope}", "data": {"class": "Son"}},
            "class_form": {
                "title": "{class}",
                "description": "{errors}\n{forbidden} {note}\nSeuil / durée / ré-armement suggérés : {suggested}. S'applique à : {scope}",
                "data": {"threshold": "Seuil", "min_duration_s": "Durée minimale", "cooldown_s": "Ré-armement", "pre_roll_s": "Clip : secondes avant",
                         "post_roll_s": "Clip : secondes après", "clip_retention_days": "Conserver les clips (jours, 0 = aucun)", "min_volume_dbfs": "Volume minimum",
                         "always_on": "Toujours écouter ce son (ignorer les plannings)"},
                "data_description": {"threshold": "Score de 0 à 1 au-dessus duquel le son compte.", "min_duration_s": "Le son doit durer au moins ce temps.",
                                     "cooldown_s": "Délai avant de signaler à nouveau le même son.", "min_volume_dbfs": "Laissez vide pour utiliser la valeur de la source ou globale."},
            },
            "defaults": {
                "title": "Valeurs par défaut",
                "description": "{errors}",
                "data": {"min_volume_dbfs": "Volume minimum", "context_boost": "Relèvement du seuil quand télévision, radio ou musique sont détectées",
                         "clips_allowed": "Autoriser les clips audio", "clips_max_days": "Conserver les clips au plus (jours)"},
            },
        },
        "error": {"invalid_config": "Le service a refusé cette configuration : {errors}", "no_sources": "Il n'y a pas encore de source. Ajoutez-en une d'abord.", "confirm_required": "Ce conseil concerne un son de sécurité : cochez la confirmation pour le masquer.",
                  "no_classes": "Aucun son n'est encore activé ici.", "not_confirmed": "Cochez la case pour confirmer."},
        "abort": {"cannot_connect": "Impossible de joindre le service."},
    },
    "entity": {
        "binary_sensor": {"connection": {"name": "Connecté"}, "detected": {"name": "{class_name}"}},
        "event": {"sound": {"name": "Détection de son", "state_attributes": {"event_type": {"state": {"detection": "Détection", "clip_ready": "Clip prêt"}}}}},
        "sensor": {"level": {"name": "Niveau sonore"}, "advice": {"name": "Conseils et avertissements"}},
    },
    "issues": {"advice": {"title": "Conseil de reconnaissance de sons", "description": "**{source}** : {message}"}},
    "selector": {
        "advice_level": {"options": {"default": "Valeur du catalogue", "info": "Information", "warning": "Avertissement", "danger": "Danger", "ignore": "Ignorer (masquer)"}},
        "source_type": {"options": {"rtsp": "Flux RTSP", "go2rtc": "go2rtc / caméra", "alsa_rpi": "Micro de Raspberry Pi", "esphome": "ESPHome (pas encore disponible)", "file": "Fichier audio (tests)"}},
        "schedule_mode": {"options": {"continuous": "Continue (en permanence)", "scheduled": "Planifiée (plage horaire)"}},
        "weekday": {"options": {"mon": "Lundi", "tue": "Mardi", "wed": "Mercredi", "thu": "Jeudi", "fri": "Vendredi", "sat": "Samedi", "sun": "Dimanche"}},
    },
}
LANGS = {"en": EN, "fr": FR}


def keys(d, p=""):
    for k, v in d.items():
        yield from keys(v, f"{p}.{k}") if isinstance(v, dict) else [f"{p}.{k}"]


if __name__ == "__main__":
    ref = set(keys(EN))
    for code, d in LANGS.items():
        assert set(keys(d)) == ref, (code, ref ^ set(keys(d)))
    os.makedirs(os.path.join(OUT, "translations"), exist_ok=True)
    for code, d in LANGS.items():
        json.dump(d, open(os.path.join(OUT, "translations", f"{code}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(EN, open(os.path.join(OUT, "strings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("translations written:", ", ".join(LANGS))
