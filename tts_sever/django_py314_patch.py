"""
Python 3.14 изменил поведение copy() для super(); Django 4.2.x до сих пор
использует copy(super()) в BaseContext.__copy__, из‑за чего падает админка.

Патч повторяет исправление из ветки Django main (см. django/template/context.py).
Удалите этот модуль после перехода на Django 5.2+ или официальный бэкпорт.
"""

from __future__ import annotations

import sys


def apply() -> None:
    if sys.version_info < (3, 14):
        return

    from copy import copy as copy_fn

    from django.template.context import BaseContext

    def __copy__(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy_fn(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = __copy__
