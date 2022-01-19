from datetime import datetime
import os.path
import re
import bs4
import cloudscraper
from texter import texter

# Define the parameters for acceptable rentals.
domain = 'https://www.imovelweb.com.br'
min_price = 5_000
max_price = 8_000
min_bedrooms = 0
min_bathrooms = 0  # regular and en-suite combined
min_total_area = 500


def scrape_for_rentals(city):
    """Search ImovelWeb for all available listings with the given parameters."""
    previously_seen_listings = load_seen_listings(city)
    available_listings = search_available_listings(city, previously_seen_listings)
    add_seen_listings(city, available_listings)
    filtered_listings = filter_available_listings(available_listings)
    text_listings(city, filtered_listings)

    for listing in filtered_listings:
        print(listing)

    file_name_with_date = datetime.now().strftime("succeeded_on_%Y_%m_%d_%I_%M_%S_%p.txt")
    file = open(file_name_with_date, 'x')
    file.close()


def add_seen_listings(city, newly_available_listings):
    """Adds the newly found listings to the list of already seen listings."""
    with open(f"{city}.txt", 'a') as file:
        for listing in newly_available_listings:
            file.write(f"{listing['id']}\n")


def load_seen_listings(city):
    """Loads from file the listing IDs that have already been seen."""
    # If the file does not exist, create it and return an empty list.
    file_name = f"{city}.txt"
    if not os.path.exists(file_name):
        print(f"No file for {city}, creating...\n")
        file = open(file_name, 'x')
        file.close()
        return []

    # Load the information for the current city.
    print(f"File found for {city}, loading...\n")
    with open(file_name, 'r') as file:
        prev_ids = file.readlines()

    # Convert all the IDs to integers
    for index, prev_id in enumerate(prev_ids):
        prev_ids[index] = int(prev_id.strip())

    return prev_ids


def text_listings(city, listings):
    """Sends a text with the link to each of the listings given."""
    # Check if there are any new listings.
    if not listings:
        print(f"No new listings in {city}\n")
        return

    # Create the body of the message.
    msg_body = f"New listings in {city}:\n\n"
    count = 1
    for listing in listings:
        msg_body += f"{count}. {listing['url']} \n"
        count += 1

    print(f"{msg_body}\n")

    # Call the function for sending a text message.
    texter(msg_body)


def filter_available_listings(available_listings):
    """Removes items in the list of available listings based on the given parameters."""
    # Copy all the listings and remove from this new copy anything that does not meet the requirements.
    filtered_listings = available_listings[:]
    for listing in available_listings:
        # Check the total price.
        total_rent = listing['rent']
        if 'condo_fee' in listing:
            total_rent += listing['condo_fee']
        if 'iptu' in listing:
            total_rent += listing['iptu']
        if total_rent < min_price or total_rent > max_price:
            filtered_listings.remove(listing)
            continue

        # Check the number of rooms.
        if 'bedrooms' in listing:
            rooms = listing['bedrooms']
        elif 'en_suite_bathrooms' in listing:
            rooms = listing['en_suite_bathrooms']
        else:
            rooms = 0
        if rooms < min_bedrooms:
            filtered_listings.remove(listing)
            continue

        # Check the number of bathrooms.
        bathrooms = 0
        if 'bathrooms' in listing:
            bathrooms += listing['bathrooms']
        if 'en_suite_bathrooms' in listing:
            bathrooms += listing['en_suite_bathrooms']
        if bathrooms < min_bathrooms:
            filtered_listings.remove(listing)
            continue

        # Check the total area.
        total_area = 100_000  # this prevents listings without a total area given from being filtered out
        if 'total_area' in listing:
            total_area = listing['total_area']
        if total_area < min_total_area:
            filtered_listings.remove(listing)
            continue

    # Return the filtered list.
    return filtered_listings


def search_available_listings(city, previously_seen_listings):
    """Search the main page for all current listings and only filter out those that have been seen before."""
    # The final list of results that will be returned.
    new_available_listings = []

    # ImovelWeb uses Cloudflare to prevent bots; use cloudscraper.
    scraper = cloudscraper.create_scraper()

    # Continue iterating over pages until there is no next page button or the max is reached.
    page_id = 0
    max_num_pages = 1
    while True:
        # For each page in the results get the info for all the listings.
        page_id += 1
        url = f"{domain}/casas-aluguel-{city}-ordem-publicado-maior-pagina-{page_id}.html"
        r = scraper.get(url)
        print(f"Currently on page {page_id}")

        # Parse the HTML to get a list of each listing page to visit.
        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        page_results = soup.findAll("div", {"data-to-posting": True})
        for page_result in page_results:
            # Get the extension to the domain to know the full URL path.
            extension = page_result.attrs['data-to-posting']
            listing_url = f"{domain}{extension}"

            # Create a dictionary for the listing and append to the full set of data.
            listing_dict = scrape_listing_page(listing_url, previously_seen_listings)
            if listing_dict:
                new_available_listings.append(listing_dict)

        # Check if there is a next page.
        next_page = soup.findAll("a", {"aria-label": "Siguiente página"})
        if not next_page or page_id >= max_num_pages:
            break
    print("")

    # Return the list of dictionaries of all listings.
    return new_available_listings


def scrape_listing_page(url, previously_seen_listings):
    """Creates a dictionary with the rental information for the listing at the given url."""
    # Create the dictionary that will be returned; add the url and ID.
    listing_dict = {
        'url': url,
        'id': int(re.search("\d+.html", url).group()[:-5])
    }

    # If the ID has already been seen then return nothing and do not scrape the page.
    if listing_dict['id'] in previously_seen_listings:
        return None

    # ImovelWeb uses Cloudflare to prevent bots; use cloudscraper.
    scraper = cloudscraper.create_scraper()
    r = scraper.get(url)

    # Parse the HTML to populate the desired data into the dictionary.
    soup = bs4.BeautifulSoup(r.text, 'html.parser')

    # Get details related to the listing.
    listing_details = soup.findAll("li", {"class": "icon-feature"})
    for listing_detail in listing_details:
        # Find the HTML identifier
        html_key = str(listing_detail.contents[1])[10:-6]
        # Create a nicer name for the dictionary.
        if html_key == 'icon-stotal':
            dict_key = 'total_area'
        elif html_key == 'icon-scubierta':
            dict_key = 'usable_area'
        elif html_key == 'icon-bano':
            dict_key = 'bathrooms'
        elif html_key == 'icon-cochera':
            dict_key = 'parking_spaces'
        elif html_key == 'icon-dormitorio':
            dict_key = 'bedrooms'
        elif html_key == 'icon-toilete':
            dict_key = 'en_suite_bathrooms'
        else:
            continue

        # If the name is expected then look for an integer value.
        html_val = int(re.search("\d+", listing_detail.contents[2]).group())

        # Add entry in the dictionary.
        listing_dict[dict_key] = html_val

    # Locate information about price
    listing_price = soup.findAll("div", {"class": "block-price-container"})
    cur_element = listing_price[0].next_element
    while not re.search("Aluguel", cur_element.getText()):
        cur_element = cur_element.next_sibling

    rent = re.search("\d+", cur_element.getText().replace(".", "")).group()
    listing_dict['rent'] = int(rent)

    cur_element = cur_element.next_sibling
    while cur_element:
        cur_text = cur_element.getText().replace(".", "")
        if re.search("Condo", cur_text):
            formatted_val = re.search("\d+", cur_text)
            if formatted_val:
                formatted_val = formatted_val.group()
                listing_dict['condo_fee'] = int(formatted_val)
        elif re.search("IPTU", cur_text):
            formatted_val = re.search("\d+", cur_text)
            if formatted_val:
                formatted_val = formatted_val.group()
                listing_dict['iptu'] = int(formatted_val)

        cur_element = cur_element.next_sibling

    return listing_dict


if __name__ == '__main__':
    cities = [
        'indaiatuba-sp',
        'valinhos-sp',
        'vinhedo-sp',
    ]
    for city in cities:
        scrape_for_rentals(city)
