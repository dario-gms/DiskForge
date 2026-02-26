# DiskForge — Launcher sem terminal
# No Windows, arquivos .pyw são executados pelo pythonw.exe,
# que não abre janela de console. Dê duplo clique para iniciar.

import runpy, os, sys
sys.argv[0] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disk_converter.py")
runpy.run_path(sys.argv[0], run_name="__main__")
