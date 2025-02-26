from fastapi import FastAPI, File, Form, HTTPException,Response, UploadFile,Query
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse    
from fastapi.staticfiles import StaticFiles
import os
import pandas as pd
from datetime import datetime
from storage import get_db
from mysql.connector import Error
from typing import Optional
from pydantic import BaseModel
from io import BytesIO

# Inicializar la API
app = FastAPI()

# Diccionario con usuarios y contraseñas
users={
    "admin1": {"password": "admin1", "role": "admin"},
    "admin2": {"password": "admin2", "role": "viewer_downloader"},
    "admin3": {"password": "admin3", "role": "viewer"}
}


# Montar la carpeta estática para que FastAPI reconozca los archivos de estilo CSS
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend/static")), name="static")

# Montar la carpeta 'CarpetaInfo' como una carpeta estática para acceder a los archivos PDF
app.mount("/CarpetaInfo", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../CarpetaInfo")), name="CarpetaInfo")


# Definir el modelo Docente
class Docente(BaseModel):
    marca_temporal: str
    nombre_completo: str
    correo_electronico: str
    numero_celular: str
    otro_numero_contacto: Optional[str] = None
    envio_whatsapp: str
    lugar_residencia: str
    nivel_formacion: str
    titulos_pregrado: str
    titulos_posgrado: str
    areas_especializacion: str
    resumen_experiencia: str
    certificaciones: str
    disponibilidad_lunes: str
    disponibilidad_martes: str
    disponibilidad_miercoles: str
    disponibilidad_jueves: str
    disponibilidad_sabado: str
    disponibilidad_viajar: str
    equipo_conexion_estable: str
    estilo_formador: str
    metodologia: str
    casos_impacto: str
    restriccion_contractual: str
    hoja_vida: Optional[str] = None
    video_enlace: Optional[str] = None
    aviso_proteccion_datos: bool


# Función asíncrona para insertar un docente en la base de datos
async def insert_docente(connection, docente_data):
    cursor = connection.cursor()
    query = """
        INSERT INTO docentes (
            marca_temporal, nombre_completo, correo_electronico, numero_celular,
            otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
            titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
            certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
            disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable,
            estilo_formador, metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace,
            aviso_proteccion_datos
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    try:
        cursor.execute(query, docente_data)
        connection.commit()  # Confirmar la transacción
    except Error as e:
        print(f"Error al insertar docente: {e}")
    finally:
        cursor.close()

# Función asíncrona para procesar el archivo Excel y guardar los datos en la BD
async def process_excel(file: UploadFile):
    # Leer el archivo en bytes
    file_bytes = await file.read()
    df = pd.read_excel(BytesIO(file_bytes))
    
    # Limpiar espacios en blanco al inicio y final de cada nombre de columna
    df.columns = df.columns.map(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Imprimir columnas para verificar (puedes comentar esta línea en producción)
    print("Columnas en el Excel:", df.columns.tolist())
    
    # Lista de columnas esperadas (deben coincidir exactamente con los encabezados después de aplicar strip())
    columnas_esperadas = [
        "Marca temporal",
        "¿Cuál es tu nombre completo?",
        "Correo electrónico que más revisas",
        "Número de celular",
        "¿Tienes otro número de contacto?",
        "¿Permites el envío de mensajes vía WhatsApp?",
        "Lugar de residencia:",
        "¿Cuál es tu último nivel de formación?",
        "Título(s) de pregrado obtenido(s)",
        "Título(s) de posgrado obtenido(s)",
        "¿Cuál o cuáles son tus principales áreas de especialización o dónde te consideras el más teso(a)? Selecciona máximo cinco.",
        "Compártenos un breve resumen de tu experiencia en formación, consultoría o talleres para emprendedor@s y empresari@s (máximo 3 líneas).",
        "¿Tienes certificaciones o estudios relevantes para las áreas de especialización que elegiste?",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Lunes]",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Martes]",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Miércoles ]",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Jueves]",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Sábado]",
        "¿Tienes disponibilidad para viajar a otros municipios/departamentos?",
        "¿Cuentas con equipo y conexión estable para sesiones virtuales? (Sí / No)",
        "¿Cómo describes tu estilo como formador(a) o consultor(a)?",
        "¿Qué metodología(s) utilizas(s) para asegurar la participación de los emprendedores y empresarios en tus sesiones?",
        "¿Podrías mencionar uno o dos casos o experiencias en la que hayas generado un impacto significativo en un grupo de emprendedores o empresarios?",
        "¿Tienes algún tipo de restricción contractual con otra organización que pueda afectar tu participación en nuestras actividades?",
        "Adjunta tu hoja de vida y/o portafolio de experiencias en un solo archivo en formato PDF",
        "Nos encantaría ver un video corto de máximo 2 minutos donde compartas tu experiencia o metodología. Si lo deseas adjunta, el enlace.",
        "La Institución Universitaria Esumer cumple con la normatividad vigente en materia de protección de datos. Los datos suministrados sólo serán utilizados para efectos del banco de talentos Esumer. Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión, portabilidad y oposición al tratamiento de tus datos mediante el correo electrónico: emprendimiento.investigacion@esumer.edu.co"
    ]
    
    # Verificar que todas las columnas esperadas existan en el DataFrame
    for col in columnas_esperadas:
        if col not in df.columns:
            raise KeyError(f"Falta la columna esperada: '{col}'")
    
    # Obtener la conexión a la base de datos
    connection = get_db()
    if connection is None:
        print("No se pudo conectar a la base de datos.")
        return
    
    # Procesar cada fila del DataFrame y mapear a los campos del modelo Docente
    for index, row in df.iterrows():
        try:
            marca_temporal = row["Marca temporal"]
            nombre_completo = row["¿Cuál es tu nombre completo?"]
            correo_electronico = row["Correo electrónico que más revisas"]
            numero_celular = row["Número de celular"]
            otro_numero_contacto = row["¿Tienes otro número de contacto?"] if pd.notna(row["¿Tienes otro número de contacto?"]) else None
            envio_whatsapp = row["¿Permites el envío de mensajes vía WhatsApp?"]
            lugar_residencia = row["Lugar de residencia:"]
            nivel_formacion = row["¿Cuál es tu último nivel de formación?"]
            titulos_pregrado = row["Título(s) de pregrado obtenido(s)"]
            titulos_posgrado = row["Título(s) de posgrado obtenido(s)"]
            areas_especializacion = row["¿Cuál o cuáles son tus principales áreas de especialización o dónde te consideras el más teso(a)? Selecciona máximo cinco."]
            resumen_experiencia = row["Compártenos un breve resumen de tu experiencia en formación, consultoría o talleres para emprendedor@s y empresari@s (máximo 3 líneas)."]
            certificaciones = row["¿Tienes certificaciones o estudios relevantes para las áreas de especialización que elegiste?"]
            disponibilidad_lunes = row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Lunes]"]
            disponibilidad_martes = row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Martes]"]
            disponibilidad_miercoles = row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Miércoles ]"]
            disponibilidad_jueves = row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Jueves]"]
            disponibilidad_sabado = row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Sábado]"]
            disponibilidad_viajar = row["¿Tienes disponibilidad para viajar a otros municipios/departamentos?"]
            equipo_conexion_estable = row["¿Cuentas con equipo y conexión estable para sesiones virtuales? (Sí / No)"]
            estilo_formador = row["¿Cómo describes tu estilo como formador(a) o consultor(a)?"]
            metodologia = row["¿Qué metodología(s) utilizas(s) para asegurar la participación de los emprendedores y empresarios en tus sesiones?"]
            casos_impacto = row["¿Podrías mencionar uno o dos casos o experiencias en la que hayas generado un impacto significativo en un grupo de emprendedores o empresarios?"]
            restriccion_contractual = row["¿Tienes algún tipo de restricción contractual con otra organización que pueda afectar tu participación en nuestras actividades?"]
            hoja_vida = row["Adjunta tu hoja de vida y/o portafolio de experiencias en un solo archivo en formato PDF"] if pd.notna(row["Adjunta tu hoja de vida y/o portafolio de experiencias en un solo archivo en formato PDF"]) else None
            video_enlace = row["Nos encantaría ver un video corto de máximo 2 minutos donde compartas tu experiencia o metodología. Si lo deseas adjunta, el enlace."] if pd.notna(row["Nos encantaría ver un video corto de máximo 2 minutos donde compartas tu experiencia o metodología. Si lo deseas adjunta, el enlace."]) else None
            aviso_proteccion_datos = True if str(row["La Institución Universitaria Esumer cumple con la normatividad vigente en materia de protección de datos. Los datos suministrados sólo serán utilizados para efectos del banco de talentos Esumer. Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión, portabilidad y oposición al tratamiento de tus datos mediante el correo electrónico: emprendimiento.investigacion@esumer.edu.co"]).strip().lower().startswith("he leído") else False

            docente_data = (
                marca_temporal, nombre_completo, correo_electronico, numero_celular,
                otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
                titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
                certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
                disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable,
                estilo_formador, metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace,
                aviso_proteccion_datos
            )
            await insert_docente(connection, docente_data)
        except KeyError as e:
            print(f"Error procesando fila {index}: {e}")
    connection.close()

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    await process_excel(file)
    return {"success": True, "message": "Archivo procesado y datos guardados en la base de datos."}



# Función para obtener los usuarios desde la base de datos
def get_teachers():
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener los usuarios
    query = """
        SELECT id, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
        envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
        titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
        disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
        metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos
        FROM docentes
    """
    cursor.execute(query)
    docentes = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    connection.close()

    return docentes

# Lista de columnas permitidas para el filtrado
ALLOWED_FILTERS = {
    "lugar_residencia",
    "nivel_formacion",
    "areas_especializacion",
    "disponibilidad_lunes",
    "disponibilidad_martes",
    "disponibilidad_miercoles",
    "disponibilidad_jueves",
    "disponibilidad_sabado",
    "disponibilidad_viajar",
    "equipo_conexion_estable",
    "restriccion_contractual"
}



# Primero definimos la ruta para obtener los valores únicos
@app.get("/teachers/distinct")
def get_distinct(field: str = Query(...)):
    if field not in ALLOWED_FILTERS:
        raise HTTPException(status_code=400, detail="El campo de filtro no es válido")
    
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    query = f"SELECT DISTINCT {field} FROM docentes"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    distinct_values = [row[field] for row in rows if row[field] is not None]
    
    cursor.close()
    connection.close()
    
    return distinct_values

# Luego definimos el endpoint para filtrar docentes
@app.get("/teachers/filter")
def filter_teachers(field: str = Query(...), value: str = Query(...)):
    if field not in ALLOWED_FILTERS:
        raise HTTPException(status_code=400, detail="El campo de filtro no es válido")
    
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    query = f"""
        SELECT id, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
        envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
        titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
        disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
        metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos
        FROM docentes
        WHERE {field} LIKE %s
    """
    cursor.execute(query, (f"%{value}%",))
    docentes = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return docentes

# Y finalmente el endpoint para el detalle del docente
@app.get("/teachers/{teacher_id}")
def get_teacher_detail(teacher_id: int):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT id, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
               envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
               titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
               disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
               metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos
        FROM docentes
        WHERE id = %s
    """
    cursor.execute(query, (teacher_id,))
    teacher = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if teacher is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    
    return teacher


    
# RUTAS DE DOCENTES 
@app.get("/admin", response_class=HTMLResponse)
async def list_docentes():
    # Obtener los usuarios usando la función de storage.py
    docentes = get_teachers()

    # Leer el archivo HTML
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/tableInfoDocentes.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inyectar los datos de los usuarios en el HTML
    table_rows = ""
    for docente in docentes:
        table_rows += f"""
            <tr>
                <td>{docente['nombre_completo']}</td>
                <td>{docente['correo_electronico']}</td>
                <td>{docente['numero_celular']}</td>
                <td>{docente['nivel_formacion']}</td>
            </tr>
        """
    
    # Reemplazamos el marcador en el HTML con las filas generadas
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)

    return HTMLResponse(content=html_content)


@app.get("/docentes_paginated", response_class=JSONResponse)
async def list_docentes_paginated(page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    """
    Obtiene la lista de docentes con paginación.
    """
    # Crear la conexión a la base de datos  
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta SQL para obtener el total de usuarios y la paginación
    query = """
        SELECT id, nombre_completo, correo_electronico, numero_celular,otro_numero_contacto,nivel_formacion,areas_especializacion
        FROM docentes
        LIMIT %s OFFSET %s
    """
    
    # Calcular el índice de inicio (OFFSET) y el número de usuarios por página (LIMIT)
    offset = (page - 1) * per_page
    cursor.execute(query, (per_page, offset))
    docentes = cursor.fetchall()

    # Consulta para obtener el número total de usuarios
    cursor.execute("SELECT COUNT(*) FROM docentes")
    total_docentes = cursor.fetchone()["COUNT(*)"]

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Calcular el número total de páginas
    total_pages = (total_docentes + per_page - 1) // per_page  # Redondeo hacia arriba
    
    return {
        "docentes": docentes,
        "total_docentes": total_docentes,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages  # Retornar el total de páginas
    }



@app.get("/docentes_search", response_class=JSONResponse)
async def search_docentes(query: str = Query(..., alias="query")):
    """
    Busca docentes por nombre, correo, número de celular, nivel de formación o áreas de especialización.
    """
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    search_query = """
        SELECT id, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto, nivel_formacion, areas_especializacion
        FROM docentes
        WHERE LOWER(nombre_completo) LIKE %s
           OR LOWER(correo_electronico) LIKE %s
           OR LOWER(numero_celular) LIKE %s
           OR LOWER(nivel_formacion) LIKE %s
           OR LOWER(areas_especializacion) LIKE %s
    """
    
    # Realizar la búsqueda usando el query proporcionado
    search_param = f"%{query.lower()}%"
    cursor.execute(search_query, (search_param, search_param, search_param, search_param, search_param))
    docentes = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"docentes": docentes}






# Cargar la página de inicio de sesión
@app.get("/", response_class=HTMLResponse)
async def index():
    # Ruta del archivo HTML de inicio
    index_path = os.path.join(os.path.dirname(__file__), "../frontend/inicio.html")
    with open(index_path, "r", encoding="utf-8") as f:
        # Retornamos la respuesta en HTML
        return HTMLResponse(content=f.read(), status_code=200)

# Manejo del inicio de sesión
@app.post("/login")
async def login(strUsuario: str = Form(...), strContrasenna: str = Form(...)):
    # Verificar que el usuario exista y que la contraseña sea correcta
    if strUsuario in users and users[strUsuario]["password"] == strContrasenna:
        # Si la validación es correcta, redirigir según el rol
        if users[strUsuario]["role"] == "admin":
            # Redirigir a la página de admin con un método GET
            return RedirectResponse(url="/admin", status_code=303)  # 303 See Other (GET)
        elif users[strUsuario]["role"] == "viewer_downloader":
            # Redirigir a la página del viewerDownloader con un método GET
            return RedirectResponse(url="/admin", status_code=303)  # 303 See Other (GET)
        else:
            # Redirigir a la página del viewer con un método GET
            return RedirectResponse(url="/admin",status_code=303)
    else:
        # Si la validación falla, lanzar un error 401
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# Vista para permisos de administrador
# @app.get("/admin")
# async def view_admin():
#     # Cargar la página HTML para el administrador
#     admin_page_path = os.path.join(os.path.dirname(__file__), "../frontend/tableInfoDocentes.html")
#     with open(admin_page_path, "r", encoding="utf-8") as f:
#         return HTMLResponse(content=f.read(), status_code=200)


@app.post("/logout")
async def logout(response: Response):
    # Eliminar la cookie de sesión
    response.delete_cookie("session") 
    
    # Redirigir al login
    return RedirectResponse(url="/", status_code=303)



