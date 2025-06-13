# logger.py

from loguru import logger
import sys

# No es necesario 'os' ni 'datetime' para esta configuración mejorada

# El nombre del archivo ahora se define directamente en el 'sink'
# usando la etiqueta {time} para que loguru lo gestione automáticamente.
log_file_path = "logs/clima_{time:YYYYMMDD}.log"

logger.remove()

# Sink para la consola (sin cambios, está perfecto)
logger.add(sys.stdout,
           colorize=True,
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")

# Sink para el archivo, ahora gestionado por loguru
logger.add(log_file_path,
           rotation="00:00",  # Rota el archivo cada día a medianoche
           retention="7 days",
           compression="zip",
           level="INFO", # Es buena práctica definir un nivel para el archivo
           format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}") # Un formato explícito para el archivo
