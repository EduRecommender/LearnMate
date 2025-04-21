import os
import arxiv
import requests
from urllib.parse import quote

def download_europepmc_articles(query, n=50, output_folder="europepmc_downloads"):
    """
    Search Europe PMC for articles matching the query and download available Open Access PDFs.
    Args:
        query (str): Search query.
        n (int): Number of articles to try to download.
        output_folder (str): Directory to save downloaded PDFs.
    """
    os.makedirs(output_folder, exist_ok=True)
    print(f"Searching Europe PMC for '{query}' and downloading up to {n} Open Access PDFs...")

    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": quote(query),
        "format": "json",
        "resultType": "lite",
        "pageSize": n
    }

    print(f"Searching Europe PMC for '{query}'...")
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    data = response.json()

    # Print out the raw response to see what's returned
    print("Search Results:")
    print(data)

    count = 0
    for i, result in enumerate(data.get("resultList", {}).get("result", [])):
        title = result.get("title", "untitled").replace('/', '_').replace('\\', '_')[:50]
        pmcid = result.get("pmcid")
        if not pmcid:
            continue

        # Construct full-text PDF URL
        pdf_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextPDF"

        try:
            pdf_response = requests.get(pdf_url)
            if pdf_response.status_code == 200 and pdf_response.headers["Content-Type"] == "application/pdf":
                pdf_path = os.path.join(output_folder, f"{i+1:03d}_{title}.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_response.content)
                print(f"Downloaded: {title}")
                count += 1
            else:
                print(f"No PDF found for: {title}")
        except Exception as e:
            print(f"Error downloading {title}: {e}")

        if count >= n:
            break

    print(f"Download complete. {count} files saved to '{output_folder}'.")

def download_arxiv_articles(query, n=50, output_folder="arxiv_downloads"):
    """
    Search ArXiv for articles matching the query and download the first n as PDFs.
    Args:
        query (str): Search query for ArXiv.
        n (int): Number of articles to download.
        output_folder (str): Directory to save downloaded PDFs.
    """

    os.makedirs(output_folder, exist_ok=True)

    search = arxiv.Search(
        query=query,
        max_results=n,
        sort_by=arxiv.SortCriterion.Relevance
    )

    print(f"Searching for '{query}' and downloading up to {n} articles...")

    for i, result in enumerate(search.results()):
        title = result.title.replace('/', '_').replace('\\', '_')
        pdf_path = os.path.join(output_folder, f"{i+1:03d}_{title[:50]}.pdf")
        print(f"Downloading: {result.title}")
        try:
            result.download_pdf(filename=pdf_path)
        except Exception as e:
            print(f"Failed to download {result.title}: {e}")

    print(f"Download complete. Files saved to '{output_folder}'.")

if __name__ == "__main__":

    output_folder = "downloads"

    # Download articles related to studying techniques
    download_europepmc_articles(query="study techniques", n=5, output_folder="arxiv_papers")
    download_arxiv_articles(query="study techniques", n=5, output_folder="arxiv_papers")
