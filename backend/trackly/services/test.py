from .scraper import *


scraper = Scraper()

result = scraper.validate_url(
    "https://www.upwork.com/nx/search/talent/?nbs=1&q=backend%20developer"
)

print(result)