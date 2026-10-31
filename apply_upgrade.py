#!/usr/bin/env python3
"""Apply Frogeye + authenticated URLhaus integration to segamalaga-dev/hosts.

Run from the root of a checkout of that repository, preferably on a test branch.
It never uses, asks for or embeds an API key. Configure URLHAUS_AUTH_KEY as an
Actions secret in GitHub, not as a tracked file.
"""
from __future__ import annotations

from pathlib import Path
import ast

ROOT = Path.cwd()
build = ROOT / 'build.py'
workflow = ROOT / '.github/workflows/update-hosts.yml'
readme = ROOT / 'README.md'
for p in (build, workflow, readme):
    if not p.is_file():
        raise SystemExit('ERROR: Run this script from the root of your hosts repository; missing '+str(p))

source = build.read_text(encoding='utf-8')
yaml = workflow.read_text(encoding='utf-8')
text = readme.read_text(encoding='utf-8')
if 'FROGEYE_URL' in source or 'URLHAUS_AUTH_KEY' in yaml:
    raise SystemExit('ERROR: An external-feed integration is already present. Inspect it before applying this patch.')

# Use exactly matched markers: fail without writing if the original changes.
def replace_once(contents, old, new, filename):
    if contents.count(old) != 1:
        raise SystemExit(f'ERROR: {filename}: expected 1 marker for {old[:50]!r}, found {contents.count(old)}. No files modified.')
    return contents.replace(old, new, 1)

source = replace_once(source, 'import tempfile\n', 'import tempfile\nimport requests\n', 'build.py')
helper = '''# External sources supplement upstream StevenBlack; they are deduplicated below.
FROGEYE_URL = "https://hostfiles.frogeye.fr/firstparty-trackers-hosts.txt"
# The Auth-Key is passed through the Actions secret URLHAUS_AUTH_KEY.
URLHAUS_TEMPLATE = "https://urlhaus-api.abuse.ch/v2/files/exports/{key}/hostfile.txt"
MAX_TOTAL_DOMAINS = 55000


def load_external_hosts(url, source, max_source_domains):
    """Read a hosts/plain-domains feed. Never print authenticated URLs."""
    if not url.startswith("https://"):
        raise RuntimeError(source + ": HTTPS is required")
    try:
        response = requests.get(url, timeout=(15, 90), headers={"User-Agent": "segamalaga-hosts/2.0"})
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            raise ValueError("feed is too large")
        body = response.content.decode("utf-8-sig")
    except (requests.RequestException, UnicodeError, ValueError):
        # Requests exceptions normally contain the URL, which may contain the key.
        raise RuntimeError(source + ": download failed; URL and credentials suppressed") from None

    domains = set()
    malformed = 0
    for raw in body.splitlines():
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        fields = line.split()
        if fields[0] in ("0.0.0.0", "127.0.0.1") and len(fields) >= 2:
            candidates = fields[1:]
        elif len(fields) == 1:
            candidates = fields
        else:
            malformed += 1
            continue
        for domain in candidates:
            domain = domain.lower().rstrip(".")
            if domain == "localhost" or not DOMAIN.fullmatch(domain):
                malformed += 1
                continue
            try:
                ipaddress.ip_address(domain)
            except ValueError:
                domains.add(domain)
            else:
                malformed += 1
    if not (10 <= len(domains) <= max_source_domains):
        raise RuntimeError(f"{source}: unexpected domain count ({len(domains)})")
    if malformed > max(50, len(domains) // 20):
        raise RuntimeError(f"{source}: unexpectedly many malformed entries ({malformed})")
    return domains


'''
source = replace_once(source, 'DOMAIN = re.compile', helper + 'DOMAIN = re.compile', 'build.py')
source = replace_once(source,
    '    with tempfile.TemporaryDirectory(prefix="selected-hosts-") as tmp:',
    '''    # Prevent upstream update scripts from inheriting our URLhaus credential.
    clean_env = dict(os.environ)
    clean_env.pop("URLHAUS_AUTH_KEY", None)
    with tempfile.TemporaryDirectory(prefix="selected-hosts-") as tmp:''', 'build.py')
source = replace_once(source, 'UPSTREAM, str(repo)], check=True)',
    'UPSTREAM, str(repo)], check=True, env=clean_env)', 'build.py')
source = replace_once(source, 'cwd=repo, text=True).strip()',
    'cwd=repo, text=True, env=clean_env).strip()', 'build.py')
source = replace_once(source, 'cwd=repo, check=True, stdout=subprocess.DEVNULL,',
    'cwd=repo, check=True, stdout=subprocess.DEVNULL, env=clean_env,', 'build.py')
source = replace_once(source,
    '        date = dt.datetime.now(dt.timezone.utc)',
    '''        original_total = len(domains)
        frogeye = load_external_hosts(FROGEYE_URL, "Frogeye", 30000)
        domains.update(frogeye)
        print(f"Frogeye: {len(frogeye)} source; {len(domains)-original_total} unique added")

        key = os.environ.get("URLHAUS_AUTH_KEY", "").strip()
        if key:
            if not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", key):
                raise RuntimeError("URLhaus: invalid Auth-Key format")
            before_urlhaus = len(domains)
            urlhaus = load_external_hosts(URLHAUS_TEMPLATE.format(key=key), "URLhaus", 30000)
            domains.update(urlhaus)
            print(f"URLhaus: {len(urlhaus)} source; {len(domains)-before_urlhaus} unique added")
        else:
            print("::warning::URLhaus disabled: configure Actions secret URLHAUS_AUTH_KEY")
        print(f"TOTAL {len(domains)} unique domains (original: {original_total})")
        if len(domains) > MAX_TOTAL_DOMAINS:
            raise RuntimeError(f"Exceeded MAX_TOTAL_DOMAINS limit ({len(domains)} > {MAX_TOTAL_DOMAINS}); no files published")

        date = dt.datetime.now(dt.timezone.utc)''', 'build.py')
source = replace_once(source,
    '''        for name, info in zip(SOURCES, metadata):
            header.append("# " + name + ": " + info["url"])''',
    '''        for name, info in zip(SOURCES, metadata):
            header.append("# " + name + ": " + info["url"])
        header.append("# Frogeye: https://hostfiles.frogeye.fr/")
        if key:
            header.append("# URLhaus: https://urlhaus.abuse.ch/api/")''', 'build.py')
source = replace_once(source,
    '''        windows_header += ["# " + name + ": " + info["url"] for name, info in zip(SOURCES, metadata)]''',
    '''        windows_header += ["# " + name + ": " + info["url"] for name, info in zip(SOURCES, metadata)]
        windows_header.append("# Frogeye: https://hostfiles.frogeye.fr/")
        if key:
            windows_header.append("# URLhaus: https://urlhaus.abuse.ch/api/")''', 'build.py')
ast.parse(source, filename='build.py')

yaml = replace_once(yaml, 'branches: [main]',
    'branches: [main, segamalaga-dev-patch-1]', 'update-hosts.yml')
yaml = replace_once(yaml, 'cron: "17 5 * * 1"',
    'cron: "17 5 * * *"', 'update-hosts.yml')
yaml = replace_once(yaml, '      - run: python3 build.py', '''      - name: Generate selected hosts
        env:
          URLHAUS_AUTH_KEY: ${{ secrets.URLHAUS_AUTH_KEY }}
        run: python3 build.py''', 'update-hosts.yml')

text = text.replace('| URLHaus | Dominios de malware; es una lista cambiante que conviene actualizar. |',
    '| URLhaus (externa, opcional) | Hostfile de dominios maliciosos activos o recientes; requiere Auth-Key de abuse.ch. |')
text = text.replace('Con la acción de GitHub incluida se actualiza cada lunes',
    'Con la acción de GitHub incluida se actualiza diariamente')
text = text.replace('El encabezado del archivo generado identifica las seis fuentes',
    'El encabezado del archivo generado identifica las fuentes activas')
text += '''

## Protección adicional: Frogeye y URLhaus

La lista [Frogeye First-party trackers (completa)](https://hostfiles.frogeye.fr/firstparty-trackers-hosts.txt)
se añade para bloquear rastreadores camuflados bajo subdominios de las webs y sus
nombres de seguimiento bajo los dominios de los proveedores. Se usa la variante
completa recomendada por el autor para bloqueadores basados en hosts.

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
'''

# Only write after successful validations. Keep ordinary backups.
for dest, data in ((build, source), (workflow, yaml), (readme, text)):
    dest.with_name(dest.name + '.bak').write_text(dest.read_text(encoding='utf-8'), encoding='utf-8')
    dest.write_text(data, encoding='utf-8')
print('SUCCESS: Updated build.py, .github/workflows/update-hosts.yml, README.md')
print('Next: set URLHAUS_AUTH_KEY in GitHub secrets; run python3 build.py; inspect output before merging.')
