# forecast_colector.py

import requests
import yaml
from logger import logger
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError # <--- CAMBIO: Usando la librería estándar

class ForecastCollectorError(Exception):
    """Excepción personalizada para errores en ForecastColector."""
    pass

class ForecastColector:
    def __init__(self, api_key: str, lat: float, lon: float, tz_str: str):
        """
        Inicializa el colector con sus dependencias (Inyección de Dependencias).
        """
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        try:
            self.tz = ZoneInfo(tz_str)
        except ZoneInfoNotFoundError:
            raise ForecastCollectorError(f"La zona horaria '{tz_str}' no es válida.")
        
        self.api_base_url = "https://api.openweathermap.org/data/3.0/onecall"
        logger.info("ForecastColector inicializado correctamente.")

    def get_forecast(self) -> list | None:
        """
        Obtiene el pronóstico extendido de la API de OpenWeatherMap.
        Retorna una lista de diccionarios (uno por día) o None si hay un error.
        """
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es",
            "exclude": "current,minutely,hourly,alerts" # Excluimos todo menos el pronóstico diario
        }

        try:
            response = requests.get(self.api_base_url, params=params, timeout=15)
            response.raise_for_status() # Lanza un error para códigos 4xx o 5xx
            data = response.json()

            forecast_data = []
            if 'daily' not in data:
                logger.warning("La respuesta de la API no contiene el pronóstico 'daily'.")
                return []

            for daily_data in data['daily']:
                # Conversión de timestamp usando zoneinfo
                dt_local = datetime.fromtimestamp(daily_data['dt'], tz=self.tz)
                
                # Análisis más seguro de la descripción del clima
                weather_info = daily_data.get('weather', [])
                clima = weather_info[0]['description'].capitalize() if weather_info else "No disponible"
                
                forecast_data.append({
                    'fecha': dt_local.date(), # Devolvemos un objeto 'date' para mayor flexibilidad
                    'temp_max': daily_data.get('temp', {}).get('max'),
                    'temp_min': daily_data.get('temp', {}).get('min'),
                    'humedad': daily_data.get('humidity'),
                    'lluvia': daily_data.get('rain', 0), # Obtiene la lluvia o 0 si no existe
                    'clima': clima
                })

            logger.info(f"Pronóstico extendido descargado: {len(forecast_data)} días.")
            return forecast_data

        except requests.exceptions.Timeout:
            logger.error("Error obteniendo pronóstico: La petición a la API tardó demasiado.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a la API de pronóstico: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Error procesando la respuesta de la API de pronóstico. Estructura inesperada: {e}")
        
        return None

if __name__ == '__main__':
    # Ejemplo de cómo se usaría la nueva clase
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        fc = ForecastColector(
            api_key=config['openweathermap_api_key'],
            lat=config['latitud'],
            lon=config['longitud'],
            tz_str=config['zona_horaria']
        )
        
        datos_forecast = fc.get_forecast()
        if datos_forecast:
            for dia in datos_forecast:
                print(dia)
    except (FileNotFoundError, KeyError) as e:
        logger.critical(f"No se pudo cargar la configuración o una clave necesaria no existe: {e}")
    except ForecastCollectorError as e:
        logger.critical(f"Error al inicializar el colector de pronóstico: {e}")
