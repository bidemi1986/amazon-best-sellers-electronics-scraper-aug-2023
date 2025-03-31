import pprint
import json
from langchain_community.document_transformers import BeautifulSoupTransformer
from utils.util import webscape_ninja  # Updated utility file with optimizations


# Load URLs from a JSON file
scrape_urls = 'source_urls.json'
with open(scrape_urls, 'r') as f:
    urls = json.load(f)  # Assuming the JSON file contains a list of URLs

# Print loaded URLs
# print(f"Loaded URLs: {urls}")

class Document:
    """Represents a document with metadata and content."""
    def __init__(self, url, content):
        self.metadata = {"source": url}
        self.page_content = content


def scrape_with_webscrape_ninja(urls, schema=''):
    """
    Scrape multiple URLs, process HTML content with BeautifulSoupTransformer, 
    and extract relevant information.
    """
    # Step 1: Scrape HTML content using webscape_ninja
    html_dict = webscape_ninja(urls)  # Returns a dictionary with URL as key and HTML as value

    # Step 2: Transform HTML content into a list of Document objects
    docs = [Document(url, html) for url, html in html_dict.items()]

    # Step 3: Extract specific tags using BeautifulSoupTransformer
    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(docs, tags_to_extract=["span"])

    # Step 4: Display the extracted content
    print(f"\nExtracted Content with LLM:")
    pprint.pprint(docs_transformed)

    # Optional: Further processing of extracted content
    # splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    #     chunk_size=1000, chunk_overlap=0
    # )
    # splits = splitter.split_documents(docs_transformed)
    # extracted_content = extract(schema=schema, content=splits[0].page_content)
    # pprint.pprint(extracted_content)

    return docs_transformed


# Example URLs for scraping
# urls = [
#     "https://www.espn.com",
#     "https://lilianweng.github.io/posts/2023-06-23-agent/",
#     "https://www.walmart.com/shop/deals/all-home?athAsset=eyJhdGhjcGlkIjoiZThlNjgxZWItM2Y5Yy00ZjQwLThhNGItZmViODQ1ODM2MGI5In0=&athena=true"
# ]

# Execute the scraper
extracted_docs = scrape_with_webscrape_ninja(urls)

# Print metadata and content length for each scraped URL
for doc in extracted_docs:
    url = doc.metadata["source"]
    content_length = len(doc.page_content)
    print(f"\nScraped content for {url} (Length: {content_length} characters)")
