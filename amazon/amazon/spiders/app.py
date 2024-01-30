import scrapy
from urllib.parse import urlencode
from googlesearch import search
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from flask import Flask, request, jsonify

app = Flask(__name__)

global product_title
global product_description

def google_search(query):
    encoded_query = urlencode({"q": query})
    for j in search(encoded_query, num_results=10):
        if not isinstance(j, str):
            if "amazon" not in j.url and "flipkart" not in j.url:
                return j.url
        else:
            if "amazon" not in j and "flipkart" not in j:
                return j

    return None


class AmazonAndGoogleVerifierSpider(scrapy.Spider):
    name = "verifier"

    # start_urls = [
    #     "https://www.amazon.in/soundcore-Bluetooth-Headphones-Cancelling-Personalization/dp/B0C3HCD34R"
    # ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse_amazon)

    def parse_amazon(self, response):
        product_title = (
            response.css("span#productTitle::text").get().strip().split("|")[0]
        )
        details = response.css("div#feature-bullets span.a-list-item::text").getall()
        product_description = " ".join(detail.strip() for detail in details)

        data = {
            "Title": product_title,
            "Description": product_description,
        }

        url = google_search(product_title)
        if url is not None:
            request = scrapy.Request(url=url, callback=self.parse_other_site)
            request.meta["data"] = data
            yield request

    def parse_other_site(self, response):
        data = response.meta["data"]
        url = response.url

        everything = response.css("p::text").getall()
        descriptionToBeVerified = []
        for thing in everything:
            thing = thing.strip()
            if len(thing) > 20:
                descriptionToBeVerified.append(thing)

        everything1 = response.css("p::text").getall()
        for thing in everything1:
            thing = thing.strip()
            if len(thing) > 20:
                descriptionToBeVerified.append(thing)

        if len(descriptionToBeVerified) < 1:
            data.update(
                {
                    "descriptionToBeVerified": response.text,
                }
            )

        else:
            data.update(
                {
                    "descriptionToBeVerified": descriptionToBeVerified,
                }
            )

        yield data



def run_spider(start_urls):
    process = CrawlerProcess(get_project_settings())
    process.crawl(AmazonAndGoogleVerifierSpider, start_urls=start_urls)
    process.start()

@app.route('/', methods=['GET'])
def verify_product():
    try:
        start_urls = request.args.get('start_urls')

        if not start_urls:
            return jsonify({'error': 'start_urls is required'}), 400

        run_spider([start_urls])

        return jsonify({'message': 'Spider is running, check logs for results.'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)