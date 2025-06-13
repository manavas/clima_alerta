# predictor.py

import joblib
import numpy as np
from logger import logger

class Predictor:
    """
    Recibe un modelo de Machine Learning entrenado y lo utiliza para
    realizar predicciones sobre nuevos datos climáticos.
    """
    def __init__(self, modelo_cargado):
        """
        Inicializa el Predictor con una instancia de un modelo ya cargado.
        
        :param modelo_cargado: El objeto del modelo (ej. de scikit-learn) cargado con joblib.
        """
        self.modelo = modelo_cargado
        if self.modelo:
            logger.info("Predictor inicializado con un modelo cargado.")
        else:
            logger.warning("Predictor inicializado sin un modelo. No podrá realizar predicciones.")

    def predecir(self, temperatura: float, humedad: int, lluvia: float) -> tuple[int, float] | None:
        """
        Realiza una predicción de riesgo basada en los datos de entrada.

        :return: Una tupla (predicción_binaria, probabilidad_de_riesgo) o None si no hay modelo.
        """
        if not self.modelo:
            logger.error("El modelo no está disponible para realizar predicciones.")
            return None

        try:
            # Preparar los datos de entrada en el formato correcto para scikit-learn
            entrada = np.array([[temperatura, humedad, lluvia]])
            
            # Realizar la predicción
            resultado_binario = self.modelo.predict(entrada)[0]
            probabilidades = self.modelo.predict_proba(entrada)[0]
            
            # La probabilidad de riesgo es la probabilidad de la clase '1'
            probabilidad_riesgo = probabilidades[1]

            logger.info(f"Predicción: {'RIESGO' if resultado_binario == 1 else 'NORMAL'}. "
                        f"Confianza de riesgo: {probabilidad_riesgo:.2%}")

            return resultado_binario, probabilidad_riesgo
            
        except Exception as e:
            logger.error(f"Error durante la predicción: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # Ejemplo de cómo se integraría y usaría la nueva clase
    
    # 1. La carga del modelo ahora es responsabilidad del orquestador
    MODELO_FILE = "modelo_riesgo.pkl"
    modelo_entrenado = None
    try:
        modelo_entrenado = joblib.load(MODELO_FILE)
        logger.info(f"Modelo de prueba cargado desde '{MODELO_FILE}'.")
    except FileNotFoundError:
        logger.error(f"Archivo de modelo '{MODELO_FILE}' no encontrado para la prueba.")
    except Exception as e:
        logger.error(f"Error cargando modelo de prueba: {e}")

    # 2. Se "inyecta" el modelo cargado en el Predictor
    predictor = Predictor(modelo_cargado=modelo_entrenado)

    # 3. Se realizan las predicciones
    if predictor.modelo:
        # 🔬 Test de ejemplo
        temp = 30.0
        humedad = 85
        lluvia = 10

        res = predictor.predecir(temp, humedad, lluvia)
        if res:
            resultado, probabilidad = res
            print(f"Resultado del Test: {resultado}, Probabilidad de Riesgo: {probabilidad:.2%}")
