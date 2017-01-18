# -*- mode: python -*-

block_cipher = None

options = [ ('u', '', 'OPTION') ]

a = Analysis(['../../src/gmv_runner.py'],
             pathex=['/Users/gaubert/Documents/Dev/gmvault'],
             binaries=None,
             datas=[('../../src/gmv/cacerts/cacert.pem', 'gmv/cacerts')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          options,
          exclude_binaries=True,
          name='gmv_runner',
          debug=False,
          strip=False,
          upx=False,
          console=True )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='gmv_app')
