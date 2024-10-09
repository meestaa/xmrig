import requests
import time

webhook_url = "https://discord.com/api/webhooks/1287114697308639277/cC_6pulNpE30vrTug6esx1_HM3plZ8EKvZt_n2QWWJNc0xEAZIJwYIZE0sAIV9EZnJQ5"

message = {
    "content": "Hello, this is a message from my Python script!"
}

while True:
    try:
        response = requests.post(webhook_url, json=message)

        if response.status_code == 204:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

    time.sleep(3)
