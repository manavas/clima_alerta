# analizador.py

from logger import logger
# 🔥 Ya no se importan las clases de los componentes, se reciben en el init

class Analizador:
    """
    Orquesta el análisis de datos, combinando un sistema de reglas basado
    en umbrales con un modelo predictivo de IA para detectar riesgos climáticos.
    """
    def __init__(self, db_manager, notifier, predictor, umbrales):
        """
        Inicializa el Analizador con sus dependencias (Inyección de Dependencias).
        """
        self.db = db_manager
        self.notifier = notifier
        self.predictor = predictor
        self.umbrales = umbrales
        logger.info("Analizador Híbrido (Reglas + IA) inicializado.")

    def analizar(self, datos_clima):
        """
        Proceso de análisis híbrido: evalúa reglas y predicciones de IA.
        """
        try:
            # --- Evaluación por Reglas de Umbrales ---
            riesgo_umbral = (
                datos_clima['temperatura'] >= self.umbrales['limite_temp_max'] or
                datos_clima['temperatura'] <= self.umbrales['limite_temp_min'] or
                datos_clima['humedad'] >= self.umbrales['limite_humedad'] or
                datos_clima['lluvia'] >= self.umbrales['limite_lluvia_mm']
            )

            # --- Evaluación Predictiva con IA ---
            probabilidad_riesgo_ia = 0.0
            riesgo_ia = False
            if self.predictor.modelo:
                res_prediccion = self.predictor.predecir(
                    datos_clima['temperatura'],
                    datos_clima['humedad'],
                    datos_clima['lluvia']
                )
                if res_prediccion:
                    _, probabilidad_riesgo_ia = res_prediccion
                    umbral_ia = self.umbrales.get('umbral_ia_probabilidad', 0.75)
                    riesgo_ia = probabilidad_riesgo_ia >= umbral_ia
            
            # --- Decisión Final y Acción ---
            if riesgo_umbral or riesgo_ia:
                mensaje = self._construir_mensaje_alerta(datos_clima, riesgo_umbral, riesgo_ia, probabilidad_riesgo_ia)
                
                # Guardar el clima en el histórico y obtener su ID
                clima_id = self.db.insert_historico_clima(
                    datos_clima['timestamp'], datos_clima['temperatura'], datos_clima['humedad'],
                    datos_clima['lluvia'], datos_clima['clima'], datos_clima.get('viento_kmh', 0)
                )

                if clima_id:
                    # Guardar la alerta en la BD y obtener su ID
                    tipo = "ia" if riesgo_ia and not riesgo_umbral else "umbral"
                    alerta_id = self.db.insert_alerta_emitida(f"riesgo_{tipo}", mensaje, clima_id)
                    # Enviar notificación con botones de feedback
                    if alerta_id:
                        self.notifier.enviar_alerta_general(mensaje, alerta_id)
                
            else:
                logger.info("Condiciones normales. No se requiere alerta.")

        except Exception as e:
            logger.critical(f"Error crítico en el proceso de análisis híbrido: {e}", exc_info=True)
            self.notifier.send_error("analizador_hibrido", str(e))

# Dentro de la clase Analizador en analizador.py

    def analizar_pronostico(self, pronostico_diario: list):
        """
        Analiza la lista de pronósticos diarios y envía una alerta si se espera
        lluvia significativa en los próximos días.
        """
        logger.info("Analizando pronóstico extendido...")
        try:
            # Analizamos el pronóstico para los próximos 2 días
            for dia in pronostico_diario[:2]: 
                fecha_pronostico = dia['fecha']
                lluvia_prevista = dia.get('lluvia', 0)
                
                # Usamos el mismo umbral de lluvia, o podríamos crear uno nuevo en config.yaml
                if lluvia_prevista >= self.umbrales['limite_lluvia_mm']:
                    logger.warning(f"Se detectó pronóstico de lluvia significativa ({lluvia_prevista} mm) para el día {fecha_pronostico.strftime('%Y-%m-%d')}.")
                    
                    # Llamamos a un nuevo método en el notificador
                    self.notifier.enviar_alerta_pronostico(
                        fecha=fecha_pronostico,
                        lluvia=lluvia_prevista,
                        descripcion=dia['clima']
                    )
                    # Opcional: podríamos guardar esta alerta predictiva en la BD también
        except Exception as e:
            logger.error(f"Error analizando el pronóstico: {e}", exc_info=True)

    def _construir_mensaje_alerta(self, datos, por_umbral, por_ia, prob_ia):
        """Función auxiliar para crear el texto de la notificación."""
        motivo = []
        if por_umbral: motivo.append("Umbrales Superados")
        if por_ia: motivo.append("Predicción IA")
        
        return (
            f"⚠️ *ALERTA CLIMÁTICA DETECTADA*\n"
            f"Motivo: *{' y '.join(motivo)}*\n\n"
            f"🌡️ Temperatura: *{datos['temperatura']}°C*\n"
            f"💧 Humedad: *{datos['humedad']}%*\n"
            f"🌧️ Lluvia: *{datos['lluvia']} mm*\n\n"
            f"🤖 Análisis IA (Prob. de Riesgo): *{prob_ia:.1%}*"
        )
