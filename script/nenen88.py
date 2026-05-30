TOKET = ''
TOBRUT = ''

from IPython.core.magic import register_line_magic
from IPython.display import display, HTML, clear_output
from urllib.parse import urlparse
from IPython import get_ipython
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import threading
import subprocess
import requests
import zipfile
import shlex
import json
import sys
import re
import os
import io
import time

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
iRON = os.environ

KAGGLE = 'KAGGLE_DATA_PROXY_TOKEN' in iRON

CIVITAI = ['civitai.com', 'civitai.red']

@dataclass
class DownloadTask:
    index: int
    raw: str
    url: str = ''
    path: Path | None = None
    filename: str | None = None
    label: str = ''
    status: str = 'Queued'
    percent: float = 0.0
    speed: str = 'N/A'
    error: str = ''
    started_at: float = 0.0
    finished_at: float = 0.0
    size_bytes: int = 0

@dataclass
class DownloadProgress:
    tasks: list[DownloadTask] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    started_at: float = field(default_factory=time.time)

    def snapshot(self):
        with self.lock:
            return [DownloadTask(**task.__dict__) for task in self.tasks]

def _safe_worker_count(max_workers):
    try:
        workers = int(max_workers)
    except Exception:
        workers = 3
    return max(1, min(workers, 8))

def _safe_aria_number(value, default=16):
    try:
        number = int(value)
    except Exception:
        number = default
    return max(1, min(number, 16))

def _format_bytes(size):
    try:
        size = float(size or 0)
    except Exception:
        size = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f'{size:,.2f} {unit}' if unit != 'B' else f'{int(size)} B'
        size /= 1024

def _format_duration(seconds):
    try:
        seconds = float(seconds or 0)
    except Exception:
        seconds = 0
    return f'{seconds:.1f}s'

def _format_speed(size, seconds):
    try:
        seconds = float(seconds or 0)
        if seconds <= 0:
            return 'N/A'
        return f'{(float(size or 0) / seconds) / (1024 * 1024):6.2f} MB/s'
    except Exception:
        return 'N/A'

def _task_file_path(task):
    if not task.path or not task.filename:
        return None
    return Path(task.path).expanduser() / task.filename

def _download_filename(url, is_known_host):
    if is_known_host:
        try:
            return get_fn(url)
        except Exception:
            return Path(urlparse(url).path).name or 'download'
    return Path(urlparse(url).path).name or 'download'

def _parse_download_task(index, line, default_cwd=None):
    raw = str(line or '').strip()
    if not raw:
        return DownloadTask(index=index, raw='', status='Skipped', error='empty slot')

    parts = raw.split()
    url = parts[0].replace('\\', '')
    cwd = Path(default_cwd or Path.cwd()).expanduser()
    known_host = any(domain in url for domain in [*CIVITAI, 'huggingface.co', 'github.com'])

    def is_path(value):
        return '/' in value or '~/' in value

    try:
        if len(parts) >= 3:
            arg1, arg2 = parts[1], parts[2]
            path_arg, file_arg = (arg2, arg1) if is_path(arg2) and not is_path(arg1) else \
                                 (arg1, arg2) if is_path(arg1) and not is_path(arg2) else \
                                 (arg2, arg1) if Path(arg2).suffix == '' and Path(arg1).suffix != '' else \
                                 (arg1, arg2)
            path = Path(path_arg).expanduser()
            filename = file_arg
        elif len(parts) == 2:
            arg = parts[1]
            if is_path(arg):
                path = Path(arg).expanduser()
                filename = _download_filename(url, known_host)
            else:
                path = cwd
                filename = arg
        else:
            path = cwd
            filename = _download_filename(url, known_host)

        label = Path(filename or _download_filename(url, known_host)).stem[:28]
        return DownloadTask(index=index, raw=raw, url=url, path=path, filename=filename, label=label)
    except Exception as exc:
        return DownloadTask(index=index, raw=raw, status='Failed', error=str(exc), label=f'link-{index}')

def analyze_download_links(lines, default_cwd=None):
    tasks = [_parse_download_task(i, line, default_cwd) for i, line in enumerate(lines, start=1)]
    _print_analysis_summary(tasks)
    return tasks

def _print_analysis_summary(tasks):
    print(f'[INFO] Analyzing {len(tasks)} link(s)...')
    valid = 0
    for task in tasks:
        if task.status == 'Skipped':
            print(f'[SKIP] [{task.index}] empty slot')
        elif task.status == 'Failed':
            print(f'[FAIL] [{task.index}] {task.error}')
        else:
            valid += 1
            name = task.filename or task.label or task.url
            print(f'[OK]   [{task.index}] {name}')
    print(f'[INFO] Valid: {valid}/{len(tasks)}')

def _progress_bar(percent, width=30):
    percent = max(0.0, min(100.0, float(percent or 0.0)))
    filled = int(round(width * percent / 100))
    return '[' + ('█' * filled) + ('-' * (width - filled)) + ']'

def render_parallel_dashboard(progress, final=False, mode='parallel'):
    tasks = progress.snapshot()
    active = sum(1 for task in tasks if task.status == 'Running')
    done = sum(1 for task in tasks if task.status == 'Done')
    valid = [task for task in tasks if task.status != 'Skipped']
    total_percent = sum(task.percent for task in valid) / len(valid) if valid else 100.0
    elapsed = max(0.0, time.time() - progress.started_at)
    total_size = sum(task.size_bytes for task in valid)
    speed = _format_speed(total_size, elapsed)

    clear_output(wait=True)
    _print_analysis_summary(tasks)
    print('[INFO] Starting parallel download...')
    print(f'TOTAL: {_progress_bar(total_percent)} {total_percent:5.1f}%')
    print(f'Speed: {speed} | Active: {active} | Done: {done}/{len(valid)}')
    print('-' * 70)
    for task in tasks:
        if task.status == 'Skipped':
            continue
        name = (task.label or task.filename or f'link-{task.index}')[:28]
        speed = task.speed or 'N/A'
        print(f'[{task.index:2}] {name:<28} : {task.percent:5.1f}% | {speed:>11} | {task.status}')
        if final and task.error:
            print(f'     error: {task.error}')

def format_download_complete(tasks, mode='parallel'):
    valid = [task for task in tasks if task.status != 'Skipped']
    done = [task for task in valid if task.status == 'Done']
    failed = [task for task in valid if task.status == 'Failed']
    start_times = [task.started_at for task in valid if task.started_at]
    finish_times = [task.finished_at for task in valid if task.finished_at]
    elapsed = (max(finish_times) - min(start_times)) if start_times and finish_times else 0
    total_size = sum(task.size_bytes for task in done)

    print('=' * 70)
    print('[INFO] Download Complete!' if not failed else '[INFO] Download Finished With Errors')
    print('-' * 70)
    for task in done:
        duration = max(0, task.finished_at - task.started_at)
        print(f'✅ [{task.index}] {(task.filename or task.label):<40} {_format_bytes(task.size_bytes):>10} {_format_duration(duration):>8}')
    for task in failed:
        print(f'❌ [{task.index}] {(task.filename or task.label):<40} {task.error}')
    print('-' * 70)
    print(f'Total: {_format_bytes(total_size)} | Time: {_format_duration(elapsed)} ({mode}) | Files: {len(done)}/{len(valid)}')
    print('=' * 70)

def _run_download_task(task, progress, aria_connections=16, aria_split=16, min_split_size='1M', skip_completed=True, fallback_to_wget=True):
    with progress.lock:
        task.status = 'Running'
        task.started_at = time.time()

    try:
        task.path.mkdir(parents=True, exist_ok=True)
        target = _task_file_path(task)
        if skip_completed and target and target.exists() and target.stat().st_size > 0:
            with progress.lock:
                task.size_bytes = target.stat().st_size
                task.percent = 100.0
                task.status = 'Done'
                task.finished_at = time.time()
                task.speed = _format_speed(task.size_bytes, task.finished_at - task.started_at)
            return task

        drive_google = 'drive.google.com' in task.url

        try:
            if drive_google:
                gdrown(task.url, task.path, task.filename)
            else:
                ariari(
                    task.url, task.path, task.filename, quiet=True,
                    aria_connections=aria_connections, aria_split=aria_split,
                    min_split_size=min_split_size
                )
        except Exception:
            if not fallback_to_wget:
                raise
            curlly(f"curl -#JL '{task.url}' -o '{task.filename}'", task.filename, cwd=task.path, quiet=True)

        with progress.lock:
            if target and target.exists():
                task.size_bytes = target.stat().st_size
            task.percent = 100.0
            task.status = 'Done'
            task.finished_at = time.time()
            task.speed = _format_speed(task.size_bytes, task.finished_at - task.started_at)
    except Exception as exc:
        with progress.lock:
            task.status = 'Failed'
            task.error = str(exc)
            task.finished_at = time.time()
    return task

def download_many(
    lines, max_workers=3, parallel=True, default_cwd=None,
    aria_connections=16, aria_split=16, min_split_size='1M',
    skip_completed=True, fallback_to_wget=True
):
    if isinstance(lines, str):
        lines = [line for line in lines.splitlines() if line.strip()]

    tasks = analyze_download_links(list(lines), default_cwd=default_cwd)
    valid = [task for task in tasks if task.status not in {'Skipped', 'Failed'}]
    if not valid:
        return tasks

    workers = _safe_worker_count(max_workers)
    parallel = bool(parallel) and workers > 1 and len(valid) > 1
    mode = 'parallel' if parallel else 'sequence'
    if not parallel:
        progress = DownloadProgress(tasks=tasks)
        for task in valid:
            _run_download_task(
                task, progress, aria_connections=aria_connections,
                aria_split=aria_split, min_split_size=min_split_size,
                skip_completed=skip_completed, fallback_to_wget=fallback_to_wget
            )
        render_parallel_dashboard(progress, final=True, mode=mode)
        format_download_complete(tasks, mode=mode)
        return tasks

    progress = DownloadProgress(tasks=tasks)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _run_download_task, task, progress,
                _safe_aria_number(aria_connections), _safe_aria_number(aria_split),
                str(min_split_size or '1M'), bool(skip_completed), bool(fallback_to_wget)
            )
            for task in valid
        ]
        while any(not future.done() for future in futures):
            render_parallel_dashboard(progress, mode=mode)
            time.sleep(0.75)
        for future in as_completed(futures):
            future.result()
    render_parallel_dashboard(progress, final=True, mode=mode)
    format_download_complete(tasks, mode=mode)
    return tasks

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
        # Add token only for non-Civitai hosts and when TOKET is set.
        try:
            parsed = urlparse(u)
            host = parsed.netloc.lower()
        except:
            return u

        # If host is Civitai or Backblaze storage, do NOT modify the signed URL.
        if any(d in host for d in CIVITAI) or host.startswith('b2.'):
            return u

        if not TOKET:
            return u

        if '?type=' in u:
            return u.replace('?type=', f'?token={TOKET}&type=')
        return f'{u}?token={TOKET}'

    if 'github.com' in url:
        url = url.replace('/blob/', '/raw/')
        return maybe_add_token(url), None, None

    elif 'huggingface.co' in url:
        url = url.split('?')[0]
        h = {'User-Agent': 'Mozilla/5.0', **({'Authorization': f'Bearer {TOBRUT}'} if TOBRUT else {})}
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

def ariari(url, fp, fn, quiet=False, aria_connections=16, aria_split=16, min_split_size='1M'):
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

    cmd = [
        'aria2c',
        f"--header=User-Agent: {civitai_headers()['User-Agent'] if f'{civitai}' in url else 'Mozilla/5.0'}",
        '--allow-overwrite=true', '--console-log-level=error', '--stderr=true',
        '-c',
        f'-x{_safe_aria_number(aria_connections)}',
        f'-s{_safe_aria_number(aria_split)}',
        f'-k{min_split_size or "1M"}',
        '-j5', '--dir', str(fp)
    ]

    if f'{civitai}/api/download/models/' in url and TOKET: cmd.append(f"--header=Authorization: Bearer {TOKET}")
    if TOBRUT and 'huggingface.co' in url: cmd.append(f'--header=Authorization: Bearer {TOBRUT}')

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
                        prog = re.sub(r'\[', MAGENTA + '【' + RESET, prog)
                        prog = re.sub(r'\]', MAGENTA + '】' + RESET, prog)
                        prog = re.sub(r'(#)(\w+)', f'{CYAN}\\1{RESET}{GREEN}\\2{RESET}', prog)
                        prog = re.sub(r'(\d+(\.\d+)?)(\w+)(/)(\d+(\.\d+)?)(\w+)', f"\\1{PURPLE}\\3{RESET}{MAGENTA}\\4{RESET}\\5{PURPLE}\\7{RESET}", prog)
                        prog = re.sub(r'(\()(\d+%)(\))', f'{MAGENTA}\\1{RESET}\\2{MAGENTA}\\3{RESET}', prog)
                        prog = re.sub(r'(CN)(:)(\d+)', f"{CYAN}\\1{RESET}\\2{ORANGE}\\3{RESET}", prog)
                        prog = re.sub(r'(DL)(:)(\d+(\.\d+)?)(\w+)', f"{CYAN}\\1{RESET}\\2\\3{PURPLE}\\5{RESET}", prog)
                        prog = re.sub(r'(ETA)(:)(\d+\w+)', f"{CYAN}\\1{RESET}\\2{YELLOW}\\3{RESET}", prog)

                        lines = prog.splitlines()
                        if not quiet:
                            for line in lines:
                                print(f"\r{' '*300}\r {line}", end='')
                                sys.stdout.flush()

                        break_line = True
                        break

        civitai = None
        error = error_code + error_line
        if not quiet:
            for lines in error: print(f'  {lines}')

        break_line and not quiet and print()

        stripe = aria2_output.find('======+====+===========')
        if stripe != -1:
            for lines in aria2_output[stripe:].splitlines():
                if '|' in lines and 'OK' in lines:
                    lines = re.sub(r'(\|\s*)(OK)(\s*\|)', f'\\1{GREEN}\\2{RESET}\\3', lines)
                    first, _, last = lines.rpartition('|')
                    last = re.sub(r'/', f'{ORANGE}/{RESET}', last)
                    lines = f'{first}|{last}'
                    if not quiet:
                        print(f'  {lines}')

        if j:
            civitai_infotags(j, fp, fn, versionId)
            civitai_preview(j, fp, fn, versionId)

        p.wait()
        if p.returncode != 0:
            message = error[-1] if error else f'aria2c exited with code {p.returncode}'
            raise RuntimeError(message)

    except KeyboardInterrupt:
        print(f'\n{"":>2}^ Canceled')

def curlly(cmd, fn, cwd=None, quiet=False):
    try:
        p = subprocess.Popen(
            shlex.split(cmd), cwd=str(Path(cwd or Path.cwd()).expanduser()),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        prog = re.compile(r'(\d+\.\d+)%')
        curl_output = ''

        pbar = None if quiet else tqdm(
            total=100, desc=f'{fn.ljust(58):>{58 + 2}}', initial=0,
            bar_format='{desc} 【{bar:20}】【{percentage:3.0f}%】',
            ascii='▷▶', file=sys.stdout
        )
        try:
            for line in iter(p.stderr.readline, ''):
                if pbar is not None and line.strip():
                    match = prog.search(line)
                    if match:
                        progress = float(match.group(1))
                        pbar.update(progress - pbar.n)
                        pbar.refresh()

                curl_output += line
        finally:
            if pbar is not None:
                pbar.close()
        p.wait()

        if p.returncode != 0:
            if quiet:
                raise RuntimeError(curl_output.strip() or f'curl exited with code {p.returncode}')
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

    repofold = fp / Path(repo).name.rstrip('.git')

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
