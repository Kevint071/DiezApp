# DiezApp

DiezApp es una aplicacion de escritorio y movil hecha con Flet para calcular la distribucion porcentual de un monto neto, guardar calculos, consultar historiales y exportar informacion en PDF.

La app esta pensada para trabajo local, sin dependencia obligatoria de backend. Los calculos y ajustes se guardan en archivos JSON dentro del proyecto.

## Caracteristicas

- Calculo principal de distribucion porcentual a partir de una cantidad neta.
- Division automatica en:
  - Envio del 21%.
  - Restante del 79%.
  - Fondo local configurable.
  - Sostenimiento calculado como diferencia final.
- Guardado local de calculos con fecha y hora.
- Historial editable y eliminable.
- Resumen mensual con sumatoria acumulada del 21% por mes.
- Desglose detallado por rango de fechas con exportacion a PDF.
- Configuracion de tema claro/oscuro.
- Configuracion del porcentaje del fondo local.
- Interfaz adaptativa con NavigationBar y AppBar.

## Requisitos

- Python 3.12 o superior.
- Flet 0.85.3 o compatible.
- fpdf2 para generar PDFs.

## Instalacion

Instala las dependencias con tu entorno Python preferido:

```bash
pip install flet fpdf2
```

Si prefieres usar el comando de Flet directamente, tambien puedes ejecutar la app con:

```bash
flet run src/main.py
```

## Uso

Al iniciar, la app muestra la pantalla principal con dos accesos:

- Distribucion porcentual: calcula el desglose de un monto ingresado.
- Resumen mensual: muestra la sumatoria del envio del 21% por cada mes.

Desde la barra inferior puedes acceder a:

- Inicio.
- Historial de calculos guardados.
- Exportar PDF por rango de fechas.
- Ajustes.

### Calculo principal

En la vista de distribucion ingresas una cantidad neta y la app calcula automaticamente:

- Envio (21%).
- Restante (79%).
- Fondo local segun el porcentaje configurado.
- Sostenimiento final.

Luego puedes guardar el calculo para que quede disponible en el historial y en los reportes.

### Historial de calculos

La vista de calculos guardados permite:

- Ver el detalle de cada registro.
- Editar la cantidad neta.
- Eliminar calculos.

Cada cambio recalcula los valores derivados para mantener la consistencia.

### Resumen mensual

La vista de resumen mensual agrupa los calculos por mes y muestra el total acumulado del envio del 21%.

Al tocar un mes se abre el desglose detallado con:

- Fecha.
- Valor individual del 21%.
- Acumulado progresivo.

### Exportacion PDF

La vista de exportacion permite elegir un rango de fechas y generar un PDF con los calculos incluidos en ese intervalo.

Si no hay registros dentro del rango, la app muestra un mensaje de error en pantalla.

### Ajustes

En ajustes puedes cambiar:

- Tema claro u oscuro.
- Porcentaje del fondo local, con validacion entre 1% y 30%.

## Persistencia local

La aplicacion usa JSON para guardar estado local:

- [src/settings.json](src/settings.json) contiene el tema activo y el porcentaje del fondo local.
- [src/saved_calculations.json](src/saved_calculations.json) contiene el historial de calculos.

Estos archivos se crean y actualizan automaticamente desde la propia app.

## Estructura del proyecto

```text
src/
 main.py
 settings.json
 saved_calculations.json
 assets/
 utils/
  pdf_export.py
  storage.py
  theme.py
 views/
  monthly_summary_view.py
  saved_calculations_view.py
  settings_view.py
```

## Modulos principales

- [src/main.py](src/main.py): punto de entrada, navegacion, calculadora principal y barra inferior.
- [src/utils/storage.py](src/utils/storage.py): lectura, escritura, actualizacion y borrado de calculos.
- [src/utils/pdf_export.py](src/utils/pdf_export.py): generacion del PDF de exportacion.
- [src/utils/theme.py](src/utils/theme.py): paleta visual y temas claro/oscuro.
- [src/views/monthly_summary_view.py](src/views/monthly_summary_view.py): resumen mensual y desglose por mes.
- [src/views/saved_calculations_view.py](src/views/saved_calculations_view.py): historial, edicion, eliminacion y exportacion por rango.
- [src/views/settings_view.py](src/views/settings_view.py): configuracion de tema y fondo local.

## Notas de implementacion

- La exportacion PDF usa `fpdf2` y genera archivos temporales antes de compartirlos.
- La app esta orientada a uso local, por lo que no requiere base de datos ni servicios externos.
- En Android, la configuracion actual compila solo `arm64-v8a` para reducir el tamano del APK.

## Desarrollo

Para ejecutar la app en modo desarrollo:

```bash
flet run src/main.py
```

Si quieres validar rapidamente la sintaxis de los archivos Python principales:

```bash
python -m py_compile src/main.py src/utils/storage.py src/utils/pdf_export.py src/views/monthly_summary_view.py src/views/saved_calculations_view.py src/views/settings_view.py
```

## Licencia

Define aqui la licencia del proyecto si quieres publicarlo o compartirlo formalmente.
