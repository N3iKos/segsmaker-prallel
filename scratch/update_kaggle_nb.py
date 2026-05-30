import json

file_path = r'd:\1NGODING\segsmaker-main\notebook\Segsmaker.ipynb'
with open(file_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] != 'code': continue
    
    source = "".join(cell['source'])
    
    if "Step 1 — Pick your WebUI:" in source:
        new_source = '''# 🖥️ WebUI Installer
import ipywidgets as widgets
from IPython.display import display, clear_output
import subprocess, sys, os
from pathlib import Path

ui_dropdown = widgets.Dropdown(
    options=["A1111", "Forge", "ReForge", "ReForge-old", "Forge-Classic", "Forge-Neo", "ComfyUI", "SwarmUI"],
    value='Forge-Neo',
    description='WebUI:'
)
civitai_key = widgets.Password(description='Civitai Key:', placeholder='Paste your Civitai API key here', layout=widgets.Layout(width='60%'))
hf_token = widgets.Password(description='HF Token:', placeholder='Huggingface READ token (optional)', layout=widgets.Layout(width='60%'))
install_btn = widgets.Button(description='▶ Install WebUI', button_style='primary')
output = widgets.Output()

def on_install_clicked(b):
    with output:
        clear_output()
        print(f"Installing {ui_dropdown.value}...")
        
        # Save tokens to environment so downloader can use them
        if civitai_key.value.strip(): os.environ['TOKET'] = civitai_key.value.strip()
        if hf_token.value.strip(): os.environ['TOBRUT'] = hf_token.value.strip()
        
        Path(os.path.expanduser('~/.conda')).mkdir(parents=True, exist_ok=True)
        _setup_py = os.path.expanduser('~/.conda/setup.py')
        _url = 'https://raw.githubusercontent.com/N3iKos/segsmaker-prallel/main/script/SM/setup.py'
        
        subprocess.run(['curl', '-fLo', _setup_py, _url], capture_output=True)
        get_ipython().run_line_magic('run', _setup_py)

install_btn.on_click(on_install_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>🖥️ WebUI Installer</h3><p>Choose your WebUI and credentials.</p>"),
    ui_dropdown, civitai_key, hf_token, install_btn, output
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

    elif "5 Checkpoint + 5 Lora + 1 VAE" in source:
        new_source = '''# 📥 Model Downloader
import ipywidgets as widgets
from IPython.display import display, clear_output

ckpts = [widgets.Text(placeholder="Checkpoint URL or leave empty", description=f"Ckpt {i+1}:", layout=widgets.Layout(width='90%')) for i in range(5)]
loras = [widgets.Text(placeholder="LoRA URL or leave empty", description=f"LoRA {i+1}:", layout=widgets.Layout(width='90%')) for i in range(5)]
vae = widgets.Text(placeholder="VAE URL or leave empty", description="VAE:", layout=widgets.Layout(width='90%'))

parallel_cb = widgets.Checkbox(value=True, description="Parallel Download")
workers_slider = widgets.IntSlider(value=3, min=1, max=6, description="Max Workers:")
download_btn = widgets.Button(description='⬇ Download Models', button_style='info')
dl_output = widgets.Output()

acc = widgets.Accordion(children=[
    widgets.VBox(ckpts),
    widgets.VBox(loras),
    widgets.VBox([vae])
])
acc.set_title(0, '🗃️ Checkpoints')
acc.set_title(1, '🎨 LoRA')
acc.set_title(2, '🎛️ VAE')

def on_download_clicked(b):
    with dl_output:
        clear_output()
        try:
            from nenen88 import parallel_batch_download
        except ImportError:
            print("❌ nenen88 not found. Make sure you've run the Bootstrap cell.")
            return
            
        _queue = []
        for w in ckpts:
            if w.value.strip(): _queue.append((w.value.strip(), str(CKPT), None))
        for w in loras:
            if w.value.strip(): _queue.append((w.value.strip(), str(LORA), None))
        if vae.value.strip():
            _queue.append((vae.value.strip(), str(VAE), None))
            
        if not _queue:
            print('No URLs provided — skipping download.')
        elif parallel_cb.value:
            parallel_batch_download(_queue, max_workers=workers_slider.value)
        else:
            for _url, _dest, _fn in _queue:
                get_ipython().run_line_magic('cd', f'-q {_dest}')
                get_ipython().run_line_magic('download', _url)

download_btn.on_click(on_download_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>📥 Model Downloader</h3><p>Fill in the slots below. Empty slots are automatically skipped.</p>"),
    acc, parallel_cb, workers_slider, download_btn, dl_output
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

    elif "Extensions / Custom Nodes (git clone URL)" in source:
        new_source = '''# 🛠️ Extra Assets
import ipywidgets as widgets
from IPython.display import display, clear_output
import tempfile, os

exts = [widgets.Text(placeholder="git clone URL or leave empty", description=f"Ext {i+1}:", layout=widgets.Layout(width='90%')) for i in range(3)]
embs = [widgets.Text(placeholder="URL or leave empty", description=f"Emb {i+1}:", layout=widgets.Layout(width='90%')) for i in range(2)]
upscs = [widgets.Text(placeholder="URL or leave empty", description=f"Upscaler {i+1}:", layout=widgets.Layout(width='90%')) for i in range(2)]

extra_btn = widgets.Button(description='📦 Install Extras', button_style='warning')
extra_output = widgets.Output()

acc_extra = widgets.Accordion(children=[
    widgets.VBox(exts),
    widgets.VBox(embs),
    widgets.VBox(upscs)
])
acc_extra.set_title(0, '🔌 Extensions')
acc_extra.set_title(1, '🖼️ Embeddings')
acc_extra.set_title(2, '🔬 Upscalers')

def on_extra_clicked(b):
    with extra_output:
        clear_output()
        try:
            from nenen88 import parallel_batch_download
        except ImportError:
            pass
            
        _ext_urls = [w.value.strip() for w in exts if w.value.strip()]
        if _ext_urls:
            _tmp_ext = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            _tmp_ext.write('\\n'.join(_ext_urls))
            _tmp_ext.flush()
            _tmp_ext.close()
            print('\\n⚡ Cloning extensions in parallel...')
            get_ipython().run_line_magic('cd', f'-q {Extensions}')
            get_ipython().run_line_magic('clone', _tmp_ext.name)
            os.unlink(_tmp_ext.name)

        _asset_queue = []
        for w in embs:
            if w.value.strip(): _asset_queue.append((w.value.strip(), str(Embeddings), None))
        for w in upscs:
            if w.value.strip(): _asset_queue.append((w.value.strip(), str(Upscalers), None))
            
        if _asset_queue:
            parallel_batch_download(_asset_queue, max_workers=3)
        
        print("✅ Extra assets installed.")

extra_btn.on_click(on_extra_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>🛠️ Extra Assets</h3>"),
    acc_extra, extra_btn, extra_output
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

    elif "Select FLUX Variant" in source:
        new_source = '''# ⚡ FLUX Model Downloader
import ipywidgets as widgets
from IPython.display import display, clear_output

flux_variant = widgets.Dropdown(
    options=["None", "FLUX.1-schnell (Fast, 4-step)", "FLUX.1-dev (Quality, 20-step)"],
    value="None", description="Variant:"
)
unet_url = widgets.Text(value="https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-schnell-fp8.safetensors", description="UNet:", layout=widgets.Layout(width='95%'))
clip_l_url = widgets.Text(value="https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors", description="CLIP L:", layout=widgets.Layout(width='95%'))
t5xxl_url = widgets.Text(value="https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors", description="T5XXL:", layout=widgets.Layout(width='95%'))
vae_url = widgets.Text(value="https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors", description="VAE:", layout=widgets.Layout(width='95%'))

flux_btn = widgets.Button(description='⚡ Download FLUX', button_style='danger')
flux_out = widgets.Output()

def on_flux_clicked(b):
    with flux_out:
        clear_output()
        if flux_variant.value == "None":
            print('FLUX Variant is "None" — skipping.')
            return
            
        from nenen88 import parallel_batch_download
        
        _unet = unet_url.value
        if 'dev' in flux_variant.value.lower() and 'schnell' in _unet:
            _unet = _unet.replace('schnell', 'dev')
            
        _flux_queue = []
        if _unet.strip(): _flux_queue.append((_unet.strip(), str(UNET), None))
        if clip_l_url.value.strip(): _flux_queue.append((clip_l_url.value.strip(), str(CLIP), None))
        if t5xxl_url.value.strip(): _flux_queue.append((t5xxl_url.value.strip(), str(CLIP), None))
        if vae_url.value.strip(): _flux_queue.append((vae_url.value.strip(), str(VAE), 'flux_ae.safetensors'))
        
        print(f'\\n⚡ Downloading {flux_variant.value} ({len(_flux_queue)} files in parallel)...')
        parallel_batch_download(_flux_queue, max_workers=2)
        print('\\n✅ FLUX ready. Enable FLUX support in your WebUI.')

flux_btn.on_click(on_flux_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>⚡ FLUX Model Downloader</h3><p>Works with Forge, ComfyUI, and SwarmUI.</p>"),
    flux_variant, unet_url, clip_l_url, t5xxl_url, vae_url, flux_btn, flux_out
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

    elif "Temporary Checkpoints" in source:
        new_source = '''# 💨 Temporary Model Downloader
import ipywidgets as widgets
from IPython.display import display, clear_output

tmp_ckpts = [widgets.Text(placeholder="URL [optional_filename] or leave empty", description=f"Tmp Ckpt {i+1}:", layout=widgets.Layout(width='90%')) for i in range(2)]
tmp_loras = [widgets.Text(placeholder="URL or leave empty", description=f"Tmp LoRA {i+1}:", layout=widgets.Layout(width='90%')) for i in range(2)]

tmp_btn = widgets.Button(description='⬇ Download Temporary Models', button_style='info')
tmp_out = widgets.Output()

def on_tmp_clicked(b):
    with tmp_out:
        clear_output()
        try:
            from nenen88 import parallel_batch_download
        except ImportError:
            pass
            
        _tmp_queue = []
        for w in tmp_ckpts:
            if not w.value.strip(): continue
            _p = w.value.strip().split(None, 1)
            _tmp_queue.append((_p[0], str(TMP_CKPT), _p[1] if len(_p) > 1 else None))
            
        for w in tmp_loras:
            if not w.value.strip(): continue
            _p = w.value.strip().split(None, 1)
            _tmp_queue.append((_p[0], str(TMP_LORA), _p[1] if len(_p) > 1 else None))
            
        if not _tmp_queue:
            print('No temporary URLs provided — skipping.')
        else:
            parallel_batch_download(_tmp_queue, max_workers=3)

tmp_btn.on_click(on_tmp_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>💨 Temporary Model Downloader</h3><p>Stored in /tmp — cleared on session end.</p>"),
    widgets.VBox(tmp_ckpts),
    widgets.VBox(tmp_loras),
    tmp_btn, tmp_out
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

    elif "Launch WebUI" in source or "Skip_Widget" in source:
        new_source = '''# 🚀 Launcher WebUI
import ipywidgets as widgets
from IPython.display import display, clear_output
import os

software_dropdown = widgets.Dropdown(
    options=["A1111", "Forge", "ReForge", "Forge-Classic", "Forge-Neo", "ComfyUI", "SwarmUI"],
    value="Forge-Neo",
    description="Software:"
)
ngrok_input = widgets.Text(
    value="2SrmI5xCy7MGdmpvSym3fTk5qEs_jDAWhnE2Y9pQof1mejaZ",
    placeholder="Enter Ngrok Token",
    description="Ngrok:",
    layout=widgets.Layout(width='60%')
)
zrok_input = widgets.Text(
    value="",
    placeholder="Enter Zrok Token",
    description="Zrok:",
    layout=widgets.Layout(width='60%')
)
launch_btn = widgets.Button(
    description="🚀 Launch",
    button_style="success",
    layout=widgets.Layout(width='60%', height='40px')
)
launch_out = widgets.Output()

def launch_clicked(b):
    with launch_out:
        clear_output()
        software = software_dropdown.value
        ngrok = ngrok_input.value.strip()
        zrok = zrok_input.value.strip()
        
        # Mapping Arguments
        args_map = {
            "A1111": "--xformers",
            "Forge": "--disable-xformers --opt-sdp-attention --cuda-stream",
            "ReForge": "--xformers --cuda-stream",
            "Forge-Classic": "--xformers --cuda-stream --persistent-patches",
            "Forge-Neo": "--xformers --cuda-stream",
            "ComfyUI": "--dont-print-server --use-pytorch-cross-attention",
            "SwarmUI": "--launch_mode none"
        }
        
        selected_args = args_map.get(software, "")
        
        # Add Tunnels
        if ngrok:
            selected_args += f" --N={ngrok}"
        if zrok:
            selected_args += f" --Z={zrok}"
            
        print(f"📦 Launching {software} with args: {selected_args}")
        
        # Determine WebUI path.
        webui_path = os.path.expanduser(f"~/{software}")
        
        if os.path.exists(webui_path):
            get_ipython().run_line_magic('cd', f'-q {webui_path}')
            get_ipython().run_line_magic('run', f'segsmaker.py {selected_args}')
        else:
            print(f"❌ Cannot find installation at {webui_path}. Did you run the WebUI Installer?")

launch_btn.on_click(launch_clicked)
display(widgets.VBox([
    widgets.HTML("<h3>🚀 Launcher WebUI</h3><p>Pilih software dan masukkan token tunnel jika diperlukan.</p>"),
    software_dropdown, ngrok_input, zrok_input, launch_btn, launch_out
]))'''
        cell['source'] = [line + '\n' for line in new_source.split('\n')]
        cell['source'][-1] = cell['source'][-1].rstrip('\n')

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)

print("Kaggle Notebook successfully updated with ipywidgets!")
