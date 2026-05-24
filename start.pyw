import subprocess, os

script_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = os.path.join(os.environ["APPDATA"], "WPS \u7075\u7280", "python-env", "pythonw.exe")
script_file = os.path.join(script_dir, "lingxi_droplet.py")
log_file = os.path.join(script_dir, "logs", "stderr.log")

os.makedirs(os.path.join(script_dir, "logs"), exist_ok=True)
with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"[{python_exe}]\n")
    f.write(f"[{script_file}]\n")
    subprocess.Popen(
        [python_exe, script_file],
        cwd=script_dir,
        stderr=f,
    )
