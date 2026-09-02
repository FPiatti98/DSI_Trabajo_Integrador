# Sistema Inteligente de Clasificación de Emails Empresariales

## Dominio elegido

El proyecto desarrolla un sistema para TecnoSupply Argentina, una empresa ficticia de venta y distribución de productos tecnológicos. El sistema utiliza un modelo de lenguaje para analizar emails de clientes, detectar su intención, asignar una prioridad y extraer información relevante, como el número de pedido o el producto mencionado.

La IA se utiliza exclusivamente para interpretar lenguaje natural. La validación del contrato y las acciones posteriores corresponden a código determinista.

## Integrantes

- Franco Piatti

## Estructura principal

- `schemas.py`: contrato de salida mediante Pydantic.
- `app.py`: clasifica un email mediante Gemini y Structured Outputs.
- `lote_pruebas.py`: ejecuta seis casos de prueba y genera `resultados_lote.md`.
- `informe.md`: documentación de las Partes A, B y C.

## Requisitos

- Python 3.10 o superior.
- Una API key de Google Gemini.

## Instalación

Crear y activar un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```powershell
python -m pip install -r requirements.txt
```

## Configuración de variables de entorno

Crear un archivo llamado `.env` en la carpeta principal del proyecto. No debe subirse al repositorio.

```env
GEMINI_API_KEY=tu_clave_real_de_gemini
GEMINI_MODEL=gemini-2.5-flash
```

Se incluye `.env.example` como referencia, sin credenciales reales.

## Ejecución

Para clasificar un email de prueba:

```powershell
python app.py
```

Para ejecutar el lote de seis casos y generar la tabla de resultados:

```powershell
python lote_pruebas.py
```

El segundo comando actualiza el archivo `resultados_lote.md`.

## Seguridad

La API key nunca debe escribirse directamente en el código ni subirse a Git. El archivo `.env` está incluido en `.gitignore`.