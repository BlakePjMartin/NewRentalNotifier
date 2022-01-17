# New Rental Notifier
Searches ImovelWeb (website for rentals in Brazil and other South American countries) for new rentals satisfying the given requirements for size, price, etc. If a new rental is found then a message is sent either via text or email to notify.

## Motivation
We were looking to move to a new location and didn't want to miss out on new listings. That being said we also didn't want to be refershing the results page multiple times a day. By automating the search and notification process with Python this task was then scheduled to run every 15 minutes to ensure we would be immediately notified when a new property was online.

## Inspiration
The inspiration for this project came from the Web Scraping chapter in the *Automate the Boring Stuff with Python* book by Al Sweigart.

## Overview of Steps

1. Load listing IDs that were previously seen.
1. Pull the HTML data from the website (ImovelWeb) for a specified city.
1. For each listing on the search page get all the details of the rental if the listing ID is new and not part of the list of IDs previously loaded.
1. Add all the new IDs to the list of previously seen listings.
1. Filter the new listings to see if any of them fit the desired criteria for price, number of bedrooms, etc.
1. If there are any listings that are new and satisfy all the requirements then send a text message to notify.


## Packages Used

* `cloudscraper` for bypassing Clourflare used on the website
* `bs4` for parsing and searching the HTML
* `twilio` for sending text messages

## Note on `texter.py`
The source code will not run as-is. My personal authentication credentials for Twilio have been removed from the `texter.py` file. Free trial accounts can be created on Twilio.

## Future Plans

* Have the code search more than one city at a time
* Improve logging information - currently an empty file is created each time the code is successfully executed
* Include the ability to send emails in addition or instead of text messages