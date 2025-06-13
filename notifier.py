# notifier.py

import requests
import yaml
import os
from logger import logger

# Se importan las clases necesarias para los botones desde la librería de Telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Definimos una excepción personalizada para errores de configuración
class NotifierConfigError(Exception):
    pass

class Notifier:
    """
    Gestiona el envío de notificaciones a través de la API de Telegram.
    """
    def __init__(self, config_path='config.yaml'):
        """
        Inicializa el notificador cargando las credenciales necesarias.
        Lanza una excepción si no se pueden cargar.
        """
        self.token, self.chat_id = self._load_credentials(config_path)
        self.api_base_url = f"https://api.telegram.org/bot{self.token}"
        logger.info("Notifier inicializado correctamente.")

    def _load_credentials(self, config_path):
        """
        Carga las credenciales desde variables de entorno o un archivo de configuración.
        Levanta NotifierConfigError si las credenciales no se encuentran.
        """
        try:
            # Prioridad 1: Variables de entorno (más seguro para producción)
            token = os.getenv('TELEGRAM_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if token and chat_id:
                logger.info("Credenciales de Telegram cargadas desde variables de entorno.")
                return token, chat_id

            # Prioridad 2: Archivo de configuración
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                token = config['telegram_token']
                chat_id = config['telegram_chat_id']
                logger.info(f"Credenciales de Telegram cargadas desde '{config_path}'.")
                return token, chat_id
                
        except FileNotFoundError:
            raise NotifierConfigError(f"El archivo de configuración '{config_path}' no fue encontrado.")
        except (KeyError, TypeError):
            raise NotifierConfigError("Las claves 'telegram_token' y 'telegram_chat_id' no se encontraron en la configuración.")

    def send_message(self, message: str, parse_mode="Markdown", disable_notification=False, reply_markup=None) -> bool:
        """
        Método base para enviar un mensaje a través de la API de Telegram.
        Acepta un 'reply_markup' opcional para adjuntar teclados de botones.
        """
        url = f"{self.api_base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }

        # --- LÓGICA CORREGIDA ---
        # Solo añadimos el 'reply_markup' al payload si se proporcionó uno.
        if reply_markup:
            # El objeto InlineKeyboardMarkup debe convertirse a un diccionario.
            payload['reply_markup'] = reply_markup.to_dict()

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status() # Lanza un error para códigos HTTP 4xx o 5xx
            logger.info("Mensaje enviado correctamente a Telegram.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje a Telegram: {e}")
            return False

    # --- Métodos específicos para diferentes tipos de alertas ---

    def enviar_alerta_general(self, mensaje: str, alerta_id: int):
        """
        Envía una alerta de texto genérica, adjuntando botones de feedback.
        Este es el método principal que usará el Analizador.
        """
        logger.warning(f"Enviando alerta general para alerta_id {alerta_id}")
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Predicción Correcta", callback_data=f"feedback:{alerta_id}:bien"),
                InlineKeyboardButton("❌ Predicción Incorrecta", callback_data=f"feedback:{alerta_id}:mal")
            ]
        ])
        self.send_message(mensaje, parse_mode="Markdown", reply_markup=keyboard)

    def send_error(self, modulo: str, error: str):
        """Envía una notificación de error del sistema (sin botones)."""
        msg = f"⚠️ *Error en el módulo {modulo}*\n\n`{error}`"
        self.send_message(msg, parse_mode="Markdown")

    def enviar_alerta_pronostico(self, fecha, lluvia, descripcion):
        """Envía una notificación específica sobre un pronóstico de lluvia."""
        mensaje = (
            f"☔ *Pronóstico de Lluvia Próxima*\n\n"
            f"Se espera una precipitación de *{lluvia:.1f} mm* para el día *{fecha.strftime('%A, %d de %B')}*.\n\n"
            f"Condición pronosticada: *{descripcion}*.\n\n"
            f"Toma tus previsiones."
        )
        self.send_message(mensaje, parse_mode="Markdown")
