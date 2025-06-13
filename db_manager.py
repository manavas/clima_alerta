# db_manager.py

import sqlite3
from logger import logger

class DBManager:
    """
    Gestor de base de datos SQLite con manejo de contexto para asegurar
    que las conexiones se abran y cierren de forma segura.
    """
    def __init__(self, db_name="clima_alerta.db"):
        self.db_name = db_name
        self.conn = None

    def __enter__(self):
        """Establece la conexión a la BD y crea las tablas si no existen."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            logger.info(f"Conexión abierta con la base de datos '{self.db_name}'")
            self._create_tables()
            return self
        except sqlite3.Error as e:
            logger.critical(f"No se pudo conectar a la base de datos: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del contexto."""
        if self.conn:
            self.conn.close()
            logger.info(f"Conexión con la base de datos '{self.db_name}' cerrada.")

    def _create_tables(self):
        """Define y crea todas las tablas necesarias con las relaciones correctas."""
        logger.info("Verificando/creando tablas...")
        try:
            with self.conn:
                # La tabla 'historico' guardará todos los registros climáticos
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS historico (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME,
                        temperatura REAL,
                        humedad INTEGER,
                        lluvia REAL,
                        clima TEXT,
                        viento_kmh REAL
                    )
                ''')
                # La tabla 'alertas_emitidas' ahora se relaciona con un registro climático específico
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS alertas_emitidas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        tipo_alerta TEXT,
                        descripcion TEXT,
                        clima_id INTEGER,
                        FOREIGN KEY (clima_id) REFERENCES historico (id)
                    )
                ''')
                # La tabla 'feedback_usuario' se relaciona con una alerta específica
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS feedback_usuario (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        alerta_id INTEGER NOT NULL,
                        feedback TEXT NOT NULL,
                        FOREIGN KEY (alerta_id) REFERENCES alertas_emitidas (id)
                    )
                ''')
            logger.info("Tablas verificadas correctamente.")
        except sqlite3.Error as e:
            logger.error(f"Error creando tablas: {e}")

    def _execute_write_query(self, query, params=(), log_success_msg=""):
        """Ejecuta una consulta de escritura (INSERT, UPDATE) y devuelve el ID de la fila insertada."""
        try:
            with self.conn:
                cursor = self.conn.execute(query, params)
            if log_success_msg:
                logger.info(log_success_msg)
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error en consulta de escritura: {e} | Query: {query}")
            return None

    def execute_select_query(self, query, params=()):
        """Ejecuta una consulta SELECT y devuelve todos los resultados."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error en consulta SELECT: {e} | Query: {query}")
            return None

    def insert_historico_clima(self, timestamp, temperatura, humedad, lluvia, clima, viento_kmh):
        """Inserta un nuevo registro de clima en la tabla histórica y devuelve su ID."""
        query = '''INSERT INTO historico (timestamp, temperatura, humedad, lluvia, clima, viento_kmh)
                   VALUES (?, ?, ?, ?, ?, ?)'''
        params = (timestamp, temperatura, humedad, lluvia, clima, viento_kmh)
        return self._execute_write_query(query, params, "Datos de clima insertados en histórico.")

    def insert_alerta_emitida(self, tipo_alerta, descripcion, clima_id):
        """Inserta una nueva alerta, asociándola con un registro de clima."""
        query = '''INSERT INTO alertas_emitidas (tipo_alerta, descripcion, clima_id)
                   VALUES (?, ?, ?)'''
        return self._execute_write_query(query, (tipo_alerta, descripcion, clima_id), f"Alerta '{tipo_alerta}' registrada.")

    def insert_feedback(self, alerta_id, feedback):
        """Inserta el feedback de un usuario para una alerta específica."""
        query = '''INSERT INTO feedback_usuario (alerta_id, feedback) VALUES (?, ?)'''
        return self._execute_write_query(query, (alerta_id, feedback), "Feedback de usuario registrado.")

    def get_status_summary(self):
        """Consulta un resumen del estado del sistema para el bot."""
        summary = {"total": 0, "ultimo": "N/A"}
        try:
            # Usamos el método genérico para leer de forma segura
            total_res = self.execute_select_query("SELECT COUNT(*) FROM historico")
            if total_res: summary["total"] = total_res[0][0]
            
            ultimo_res = self.execute_select_query("SELECT timestamp FROM historico ORDER BY id DESC LIMIT 1")
            if ultimo_res: summary["ultimo"] = ultimo_res[0][0]
            
            return summary
        except Exception as e:
            logger.error(f"Error al obtener el resumen de estado: {e}")
            return summary
