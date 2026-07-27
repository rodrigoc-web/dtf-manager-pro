"""
main.py — DTF MANAGER PRO — ponto de entrada.
Resolve BASE_DIR (pasta do .exe) e SISTEMA_DIR (pasta empacotada / _MEIPASS),
insere ambos no sys.path e sobe a janela principal (ui.app.DTFProApp).
"""
from __future__ import annotations
import sys
import traceback
from pathlib import Path

if getattr(sys, "frozen", False):
    SISTEMA_DIR = Path(sys._MEIPASS)
    BASE_DIR    = Path(sys.executable).parent
else:
    SISTEMA_DIR = Path(__file__).parent
    BASE_DIR    = SISTEMA_DIR

for p in (str(BASE_DIR), str(SISTEMA_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main():
    from infrastructure.db.database import inicializar_banco
    from infrastructure.filesystem import db_path
    inicializar_banco(str(db_path()))

    from ui.app import DTFProApp
    app = DTFProApp(str(BASE_DIR), str(SISTEMA_DIR))
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        if not getattr(sys, "frozen", False):
            raise
        input("\nErro fatal. Pressione ENTER para fechar.")
