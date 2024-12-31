import streamlit as st
import pywhatkit as kit
import re
from datetime import datetime
import time

def validate_indian_number(number):
    pattern = r'^(\+91|91)?[6-9]\d{9}$'
    return bool(re.match(pattern, number))

def send_wishes(phone_number, message):
    try:
        if not validate_indian_number(phone_number):
            st.error(f"Invalid Indian phone number: {phone_number}")
            return False

        if not phone_number.startswith("+91"):
            phone_number = "+91" + phone_number.lstrip("91")

        kit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=15,
            tab_close=True,
            close_time=3
        )
        time.sleep(2)
        return True
    except Exception as e:
        st.error(f"Failed to send message to {phone_number}. Error: {str(e)}")
        return False

def main():
    st.title("New Year Wishes Sender")

    phone_numbers = st.text_area("Enter Indian phone numbers (one per line):", height=150)
    message = st.text_area("Enter your New Year message:", "Happy New Year 2025!")

    progress = st.empty()

    if st.button("Send Wishes"):
        if not all([phone_numbers.strip(), message.strip()]):
            st.error("All fields are required.")
            return

        numbers = [num.strip() for num in phone_numbers.strip().splitlines() if num.strip()]
        total = len(numbers)

        for idx, number in enumerate(numbers, 1):
            progress.text(f"Processing {idx}/{total}: {number}")
            success = send_wishes(number, message)
            if success:
                st.success(f"✓ Sent to {number}")
            time.sleep(2)

if __name__ == "__main__":
    main()