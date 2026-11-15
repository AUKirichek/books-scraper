import json
from types import SimpleNamespace
import pytest

# наш парсер
import scraper

DESCRIPTION_HTML = """<div id="product_description">
    <h2>Product Description</h2>
</div>
<p>A sample book description.</p>"""

BOOK_HTML = f"""<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body>
    <h1>A Light in the Attic</h1>
    <p class="price_color">£51.77</p>
    <p class="star-rating Three"><i class="icon-star"></i></p>
    <p class="instock availability">In stock (22 available)</p>
    {DESCRIPTION_HTML}
    <table class="table table-striped">
        <tr><th>UPC</th><td>a897fe39b1053632</td></tr>
        <tr><th>Product Type</th><td>Books</td></tr>
        <tr><th>Price (excl. tax)</th><td>£51.77</td></tr>
        <tr><th>Price (incl. tax)</th><td>£51.77</td></tr>
        <tr><th>Tax</th><td>£0.00</td></tr>
        <tr><th>Availability</th><td>In stock (22 available)</td></tr>
        <tr><th>Number of reviews</th><td>0</td></tr>
    </table>
</body>
</html>"""


def test_get_book_data(monkeypatch):
    """Проверяем все поля книги на заранее подготовленном HTML."""
    # вместо запроса к сайту возвращаем наш HTML в виде байтов
    def fake_get_response(url):
        # вернем объект с атрибутом content - последовательность байтов
        return SimpleNamespace(content=BOOK_HTML.encode("utf-8"))

    # заменим получение ответа от сайта тестовым ответом на время выполнения теста
    monkeypatch.setattr(scraper, "get_response", fake_get_response)

    result = scraper.get_book_data("test_url")

    # assert проверяет, совпал ли результат с ожидаемым словарём
    assert result == {
        "title": "A Light in the Attic",
        "price": "£51.77",
        "rating": "Three",
        "stock": "22",
        "availability": "In stock (22 available)",
        "description": "A sample book description.",
        "product_info": {
            "UPC": "a897fe39b1053632",
            "Product Type": "Books",
            "Price (excl. tax)": "£51.77",
            "Price (incl. tax)": "£51.77",
            "Tax": "£0.00",
            "Availability": "In stock (22 available)",
            "Number of reviews": "0",
        },
    }


def test_get_book_data_without_description(monkeypatch):
    """Без заголовка описания возвращается пустая строка."""
    # заменим заголовок пустотой
    book_html = BOOK_HTML.replace(DESCRIPTION_HTML, "")

    def fake_get_response(url):
        # объект с атрибутом content
        return SimpleNamespace(content=book_html.encode("utf-8"))

    monkeypatch.setattr(scraper, "get_response", fake_get_response)

    result = scraper.get_book_data("test_url")

    assert result["description"] == ""


@pytest.mark.parametrize("is_save", [False, True])
def test_scrape_books(monkeypatch, tmp_path, is_save):
    """Проверяем две страницы каталога и оба значения флага сохранения."""
    first_catalog_url = "https://books.toscrape.com/catalogue/page-1.html"
    second_catalog_url = "https://books.toscrape.com/catalogue/page-2.html"
    first_book_url = "https://books.toscrape.com/catalogue/first-book/index.html"
    second_book_url = "https://books.toscrape.com/catalogue/second-book/index.html"

    # на первой странице есть ссылка next, на второй её уже нет
    catalog_pages = {
        first_catalog_url: """<html>
            <head><meta charset="utf-8"></head>
            <body>
                <article class="product_pod">
                    <h3><a href="first-book/index.html">Первая книга</a></h3>
                </article>
                <ul class="pager">
                    <li class="next"><a href="page-2.html">next</a></li>
                </ul>
            </body>
        </html>""",
        second_catalog_url: """<html>
            <head><meta charset="utf-8"></head>
            <body>
                <article class="product_pod">
                    <h3><a href="second-book/index.html">Вторая книга</a></h3>
                </article>
            </body>
        </html>""",
    }
    book_results = {
        first_book_url: {"title": "Первая книга", "price": "£10.00"},
        second_book_url: {"title": "Вторая книга", "price": "£20.00"},
    }
    catalog_requests = []
    book_requests = []

    def fake_get_response(url):
        catalog_requests.append(url)
        # объект с атрибутом content
        return SimpleNamespace(content=catalog_pages[url].encode("utf-8"))

    # тестовая замена для получения данных из книги
    def fake_get_book_data(url):
        book_requests.append(url)
        return book_results[url]

    monkeypatch.setattr(scraper, "get_response", fake_get_response)
    monkeypatch.setattr(scraper, "get_book_data", fake_get_book_data)
    # времменно изменим папку для хранения тестового результата
    monkeypatch.chdir(tmp_path)

    result = scraper.scrape_books(is_save)

    # доп проверки на правильность составления адресов 
    assert catalog_requests == [first_catalog_url, second_catalog_url]
    assert book_requests == [first_book_url, second_book_url]

    # сформируем полный путь до файла с данными
    output_file = tmp_path / "books_data.txt"
    if is_save:
        # проверим, что файл был создан
        assert output_file.is_file()
        # проверка данных
        saved_result = json.loads(output_file.read_text(encoding="utf-8"))
        assert saved_result == result
    else:
        # проверим, что файл не был создан
        assert not output_file.exists()
