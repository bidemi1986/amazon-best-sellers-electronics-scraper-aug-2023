from langchain_community.document_loaders.sitemap import SitemapLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
import pprint

# Initialize the SitemapLoader
sitemap_loader = SitemapLoader(web_path="https://aubonclimat.com/sitemap_index.xml")

# Load all URLs from the sitemap
print("Fetching URLs from the sitemap...")
all_docs = sitemap_loader.load()

# Display the URLs fetched from the sitemap
print("\nFetched URLs:")
urls = [doc.metadata["source"] for doc in all_docs]
pprint.pprint(urls)

# Optionally, process each URL using BeautifulSoupTransformer
print("\nProcessing fetched pages for content extraction...")
bs_transformer = BeautifulSoupTransformer()
transformed_docs = bs_transformer.transform_documents(all_docs, tags_to_extract=["title", "h1", "p"])

# Display transformed content
print("\nExtracted Content from Sitemap:")
for doc in transformed_docs:
    print(f"Source: {doc.metadata['source']}")
    print(f"Content: {doc.page_content[:200]}...")  # Print the first 200 characters
    print("-" * 80)

# Save the URLs or extracted content to a file if needed
with open("extracted_urls.txt", "w") as f:
    for url in urls:
        f.write(url + "\n")
print("\nURLs saved to 'extracted_urls.txt'")
