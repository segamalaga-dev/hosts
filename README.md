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
| URLhaus (externa, opcional) | Hostfile de dominios maliciosos activos o recientes; requiere Auth-Key de abuse.ch. |

Se excluyen, entre otras, `hostsVN` (la fuente incorporada por StevenBlack es específicamente vietnamita), `KADhosts` (muchos dominios internacionales de fraude, pero gran tamaño y caducidad rápida), `mvps.org` (su propio encabezado fecha la última actualización en marzo de 2021), `UncheckyAds` (instaladores Windows) y `Badd-Boyz-Hosts` (referidores spam, principalmente útiles para servidores). Excluirlas reduce cobertura potencial; esta selección busca un equilibrio de cobertura y tamaño, no una medida demostrada de anuncios bloqueados.

## Regenerar

Necesitas Git y Python 3. En Linux o macOS:

```bash
python3 -m pip install -r requirements.txt
python3 build.py
```

El generador clona la versión actual del repositorio original y usa **las copias de las fuentes incluidas en ese commit**, sin descargar cada fuente de nuevo. Así la salida corresponde a un conjunto coherente, aunque puede ir algunos días por detrás de cada proveedor. Con la acción de GitHub incluida se actualiza diariamente y también se puede ejecutar manualmente desde «Actions».

Los resultados aparecen en `hosts` (Android) y `hosts-windows` (Windows). Antes de copiar uno al dispositivo correspondiente, guarda una copia de sus hosts actuales, especialmente si contienen asignaciones propias además de `localhost`. Copia el archivo siguiendo tu procedimiento habitual y comprueba que `localhost` resuelve correctamente. En Windows, el destino se llama `C:\Windows\System32\drivers\etc\hosts`, sin extensión, y requiere permisos de administrador. La actualización en GitHub no instala automáticamente el archivo en ninguno de los dispositivos.

## Licencias y atribución

El encabezado del archivo generado identifica las fuentes activas con sus URL originales. Dan Pollock permite copiar y distribuir su archivo para fines no comerciales con atribución y URL original. Las demás fuentes conservan sus condiciones respectivas: consulta la [tabla de fuentes y licencias del proyecto original](https://github.com/StevenBlack/hosts#sources-of-hosts-data-unified-in-this-variant) antes de distribuir la compilación con otro fin.


## Protección adicional: Frogeye y URLhaus

La lista [Frogeye First-party only](https://hostfiles.frogeye.fr/firstparty-only-trackers-hosts.txt)
se añade para mejorar la privacidad y bloquear rastreadores de primera parte.

URLhaus fue retirada de las fuentes del repositorio original de StevenBlack. Este fork
puede añadir su hostfile actualizado de dominios asociados a distribución de malware.
Desde octubre de 2026 requiere una clave. Para habilitar la descarga, ve a
**Settings → Secrets and variables → Actions → New repository secret**, y crea
`URLHAUS_AUTH_KEY` con la clave de [auth.abuse.ch](https://auth.abuse.ch/).
No pongas la clave en el código, un commit o un README. El generador no la registra,
y evita transmitirla a los scripts descargados de StevenBlack.

Si no se define el secreto, URLhaus no se incorpora y Actions mostrará una advertencia.
Las fuentes se validan, se deduplican por dominio y se impone un límite de 55.000
dominios únicos en el archivo generado. Ante error, la acción no publica la versión
fallida. Se actualiza diariamente, pero debes instalar manualmente el nuevo hosts
en los dispositivos que lo utilicen. Comprueba las condiciones de redistribución
para cada fuente antes de hacer pública la compilación.
