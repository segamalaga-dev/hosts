# Hosts seleccionados para Android

Archivo `hosts` para uso personal, basado en fuentes del proyecto [StevenBlack/hosts](https://github.com/StevenBlack/hosts). La generación utiliza el programa oficial de StevenBlack para fusionar las fuentes y eliminar duplicados. Después conserva solo asignaciones de bloqueo a `0.0.0.0`, y las asignaciones locales mínimas. No se modifica `/etc/hosts` al generar el archivo.

El archivo `hosts-windows` contiene exactamente los mismos dominios bloqueados, agrupados hasta nueve por línea para Windows 11. No contiene comentarios finales. Conserva únicamente un pequeño encabezado con las URL y la atribución de las fuentes; los comentarios no se procesan como dominios.

## Fuentes elegidas

| Fuente | Motivo |
| --- | --- |
| Dan Pollock (`someonewhocares.org`) | Continuidad con la lista utilizada hasta ahora. |
| AdAway (`adaway.org`) | Publicidad y análisis de aplicaciones móviles. |
| yoyo.org | Publicidad y seguimiento general. |
| StevenBlack | Aportaciones propias del mantenedor. |
| add.2o7Net | Dominios de seguimiento, con aportación de tamaño moderada. |
| URLHaus | Dominios de malware; es una lista cambiante que conviene actualizar. |

Se excluyen, entre otras, `hostsVN` (la fuente incorporada por StevenBlack es específicamente vietnamita), `KADhosts` (muchos dominios internacionales de fraude, pero gran tamaño y caducidad rápida), `mvps.org` (su propio encabezado fecha la última actualización en marzo de 2021), `UncheckyAds` (instaladores Windows) y `Badd-Boyz-Hosts` (referidores spam, principalmente útiles para servidores). Excluirlas reduce cobertura potencial; esta selección busca un equilibrio de cobertura y tamaño, no una medida demostrada de anuncios bloqueados.

## Regenerar

Necesitas Git y Python 3. En Linux o macOS:

```bash
python3 -m pip install -r requirements.txt
python3 build.py
```

El generador clona la versión actual del repositorio original y usa **las copias de las fuentes incluidas en ese commit**, sin descargar cada fuente de nuevo. Así la salida corresponde a un conjunto coherente, aunque puede ir algunos días por detrás de cada proveedor. Con la acción de GitHub incluida se actualiza cada lunes y también se puede ejecutar manualmente desde «Actions».

Los resultados aparecen en `hosts` (Android) y `hosts-windows` (Windows). Antes de copiar uno al dispositivo correspondiente, guarda una copia de sus hosts actuales, especialmente si contienen asignaciones propias además de `localhost`. Copia el archivo siguiendo tu procedimiento habitual y comprueba que `localhost` resuelve correctamente. En Windows, el destino se llama `C:\Windows\System32\drivers\etc\hosts`, sin extensión, y requiere permisos de administrador. La actualización en GitHub no instala automáticamente el archivo en ninguno de los dispositivos.

## Licencias y atribución

El encabezado del archivo generado identifica las seis fuentes con sus URL originales. Dan Pollock permite copiar y distribuir su archivo para fines no comerciales con atribución y URL original. Las demás fuentes conservan sus condiciones respectivas: consulta la [tabla de fuentes y licencias del proyecto original](https://github.com/StevenBlack/hosts#sources-of-hosts-data-unified-in-this-variant) antes de distribuir la compilación con otro fin.
