import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# Возможно у меня проблемы с интернетом и страницы не с первого раза открываются
def get_response(url: str) -> requests.Response:
    """Получает страницу, делая до трёх попыток при сетевом сбое."""
    for attempt in range(1, 4):
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            return response

        except (requests.ConnectionError, requests.Timeout):
            if attempt == 3:
                raise

            delay = 2 * attempt
            print(f"Сбой запроса. Повтор через {delay} сек.: {url}")
            time.sleep(delay)


def get_book_data(book_url: str) -> dict:
   """
   Сборка данных о книге с сайта.

   Args:
      book_url (str): URL книги.

   Returns:
      dict: название, цена, рейтинг, количество, статус наличия,
         описание, другие характеристики. 
   """

   # НАЧАЛО ВАШЕГО РЕШЕНИЯ
   # получим доступ к странице
   response = get_response(book_url)
   # разбираем html
   soup = BeautifulSoup(response.content, "html.parser")

   # название находится в теге h1
   title = soup.find("h1").get_text()
   # вытащим цену из тега p с классом price_color
   price = soup.find("p", class_="price_color").get_text()

   # получаем рейтинг в виде слова из второго класса элемента с тегом p и классом star-rating 
   rating = soup.find("p", class_="star-rating")["class"][1]

   # наличие в классе availability
   availability = soup.find("p", class_="availability").get_text().strip()
   stock = re.search(r"\d+", availability).group()

   # находим блок с заголовком описания по его id
   description_header = soup.find("div", id="product_description")
   # Если описание отсутствует, оставляем пустую строку
   description = ""

   # оказывается у некоторых книжек нету описания!
   if description_header is not None:
      # на одном уровне с этим заголовком находится тег p, внутри которого есть описание
      description_tag = description_header.find_next_sibling("p")
      description = description_tag.get_text(strip=True)

   # остается распарсить таблицу
   table = soup.find("table", class_="table-striped")
   product_info = {}
   for row in table.find_all("tr"):
      product_info[row.find("th").get_text()] = row.find("td").get_text()

   # сборка данных книги в словарь
   return {
      "title": title,
      "price": price,
      "rating": rating,
      "stock": stock,
      "availability": availability,
      "description": description,
      "product_info": product_info
   }
   # КОНЕЦ ВАШЕГО РЕШЕНИЯ


import json
from urllib.parse import urljoin


def scrape_books(is_save: bool = False) -> list:
    """Сборка всех книг из каталога.

    Args:
        is_save (bool): Если True, сохраняет результат в books_data.txt
            в текущей рабочей папке. По умолчанию False.

    Returns:
        list: Список словарей с данными о книгах.
    """

    # НАЧАЛО ВАШЕГО РЕШЕНИЯ
    books = []
    catalog_url = "https://books.toscrape.com/catalogue/page-1.html"

    while True:
        # получим текущую страницу каталога
        response = get_response(catalog_url)
        # снова начинаем разбирать html
        soup = BeautifulSoup(response.content, "html.parser")

        # все элементы в каталоге с тегом h3 имеют подэлемент с тегом a, где указана ссылка на книжку
        for heading in soup.find_all("h3"):
            link_tag = heading.find("a")
            # получаем полный путь книги
            book_url = urljoin(catalog_url, link_tag["href"])
            book_data = get_book_data(book_url)
            books.append(book_data)

        # сделаем логирование количества собранных книг на данной странице
        print(f"Собрано книг: {len(books)}")

        # ищем ссылку на следующую страницу.
        next_page = soup.find("li", class_="next")

        # если следующей страницы нет, завершаем цикл
        if next_page is None:
            break

        next_link = next_page.find("a")["href"]
        catalog_url = urljoin(catalog_url, next_link)

    # При необходимости сохраняем весь результат
    if is_save:
        with open("books_data.txt", "w", encoding="utf-8") as file:
            json.dump(books, file, ensure_ascii=False, indent=4)

    return books
    # КОНЕЦ ВАШЕГО РЕШЕНИЯ
