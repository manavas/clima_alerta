# colector.py

import requests
import yaml
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError # <--- CAMBIO: Usando la librería estándar
from datetime import datetime
from db_manager import DBManager
from logger import logger

class ColectorError(Exception):
    """Excepción personalizada para errores del Colector."""
    pass

class Colector:
    """
    Componente responsable de obtener los datos climáticos actuales desde una API
    y persistirlos en la base de datos.
    """
    def __init__(self, db_manager: DBManager, api_key: str, lat: float, lon: float, tz_str: str):
        """
        Inicializa el Colector con sus dependencias (Inyección de Dependencias).
        """
        self.db = db_manager
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        try:
            self.tz = ZoneInfo(tz_str)
        except ZoneInfoNotFoundError:
            raise ColectorError(f"La zona horaria '{tz_str}' no es válida.")
            
        self.api_base_url = "https://api.openweathermap.org/data/3.0/onecall"
        logger.info("Colector inicializado correctamente.")

    def obtener_datos_actuales(self) -> dict | None:
        """
        Obtiene los datos meteorológicos actuales desde la API de OpenWeatherMap.
        Retorna un diccionario con los datos o None si ocurre un error.
        """
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es",
            "exclude": "minutely,hourly,daily,alerts"
        }

        try:
            response = requests.get(self.api_base_url, params=params, timeout=15)
            response.raise_for_status() # Lanza un error para respuestas 4xx o 5xx
            data = response.json().get('current', {})

            if not data:
                logger.error("La respuesta de la API no contiene la sección 'current'.")
                return None
            
            # Análisis seguro de los datos
            weather_info = data.get('weather', [])
            clima = weather_info[0]['description'].capitalize() if weather_info else "No disponible"
            
            # Conversión de timestamp usando zoneinfo
            dt_local = datetime.fromtimestamp(data['dt'], tz=self.tz)

            return {
                'timestamp': dt_local,
                'temperatura': data.get('temp'),
                'humedad': data.get('humidity'),
                'lluvia': data.get('rain', {}).get('1h', 0),
                'clima': clima,
                'viento_kmh': data.get('wind_speed', 0) * 3.6
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a la API: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Error procesando la respuesta de la API. Estructura inesperada: {e}")
        
        return None

    def ejecutar(self):
        """
        Orquesta el proceso completo: obtiene los datos y los guarda en la BD.
        """
        logger.info("Ejecutando ciclo de recolección...")
        datos = self.obtener_datos_actuales()
        if datos:
            # Capturamos el ID del registro insertado
            clima_id = self.db.insert_historico_clima(
                datos['timestamp'],
                datos['temperatura'],
                datos['humedad'],
                datos['lluvia'],
                datos['clima'],
                round(datos['viento_kmh'], 2)
            )
            # Verificamos si la inserción tuvo éxito (si obtuvimos un ID)
            if clima_id:
                logger.info(f"Ciclo de recolección finalizado. Registro guardado con ID: {clima_id}")
            else:
                logger.error("El ciclo de recolección falló al intentar guardar los datos en la BD.")
        else:
            logger.error("No se pudieron obtener datos, el ciclo de recolección falló.")

if __name__ == '__main__':
    # Ejemplo de cómo se usaría la nueva clase desde un orquestador
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        # La conexión a la BD se maneja con un gestor de contexto
        with DBManager(db_name=config.get('db_name', 'clima_alerta.db')) as db:
            # Se crea el colector "inyectándole" sus dependencias
            colector = Colector(
                db_manager=db,
                api_key=config['openweathermap_api_key'],
                lat=config['latitud'],
                lon=config['longitud'],
                tz_str=config['zona_horaria']
            )
            
            colector.ejecutar()

    except (FileNotFoundError, KeyError) as e:
        logger.critical(f"No se pudo cargar la configuración o una clave necesaria no existe: {e}")
    except ColectorError as e:
        logger.critical(f"Error al inicializar el colector: {e}")
