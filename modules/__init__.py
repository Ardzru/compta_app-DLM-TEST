# modules/__init__.py
"""
Package modules.

IMPORTANT :
Ce fichier doit rester léger.
Ne pas importer module_1, module_2, module_3 ni leurs handlers ici.

Pourquoi ?
Importer `modules.module_1.handlers.xxx` charge d'abord ce fichier.
Si ce fichier importe tout, une erreur Module 2/3 peut bloquer Module 1.
"""

__all__ = [
    "module_1",
    "module_2",
    "module_3",
]
