# clima_bot.py

# --- Importaciones de la librería del Bot ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode

# --- Importaciones de otros módulos y librerías estándar ---
import yaml
from db_manager import DBManager
from logger import logger

# --- Funciones de los Handlers (Ahora todas son ASÍNCRONAS) ---

async def start(update: Update, context: CallbackContext) -> None: # <--- CAMBIO: async
    """
    Maneja los comandos /start y /help.
    Envía un mensaje de bienvenida con la lista de comandos disponibles.
    """
    mensaje = (
        "🌦️ *Bienvenido al Sistema de Alerta Meteorológica Personal*\n\n"
        "Recibirás alertas automáticas con la información del clima. "
        "Puedes reaccionar a ellas usando los botones para ayudarnos a mejorar.\n\n"
        "Comandos disponibles:\n"
        "• /status — Muestra el estado actual y estadísticas del sistema.\n"
        "• /help — Muestra este mensaje de ayuda."
    )
    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN) # <--- CAMBIO: await

async def status(update: Update, context: CallbackContext) -> None: # <--- CAMBIO: async
    """
    Maneja el comando /status.
    Consulta la base de datos para obtener un resumen del estado del sistema.
    """
    try:
        with DBManager() as db:
            summary = db.get_status_summary()
        
        mensaje = (
            f"📊 *Estado del Sistema:*\n\n"
            f"• Total mediciones registradas: *{summary.get('total', 0)}*\n"
            f"• Última medición recibida: *{summary.get('ultimo', 'N/A')}*\n"
            f"• Estado: 🟢 *Operativo*"
        )
        await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN) # <--- CAMBIO: await
    except Exception as e:
        logger.error(f"Error en el handler /status: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Lo sentimos, ocurrió un error al consultar el estado del sistema.") # <--- CAMBIO: await

async def feedback_handler(update: Update, context: CallbackContext) -> None: # <--- CAMBIO: async
    """
    Maneja las pulsaciones de los botones de feedback (callbacks).
    """
    query = update.callback_query
    await query.answer() # <--- CAMBIO: await

    try:
        _, alerta_id_str, opinion = query.data.split(':')
        alerta_id = int(alerta_id_str)
        
        with DBManager() as db:
            db.insert_feedback(alerta_id=alerta_id, feedback=opinion)

        feedback_confirmado = f"✅ Feedback ('{opinion}') registrado. ¡Gracias por tu ayuda!"
        await query.edit_message_text(text=f"{query.message.text_markdown}\n\n*{feedback_confirmado}*", parse_mode=ParseMode.MARKDOWN) # <--- CAMBIO: await
        
        logger.info(f"Feedback registrado para alerta ID {alerta_id}: '{opinion}'")
    except Exception as e:
        logger.error(f"Error procesando el callback de feedback: {e}", exc_info=True)
        try:
            await query.edit_message_text(text=f"{query.message.text_markdown}\n\n*⚠️ Hubo un error al registrar tu feedback.*", parse_mode=ParseMode.MARKDOWN) # <--- CAMBIO: await
        except:
            pass

def main() -> None:
    """
    Punto de entrada principal del bot.
    Construye la aplicación, añade los handlers y la ejecuta.
    """
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        token = config['telegram_token']
    except (FileNotFoundError, KeyError) as e:
        logger.critical(f"Error fatal: No se pudo cargar el token de Telegram desde config.yaml. {e}")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(feedback_handler, pattern='^feedback:'))

    logger.info("Bot de Telegram iniciado y listo para recibir comandos 🚀")
    application.run_polling()


if __name__ == '__main__':
    main()
