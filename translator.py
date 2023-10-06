import os
import i18n
from i18n import TranslatorGroup as Translator

i18n.load_path.append(os.path.abspath('./locales'))
i18n.set('filename_format','{namespace}.{format}')
i18n.set('file_format','yml')
