# aprender.py
# Script para ejecutar el proceso de aprendizaje periódicamente.

from db_manager import DBManager
from aprendiz import Aprendiz
import yaml

CONFIG_BASE = "config.yaml"
CONFIG_DINAMICO = "config_dinamico.yaml"

def main():
    # Cargar la configuración actual (dinámica si existe, si no la base)
    try:
        with open(CONFIG_DINAMICO, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        with open(CONFIG_BASE, 'r') as f:
            config = yaml.safe_load(f)

    umbrales = config.get('umbrales', {})

    with DBManager() as db:
        aprendiz = Aprendiz(db_manager=db, umbrales_actuales=umbrales)
        aprendiz.ajustar_limites(CONFIG_DINAMICO)

if __name__ == '__main__':
    main()
