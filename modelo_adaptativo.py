# modelo_adaptativo.py

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from logger import logger
from db_manager import DBManager # <-- Importamos nuestro gestor

MODELO_FILE = "modelo_riesgo.pkl"

class ModeloAdaptativo:
    """
    Entrena un modelo de clasificación para predecir el riesgo climático
    basado en el feedback histórico de los usuarios.
    """
    def __init__(self, db_manager: DBManager):
        """Inicializa el modelo con una instancia del DBManager."""
        self.db = db_manager
        self.modelo = None
        logger.info("Módulo de Modelo Adaptativo inicializado.")

    def _cargar_datos_entrenamiento(self):
        """Carga y procesa los datos desde la BD usando la consulta SQL correcta."""
        query = """
            SELECT
                h.temperatura, h.humedad, h.lluvia, f.feedback
            FROM
                feedback_usuario f
            JOIN
                alertas_emitidas a ON f.alerta_id = a.id
            JOIN
                historico h ON a.clima_id = h.id
            WHERE
                h.temperatura IS NOT NULL AND f.feedback IN ('bien', 'mal')
        """
        try:
            registros = self.db.execute_select_query(query)
            if not registros:
                return None, None

            X = []
            y = []
            for temp, hum, lluvia, feedback in registros:
                # Asegurarnos de que los datos son numéricos y no nulos
                if all(v is not None for v in [temp, hum, lluvia]):
                    X.append([temp, hum, lluvia])
                    # Mapeo: 'mal' (hubo un riesgo no detectado o mal evaluado) -> 1
                    # 'bien' (la alerta fue correcta o no hubo nada) -> 0
                    y.append(1 if feedback == "mal" else 0)

            logger.info(f"Se cargaron {len(X)} registros de entrenamiento válidos.")
            return np.array(X), np.array(y)
        except Exception as e:
            logger.error(f"Error cargando datos de entrenamiento: {e}", exc_info=True)
            return None, None

    def entrenar_y_guardar(self):
        """
        Orquesta el flujo completo de entrenamiento, evaluación y guardado del modelo.
        """
        X, y = self._cargar_datos_entrenamiento()

        if X is None or len(X) < 20: # Umbral mínimo de datos para entrenar
            logger.warning(f"No hay suficientes datos ({len(X if X is not None else [])}/20) para entrenar un nuevo modelo.")
            return

        # Dividir los datos manteniendo la proporción de clases (stratify=y)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )

        # Inicializar el clasificador con manejo de desbalance de clases
        self.modelo = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight='balanced' # <-- ¡Mejora clave!
        )
        
        self.modelo.fit(X_train, y_train)

        # Evaluar el modelo
        y_pred = self.modelo.predict(X_test)
        reporte = classification_report(y_test, y_pred, target_names=['Normal (0)', 'Riesgo (1)'])
        
        logger.info("--- Reporte de Clasificación del Modelo ---")
        # El logger puede no mostrar bien el formato, pero en consola se verá perfecto.
        print("\n" + reporte) 
        logger.info("--- Fin del Reporte ---")

        # Guardar el modelo entrenado
        try:
            joblib.dump(self.modelo, MODELO_FILE)
            logger.info(f"Modelo guardado exitosamente en '{MODELO_FILE}'.")
        except Exception as e:
            logger.error(f"Error al guardar el modelo: {e}")

    @staticmethod
    def cargar_modelo(path=MODELO_FILE):
        """Método estático para cargar el modelo desde cualquier parte de la aplicación."""
        try:
            modelo = joblib.load(path)
            logger.info(f"Modelo cargado desde '{path}'.")
            return modelo
        except FileNotFoundError:
            logger.warning(f"No se encontró un archivo de modelo en '{path}'. Se operará sin modelo predictivo.")
            return None
        except Exception as e:
            logger.error(f"Error al cargar el modelo: {e}")
            return None

if __name__ == '__main__':
    # Ejemplo de cómo se ejecutaría este script (ej. con un cron job)
    logger.info("Iniciando proceso de re-entrenamiento del modelo adaptativo...")
    try:
        with DBManager() as db:
            entrenador = ModeloAdaptativo(db_manager=db)
            entrenador.entrenar_y_guardar()
        logger.info("Proceso de re-entrenamiento finalizado.")
    except Exception as e:
        logger.critical(f"El proceso de entrenamiento falló de forma crítica: {e}", exc_info=True)
