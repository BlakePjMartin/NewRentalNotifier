from twilio.rest import Client


def texter(msg):
    """Sends the given message as a text."""

    # Account information to get client.
    account_sid = 'Enter account info here as a string'
    auth_token = 'Enter authentication token here as a string'
    twilio_client = Client(account_sid, auth_token)

    # Details to send the message.
    my_twilio_number = 'Enter the twilio number as a string and with the +, i.e. +18001234567'
    my_cell_phone = 'Enter phone number to receive the message as a string and with the +, i.e. +18001234567'
    twilio_client.messages.create(
        body=msg,
        from_=my_twilio_number,
        to=my_cell_phone
    )
