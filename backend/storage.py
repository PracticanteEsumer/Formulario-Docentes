import mysql.connector
from mysql.connector import Error

#  Conexión a la base de datos
def get_db():
     connection = None
     try:
         # Conectamos a la base de datos
         connection = mysql.connector.connect(
             host="127.0.0.1",
             user="root",
             password="",
             database="db_docentes"
         )
     except Error as e:
         print(f"Error: '{e}'")
     return connection