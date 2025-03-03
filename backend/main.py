from fastapi import FastAPI, File, Form, HTTPException,Response, UploadFile,Query,Depends
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
from decimal import Decimal, ROUND_HALF_UP

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
    
    # Nuevos campos para notas
    puntuacion_total: int   # Almacenará la suma de todas las notas
    total_usuarios: int   # Número de usuarios que han registrado una nota
    promedio: str  # Promedio de las notas registradas




# Función asíncrona para insertar un docente en la base de datos
async def insert_docente(connection, docente_data):
    cursor = connection.cursor()
    query = """
        INSERT INTO docentes (
            identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular,
            otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
            titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
            certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
            disponibilidad_jueves,disponibilidad_viernes,disponibilidad_viajar, equipo_conexion_estable,
            estilo_formador, metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace,
            aviso_proteccion_datos,disponibilidad_sabado
        ) VALUES (
            %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
async def process_excel(file: UploadFile) -> dict:
    file_bytes = await file.read()
    df = pd.read_excel(BytesIO(file_bytes))
    
    # Limpiar espacios en blanco en nombres de columna
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
    
    # Verificar que todas existan
    for col in columnas_esperadas:
        if col not in df.columns:
            raise KeyError(f"Falta la columna esperada: '{col}'")
    
    connection = get_db()
    if connection is None:
        return {"error": "No se pudo conectar a la base de datos."}
    
    # Contadores y lista para registros duplicados
    inserted_count = 0
    duplicate_count = 0
    duplicate_emails = []
    
    # Función auxiliar para validar valores
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
                identificacion,marca_temporal, nombre_completo, correo_electronico, numero_celular,
                otro_numero_contacto, envio_whatsapp, lugar_residencia, nivel_formacion,
                titulos_pregrado, titulos_posgrado, areas_especializacion, resumen_experiencia,
                certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles,
                disponibilidad_jueves, disponibilidad_viernes, disponibilidad_viajar, equipo_conexion_estable,
                estilo_formador, metodologia, casos_impacto, restriccion_contractual,
                hoja_vida, video_enlace, aviso_proteccion_datos, disponibilidad_sabado
            )

            # Verificar si ya existe un registro con el mismo correo en la BD
            check_cursor = connection.cursor()
            check_query = "SELECT COUNT(*) FROM docentes WHERE correo_electronico = %s"
            check_cursor.execute(check_query, (correo_electronico,))
            result = check_cursor.fetchone()
            check_cursor.close()

            if result and result[0] > 0:
                duplicate_count += 1
                duplicate_emails.append(correo_electronico)
                print(f"El correo {correo_electronico} ya se encuentra registrado. Saltando esta fila.")
                continue

            await insert_docente(connection, docente_data)
            inserted_count += 1
        except KeyError as e:
            print(f"Error procesando fila {index}: {e}")

    connection.close()
    return {
        "inserted": inserted_count,
        "duplicates": duplicate_count,
        "duplicate_emails": duplicate_emails
    }

# Endpoint de carga de archivo
@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    result = await process_excel(file)
    # Mensaje base de registros insertados
    message = f"Se insertaron {result['inserted']} registros correctamente."
    
    # Si existen duplicados, se agrega un mensaje de error con los correos
    if result["duplicates"] > 0:
        duplicate_message = (
            "Error: Los siguientes correos ya se encuentran registrados:<br>" +
            "<br>".join(result["duplicate_emails"])
        )
        message += "<br>" + duplicate_message

    return {"success": True, "message": message}



# Función para obtener los usuarios desde la base de datos
def get_teachers():
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    # Consulta para obtener los usuarios
    query = """ 
        SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
        envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
        titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
        disponibilidad_jueves, disponibilidad_viernes, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
        metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos, promedio
        FROM docentes
    """
    cursor.execute(query)
    docentes = cursor.fetchall()

    # Cerrar la conexión
    cursor.close()
    connection.close()

    return docentes  # Sin la coma



def get_teachers_with_rating(user_id: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)

    query = """ 
        SELECT 
            d.identificacion, 
            d.marca_temporal, 
            d.nombre_completo, 
            d.correo_electronico, 
            d.numero_celular, 
            d.otro_numero_contacto,
            d.envio_whatsapp, 
            d.lugar_residencia, 
            d.nivel_formacion, 
            d.titulos_pregrado, 
            d.areas_especializacion, 
            d.resumen_experiencia, 
            d.titulos_posgrado, 
            d.certificaciones, 
            d.disponibilidad_lunes, 
            d.disponibilidad_martes, 
            d.disponibilidad_miercoles, 
            d.disponibilidad_jueves, 
            d.disponibilidad_viernes, 
            d.disponibilidad_sabado, 
            d.disponibilidad_viajar, 
            d.equipo_conexion_estable, 
            d.estilo_formador, 
            d.metodologia, 
            d.casos_impacto, 
            d.restriccion_contractual, 
            d.hoja_vida, 
            d.video_enlace, 
            d.aviso_proteccion_datos, 
            d.promedio,
            CASE WHEN c.user_id IS NOT NULL THEN TRUE ELSE FALSE END AS ya_califico
        FROM docentes d
        LEFT JOIN calificaciones c 
            ON d.identificacion = c.docente_identificacion AND c.user_id = %s
    """
    
    cursor.execute(query, (user_id,))
    docentes = cursor.fetchall()
    cursor.close()
    connection.close()

    return docentes




# Comentario de segurity
# Lista de columnas permitidas para el filtrado
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
        SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
        envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
        titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
        disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
        metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos,promedio
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
def get_teacher_detail(teacher_id: str):
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT identificacion, marca_temporal, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto,
               envio_whatsapp, lugar_residencia, nivel_formacion, titulos_pregrado, areas_especializacion, resumen_experiencia, 
               titulos_posgrado, certificaciones, disponibilidad_lunes, disponibilidad_martes, disponibilidad_miercoles, 
               disponibilidad_jueves, disponibilidad_sabado, disponibilidad_viajar, equipo_conexion_estable, estilo_formador, 
               metodologia, casos_impacto, restriccion_contractual, hoja_vida, video_enlace, aviso_proteccion_datos, promedio
        FROM docentes
        WHERE identificacion = %s
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
                <td>{docente['promedio']}</td>
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
        SELECT identificacion, nombre_completo, correo_electronico, numero_celular,otro_numero_contacto,nivel_formacion,areas_especializacion,promedio
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
        SELECT identificacion, nombre_completo, correo_electronico, numero_celular, otro_numero_contacto, 
               nivel_formacion, areas_especializacion, promedio
        FROM docentes
        WHERE LOWER(nombre_completo) LIKE %s
           OR LOWER(correo_electronico) LIKE %s
           OR LOWER(numero_celular) LIKE %s
           OR LOWER(nivel_formacion) LIKE %s
           OR LOWER(areas_especializacion) LIKE %s
    """
    
    search_param = f"%{query.lower()}%"
    cursor.execute(search_query, (search_param, search_param, search_param, search_param, search_param))
    docentes = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"docentes": docentes}



# Modelo para recibir la nota (entero de 1 a 5)
class NotaModel(BaseModel):
    nota: int

# Función asíncrona para registrar la nota y actualizar el docente
async def registrar_nota(connection, docente_identificacion: str, nueva_nota: int):
    cursor = connection.cursor()
    
    # Consultar los valores actuales del docente usando 'identificacion'
    query_select = "SELECT puntuacion_total, total_usuarios FROM docentes WHERE identificacion = %s"
    cursor.execute(query_select, (docente_identificacion,))
    row = cursor.fetchone()

    if row is None:
        cursor.close()
        raise Exception(f"Docente con identificación {docente_identificacion} no encontrado")
    
    puntuacion_total, total_usuarios = row
    
    # Actualizamos la puntuación total y el contador de usuarios
    nueva_puntuacion_total = puntuacion_total + nueva_nota
    nuevo_total_usuarios = total_usuarios + 1
    nuevo_promedio = nueva_puntuacion_total / nuevo_total_usuarios

    # Convertir el promedio a Decimal con dos decimales (5,2) redondeando correctamente
    nuevo_promedio_decimal = Decimal(nuevo_promedio).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    
    # Actualizar el registro en la base de datos usando 'identificacion'
    query_update = """
        UPDATE docentes SET 
            puntuacion_total = %s, 
            total_usuarios = %s, 
            promedio = %s
        WHERE identificacion = %s
    """
    try:
        cursor.execute(query_update, (nueva_puntuacion_total, nuevo_total_usuarios, nuevo_promedio_decimal, docente_identificacion))
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise Exception(f"Error al actualizar docente: {str(e)}")
    finally:
        cursor.close()
    
    # Retornamos el nuevo promedio en cadena para la respuesta
    return {"mensaje": "Nota registrada exitosamente", "promedio_actual": str(nuevo_promedio_decimal)}

# Endpoint para registrar la nota
@app.post("/docentes/{docente_identificacion}/nota")
async def registrar_nota_endpoint(
    docente_identificacion: str,
    nota_model: NotaModel,
    connection = Depends(get_db)
):
    try:
        resultado = await registrar_nota(connection, docente_identificacion, nota_model.nota)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))





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

@app.post("/logout")
async def logout(response: Response):
    # Eliminar la cookie de sesión
    response.delete_cookie("session") 
    
    # Redirigir al login
    return RedirectResponse(url="/", status_code=303)



