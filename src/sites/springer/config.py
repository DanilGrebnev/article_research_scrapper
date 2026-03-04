import os

from config import DOWNLOAD_DIR

# Базовый URL сайта SpringerLink
BASE_URL = "https://link.springer.com"

# Поисковый запрос для поиска статей
SEARCH_QUERY = "surface alloying of iron castings in a casting mold"

# Путь к файлу с результатами скраппинга
OUTPUT_FILE = os.path.join(DOWNLOAD_DIR, "results.txt")

# Фильтр по доступу к статьям:
#   True  — собирать только статьи с полным доступом (Full access)
#   False — собирать все статьи, включая без полного доступа
ONLY_FULL_ACCESS = True
