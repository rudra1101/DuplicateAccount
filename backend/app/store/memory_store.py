from datetime import datetime

# Uploaded accounts
accounts = []

# AI detection results
duplicate_groups = {}

duplicate_details = {}

# Scan information
last_scan = None


def save_scan(uploaded_accounts, groups, details):
    global accounts
    global duplicate_groups
    global duplicate_details
    global last_scan

    accounts = uploaded_accounts
    duplicate_groups = groups
    duplicate_details = details
    last_scan = datetime.now()


def clear():
    global accounts
    global duplicate_groups
    global duplicate_details
    global last_scan

    accounts = []
    duplicate_groups = {}
    duplicate_details = {}
    last_scan = None