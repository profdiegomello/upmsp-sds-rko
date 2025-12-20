# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# =========================================================
# NOTA: Este arquivo assume que você roda o comando
# 'pyinstaller RKO.spec' DE DENTRO da pasta 'APP'
# =========================================================

# --- 1. ANÁLISE DA INTERFACE (MAIN) ---
a_main = Analysis(
    ['main.py'],  # <--- CAMINHO RELATIVO DIRETO
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')], # Copia a pasta assets
    hiddenimports=['PIL._tkinter_finder', 'backend', 'interface'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- 2. ANÁLISE DO SOLVER (WORKER) ---
a_solver = Analysis(
    ['backend/rko_dependencies/solver_rko.py'],
    pathex=[],
    binaries=[],
    datas=[], 
    # ADICIONAMOS A CORREÇÃO AQUI TAMBÉM:
    hiddenimports=['PIL._tkinter_finder'], 
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- 3. MESCLAGEM (MERGE) ---
merger = MERGE( (a_main, 'main', 'RKO_Solver_App'), (a_solver, 'solver', 'solver_worker') )

# --- 4. CRIAÇÃO DOS ARQUIVOS PYTHON (PYZ) ---
pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher)
pyz_solver = PYZ(a_solver.pure, a_solver.zipped_data, cipher=block_cipher)

# --- 5. CRIAÇÃO DOS EXECUTÁVEIS (EXE) ---
exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],
    exclude_binaries=True,
    name='RKO_Solver_App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

exe_solver = EXE(
    pyz_solver,
    a_solver.scripts,
    [],
    exclude_binaries=True,
    name='solver_worker', 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --- 6. COLETA FINAL (COLLECT) ---
coll = COLLECT(
    exe_main,
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    
    exe_solver, 
    a_solver.binaries,
    a_solver.zipfiles,
    a_solver.datas,
    
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RKO_Solver_App', 
)