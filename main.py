"""
main.py — Punto de entrada principal del Campus Virtual IES N°5 Launcher.
Inicia la aplicación híbrida Pyloid con interfaz gráfica web moderna.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_pyloid import main as pyloid_main

if __name__ == "__main__":
    pyloid_main()
