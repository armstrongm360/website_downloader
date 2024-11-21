import os
import requests
from bs4 import BeautifulSoup
import wget
from urllib.parse import urljoin, urlparse, urlunparse

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_asset(asset_url, download_path):
    try:
        wget.download(asset_url, out=download_path)
        print(f"\nDownloaded: {asset_url}")
    except Exception as e:
        print(f"Failed to download {asset_url}: {e}")

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def is_same_domain(url, base_url):
    return urlparse(url).netloc == urlparse(base_url).netloc

def localize_link(link_url, base_url):
    parsed_link = urlparse(link_url)
    parsed_base = urlparse(base_url)
    if parsed_link.netloc == parsed_base.netloc:
        return urlunparse(parsed_link._replace(scheme='', netloc=''))
    return link_url

def download_page(url, base_url, base_path, visited, depth, max_depth):
    if url in visited or depth > max_depth:
        return
    visited.add(url)
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Skipping {url}")
        return
    except Exception as err:
        print(f"Other error occurred: {err} - Skipping {url}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Create a name for this page's file
    page_name = urlparse(url).path.replace('/', '_').strip('_') or 'index'
    if not page_name.endswith('.html'):
        page_name += '.html'
    page_file_path = os.path.join(base_path, page_name)
    
    # Save the HTML file
    with open(page_file_path, 'w', encoding='utf-8') as file:
        file.write(response.text)
    
    # Download assets and update links to point to local files
    for tag in soup.find_all(['img', 'link', 'script']):
        asset_url = None
        if tag.name == 'img':
            asset_url = tag.get('src')
        elif tag.name == 'link' and tag.get('rel') == ['stylesheet']:
            asset_url = tag.get('href')
        elif tag.name == 'script' and tag.get('src'):
            asset_url = tag.get('src')
        
        if asset_url:
            full_asset_url = urljoin(url, asset_url)
            if is_valid_url(full_asset_url):
                asset_name = os.path.basename(full_asset_url)
                download_path = os.path.join(base_path, asset_name)
                download_asset(full_asset_url, download_path)
                # Update the tag to point to the local file
                if tag.name == 'img':
                    tag['src'] = asset_name
                elif tag.name == 'link':
                    tag['href'] = asset_name
                elif tag.name == 'script':
                    tag['src'] = asset_name

    # Update page links
    for link in soup.find_all('a', href=True):
        link_url = urljoin(url, link['href'])
        if is_valid_url(link_url) and is_same_domain(link_url, base_url):
            localized_link = localize_link(link_url, base_url)
            link_page_name = urlparse(link_url).path.replace('/', '_').strip('_') or 'index'
            if not link_page_name.endswith('.html'):
                link_page_name += '.html'
            link['href'] = link_page_name
            # Recursively download linked pages
            download_page(link_url, base_url, base_path, visited, depth + 1, max_depth)
    
    # Save the modified HTML with updated asset links
    with open(page_file_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))

def signal_handler(sig, frame):
    print('\nProgram terminated by user')
    sys.exit(0)

if __name__ == '__main__':
    import signal
    import sys

    signal.signal(signal.SIGINT, signal_handler)

    website_url = input("Enter the website URL: ")
    download_directory = input("Enter the directory to save the website: ")
    max_depth = 3  # Set a reasonable depth limit
    
    create_directory(download_directory)
    visited_urls = set()
    download_page(website_url, website_url, download_directory, visited_urls, 0, max_depth)
    
    print("\nWebsite download completed.")
