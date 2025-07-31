.PHONY: help install test clean run-heightmap benchmark

# Configuration
PYTHON := python3
PIP := pip3
PYTEST := pytest
TERRAIN_SIZE := 1024
SEED := 42

help: ## Afficher l'aide
	@echo "Wilderness-like Prototype - Commandes disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installer les dépendances
	$(PIP) install -r requirements.txt
	@echo "Installation terminée."

# Tests
test: ## Exécuter tous les tests unitaires
	@echo "Tests unitaires à implémenter"
	@echo "Module terrain_gen/erosion.py nécessite des tests"

benchmark: ## Tests de performance
	@echo "Benchmarks à implémenter"
	@echo "Utiliser terrain_gen/erosion.py pour les tests de performance"

# Génération de terrain
run-heightmap: ## Générer heightmap Diamond-Square + Perlin fBm
	$(PYTHON) -m terrain_gen.heightmap --size $(TERRAIN_SIZE) --seed $(SEED) --output output/heightmap.png
	@echo "Heightmap générée: output/heightmap.png"

run-erosion: ## Appliquer érosion hydraulique sur heightmap existante
	$(PYTHON) -m terrain_gen.erosion output/heightmap.png --iterations 50 --output output/eroded_heightmap.png
	@echo "Érosion appliquée: output/eroded_heightmap.png"

run-erosion-light: ## Érosion légère (20 itérations) - DÉPRÉCIÉ
	@echo "Commande dépréciée. Utilisez 'make run-erosion' pour l'érosion standard."

run-erosion-heavy: ## Érosion forte (100 itérations) - DÉPRÉCIÉ
	@echo "Commande dépréciée. Utilisez 'make run-erosion' pour l'érosion standard."

run-erosion-custom: ## Érosion personnalisée (paramètres configurables) - DÉPRÉCIÉ
	@echo "Commande dépréciée. Utilisez 'make run-erosion' pour l'érosion standard."

run-erosion-demo: ## Démonstration érosion sur terrain généré
	$(PYTHON) -m terrain_gen.erosion --demo
	@echo "Démonstration érosion terminée"

run-terrain-complete: ## Pipeline complet: génération + érosion
	$(MAKE) run-heightmap
	$(MAKE) run-erosion
	@echo "Pipeline complet terminé ✓"

run-eroded-terrains: ## Générer terrain érodé unique (FONCTIONNEL)
	$(MAKE) run-erosion
	@echo "Terrain érodé généré: output/eroded_heightmap.png"

run-eroded-terrains-working: ## Générer terrains érodés fonctionnels (FONCTIONNEL)
	$(MAKE) run-eroded-terrains
	@echo "Tous les terrains érodés fonctionnels générés ✓"

run-reunion-4k: ## Générer heightmap 4K Réunion (données réelles)
	$(PYTHON) terrain_gen/generate_reunion_4k.py
	@echo "Heightmap Réunion 4K générée: output/reunion_real_*.png"

run-honshu-4k: ## Générer heightmap 4K Honshu complète (données réelles)
	printf "full\ny\n" | $(PYTHON) terrain_gen/generate_honshu_4k.py
	@echo "Heightmap Honshu 4K générée: output/honshu_full_*.png"

run-honshu-kanto: ## Générer heightmap zone Kanto (Tokyo, mont Fuji)
	printf "kanto\ny\n" | $(PYTHON) terrain_gen/generate_honshu_4k.py
	@echo "Heightmap Honshu Kanto générée: output/honshu_kanto_*.png"

run-honshu-kansai: ## Générer heightmap zone Kansai (Osaka, Kyoto)
	printf "kansai\ny\n" | $(PYTHON) terrain_gen/generate_honshu_4k.py
	@echo "Heightmap Honshu Kansai générée: output/honshu_kansai_*.png"

run-honshu-alps: ## Générer heightmap Alpes japonaises 
	printf "alps\ny\n" | $(PYTHON) terrain_gen/generate_honshu_4k.py
	@echo "Heightmap Alpes japonaises générée: output/honshu_alps_*.png"

run-yakushima-4k: ## Générer heightmap 4K Île de Yakushima (site UNESCO)
	$(PYTHON) terrain_gen/generate_yakushima_4k.py --zone full --resolution 4k
	@echo "Heightmap Yakushima générée: output/yakushima_full_4k.png"

run-yakushima-central: ## Générer heightmap 4K Zone centrale Yakushima (Mont Miyanoura)
	$(PYTHON) terrain_gen/generate_yakushima_4k.py --zone central --resolution 4k
	@echo "Heightmap Yakushima centrale générée: output/yakushima_central_4k.png"

run-yakushima-jomon: ## Générer heightmap 4K Forêt de Jōmon-sugi
	$(PYTHON) terrain_gen/generate_yakushima_4k.py --zone jomon --resolution 4k
	@echo "Heightmap Forêt Jōmon-sugi générée: output/yakushima_jomon_4k.png"

run-yakushima-senpiro: ## Générer heightmap 4K Cascade de Senpiro
	$(PYTHON) terrain_gen/generate_yakushima_4k.py --zone senpiro --resolution 4k
	@echo "Heightmap Cascade Senpiro générée: output/yakushima_senpiro_4k.png"

run-yakushima-steep: ## Générer heightmap 4K Zone côte-à-colline abrupte
	$(PYTHON) terrain_gen/generate_yakushima_4k.py --zone steep --resolution 4k
	@echo "Heightmap Zone abrupte Yakushima générée: output/yakushima_steep_4k.png"

# Développement  
format: ## Formater le code avec black
	black terrain_gen/ tests/
	@echo "Code formaté"

lint: ## Vérifier le style avec flake8
	flake8 terrain_gen/ tests/
	@echo "Linting terminé"

type-check: ## Vérification des types avec mypy
	mypy terrain_gen/
	@echo "Vérification des types terminée"

pre-commit: format lint type-check test ## Vérifications avant commit
	@echo "Toutes les vérifications passées ✓"

# Nettoyage
clean: ## Nettoyer les fichiers temporaires
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/
	rm -rf build/
	rm -rf dist/
	rm -rf output/*.png
	rm -rf output/*.raw
	@echo "Nettoyage terminé"

# Serveur web pour visualisation
serve-web: ## Lancer le serveur web pour visualisation 3D
	cd web && $(PYTHON) -m http.server 8000
	@echo "Visualiseur 3D disponible sur http://localhost:8000"

# Utilitaires
create-dirs: ## Créer les dossiers de sortie
	mkdir -p output
	@echo "Dossiers créés"

# Par défaut
all: install create-dirs test run-heightmap ## Installation complète et génération terrain
	@echo "Setup complet terminé ✓" 