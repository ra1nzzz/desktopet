import subprocess, os, sys

script_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = os.path.join(os.environ["APPDATA"], "WPS \u7075\u7280", "python-env", "pythonw.exe")
script_file = os.path.join(script_dir, "lingxi_droplet.py")
log_file = os.path.join(script_dir, "logs", "stderr.log")

os.makedirs(os.path.join(script_dir, "logs"), exist_ok=True)
with open(log_file, "w") as f:
    subprocess.Popen(
        [python_exe, script_file],
        cwd=script_dir,
        stderr=f,
    )
