# Knowledge

A simple, personal command centre for your life. Write notes, plan your day, track money, and keep logs all in one place behind a login.

---

## Who is this for?

- You want one lightweight app to organise your life without juggling lots of tools.
- You prefer simple screens and clear actions over complex settings.
- You’re fine running a small local web app on your own computer, or are
willing to pay for or find a free hosted solution.

---

## What you can do

- Home Dashboard
  - See all modules at a glance and jump right in.

- Notes & Docs (Bulletins/Archives)
  - Write and format pages in a WYSIWYG editor.
  - Tag, search, update, delete, and export to PDF.

- People (Central Files)
  - Keep simple profiles for people: name, age, pronouns.
  - Add timestamped notes to each profile.

- Money (Ledger)
  - Create accounts and record income/expenses.
  - Plan recurring costs and see totals and charts.
  - Track debts and payments between people.

- Daily Plans (Battle Plans)
  - Make a daily to‑do list with quotas (how much you aim to get done).
  - View your last week’s productivity at a glance.
  - Import the incomplete parts of yesterday’s plan to today's

- Logs (Log Viewer)
  - Browse the app’s daily logs and search them if needed.
  Good for accountability when someone does something weird.

---

## Quick start

Prerequisites: Python 3.12

1) Get the code  
2) (Optional) Create and activate a virtual environment:
   - macOS/Linux:
     ```bash
     python3.12 -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python3.12 -m venv venv
     venv\Scripts\Activate.ps1
     ```
3) Install and run:
   ```bash
   python3.12 -m pip install -r requirements.txt
   uvicorn knowledge:fastapp --reload --port 8020
   ```
Then open http://localhost:8020/ in your browser and create an account.

Tip: You can also run:
```
bash
python knowledge.py
```
This uses port 8020 by default. To change it,
you'll need to modify knowledge.py.<br>
It'll be a variable at the top of the file called "WEB_PORT"

---

## Using the app

- First time: you’ll be asked to register. After that, log in with your credentials.
- Home: use the dashboard to open any module.

Suggested first steps:
1) Create a few notes in Archives (great for ideas, instructions, or journal entries).
2) Add a couple of people in Central Files if you keep contact notes.
3) Set up one or two accounts in Ledger and add a few transactions.
4) Open Battle Plans to create today’s to‑do list and set a quota.

---

## Backups and your data

- Your data is stored in a single file named data.sqlite (in the project folder).
- It's recommended you back it up regularly (copy it somewhere safe while the app is stopped).
- Logs are stored in the logs/ folder by date.

---

## Privacy and safety (important)

- This app is intended for personal use only with trusted friends.
- Do not expose it publicly on the internet without adding proper security.
- If you must use it over a network, ensure you understand the risks, use HTTPS, and protect access.
Ideally, you should run it exclusively over a service like Tailscale or Hamachi.
Some VPN that protects you from all outside access.

YOU ARE RESPONSIBLE FOR YOUR OWN DATA AND SECURITY.<br>
We have added methods which will help you protect your data,
but I do not claim them to be fully secure.

---

## Troubleshooting

- “Can’t install or run”
    - Confirm Python 3.12 is installed and selected.
    - If you use a virtual environment, make sure it’s activated.
- “Can’t open the site”
    - Check the terminal and log files for errors.
    - Make sure the server is running, and you’re visiting the correct port (default 8020).
- “I forgot my password”
    - There’s no built‑in reset. Upload data.sqlite to a website meant
    for reading .sqlite files and check the table "authbook" and
    look for your password. I recommend 
    https://inloop.github.io/sqlite-viewer/
    - If you can't do that, make a new account or ask for help.
---

## FAQ

- Can I use this with multiple people?
    - Yes, but only with people you trust.
- Does it work offline?
    - Yes, it runs locally in your browser while the server is running.
    But it won't work if you want to connect from another device.
- Can I use it on mobile?
    - Yes, it's less good, but it works and still looks good.

---

## License

This project is under the CC Zero v1.0 Universal Licence.