# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['src/main.py'],
             pathex=['./'],
             binaries=[],
             datas=[
                 ('data/config.yaml', 'data'),
                 ('data/.default_config.yaml', 'data'),
                 ('data/backups', 'data/backups'),
                 ('data/logs', 'data/logs')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[
                 './data/test',
                 './data/backups/*',
                 './data/logs/*'
             ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='spautomod',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='SpotifyAutoModerator')
