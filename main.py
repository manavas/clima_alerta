# main.py (Versión Final con Tareas Consistentes)

import yaml
import sqlite3
from logger import logger
from apscheduler.schedulers.blocking import BlockingScheduler

# --- Importamos TODAS las clases necesarias ---
from db_manager import DBManager
from notifier import Notifier, NotifierConfigError
from colector import Colector, ColectorError
from forecast_colector import ForecastColector, ForecastCollectorError
from analizador import Analizador
from modelo_adaptativo import ModeloAdaptativo
from predictor import Predictor

# --- Funciones de Tareas para el Scheduler ---

def tarea_ciclo_principal():
    """Tarea principal: recolecta y analiza los datos actuales."""
    logger.info("--- ⏰ INICIANDO CICLO PRINCIPAL DE MONITOREO ---")
    try:
        # Carga la configuración más reciente en cada ejecución
        try:
            with open('config_dinamico.yaml', 'r') as f: config = yaml.safe_load(f)
        except FileNotFoundError:
            with open('config.yaml', 'r') as f: config = yaml.safe_load(f)

        with DBManager(config.get('db_name')) as db:
            # Instanciamos los componentes necesarios para este ciclo
            notifier = Notifier()
            colector = Colector(db, config.get('openweathermap_api_key'), config.get('lat'), config.get('lon'), config.get('zona_horaria'))
            modelo = ModeloAdaptativo.cargar_modelo()
            predictor = Predictor(modelo_cargado=modelo)
            analizador = Analizador(db, notifier, predictor, config.get('umbrales', {}))
            
            datos = colector.obtener_datos_actuales()
            if datos:
                analizador.analizar(datos)

    except Exception as e:
        logger.critical(f"Error no controlado en el ciclo principal: {e}", exc_info=True)
    logger.info("--- 🏁 FIN DEL CICLO PRINCIPAL DE MONITOREO ---")


def tarea_analisis_pronostico():
    """Tarea periódica: obtiene y analiza el pronóstico del tiempo."""
    logger.info("--- ⛅ INICIANDO CICLO DE ANÁLISIS DE PRONÓSTICO ---")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        with DBManager(config.get('db_name')) as db:
            notifier = Notifier()
            forecast_colector = ForecastColector(config.get('openweathermap_api_key'), config.get('lat'), config.get('lon'), config.get('zona_horaria'))
            # Para esta tarea, el predictor de riesgo actual no es necesario
            analizador = Analizador(db, notifier, predictor=None, umbrales=config.get('umbrales', {}))

            pronostico = forecast_colector.get_forecast()
            if pronostico:
                analizador.analizar_pronostico(pronostico)

    except Exception as e:
        logger.critical(f"Error no controlado en el ciclo de pronóstico: {e}", exc_info=True)
    logger.info("--- 🏁 FIN DEL CICLO DE ANÁLISIS DE PRONÓSTICO ---")


def tarea_reentrenamiento_modelo():
    """Tarea programada: re-entrena el modelo de ML."""
    logger.info("--- 🧠 INICIANDO TAREA DE RE-ENTRENAMIENTO ---")
    try:
        with DBManager() as db:
            entrenador = ModeloAdaptativo(db_manager=db)
            entrenador.entrenar_y_guardar()
    except Exception as e:
        logger.critical(f"El proceso de re-entrenamiento falló: {e}", exc_info=True)
    logger.info("--- ✅ FIN DE LA TAREA DE RE-ENTRENAMIENTO ---")


def run():
    """Punto de entrada: Configura e inicia el scheduler con todas las tareas."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        scheduler = BlockingScheduler(timezone='UTC')
        umbrales = config.get('umbrales', {})

        # Tarea #1: Ciclo principal
        minutos = int(umbrales.get('intervalo_consulta_min', 30))
        scheduler.add_job(tarea_ciclo_principal, 'interval', minutes=minutos, id='ciclo_principal')
        logger.info(f"Tarea de monitoreo principal programada cada {minutos} minutos.")

        # Tarea #2: Análisis de pronóstico
        scheduler.add_job(tarea_analisis_pronostico, 'interval', hours=6, id='analisis_pronostico')
        logger.info("Tarea de análisis de pronóstico programada cada 6 horas.")

        # Tarea #3: Re-entrenamiento del modelo
        scheduler.add_job(tarea_reentrenamiento_modelo, 'cron', day_of_week='sun', hour=3, id='reentrenamiento_semanal')
        logger.info("Tarea de re-entrenamiento del modelo programada para cada domingo a las 03:00 UTC.")
        
        print("\n>>> Servicio de Monitoreo y Alertas iniciado. Presiona Ctrl+C para detener. <<<\n")
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        logger.warning("El servicio de monitoreo ha sido detenido manualmente.")
        print("\nServicio detenido. ¡Hasta luego!")
    except Exception as e:
        logger.critical(f"Ocurrió un error inesperado en el arranque: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        with DBManager():
            logger.info("Base de datos verificada. Iniciando el servicio de monitoreo...")
        run()
    except sqlite3.Error as e:
        logger.critical(f"No se pudo establecer la conexión inicial con la base de datos: {e}")
