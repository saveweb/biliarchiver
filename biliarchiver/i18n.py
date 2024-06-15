import gettext
import locale
from pathlib import Path
import warnings

default_lang, default_enc = locale.getdefaultlocale()
default_lang = default_lang or "en"
languages = ["en"] if not default_lang.lower().startswith("zh") else ["zh_CN"]
appname = "biliarchiver"

localedir = Path(__file__).parent / "locales"
if not localedir.exists():
    warnings.warn("Locales directory not found, i18n will not work.", RuntimeWarning)

i18n = gettext.translation(
    appname, localedir=localedir, fallback=True, languages=languages
)

_ = i18n.gettext
ngettext = i18n.ngettext
