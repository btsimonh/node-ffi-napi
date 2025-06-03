# This file is used with the GYP meta build system.
# http://code.google.com/p/gyp
# To build try this:
#   svn co http://gyp.googlecode.com/svn/trunk gyp
#   ./gyp/gyp -f make --depth=`pwd` libffi.gyp
#   make
#   ./out/Debug/test

{
  'variables': {
    'target_arch%': 'ia32', # built for a 32-bit CPU by default
    # Automatically detect platform based on os.type()
    'target_platform%': '<!(node -p "require(\'os\').type().startsWith(\'MINGW\') ? \'mingw\' : (process.platform === \'win32\' ? \'msvc\' : \'\')")',
  },
  'target_defaults': {
    'default_configuration': 'Debug',
    'configurations': {
      # MSVC specific runtime library settings
      'Debug': {
        'defines': [ 'DEBUG', '_DEBUG' ],
        'conditions': [
          ['target_platform=="msvc"', {
            'msvs_settings': {
              'VCCLCompilerTool': { 'RuntimeLibrary': 1 }, # static debug (/MTd)
            },
          }],
        ],
      },
      'Release': {
        'defines': [ 'NDEBUG' ],
         'conditions': [
          ['target_platform=="msvc"', {
             'msvs_settings': {
               'VCCLCompilerTool': { 'RuntimeLibrary': 0 }, # static release (/MT)
             },
          }],
        ],
      }
    },
    # MSVC specific settings block
    'conditions': [
      ['target_platform=="msvc"', {
        'msvs_settings': {
          'VCCLCompilerTool': {
          },
          'VCLibrarianTool': {
          },
          'VCLinkerTool': {
            'GenerateDebugInformation': 'true',
          },
        },
      }],
      ['OS == "win"', {
        'defines': [
          'WIN32' # Generic define for Windows (MSVC and MinGW)
        ],
      }]
    ],
  },

  # MSVC-specific rules for processing .preasm files
  'conditions': [
    ['OS=="win" and target_platform=="msvc"', {
      'target_defaults': {
        'variables': {
          # Define assembler based on architecture for MSVC
          # REMOVED ---> 'ml': '',
          'conditions': [
            # Define ml ONLY as a list within the relevant condition
            ['target_arch=="ia32"',  { 'ml': ['ml', '/c', '/nologo', '/safeseh' ] }],
            ['target_arch=="arm64"', { 'ml': ['armasm64', '/nologo' ] }],
            ['target_arch=="x64"',   { 'ml': ['ml64', '/c', '/nologo' ] }],
          ],
        },
        'rules': [
          {
            'rule_name': 'preprocess_asm',
            'msvs_cygwin_shell': 0,
            'extension': 'preasm',
            'inputs': [],
            'outputs': [ '<(INTERMEDIATE_DIR)/<(RULE_INPUT_ROOT).asm' ],
            'action': [
              '../../../deps/libffi/preprocess_asm.cmd',
                'include',
                'config/<(OS)/<(target_arch)',
                '<(RULE_INPUT_PATH)',
                '<(INTERMEDIATE_DIR)/<(RULE_INPUT_ROOT).asm',
            ],
            'message': 'Preprocessing assembly file <(RULE_INPUT_PATH) for MSVC',
            'process_outputs_as_sources': 1,
          },
          {
            'rule_name': 'build_asm',
            'msvs_cygwin_shell': 0,
            'extension': 'asm',
            'inputs': [],
            'outputs': [ '<(INTERMEDIATE_DIR)/<(RULE_INPUT_ROOT).obj' ],
            'action': [
              # '<@(ml)' correctly expands the list defined in the conditions above
              '<@(ml)',
              '/Fo<(INTERMEDIATE_DIR)/<(RULE_INPUT_ROOT).obj',
              '<(INTERMEDIATE_DIR)/<(RULE_INPUT_ROOT).asm',
            ],
            'message': 'Building assembly file <(RULE_INPUT_PATH) for MSVC',
            'process_outputs_as_sources': 1,
          },
        ],
      },
    }],
    # NOTE: No special rules needed for MinGW (.S files listed in sources
    # will be handled by GYP's default GCC integration).
  ],	  

  'targets': [
    {
      'target_name': 'ffi',
      'product_prefix': 'lib',
      'type': 'static_library',

      # for CentOS 5 support: https://github.com/rbranson/node-ffi/issues/110
      'standalone_static_library': 1,

      'sources': [
        # Common sources for all platforms/architectures
        'src/prep_cif.c',
        'src/types.c',
        'src/raw_api.c',
        'src/java_raw_api.c',
        'src/closures.c',
      ],
      'defines': [
        'PIC',
        'FFI_BUILDING',
        'HAVE_CONFIG_H'
      ],
      'include_dirs': [
        'include',
        # platform and arch-specific headers
        'config/<(OS)/<(target_arch)'
      ],
      'direct_dependent_settings': {
        'include_dirs': [
          'include',
          # platform and arch-specific headers
          'config/<(OS)/<(target_arch)'
        ],
      },
      'conditions': [
        # --- ARM ---
        ['target_arch=="arm"', {
          'sources': [ 'src/arm/ffi.c' ],
          'conditions': [
            ['OS=="linux"', { # Add other OS needing sysv.S if necessary
              'sources': [ 'src/arm/sysv.S' ]
            }],
            # Add Windows ARM specific sources if needed (currently none defined)
            # ['OS=="win"', { ... }]
          ]
        }],
        # --- ARM64 ---
        ['target_arch=="arm64"', {
          'sources': [ 'src/aarch64/ffi.c' ],
          'conditions': [
            ['OS=="linux" or OS=="mac"', {
              'sources': [ 'src/aarch64/sysv.S' ]
            }],
            ['OS=="win"', {
              'conditions': [
                ['target_platform=="msvc"', {
                  # MSVC uses specific preprocessed assembly
                  'sources': [ 'src/aarch64/win64_armasm.preasm' ]
                }],
                # For MinGW AArch64, assume sysv.S works (Needs Verification?)
                # Libffi's configure might select something else (e.g., win64.S if available/compatible)
                ['target_platform=="mingw"', {
                  'sources': [ 'src/aarch64/sysv.S' ]
                   # Alternatively, if src/aarch64/win64.S exists and works with GCC:
                   # 'sources': [ 'src/aarch64/win64.S' ]
                }],
              ],
            }],
          ]
        }],
        # --- IA32 (x86) ---
        ['target_arch=="ia32"', {
          'sources': [ 'src/x86/ffi.c' ],
          'conditions': [
            ['OS=="win"', {
              'conditions': [
                ['target_platform=="msvc"', {
                  # MSVC uses specific preprocessed assembly
                  'sources': [ 'src/x86/sysv_intel.preasm' ],
                }],
                ['target_platform=="mingw"', {
                  # MinGW uses standard GCC assembly syntax
                  'sources': [ 'src/x86/sysv.S' ],
                }],
              ],
            }, { # Not Windows (Linux, macOS, etc.)
              'sources': [ 'src/x86/sysv.S' ],
            }],
          ],
        }],
        # --- x64 ---
        ['target_arch=="x64"', {
          'conditions': [
            ['OS=="win"', {
              'conditions': [
                ['target_platform=="msvc"', {
                  # MSVC uses win64-specific C file and preprocessed assembly
                  'sources': [
                    'src/x86/ffiw64.c',
                    'src/x86/win64_intel.preasm',
                  ],
                  # MSVC-specific warning disable
                  'msvs_disabled_warnings': [ 4267 ],
                }],
                ['target_platform=="mingw"', {
                  # MinGW uses the standard ffi64.c and GCC assembly files
                  'sources': [
                    'src/x86/ffiw64.c',
                    #'src/x86/unix64.S', # Used by System V ABI (Linux, macOS, MinGW)
                    'src/x86/win64.S',  # Contains Windows x64 specific implementations
                  ],
                }],
              ],
            }, { # Not Windows (Linux, macOS, etc.)
              'sources': [
                'src/x86/ffi64.c',
                'src/x86/unix64.S',
                # win64.S is sometimes included even on non-windows, check libffi's logic if needed
                # 'src/x86/win64.S',
              ],
              # If unix64.S depends on win64.S contents, include it. Often it doesn't.
              # Check the libffi build system (configure.ac / Makefile.am) for exact sources used.
              # For now, assume only unix64.S is needed for non-Windows x64.
            }]
          ],
        }],
        # --- s390x ---
        ['target_arch=="s390x"', {
           # Assuming s390x is not relevant for Windows/MinGW
          'sources': [
            'src/s390/ffi.c',
            'src/s390/sysv.S',
          ],
        }],
        # --- Common Settings ---
        # (Moved msvs_disabled_warnings into the x64->win->msvc condition)
      ] # end conditions for ffi target
    },

    # Test targets should work without modification if 'ffi' builds correctly
    {
      'target_name': 'test',
      'type': 'executable',
      'dependencies': [ 'ffi' ],
      'sources': [ 'test.c' ],
      'conditions': [
        ['OS=="win" and target_platform=="mingw"', {
          # Link with libgcc if needed? Typically handled automatically.
          # 'libraries': ['-lgcc']
        }],
      ],
    },

    {
      'target_name': 'closure-test',
      'type': 'executable',
      'dependencies': [ 'ffi' ],
      'sources': [ 'closure.c' ],
       'conditions': [
        ['OS=="win" and target_platform=="mingw"', {
          # Link with libgcc if needed? Typically handled automatically.
          # 'libraries': ['-lgcc']
        }],
      ],
    }
  ]
}
