import base64, subprocess, sys
u = sys.argv[1].replace('lingxi-locate://', '')
p = base64.b64decode(u).decode('utf-8')
subprocess.Popen(['explorer', '/select,', p])
