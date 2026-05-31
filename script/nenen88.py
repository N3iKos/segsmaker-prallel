TOKET = ''
TOBRUT = ''

from IPython.core.magic import register_line_magic
from IPython.display import display, HTML, clear_output
from urllib.parse import urlparse
from IPython import get_ipython
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
import subprocess
import threading
import requests
import zipfile
import shlex
import json
import time
import sys
import re
import os
import io

MAGENTA = '\033[35m'
RED = '\033[31m'
CYAN = '\033[36m'
GREEN = '\033[38;5;35m'
YELLOW = '\033[33m'
BLUE = '\033[38;5;69m'
PURPLE = '\033[38;5;135m'
ORANGE = '\033[38;5;208m'
RESET = '\033[0m'

CD = os.chdir
SyS = get_ipython().system

# ─── Aria2c progress helpers ─────────────────────────────────────────────────
_TO_BYTES = {'B':1,'KiB':1024,'MiB':1024**2,'GiB':1024**3,
             'KB':1000,'MB':1000**2,'GB':1000**3}

def _parse_aria2_stats(raw):
    """Extract numeric stats from a raw aria2c progress line."""
    s = {'pct':0,'done_b':0.0,'total_b':0.0,'speed_b':0.0,'eta_s':0}
    m = re.search(r'([\d.]+)(\w+)/([\d.]+)(\w+)\((\d+)%\)', raw)
    if m:
        s['done_b']  = float(m.group(1)) * _TO_BYTES.get(m.group(2), 1)
        s['total_b'] = float(m.group(3)) * _TO_BYTES.get(m.group(4), 1)
        s['pct']     = int(m.group(5))
    m = re.search(r'DL:([\d.]+)(\w+)', raw)
    if m: s['speed_b'] = float(m.group(1)) * _TO_BYTES.get(m.group(2), 1)
    m = re.search(r'ETA:(\d+)(s|m|h)', raw)
    if m: s['eta_s'] = int(m.group(1)) * {'s':1,'m':60,'h':3600}[m.group(2)]
    return s

def _fmt_size(b):
    for u in ('B','KiB','MiB','GiB'):
        if b < 1024 or u == 'GiB': return f'{b:.1f}{u}'
        b /= 1024

def _fmt_eta(s):
    if s <= 0: return '?'
    return f'{s}s' if s < 60 else f'{s//60}m{s%60:02d}s'

def _fmt_progress(raw):
    """Apply ANSI formatting to a raw aria2c progress line."""
    p = raw
    p = re.sub(r'\[', MAGENTA + '【' + RESET, p)
    p = re.sub(r'\]', MAGENTA + '】' + RESET, p)
    p = re.sub(r'(#)(\w+)', f'{CYAN}\\1{RESET}{GREEN}\\2{RESET}', p)
    p = re.sub(r'(\d+(\.\d+)?)(\w+)(/)(\d+(\.\d+)?)(\w+)',
               f'\\1{PURPLE}\\3{RESET}{MAGENTA}\\4{RESET}\\5{PURPLE}\\7{RESET}', p)
    p = re.sub(r'(\()(\d+%)(\))', f'{MAGENTA}\\1{RESET}\\2{MAGENTA}\\3{RESET}', p)
    p = re.sub(r'(CN)(:)(\d+)', f'{CYAN}\\1{RESET}\\2{ORANGE}\\3{RESET}', p)
    p = re.sub(r'(DL)(:)([\d.]+)(\w+)', f'{CYAN}\\1{RESET}\\2\\3{PURPLE}\\4{RESET}', p)
    p = re.sub(r'(ETA)(:)(\d+\w+)', f'{CYAN}\\1{RESET}\\2{YELLOW}\\3{RESET}', p)
    return p
iRON = os.environ

KAGGLE = 'KAGGLE_DATA_PROXY_TOKEN' in iRON

CIVITAI = ['civitai.com', 'civitai.red']

@register_line_magic
def say(line):
    args = re.findall(r'\{[^\{\}]+\}|[^\s\{\}]+', line)
    output = []
    theme = get_ipython().config.get('InteractiveShellApp', {}).get('theme', 'light')
    default_color = 'white' if theme == 'dark' else 'black'

    i = 0
    while i < len(args):
        msg = args[i]
        color = None

        if re.match(r'^\{[^\{\}]+\}$', msg.lower()):
            color = msg[1:-1]
            msg = ''
        else:
            while i < len(args) - 1 and not re.match(r'^\{[^\{\}]+\}$', args[i + 1].lower()):
                i += 1
                msg += ' ' + args[i]

        if color == 'd':
            color = default_color
        elif color is None and i < len(args) - 1:
            if re.match(r'^\{[^\{\}]+\}$', args[i + 1].lower()):
                color = args[i + 1][1:-1]
                i += 1

        span_text = f'<span'
        if color:
            span_text += f" style='color:{color};'"
        span_text += f'>{msg}</span>'
        output.append(span_text)
        i += 1

    display(HTML(' '.join(output)))

@register_line_magic
def download(i):
    args = i.split()
    if not args:
        print('  missing URL, downloading nothing')
        return

    url = args[0]
    path = Path(url).expanduser()
    if url.endswith('.txt') and path.is_file():
        for l in path.read_text(encoding='utf-8').splitlines(): netorare(l)
    else: netorare(i)

def netorare(line):
    fp, fn = None, None

    parts = line.strip().split()
    if not parts: return

    cwd = Path.cwd()
    url = parts[0].replace('\\', '')
    CHG = any(domain in url for domain in [*CIVITAI, 'huggingface.co', 'github.com'])
    DriveGoogle = 'drive.google.com' in url

    path = lambda s: '/' in s or '~/' in s

    try:
        if len(parts) >= 3:
            arg1, arg2 = parts[1], parts[2]
            path_arg, file_arg = (arg2, arg1) if path(arg2) and not path(arg1) else \
                                 (arg1, arg2) if path(arg1) and not path(arg2) else \
                                 (arg2, arg1) if Path(arg2).suffix == '' and Path(arg1).suffix != '' else \
                                 (arg1, arg2)

            fp, fn = Path(path_arg).expanduser(), file_arg
            fp.mkdir(parents=True, exist_ok=True)
            CD(fp)

        elif len(parts) == 2:
            arg = parts[1]
            if path(arg):
                fp = Path(arg).expanduser()
                fp.mkdir(parents=True, exist_ok=True)
                CD(fp)
                fn = get_fn(url) if CHG else Path(urlparse(url).path).name
            else:
                fn = arg
                fp = cwd
        else:
            fn = get_fn(url) if CHG else Path(urlparse(url).path).name
            fp = cwd

        if CHG: ariari(url, fp, fn)
        elif DriveGoogle: gdrown(url, fp, fn)
        else:
            path_only = len(parts) == 2 and fp is not None
            cmd = f"curl -#{'OJL' if len(parts) == 1 or path_only else 'JL'} '{url}'" + (f" -o '{fn}'" if fn is not None and not path_only else "")
            curlly(cmd, fn)
    finally:
        CD(cwd)

def resizer(b, size=512):
    from PIL import Image
    i = Image.open(io.BytesIO(b))
    w, h = i.size
    s = (size, int(h * size / w)) if w > h else (int(w * size / h), size)
    o = io.BytesIO()
    i.resize(s, Image.LANCZOS).save(o, format='PNG')
    o.seek(0)
    return o

def get_civdom(url: str) -> str | None:
    try:
        h = urlparse(url).netloc.lower()
        for d in CIVITAI:
            if d in h:
                return d
    except:
        pass
    return None

def civitai_headers():
    return {'User-Agent': 'CivitaiLink:Automatic1111'}

def civitai_preview(j, p, fn, versionId=None):
    v = get_civitai(j, versionId)
    if not v: return

    images = v.get('images', [])
    name = fn or v.get('files', [{}])[0].get('name')
    if not name: return

    path = Path(p) / f'{Path(name).stem}.preview.png'
    if path.exists(): return

    preview = next((img.get('url', '') for img in images if not img.get('url', '').lower().endswith(('.mp4', '.gif'))), None)
    if not preview: return

    r = requests.get(preview, headers=civitai_headers()).content
    resized = resizer(r)

    if KAGGLE:
        from melon00 import image_encryption
        image_encryption(resized, path)
    else:
        path.write_bytes(resized.read())

def civitai_infotags(j, p, fn, versionId=None):
    v = get_civitai(j, versionId)
    if not v: return

    modelId = j.get('id') or v.get('modelId')
    name = fn or v.get('files', [{}])[0].get('name')
    if not name: return

    info = Path(p) / f'{Path(name).stem}.json'
    if info.exists(): return

    baseList = {
        'SD 1': 'SD1',
        'SD 1.5': 'SD1',
        'SD 2': 'SD2',
        'SD 3': 'SD3',
        'SDXL': 'SDXL',
        'Pony': 'SDXL',
        'Illustrious': 'SDXL',
    }

    data = {
        'activation text': ', '.join(v.get('trainedWords', [])),
        'sd version': next((s for k, s in baseList.items() if k in v.get('baseModel', '')), ''),
        'modelId': modelId,
        'modelVersionId': v.get('id'),
        'sha256': v.get('files', [{}])[0].get('hashes', {}).get('SHA256')
    }

    info.write_text(json.dumps(data, indent=4))

def civitai_earlyAccess(j, versionId=None, civitai=None):
    v = get_civitai(j, versionId)
    if not v: return False

    if v.get('availability') == 'EarlyAccess' or v.get('earlyAccessEndsAt'):
        modelId = j.get('id') or v.get('modelId')
        modelVersionId = v.get('id')
        page = f'https://{civitai}/models/{modelId}?modelVersionId={modelVersionId}'
        print(f'{page}\n-> The model version is in early access and requires payment for downloading.')
        return True

    return False

def get_fn(url):
    if any(x in url for x in [*CIVITAI, 'drive.google.com']): return None
    return Path(urlparse(url).path).name

def get_json(api_url, headers):
    try:
        r = requests.get(api_url, headers=headers, timeout=15)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

def get_civitai(j, versionId=None):
    v = None

    if versionId:
        if 'modelVersions' in j: v = next((mv for mv in j['modelVersions'] if str(mv.get('id')) == str(versionId)), None)
        if not v and str(j.get('id')) == str(versionId) and 'files' in j: v = j

    if not v:
        if 'modelVersions' in j: v = j['modelVersions'][0]
        else: v = j

    return v

def get_url(url, fn):
    """
    Resolve a user-provided URL into a direct download URL when possible.
    Important fix: do NOT append ?token=... to CivitAI/Backblaze signed URLs (they are sensitive to modification).
    Only append TOKET for non-Civitai hosts when TOKET is set and needed.
    """

    civitai = get_civdom(url)

    def maybe_add_token(u):
        # We should NEVER append Civitai token (TOKET) to HuggingFace, GitHub, or other non-Civitai hosts!
        # Doing so causes "Authorization failed" (401/403) errors.
        try:
            parsed = urlparse(u)
            host = parsed.netloc.lower()
        except:
            return u

        # Only append to Civitai hosts if it is actually Civitai and doesn't already have it
        if not any(d in host for d in CIVITAI):
            return u

        if not TOKET:
            return u

        if 'token=' in u:
            return u

        if '?type=' in u:
            return u.replace('?type=', f'?token={TOKET}&type=')
        return f'{u}?token={TOKET}'

    if 'github.com' in url:
        url = url.replace('/blob/', '/raw/')
        return maybe_add_token(url), None, None

    elif 'huggingface.co' in url:
        url = url.split('?')[0]
        is_hf_token = TOBRUT and TOBRUT.strip().startswith('hf_')
        h = {'User-Agent': 'Mozilla/5.0', **({'Authorization': f'Bearer {TOBRUT.strip()}'} if is_hf_token else {})}
        ext = ['.safetensors', '.pt', '.pth']
        j, versionId = None, None

        if fn and Path(fn).suffix.lower() in ext:
            try:
                res = requests.get(re.sub(r'/(resolve|blob)/', '/raw/', url), headers=h)
                t = re.search(r'oid sha256:([a-fA-F0-9]{64})', res.text)

                if t:
                    sha256 = t.group(1)
                    j = None

                    for c in CIVITAI:
                        try:
                            api_url = f'https://{c}/api/v1/model-versions/by-hash/{sha256}'
                            j_try = get_json(api_url, civitai_headers())

                            if not j_try:
                                continue

                            r = next(
                                (f for f in j_try.get('files', [])
                                if f.get('hashes', {}).get('SHA256', '').lower() == sha256.lower()),
                                None
                            )

                            if r:
                                j = j_try
                                break

                        except Exception:
                            continue

            except Exception:
                j = None

        url = url.replace('/blob/', '/resolve/')
        return maybe_add_token(url), j, versionId

    elif civitai in url:
        input_url = url
        url = url.split('?token=')[0] if '?token=' in url else url

        if f'{civitai}/api/download/models/' in url:
            versionId = url.split('models/')[1].split('/')[0].split('?')[0]
            api_url = f'https://{civitai}/api/v1/model-versions/{versionId}'
            j = get_json(api_url, civitai_headers())

            if j:
                v = get_civitai(j, versionId)
                if v:
                    return url, j, versionId

            return url, None, None

        elif f'{civitai}/models/' in url:
            versionId = None
            modelId = url.split('models/')[1].split('/')[0].split('?')[0]
            if '?modelVersionId=' in url:
                versionId = url.split('?modelVersionId=')[1]

            api_url = f'https://{civitai}/api/v1/models/{modelId}'
            j = get_json(api_url, civitai_headers())

            if not j or civitai_earlyAccess(j, versionId, civitai):
                return None, None, None

            v = get_civitai(j, versionId)
            if not v:
                print(f'Unable to find download URL for\n-> {input_url}\n')
                return None, None, None

            url = next((f.get('downloadUrl') for f in v.get('files', []) if f.get('downloadUrl')), None)
            if not url:
                print(f'Unable to find download URL for\n-> {input_url}\n')
                return None, None, None

            return url, j, versionId

    return maybe_add_token(url), None, None

def ariari(url, fp, fn, on_progress=None):
    url, j, versionId = get_url(url, fn)
    if not url: return

    civitai = get_civdom(url)
    civitai_api = (f'{civitai}/api/download/models/' in url and bool(TOKET))

    if civitai_api:
        try:
            headers = {'User-Agent': civitai_headers()['User-Agent'], 'Authorization': f'Bearer {TOKET}'}
            request_url = url
            resp = requests.get(request_url, headers=headers, allow_redirects=True, stream=True, timeout=30)
            final_url = resp.url
            resp.close()

            if final_url and final_url != request_url: url = final_url
            else: print("  No redirect detected; aria2 will use Authorization header.")

        except Exception as e:
            print(f"  Preflight failed: {e}")
            print("  Falling back to aria2 with Authorization header.")

    # Optimized aria2c flags for cloud network:
    # -x16 -s16: 16 connections per file, 16 splits — maximizes bandwidth on cloud links
    # -k1M: 1MB chunk size — optimal for large model files
    # -j5: up to 5 parallel jobs per aria2c instance
    # --min-split-size=1M: ensures splits are meaningful
    # --auto-file-renaming=false: prevents duplicate-name collisions when running parallel
    cmd = [
        'aria2c',
        f"--header=User-Agent: {civitai_headers()['User-Agent'] if f'{civitai}' in url else 'Mozilla/5.0'}",
        '--allow-overwrite=true', '--console-log-level=error', '--stderr=true',
        '--auto-file-renaming=false', '--min-split-size=1M',
        f'--dir={str(fp)}',
        '-c', '-x16', '-s16', '-k1M', '-j5'
    ]

    if f'{civitai}/api/download/models/' in url and TOKET: cmd.append(f"--header=Authorization: Bearer {TOKET}")
    is_hf_token = TOBRUT and TOBRUT.strip().startswith('hf_')
    if is_hf_token and 'huggingface.co' in url: cmd.append(f'--header=Authorization: Bearer {TOBRUT.strip()}')

    if fn: cmd += ['-o', fn]

    cmd.append(url)

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        aria2_output, break_line, error_code, error_line = '', False, [], []

        while True:
            lines = p.stderr.readline()
            if lines == '' and p.poll() is not None: break

            if lines:
                aria2_output += lines

                for prog in lines.splitlines():
                    if 'errorCode' in prog or 'Exception' in prog:
                        error_code.append(prog)
                    if '|' in prog and 'error_line' in prog:
                        prog = re.sub(r'(\|\s*)(error_line)(\s*\|)', f'\\1{RED}\\2{RESET}\\3', prog)
                        first, _, last = prog.rpartition('|')
                        last = re.sub(r'/', f'{CYAN}/{RESET}', last)
                        prog = f'{first}|{last}'
                        error_line.append(prog)

                    if re.match(r'\[#\w{6}\s.*\]', prog):
                        raw_prog = prog  # keep raw for stats / callback
                        if on_progress:
                            on_progress(raw_prog)
                        else:
                            formatted = _fmt_progress(raw_prog)
                            print(f"\r{' '*300}\r {formatted}", end='')
                            sys.stdout.flush()
                        break_line = True
                        break

        civitai = None
        error = error_code + error_line
        for lines in error: print(f'  {lines}')

        if break_line and not on_progress: print()

        stripe = aria2_output.find('======+====+===========')
        if stripe != -1:
            for lines in aria2_output[stripe:].splitlines():
                if '|' in lines and 'OK' in lines:
                    lines = re.sub(r'(\|\s*)(OK)(\s*\|)', f'\\1{GREEN}\\2{RESET}\\3', lines)
                    first, _, last = lines.rpartition('|')
                    last = re.sub(r'/', f'{ORANGE}/{RESET}', last)
                    lines = f'{first}|{last}'
                    print(f'  {lines}')

        if j:
            civitai_infotags(j, fp, fn, versionId)
            civitai_preview(j, fp, fn, versionId)

        p.wait()

    except KeyboardInterrupt:
        print(f'\n{"":>2}^ Canceled')

def curlly(cmd, fn):
    try:
        p = subprocess.Popen(
            shlex.split(cmd), cwd=str(Path.cwd()),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        prog = re.compile(r'(\d+\.\d+)%')
        curl_output = ''

        with tqdm(
            total=100, desc=f'{fn.ljust(58):>{58 + 2}}', initial=0,
            bar_format='{desc} 【{bar:20}】【{percentage:3.0f}%】',
            ascii='▷▶', file=sys.stdout
        ) as pbar:
            for line in iter(p.stderr.readline, ''):
                if line.strip():
                    match = prog.search(line)
                    if match:
                        progress = float(match.group(1))
                        pbar.update(progress - pbar.n)
                        pbar.refresh()

                curl_output += line
            pbar.close()
        p.wait()

        if p.returncode != 0:
            if 'curl: (23)' in curl_output:
                print(
                    f"{'':>2}^ File already exists; download skipped. "
                    "Append a custom name after the URL or PATH to overwrite."
                )
            elif 'curl: (3)' in curl_output:
                print('')
            else:
                print(f"{'':>2}^ Error: {curl_output}")
        else:
            pass

    except KeyboardInterrupt:
        print(f"{'':>2}^ Canceled")

def gdrown(url, fp=None, fn=None):
    is_folder = 'drive.google.com/drive/folders' in url
    cmd = f'gdown --fuzzy {url}'

    if fp:
        fp = Path(fp).expanduser()
        fp.mkdir(parents=True, exist_ok=True)
        if fn:
            fn = fp / fn
            cmd += f' -O {fn}'
        cwd = str(fp)
    else:
        cwd = None

    if fn and not fp: cmd += f' -O {fn}'
    if is_folder: cmd += ' --folder'

    SyS(f'cd {cwd} && {cmd}' if cwd else cmd)

@register_line_magic
def clone(i):
    p = Path(i).expanduser()

    def proc(line):
        return line.strip()[len('git clone '):].strip() if line.strip().startswith('git clone') else line.strip()

    if p.suffix == '.txt' and p.is_file():
        cmds = [f'git clone {proc(line)}' for line in p.read_text().splitlines()]
    elif isinstance(i, str):
        cmds = [f'git clone {proc(i)}']
    else:
        cmds = [f'git clone {proc(l)}' for l in i]

    for cmd in cmds:
        cmd = cmd.strip()
        if not cmd:
            continue

        cmd_list = shlex.split(cmd)
        url = next((repo for repo in cmd_list if re.match(r'https?://', repo)), None)

        p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        while True:
            output = p.stdout.readline()
            if not output and p.poll() is not None:
                break

            if output := output.strip():
                if 'fatal' in output:
                    print(f'  {output}')
                elif output.startswith('Cloning into'):
                    repo_name = "/".join(output.split("'")[1].split("/")[-3:])
                    print(f'  {repo_name} ▶ {url}')

        p.wait()

@register_line_magic
def pull(line):
    inputs = line.split()
    if len(inputs) < 3: return

    subs = subprocess.run
    repo, tarfold, despath = inputs[:3]
    branch = inputs[3] if len(inputs) == 4 else None

    print(
        f"\n{'':>2}{'pull':<4} : {tarfold}",
        f"\n{'':>2}{'from':<4} : {repo}",
        f"\n{'':>2}{'into':<4} : {despath}",
        end=''
    )

    if branch: print(f"\n{'':>2}{'branch':<4} : {branch}")
    print()

    fp = Path(despath).expanduser()
    opts = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE, 'check': True}
    cmd1 = f'git clone -n --depth=1 --filter=tree:0'
    if branch: cmd1 += f' --branch {branch}'
    cmd1 += f' {repo}'
    subs(shlex.split(cmd1), cwd=str(fp), **opts)

    repo_name = Path(repo).name
    if repo_name.lower().endswith('.git'):
        repo_name = repo_name[:-4]
    repofold = fp / repo_name

    cmd2 = f'git sparse-checkout set --no-cone {tarfold}'
    subs(shlex.split(cmd2), cwd=str(repofold), **opts)

    cmd3 = 'git checkout'
    subs(shlex.split(cmd3), cwd=str(repofold), **opts)

    zipin = repofold / 'config' / tarfold
    zipout = fp / f'{tarfold}.zip'
    with zipfile.ZipFile(str(zipout), 'w') as zipf:
        for root in zipin.rglob('*'):
            if root.is_file():
                arcname = str(root.relative_to(zipin))
                zipf.write(str(root), arcname=arcname)

    cmd4 = f'unzip -o {str(zipout)}'
    subs(shlex.split(cmd4), cwd=str(fp), **opts)
    zipout.unlink()

    cmd5 = f'rm -rf {str(repofold)}'
    subs(shlex.split(cmd5), cwd=str(fp), **opts)

_print_lock = threading.Lock()

def parallel_batch_download(items, max_workers=3):
    """
    Download multiple files in parallel with per-slot progress lines + aggregate summary.
    Each download occupies its own line; a final '【#Parallel ...】' line shows combined stats.
    """
    if not items:
        return {}

    total  = len(items)
    results = {}

    # ── Shared progress state (written by workers, read by renderer) ──────────
    _state_lock = threading.Lock()
    _state = {}   # idx -> {'label': str, 'raw': str, 'done': bool, 'ok': bool}

    def _set_state(idx, **kw):
        with _state_lock:
            if idx not in _state:
                _state[idx] = {'label': '', 'raw': '', 'done': False, 'ok': True}
            _state[idx].update(kw)

    # ── Renderer ──────────────────────────────────────────────────────────────
    _stop_render = threading.Event()

    def _build_frame():
        with _state_lock:
            snap = {k: dict(v) for k, v in _state.items()}

        lines_out = []
        agg_speed = 0.0; agg_done = 0.0; agg_total = 0.0; agg_eta = 0; active = 0

        for i in range(total):
            slot  = snap.get(i, {})
            label = slot.get('label', f'file {i+1}')
            done  = slot.get('done', False)
            ok    = slot.get('ok', True)
            raw   = slot.get('raw', '')

            if done:
                icon = f'{GREEN}✓{RESET}' if ok else f'{RED}✗{RESET}'
                lines_out.append(f'  [{i+1}/{total}] {icon} {label}')
            elif raw:
                lines_out.append(f' {_fmt_progress(raw)}')
                st = _parse_aria2_stats(raw)
                agg_speed += st['speed_b']; agg_done += st['done_b']
                agg_total += st['total_b']; agg_eta = max(agg_eta, st['eta_s'])
                active += 1
            else:
                lines_out.append(f'  [{i+1}/{total}] {YELLOW}⏳{RESET} {label} — starting...')

        # Aggregate summary line
        if active > 0:
            pct  = int(100 * agg_done / agg_total) if agg_total else 0
            spd  = _fmt_size(agg_speed) + '/s'
            done_s  = _fmt_size(agg_done)
            total_s = _fmt_size(agg_total)
            eta  = _fmt_eta(agg_eta)
            agg_line = (
                f' {MAGENTA}【{RESET}'
                f'{CYAN}#Parallel{RESET} '
                f'{done_s}{MAGENTA}/{RESET}{total_s}'
                f'{MAGENTA}({RESET}{pct}%{MAGENTA}){RESET} '
                f'{CYAN}DL{RESET}:{PURPLE}{spd}{RESET} '
                f'{CYAN}ETA{RESET}:{YELLOW}{eta}{RESET}'
                f'{MAGENTA}】{RESET}'
            )
        else:
            done_c = sum(1 for s in snap.values() if s.get('done'))
            agg_line = f'  {CYAN}▶ {done_c}/{total} completed{RESET}'

        lines_out.append(agg_line)
        return '\n'.join(lines_out)

    def _render_loop():
        while not _stop_render.is_set():
            frame = _build_frame()
            clear_output(wait=True)
            print(frame)
            sys.stdout.flush()
            _stop_render.wait(0.25)
        # final frame
        clear_output(wait=True)
        print(_build_frame())
        sys.stdout.flush()

    renderer = threading.Thread(target=_render_loop, daemon=True, name='progress-renderer')
    renderer.start()

    # ── Workers ───────────────────────────────────────────────────────────────
    def _worker(idx, url, fp, fn):
        label = fn if fn else Path(urlparse(url).path).name or url
        _set_state(idx, label=label)
        try:
            fp = Path(fp).expanduser()
            fp.mkdir(parents=True, exist_ok=True)

            def _on_progress(raw):
                _set_state(idx, raw=raw)

            CHG = any(domain in url for domain in [*CIVITAI, 'huggingface.co', 'github.com'])
            if CHG:
                ariari(url, fp, fn, on_progress=_on_progress)
            elif 'drive.google.com' in url:
                gdrown(url, fp, fn)
            else:
                cmd = (f"curl -#OJL '{url}'" if not fn else f"curl -#L '{url}' -o '{fn}'")
                old_cwd = Path.cwd(); CD(fp)
                curlly(cmd, fn or label)
                CD(old_cwd)

            _set_state(idx, done=True, ok=True, raw='')
            return url, 'ok'
        except Exception as e:
            _set_state(idx, done=True, ok=False, raw='')
            return url, 'error'

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_worker, idx, url, fp, fn)
                   for idx, (url, fp, fn) in enumerate(items)]
        for f in as_completed(futures):
            url, status = f.result()
            results[url] = status

    _stop_render.set()
    renderer.join(timeout=2)

    ok  = sum(1 for s in results.values() if s == 'ok')
    err = sum(1 for s in results.values() if s == 'error')
    print(f'\n{CYAN}▶ Batch complete — {GREEN}{ok} ok{RESET}, {RED}{err} error(s){RESET}\n')
    return results


@register_line_magic
def tempe(line=''):
    try:
        from KANDANG import TEMPPATH
        TMP = Path(TEMPPATH)
    except ImportError:
        TMP = Path('/tmp')

    DIRS = [
        'ckpt',
        'lora',
        'controlnet',
        'svd',
        'z123',
        'clip',
        'clip_vision',
        'diffusers',
        'diffusion_models',
        'text_encoders',
        'unet'
    ]

    for SUB in DIRS: Path(f'{TMP}/{SUB}').mkdir(parents=True, exist_ok=True)
