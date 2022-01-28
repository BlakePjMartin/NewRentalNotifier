from datetime import datetime
import os.path
import re
import bs4
import cloudscraper
from texter import texter


class NewRentalNotifier:
    """Takes in a city to search and sends a notification if there is a new listing available."""

    def __init__(self, city):
        """Set the class parameters and start the searching process."""
        # Search requirements for a new listing.
        self.min_price = 5_000  # this is the minimum price for the rent alone
        self.max_price = 8_000  # this is the maximum price for the combination of rent/condo/IPTU
        self.min_bedrooms = 0
        self.min_bathrooms = 0  # regular and en-suite combined
        self.min_total_area = 500

        # Set the city and domain for the searching.
        self.city = city
        self.domain = 'https://www.imovelweb.com.br'

        # Set the log info to the name of the city.
        self.log = f"Searching listings for {self.city}...\n"

        # Variables used during the searching process.
        self.previously_seen_listings = None
        self.available_listings = None
        self.filtered_listings = None

        # Call the function to perform the search.
        self.scrape_for_rentals()

    def scrape_for_rentals(self):
        """Search ImovelWeb for all available listings with the given parameters."""
        self.load_seen_listings()
        self.search_available_listings()
        self.add_seen_listings()
        self.filter_available_listings()
        self.text_listings()

    def load_seen_listings(self):
        """Loads from file the listing IDs that have already been seen."""
        # If the file does not exist, create it and return an empty list.
        file_name = f"{self.city}.txt"
        if not os.path.exists(file_name):
            self.log += f"Creating ID file for {self.city}\n"
            file = open(file_name, 'x')
            file.close()
            self.previously_seen_listings = []

        # Load the information for the current city.
        self.log += f"Loading ID file for {self.city}\n"
        with open(file_name, 'r') as file:
            prev_ids = file.readlines()

        # Convert all the IDs to integers
        for index, prev_id in enumerate(prev_ids):
            prev_ids[index] = int(prev_id.strip())

        self.previously_seen_listings = prev_ids

    def search_available_listings(self):
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
            url = f"{self.domain}/casas-aluguel-{self.city}-ordem-publicado-maior-pagina-{page_id}.html"
            r = scraper.get(url)
            self.log += f"Currently on page {page_id}\n"

            # Parse the HTML to get a list of each listing page to visit.
            soup = bs4.BeautifulSoup(r.text, 'html.parser')
            page_results = soup.findAll("div", {"data-to-posting": True})
            for page_result in page_results:
                # Get the extension to the domain to know the full URL path.
                extension = page_result.attrs['data-to-posting']
                listing_url = f"{self.domain}{extension}"

                # Create a dictionary for the listing and append to the full set of data.
                try:
                    listing_dict = self.scrape_listing_page(listing_url)
                except:
                    listing_dict = None
                    self.log += f"ERROR WHILE TRYING TO SCRAPE: {listing_url}\n"

                if listing_dict:
                    new_available_listings.append(listing_dict)

            # Check if there is a next page.
            next_page = soup.findAll("a", {"aria-label": "Siguiente página"})
            if not next_page or page_id >= max_num_pages:
                break

        # Return the list of dictionaries of all listings.
        self.available_listings = new_available_listings

    def scrape_listing_page(self, url):
        """Creates a dictionary with the rental information for the listing at the given url."""
        # Create the dictionary that will be returned; add the url and ID.
        listing_dict = {
            'url': url,
            'id': int(re.search("\d+.html", url).group()[:-5])
        }

        # If the ID has already been seen then return nothing and do not scrape the page.
        if listing_dict['id'] in self.previously_seen_listings:
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

        for element in cur_element:
            cur_text = str(element).replace(".", "")
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

        return listing_dict

    def add_seen_listings(self):
        """Adds the newly found listings to the list of already seen listings."""
        # Add the number of listings found to the log file.
        self.log += f"Number of new listings found: {len(self.available_listings)}\n"

        # Write the listing IDs to file.
        with open(f"{self.city}.txt", 'a') as file:
            for listing in self.available_listings:
                file.write(f"{listing['id']}\n")

    def filter_available_listings(self):
        """Removes items in the list of available listings based on the given parameters."""
        # Copy all the listings and remove from this new copy anything that does not meet the requirements.
        self.filtered_listings = self.available_listings[:]
        for listing in self.available_listings:
            # Check the base rent price.
            total_rent = listing['rent']
            if total_rent < self.min_price:
                self.filtered_listings.remove(listing)
                continue

            # Check the total rent price (rent + condo + IPTU)
            if 'condo_fee' in listing:
                total_rent += listing['condo_fee']
            if 'iptu' in listing:
                total_rent += listing['iptu']
            if total_rent > self.max_price:
                self.filtered_listings.remove(listing)
                continue

            # Check the number of rooms.
            if 'bedrooms' in listing:
                rooms = listing['bedrooms']
            elif 'en_suite_bathrooms' in listing:
                rooms = listing['en_suite_bathrooms']
            else:
                rooms = 0
            if rooms < self.min_bedrooms:
                self.filtered_listings.remove(listing)
                continue

            # Check the number of bathrooms.
            bathrooms = 0
            if 'bathrooms' in listing:
                bathrooms += listing['bathrooms']
            if 'en_suite_bathrooms' in listing:
                bathrooms += listing['en_suite_bathrooms']
            if bathrooms < self.min_bathrooms:
                self.filtered_listings.remove(listing)
                continue

            # Check the total area.
            total_area = 100_000  # this prevents listings without a total area given from being filtered out
            if 'total_area' in listing:
                total_area = listing['total_area']
            if total_area < self.min_total_area:
                self.filtered_listings.remove(listing)
                continue

        # Add information to the log text.
        self.log += f"Number of new listings after filtering: {len(self.filtered_listings)}\n"
        for listing in self.filtered_listings:
            self.log += f"{listing['url']}\n"

    def text_listings(self):
        """Sends a text with the link to each of the listings given."""
        # Check if there are any new listings.
        if not self.filtered_listings:
            self.log += f"From text_listings: No new listings in {self.city}\n"
            return

        # Create the body of the message.
        msg_body = f"New listings in {self.city}:\n\n"
        count = 1
        for listing in self.filtered_listings:
            msg_body += f"{count}. {listing['url']} \n"
            count += 1

        print(f"From text_listings: Texting the message below\n{msg_body}\n")

        # Call the function for sending a text message.
        texter(msg_body)


def write_to_log(msg):
    """Writes a message to the log file."""
    # If the file does not exist, create it and return an empty list.
    file_name = f"log.txt"
    if not os.path.exists(file_name):
        file = open(file_name, 'x')
        file.close()

    # Write the message to the log file.
    # Prepend the new string to the top of the file.
    with open(file_name, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(msg.rstrip('\r\n') + '\n\n\n' + content)


if __name__ == '__main__':
    # List of cities that we want to search.
    cities = [
        'indaiatuba-sp',
        'valinhos-sp',
        'vinhedo-sp',
    ]

    # Create a string that will be written to the log file.
    log_str = datetime.now().strftime(
        "##############################################################################################################"
        "\nResults from %d-%m-%Y at %I:%M:%S %p:\n\n"
    )

    for city in cities:
        notifier = NewRentalNotifier(city)
        log_str += f"{notifier.log}\n"
    log_str += "\n\n"

    # Add the details to the log file.
    write_to_log(log_str)
