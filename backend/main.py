# =============================================================================
# IMPORTS Y CONFIGURACIÓN
# =============================================================================
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, Query, Depends, Cookie,Request    
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import pandas as pd
from datetime import datetime
from storage import get_db
from mysql.connector import Error
from typing import Optional
from pydantic import BaseModel
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP

# Inicializar la aplicación FastAPI
app = FastAPI()

# Montar archivos estáticos (CSS, PDFs, etc.)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend/static")),
    name="static"
)
app.mount(
    "/CarpetaInfo",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../CarpetaInfo")),
    name="CarpetaInfo"
)

# =============================================================================
# USUARIOS (Autenticación)
# =============================================================================
# Diccionario de usuarios
users = {
    "admin1": {"id": "10", "password": "admin1", "role": "admin", "nombre_completo": "Admin Uno"},
    "admin2": {"id": "11", "password": "admin2", "role": "admin", "nombre_completo": "Admin Dos"},
    "admin3": {"id": "12", "password": "admin3", "role": "admin", "nombre_completo": "Admin Tres"},
    "formacion empresarial": {"id": "1", "password": "admin3", "role": "admin", "nombre_completo": "Formación Empresarial"},
    "observatorio de tendencias": {"id": "2", "password": "admin3", "role": "admin", "nombre_completo": "Observatorio de Tendencias"},
    "emprendimiento": {"id": "4", "password": "admin3", "role": "admin", "nombre_completo": "Emprendimiento"},
    "coordinador1": {"id": "5", "password": "admin3", "role": "admin", "nombre_completo": "Coordinador Uno"},
    "coordinador2": {"id": "6", "password": "admin3", "role": "admin", "nombre_completo": "Coordinador Dos"},
    "vicerrectoria": {"id": "7", "password": "vice", "role": "admin", "nombre_completo": "Vicerrectoría"}
}

# Crear un mapeo de user_id a usuario (nombre completo, etc.)
users_by_id = { info["id"]: info for info in users.values() }


# =============================================================================
# MODELOS Pydantic
# =============================================================================
class Docente(BaseModel):
    identificacion: str
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
    disponibilidad_viernes: str
    disponibilidad_viajar: str
    equipo_conexion_estable: str
    estilo_formador: str
    metodologia: str
    casos_impacto: str
    restriccion_contractual: str
    hoja_vida: Optional[str] = None
    video_enlace: Optional[str] = None
    aviso_proteccion_datos: str
    disponibilidad_sabado: str
    # Campos para notas
    puntuacion_total: int
    total_usuarios: int
    promedio: str

class NotaModel(BaseModel):
    nota: int
    str_Evi: str
    str_ClienteExterno: str


class CalificacionModel(BaseModel):
    id: int = None  
    docente_identificacion: str
    user_id: str
    nota: int
    str_Evi: str
    str_ClienteExterno: str
    
    created_at: datetime = None

    class Config:
        from_attributes = True  

# =============================================================================
# FUNCIONES UTILITARIAS
# =============================================================================
# Función para insertar un docente en la base de datos
async def insert_docente(connection, docente_data):
    cursor = connection.cursor()
    query = """
        INSERT INTO docentes (
            identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular,
            otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
            titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
            certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
            disponibilidad_jueves, disponibilidad_viernes, disponibilidad_viajar, equipo_conexion_estable,
            estilo_formador, metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace,
            aviso_proteccion_datos, disponibilidad_sabado
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    try:
        cursor.execute(query, docente_data)
        connection.commit()
    except Error as e:
        print(f"Error al insertar docente: {e}")
    finally:
        cursor.close()

# Función para procesar el archivo Excel y guardar los docentes en la BD
async def process_excel(file: UploadFile) -> dict:
    file_bytes = await file.read()
    df = pd.read_excel(BytesIO(file_bytes))
    
    # Limpiar nombres de columnas
    df.columns = df.columns.map(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Lista de columnas esperadas
    columnas_esperadas = [
        "Marca temporal",
        "¿Cuál es tu nombre completo?",
        "Correo electrónico que más revisas",
        "Número de celular",
        "¿Tienes otro número de contacto?",
        "¿Permites el envío de mensajes vía WhatsApp?",
        "Lugar de residencia (Ciudad):",
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
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Viernes]",
        "¿Tienes disponibilidad para viajar a otros municipios/departamentos?",
        "¿Cuentas con equipo y conexión estable para sesiones virtuales? (Sí / No)",
        "¿Cómo describes tu estilo como formador(a) o consultor(a)?",
        "¿Qué metodología(s) utilizas(s) para asegurar la participación de los emprendedores y empresarios en tus sesiones?",
        "¿Podrías mencionar uno o dos casos o experiencias en la que hayas generado un impacto significativo en un grupo de emprendedores o empresarios?",
        "¿Tienes algún tipo de restricción contractual con otra organización que pueda afectar tu participación en nuestras actividades?",
        "Adjunta tu hoja de vida y/o portafolio de experiencias en un solo archivo en formato PDF",
        "Nos encantaría ver un video corto de máximo 2 minutos donde compartas tu experiencia o metodología. Si lo deseas adjunta, el enlace.",
        "La Institución Universitaria Esumer cumple con la normatividad vigente en materia de protección de datos. Los datos suministrados sólo serán utilizados para efectos del banco de talentos Esumer. Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión, portabilidad y oposición al tratamiento de tus datos mediante el correo electrónico: emprendimiento.investigacion@esumer.edu.co",
        "¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Sábado ]",
        "Numero de documento de identidad"
    ]
    
    # Verificar que todas las columnas existan
    for col in columnas_esperadas:
        if col not in df.columns:
            raise KeyError(f"Falta la columna esperada: '{col}'")
    
    connection = get_db()
    if connection is None:
        return {"error": "No se pudo conectar a la base de datos."}
    
    inserted_count = 0
    duplicate_count = 0
    duplicate_ids = []
    
    def valida_valor(valor):
        return valor if pd.notna(valor) else "No aplica"
    
    for index, row in df.iterrows():
        try:
            marca_temporal       = valida_valor(row["Marca temporal"])
            nombre_completo      = valida_valor(row["¿Cuál es tu nombre completo?"])
            correo_electronico   = valida_valor(row["Correo electrónico que más revisas"])
            numero_celular       = valida_valor(row["Número de celular"])
            otro_numero_contacto = valida_valor(row["¿Tienes otro número de contacto?"])
            envio_whatsapp       = valida_valor(row["¿Permites el envío de mensajes vía WhatsApp?"])
            lugar_residencia     = valida_valor(row["Lugar de residencia (Ciudad):"])
            nivel_formacion      = valida_valor(row["¿Cuál es tu último nivel de formación?"])
            titulos_pregrado     = valida_valor(row["Título(s) de pregrado obtenido(s)"])
            titulos_posgrado     = valida_valor(row["Título(s) de posgrado obtenido(s)"])
            areas_especializacion= valida_valor(row["¿Cuál o cuáles son tus principales áreas de especialización o dónde te consideras el más teso(a)? Selecciona máximo cinco."])
            resumen_experiencia  = valida_valor(row["Compártenos un breve resumen de tu experiencia en formación, consultoría o talleres para emprendedor@s y empresari@s (máximo 3 líneas)."])
            certificaciones      = valida_valor(row["¿Tienes certificaciones o estudios relevantes para las áreas de especialización que elegiste?"])
            disponibilidad_lunes = valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Lunes]"])
            disponibilidad_martes= valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Martes]"])
            disponibilidad_miercoles = valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Miércoles ]"])
            disponibilidad_jueves= valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Jueves]"])
            disponibilidad_viernes= valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Viernes]"])
            disponibilidad_viajar= valida_valor(row["¿Tienes disponibilidad para viajar a otros municipios/departamentos?"])
            equipo_conexion_estable = valida_valor(row["¿Cuentas con equipo y conexión estable para sesiones virtuales? (Sí / No)"])
            estilo_formador      = valida_valor(row["¿Cómo describes tu estilo como formador(a) o consultor(a)?"])
            metodologia          = valida_valor(row["¿Qué metodología(s) utilizas(s) para asegurar la participación de los emprendedores y empresarios en tus sesiones?"])
            casos_impacto        = valida_valor(row["¿Podrías mencionar uno o dos casos o experiencias en la que hayas generado un impacto significativo en un grupo de emprendedores o empresarios?"])
            restriccion_contractual = valida_valor(row["¿Tienes algún tipo de restricción contractual con otra organización que pueda afectar tu participación en nuestras actividades?"])
            hoja_vida            = valida_valor(row["Adjunta tu hoja de vida y/o portafolio de experiencias en un solo archivo en formato PDF"])
            video_enlace         = valida_valor(row["Nos encantaría ver un video corto de máximo 2 minutos donde compartas tu experiencia o metodología. Si lo deseas adjunta, el enlace."])
            identificacion       = valida_valor(row["Numero de documento de identidad"])
            
            aviso_raw = valida_valor(row["La Institución Universitaria Esumer cumple con la normatividad vigente en materia de protección de datos. Los datos suministrados sólo serán utilizados para efectos del banco de talentos Esumer. Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión, portabilidad y oposición al tratamiento de tus datos mediante el correo electrónico: emprendimiento.investigacion@esumer.edu.co"])
            if aviso_raw == "No aplica":
                aviso_proteccion_datos = "No aplica"
            else:
                aviso_proteccion_datos = "Sí" if str(aviso_raw).strip().lower().startswith("he leído") else "No"
            
            disponibilidad_sabado = valida_valor(row["¿En qué días y horas tienes mayor disponibilidad para actividades presenciales o virtuales?  [Sábado ]"])
            
            docente_data = (
                identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular,
                otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
                titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
                certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
                disponibilidad_jueves, disponibilidad_viernes, disponibilidad_viajar, equipo_conexion_estable,
                estilo_formador, metodologia, casos_impacto, restriccion_contractual,
                hoja_vida, video_enlace, aviso_proteccion_datos, disponibilidad_sabado
            )
            
            # Verificar duplicados por correo electrónico
            check_cursor = connection.cursor()
            check_query = "SELECT COUNT(*) FROM docentes WHERE identificacion = %s"
            check_cursor.execute(check_query, (identificacion,))
            result = check_cursor.fetchone()
            check_cursor.close()
            
            if result and result[0] > 0:
                duplicate_count += 1
                duplicate_ids.append(identificacion)
                print(f"La identificación {identificacion} ya se encuentra registrado. Saltando esta fila.")
                continue

            await insert_docente(connection, docente_data)
            inserted_count += 1
        except KeyError as e:
            print(f"Error procesando fila {index}: {e}")
    
    connection.close()
    return {
        "inserted": inserted_count,
        "duplicates": duplicate_count,
        "duplicate_ids": duplicate_ids
    }

# =============================================================================
# RUTAS DE DOCENTES
# =============================================================================
# Endpoint para cargar archivo Excel y procesar datos
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    result = await process_excel(file)
    message = f"Se insertaron {result['inserted']} registros correctamente."
    if result["duplicates"] > 0:
        duplicate_message = (
            "Error: Las siguientes identifiaciones ya se encuentran registrados:<br>" +
            "<br>".join(str(id) for id in result["duplicate_ids"])

        )
        message += "<br>" + duplicate_message
    return {"success": True, "message": message}

# Función para obtener todos los docentes de la BD
def get_teachers(current_user: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    query = """ 
        SELECT d.identificacion, d.nombre_completo, d.correo_electronico, d.numero_celular, d.nivel_formacion, d.promedio,
        c.nota as user_nota
        FROM docentes d
        LEFT JOIN calificaciones c 
        ON d.identificacion = c.docente_identificacion AND c.user_id = %s
    """
    cursor.execute(query, (current_user,))
    docentes = cursor.fetchall()
    cursor.close()
    connection.close()
    return docentes


# Lista de columnas permitidas para filtrar docentes
ALLOWED_FILTERS = {
    "lugar_residencia",
    "nivel_formacion",
    "areas_especializacion",
    "disponibilidad_lunes",
    "disponibilidad_martes",
    "disponibilidad_miercoles",
    "disponibilidad_jueves",
    "disponibilidad_viernes",
    "disponibilidad_sabado",
    "disponibilidad_viajar",
    "equipo_conexion_estable",
    "restriccion_contractual"
}

# Endpoint para obtener valores únicos (distinct) de una columna
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

# Endpoint para filtrar docentes según un campo y valor
@app.get("/teachers/filter")
def filter_teachers(field: str = Query(...), value: str = Query(...)):
    if field not in ALLOWED_FILTERS:
        raise HTTPException(status_code=400, detail="El campo de filtro no es válido")
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    query = f"""
        SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
        envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
        titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
        disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
        metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos, promedio
        FROM docentes
        WHERE {field} LIKE %s
    """
    cursor.execute(query, (f"%{value}%",))
    docentes = cursor.fetchall()
    cursor.close()
    connection.close()
    return docentes


# Endpoint para obtener el detalle de un docente por identificación
# @app.get("/teachers/{teacher_id}")
# def get_teacher_detail(teacher_id: str):
#     connection = get_db()
#     cursor = connection.cursor(dictionary=True)
#     query = """
#         SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
#                envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
#                titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
#                disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
#                metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos, promedio
#         FROM docentes
#         WHERE identificacion = %s
#     """
#     cursor.execute(query, (teacher_id,))
#     teacher = cursor.fetchone()
#     cursor.close()
#     connection.close()
#     if teacher is None:
#         raise HTTPException(status_code=404, detail="Docente no encontrado")
#     return teacher



# Endpoint para obtener docentes paginados
@app.get("/docentes_paginated", response_class=JSONResponse)
async def list_docentes_paginated(request: Request, page: int = Query(1, alias="page"), per_page: int = Query(10, alias="per_page")):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    # Obtener el usuario actual desde la cookie o la autenticación
    current_user = request.cookies.get("user_id")  # O usa tu método de autenticación
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    # Consulta SQL para traer los docentes y la calificación del usuario actual (si existe)
    query = """
        SELECT d.identificacion, d.nombre_completo, d.correo_electronico, d.numero_celular, 
               d.nivel_formacion, d.areas_especializacion, d.promedio, 
               c.nota as user_nota
        FROM docentes d
        LEFT JOIN calificaciones c 
        ON d.identificacion = c.docente_identificacion AND c.user_id = %s
        LIMIT %s OFFSET %s
    """
    offset = (page - 1) * per_page
    cursor.execute(query, (current_user, per_page, offset))
    docentes = cursor.fetchall()

    # Obtener el total de docentes
    cursor.execute("SELECT COUNT(*) as total FROM docentes")
    total_docentes = cursor.fetchone()["total"]

    # Cálculo de total de páginas
    total_pages = (total_docentes + per_page - 1) // per_page

    cursor.close()
    connection.close()

    # Armar la respuesta JSON
    return {
        "docentes": docentes,
        "total_docentes": total_docentes,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


@app.get("/docentes_search", response_class=JSONResponse)
async def search_docentes(query: str = Query(..., alias="query")):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    # Preparamos el parámetro para la búsqueda textual
    search_param = f"%{query.lower()}%"
    
    # Intentamos convertir la query a un número para filtrar por nota (promedio)
    try:
        numeric_value = float(query)
    except ValueError:
        numeric_value = -1  # Valor que no se encontrará (suponiendo que el promedio no puede ser negativo)

    # Se agregan 4 condiciones: identificación, nombre, nivel y promedio
    search_query = """
        SELECT identificacion, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto, 
               nivel_formacion, areas_especializacion, promedio
        FROM docentes
        WHERE LOWER(identificacion) LIKE %s
           OR LOWER(nombre_completo) LIKE %s
           OR LOWER(nivel_formacion) LIKE %s
           OR promedio = %s
    """
    cursor.execute(search_query, (search_param, search_param, search_param, numeric_value))
    docentes = cursor.fetchall()
    cursor.close()
    connection.close()
    return {"docentes": docentes}



# Endpoint para la página de administración (HTML) que lista docentes
@app.get("/admin", response_class=HTMLResponse)
async def list_docentes(request: Request):
    # Supongamos que obtienes el usuario actual de las cookies o autenticación
    current_user = request.cookies.get("user_id")  # O usa tu método de autenticación
    docentes = get_teachers(current_user)
    template_path = os.path.join(os.path.dirname(__file__), "../frontend/tableInfoDocentes.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    table_rows = ""
    for docente in docentes:
        user_nota = docente['user_nota'] if docente['user_nota'] else "No calificado"
        table_rows += f"""
            <tr>
                <td>{docente['identificacion']}</td>
                <td>{docente['nombre_completo']}</td>
                <td>{docente['nivel_formacion']}</td>
                <td>{docente['promedio']}</td>
                <td>{user_nota}</td>
            </tr>
        """
    
    html_content = html_content.replace("<!-- rows-placeholder -->", table_rows)
    return HTMLResponse(content=html_content)


# =============================================================================
# RUTAS DE AUTENTICACIÓN Y USUARIOS
# =============================================================================
# Endpoint para mostrar la página de inicio de sesión
@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(os.path.dirname(__file__), "../frontend/inicio.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

# Endpoint para el manejo del inicio de sesión
@app.post("/login")
async def login(strUsuario: str = Form(...), strContrasenna: str = Form(...)):
    if strUsuario in users and users[strUsuario]["password"] == strContrasenna:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="user_id",
            value=users[strUsuario]["id"],
            httponly=False,  # Cambiar a True en producción
            secure=False,
            samesite="lax"
        )
        return response
    else:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# Endpoint para obtener el usuario actual (para depuración)
@app.get("/current_user")
async def current_user(user_id: str = Cookie(...)):
    return {"user_id": user_id}

# Dependencia para obtener el usuario actual a partir de la cookie "user_id"
def get_current_user(user_id: str = Cookie(...)):
    print("Current user ID from cookie:", user_id)
    if user_id not in [u["id"] for u in users.values()]:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    return user_id

# Endpoint para cerrar sesión (Logout)
@app.post("/logout")
async def logout(response: Response):
    # Se elimina la cookie "user_id"
    response.delete_cookie("user_id")   
    return RedirectResponse(url="/", status_code=303)

# =============================================================================
# RUTAS DE CALIFICACIONES
# =============================================================================
# Función para registrar la nota de un docente y actualizar sus datos

async def registrar_nota(connection, docente_identificacion: str, nueva_nota: int, current_user: str, str_Evi: str, str_ClienteExterno: str):
    cursor = connection.cursor(dictionary=True)
    try:
        # Verificar si el usuario ya calificó a este docente
        query_check = """
            SELECT * FROM calificaciones 
            WHERE docente_identificacion = %s AND user_id = %s
        """
        print(f"Verificando si el usuario {current_user} ya calificó al docente {docente_identificacion}...")
        cursor.execute(query_check, (docente_identificacion, current_user))
        existing = cursor.fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Ya has calificado a este docente.")
        
        # Insertar la nueva calificación en la tabla calificaciones
        query_insert = """
            INSERT INTO calificaciones (docente_identificacion, user_id, nota, str_Evi, str_ClienteExterno, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        print("Insertando nueva calificación...")
        cursor.execute(query_insert, (docente_identificacion, current_user, nueva_nota, str_Evi, str_ClienteExterno))
        
        # Obtener la puntuación total y el total de usuarios del docente
        query_select = """
            SELECT puntuacion_total, total_usuarios 
            FROM docentes 
            WHERE identificacion = %s
        """
        cursor.execute(query_select, (docente_identificacion,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        puntuacion_total = row["puntuacion_total"]
        total_usuarios = row["total_usuarios"]
        print(f"Puntuación actual: {puntuacion_total} con {total_usuarios} usuarios.")
        
        # Actualizar la puntuación y calcular el nuevo promedio
        nueva_puntuacion_total = puntuacion_total + nueva_nota
        nuevo_total_usuarios = total_usuarios + 1
        nuevo_promedio = nueva_puntuacion_total / nuevo_total_usuarios
        nuevo_promedio_decimal = Decimal(nuevo_promedio).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        print(f"Nueva puntuación total: {nueva_puntuacion_total}, Total usuarios: {nuevo_total_usuarios}, Nuevo promedio: {nuevo_promedio_decimal}")
        
        # Actualizar el registro del docente
        query_update = """
            UPDATE docentes 
            SET puntuacion_total = %s, total_usuarios = %s, promedio = %s
            WHERE identificacion = %s
        """
        cursor.execute(query_update, (nueva_puntuacion_total, nuevo_total_usuarios, nuevo_promedio_decimal, docente_identificacion))
        
        connection.commit()
        print("Transacción completada exitosamente.")
    except Exception as e:
        connection.rollback()
        print(f"Error durante el registro de nota: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al registrar la nota: {str(e)}")
    finally:
        cursor.close()
        connection.close()
    
    return {"mensaje": "Nota registrada exitosamente", "promedio_actual": str(nuevo_promedio_decimal)}


class EditarNotaRequest(BaseModel):
    nueva_nota: int
    str_Evi: Optional[str] = None
    str_ClienteExterno: Optional[str] = None
        
    class Config:
        from_attributes = True
        
    

# Modelo para la salida (opcional, para documentación y consistencia)
class CalificacionModel(BaseModel):
    id: Optional[int] = None
    docente_identificacion: str
    user_id: str
    nota: int
    str_Evi: Optional[str] = None
    str_ClienteExterno: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Endpoint para editar la nota de un docente
@app.put("/docentes/{docente_identificacion}/editar_nota", response_class=JSONResponse)
async def editar_nota_endpoint(
    docente_identificacion: str, 
    nota_request: EditarNotaRequest, 
    current_user: str = Depends(get_current_user),
    connection = Depends(get_db)
):
    # Validar la nueva nota (entre 1 y 5)
    if nota_request.nueva_nota < 1 or nota_request.nueva_nota > 5:
        raise HTTPException(status_code=400, detail="La nota debe estar entre 1 y 5.")

    try:
        resultado = await editar_nota(
            connection, 
            docente_identificacion, 
            nota_request.nueva_nota, 
            current_user, 
            nota_request.str_Evi, 
            nota_request.str_ClienteExterno
        )
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




async def editar_nota(connection, docente_identificacion: str, nueva_nota: int, current_user: str, str_Evi: str, str_ClienteExterno: str):
    cursor = connection.cursor(dictionary=True)
    try:
        # Verificar si el usuario ya calificó a este docente
        query_check = """
            SELECT * FROM calificaciones 
            WHERE docente_identificacion = %s AND user_id = %s
        """
        print(f"Verificando si el usuario {current_user} ya calificó al docente {docente_identificacion}...")
        cursor.execute(query_check, (docente_identificacion, current_user))
        existing = cursor.fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="No has calificado a este docente aún.")
        
        # Guardar la calificación anterior para actualizar correctamente la puntuación total
        nota_anterior = existing["nota"]
        
        # Actualizar la calificación en la tabla calificaciones (sin updated_at)
        query_update_calificacion = """
            UPDATE calificaciones 
            SET nota = %s, str_Evi = %s, str_ClienteExterno = %s
            WHERE docente_identificacion = %s AND user_id = %s
        """
        print(f"Actualizando calificación de {nota_anterior} a {nueva_nota}...")
        cursor.execute(query_update_calificacion, (nueva_nota, str_Evi, str_ClienteExterno, docente_identificacion, current_user))
        
        # Obtener la puntuación total y el total de usuarios del docente
        query_select = """
            SELECT puntuacion_total, total_usuarios 
            FROM docentes 
            WHERE identificacion = %s
        """
        cursor.execute(query_select, (docente_identificacion,))
        row = cursor.fetchone()
        
        if row is None:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        puntuacion_total = row["puntuacion_total"]
        total_usuarios = row["total_usuarios"]
        print(f"Puntuación actual: {puntuacion_total} con {total_usuarios} usuarios.")
        
        # Recalcular la puntuación total restando la nota anterior y sumando la nueva
        nueva_puntuacion_total = puntuacion_total - nota_anterior + nueva_nota
        nuevo_promedio = nueva_puntuacion_total / total_usuarios
        nuevo_promedio_decimal = Decimal(nuevo_promedio).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        print(f"Nueva puntuación total: {nueva_puntuacion_total}, Nuevo promedio: {nuevo_promedio_decimal}")
        
        # Actualizar el registro del docente con la nueva puntuación y promedio
        query_update_docente = """
            UPDATE docentes 
            SET puntuacion_total = %s, promedio = %s
            WHERE identificacion = %s
        """
        cursor.execute(query_update_docente, (nueva_puntuacion_total, nuevo_promedio_decimal, docente_identificacion))
        
        connection.commit()
        print("Transacción de actualización completada exitosamente.")
    except Exception as e:
        connection.rollback()
        print(f"Error durante la edición de la nota: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al editar la nota: {str(e)}")
    finally:
        cursor.close()
        connection.close()
    
    return {"mensaje": "Nota editada exitosamente", "promedio_actual": str(nuevo_promedio_decimal)}


def get_teachers_with_rating(current_user: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            d.identificacion,
            d.nombre_completo,
            d.correo_electronico,
            d.numero_celular,
            d.nivel_formacion,
            d.promedio,
            c.nota AS user_nota,
            c.str_Evi,
            c.str_ClienteExterno
        FROM docentes d
        LEFT JOIN calificaciones c 
            ON d.identificacion = c.docente_identificacion AND c.user_id = %s
    """
    cursor.execute(query, (current_user,))
    docentes = cursor.fetchall()
    cursor.close()
    connection.close()
    return docentes

@app.get("/docente/{docente_identificacion}/rating", response_class=JSONResponse)
async def get_rating_for_teacher(
    docente_identificacion: str, 
    current_user: str = Depends(get_current_user)
):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            nota,
            COALESCE(str_Evi, '') AS str_Evi,
            COALESCE(str_ClienteExterno, '') AS str_ClienteExterno
        FROM calificaciones
        WHERE docente_identificacion = %s AND user_id = %s
    """
    cursor.execute(query, (docente_identificacion, current_user))
    rating = cursor.fetchone()
    cursor.close()
    connection.close()
    
    # Si no hay calificación, se retornan valores por defecto
    if not rating:
        rating = {"nota": None, "str_Evi": "", "str_ClienteExterno": ""}
    return rating





# Endpoint para registrar la nota de un docente
@app.post("/docentes/{docente_identificacion}/nota", response_class=JSONResponse)
async def registrar_nota_endpoint(
    docente_identificacion: str,
    nota_model: NotaModel,
    connection = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    resultado = await registrar_nota(
        connection, 
        docente_identificacion, 
        nota_model.nota, 
        current_user, 
        nota_model.str_Evi, 
        nota_model.str_ClienteExterno
    )
    return resultado

async def eliminar_nota(connection, docente_identificacion: str, current_user: str):
    cursor = connection.cursor(dictionary=True)
    try:
        # Verificar si existe una calificación para este docente y usuario
        query_check = """
            SELECT * FROM calificaciones 
            WHERE docente_identificacion = %s AND user_id = %s
        """
        print(f"Verificando existencia de calificación para el docente {docente_identificacion} por el usuario {current_user}...")
        cursor.execute(query_check, (docente_identificacion, current_user))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="No existe calificación para este docente.")

        # Obtener la nota que se eliminará
        nota_a_eliminar = existing["nota"]

        # Eliminar la calificación de la tabla calificaciones
        query_delete = """
            DELETE FROM calificaciones
            WHERE docente_identificacion = %s AND user_id = %s
        """
        cursor.execute(query_delete, (docente_identificacion, current_user))

        # Obtener la puntuación total y el total de usuarios del docente
        query_select = """
            SELECT puntuacion_total, total_usuarios 
            FROM docentes 
            WHERE identificacion = %s
        """
        cursor.execute(query_select, (docente_identificacion,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        puntuacion_total = row["puntuacion_total"]
        total_usuarios = row["total_usuarios"]
        print(f"Puntuación actual: {puntuacion_total} con {total_usuarios} usuarios.")

        # Recalcular la puntuación total y el promedio:
        # Restar la nota eliminada y disminuir el total de usuarios.
        nueva_puntuacion_total = puntuacion_total - nota_a_eliminar
        nuevo_total_usuarios = total_usuarios - 1

        if nuevo_total_usuarios > 0:
            nuevo_promedio = nueva_puntuacion_total / nuevo_total_usuarios
            nuevo_promedio_decimal = Decimal(nuevo_promedio).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
        else:
            nuevo_promedio_decimal = "0.00"
            nueva_puntuacion_total = 0
            nuevo_total_usuarios = 0

        # Actualizar el registro del docente en la tabla docentes
        query_update_docente = """
            UPDATE docentes 
            SET puntuacion_total = %s, total_usuarios = %s, promedio = %s
            WHERE identificacion = %s
        """
        cursor.execute(query_update_docente, (nueva_puntuacion_total, nuevo_total_usuarios, nuevo_promedio_decimal, docente_identificacion))

        connection.commit()
        print("Calificación eliminada y docente actualizado correctamente.")
    except Exception as e:
        connection.rollback()
        print(f"Error al eliminar la nota: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar la nota: {str(e)}")
    finally:
        cursor.close()
        connection.close()
    
    return {"mensaje": "Calificación eliminada exitosamente", "promedio_actual": str(nuevo_promedio_decimal)}



@app.delete("/docentes/{docente_identificacion}/eliminar_nota", response_class=JSONResponse)
async def eliminar_nota_endpoint(
    docente_identificacion: str,
    current_user: str = Depends(get_current_user),
    connection = Depends(get_db)
):
    try:
        resultado = await eliminar_nota(connection, docente_identificacion, current_user)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/teachers/{teacher_id}", response_class=JSONResponse)
def get_teacher_detail(teacher_id: str, current_user: str = Depends(get_current_user)):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    # Consulta para obtener los datos básicos del docente
    query_teacher = """
        SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, 
               otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, 
               areas_especializacion, resumen_experiencia, titulos_posgrado, certificaciones, disponibilidad_lunes, 
               disponibilidad_martes, disponibilidad_miercoles, disponibilidad_jueves, disponibilidad_sabado, 
               disponibilidad_viajar, equipo_conexion_estable, estilo_formador, metodologia, casos_impacto, 
               restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos, promedio,
               puntuacion_total, total_usuarios
        FROM docentes
        WHERE identificacion = %s
    """
    cursor.execute(query_teacher, (teacher_id,))
    teacher = cursor.fetchone()
    if teacher is None:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    
    # Obtener las calificaciones
    if current_user == "7":  # Si el usuario es "vicerrectoria"
        query_notas = """
            SELECT nota, str_Evi, str_ClienteExterno, created_at, user_id
            FROM calificaciones
            WHERE docente_identificacion = %s
            ORDER BY created_at ASC
        """
        cursor.execute(query_notas, (teacher_id,))
        notas = cursor.fetchall()
        # Asignar el nombre del usuario usando el diccionario
        for nota in notas:
            uid = nota.get("user_id")
            nota["usuario_nombre"] = users_by_id.get(uid, {}).get("nombre_completo", "Desconocido")
        print("Notas obtenidas para vicerrectoria:", notas)
    else:
        # Obtener solo la nota del usuario actual
        query_notas = """
            SELECT nota, str_Evi, str_ClienteExterno, created_at, user_id
            FROM calificaciones
            WHERE docente_identificacion = %s AND user_id = %s
        """
        cursor.execute(query_notas, (teacher_id, current_user))
        nota = cursor.fetchone()
        notas = [nota] if nota else []
        
        # Asignar el nombre del usuario usando el diccionario
        if notas:
            uid = notas[0].get("user_id")
            notas[0]["usuario_nombre"] = users_by_id.get(uid, {}).get("nombre_completo", "Desconocido")
        print("Nota obtenida para usuario normal:", notas)

    teacher["notas"] = notas
    print("Teacher final:", teacher)
    cursor.close()
    connection.close()
    return {"teacher": teacher}







    
@app.get("/docente/{docente_identificacion}/rating", response_class=JSONResponse)
async def get_rating_for_teacher(
    docente_identificacion: str, 
    current_user: str = Depends(get_current_user)
):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            nota,
            COALESCE(str_Evi, '') AS str_Evi,
            COALESCE(str_ClienteExterno, '') AS str_ClienteExterno
        FROM calificaciones
        WHERE docente_identificacion = %s AND user_id = %s
    """
    cursor.execute(query, (docente_identificacion, current_user))
    rating = cursor.fetchone()
    cursor.close()
    connection.close()
    
    # Si no hay calificación, retornamos valores por defecto
    if not rating:
        rating = {"nota": None, "str_Evi": "", "str_ClienteExterno": ""}
    return rating



