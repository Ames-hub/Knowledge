<div align="center">

# Knowledge  
*Keep it simple*  

A simple, personal command centre for your life. Write notes, plan your day, track money, and keep logs all in one place behind a login.

</div>

---

## Who is this for?

- You want one lightweight app to organise your life without juggling lots of tools.
- You prefer simple screens and clear actions over complex settings.
- You’re fine running a small local web app on your own computer, or are
willing to pay for or find a free hosted solution.

---

## What you can do

To show you how built-out each system is, we'll show you a number from 1 to 5!<br>
1 Being barely developed, 5 being highly developed.
1 Also being not too great, and 5 being very good!

- Home Dashboard (4/5)
  - See all modules at a glance and jump right in.

- Central Files (4/5)
  - A Workable CRM
  - Keep track of people's names, their faces, age, D.o.b, and more!
  - See what debts are connected to them
  - See all the invoices you've made for this person!
  - If you are a Dianetics Auditor, keep track of their case!
  - Track all agreements with this person

- Notes & Docs Textbook (5/5)
  - Write and format pages in a nice editor.
  - Tag, search, update, delete, and export to PDF.

- Log Viewer (5/5)
  - Browse the app’s daily logs and search them if needed.
  Good for accountability when someone does something weird.

- Ledger (5/5)
  - Create accounts and record income/expenses.
  - Plan recurring costs and see totals and charts. (Also called a "Financial Plan No. 1")
  - Track debts and payments between people.
  - Create custom, modular invoices!

- Daily Plans (Battle Plans) (5/5)
  - Make a daily to‑do list with quotas (how much you aim to get done).
  - View your last week’s productivity at a glance.
  - Import the incomplete parts of yesterday’s plan to today's
  - Auto-Calculate how much you need each day to reach a weekly target
  - Set which day is the day your week starts on!
  - Export it to a nice looking PDF!

- FTP Server (2/5)
  - Upload files and folders
  - Browse directories
  - View or Edit text files without downloading them first



---

## Quick start

Prerequisites: Python 3.13

1) Get the code  
2) (Optional) Create and activate a virtual environment:
   - macOS/Linux:
     ```bash
     python3.13 -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python3.13 -m venv venv
     venv\Scripts\Activate.ps1
     ```
3) Install and run:
   ```bash
   python3.13 -m pip install -r requirements.txt
   uvicorn knowledge:fastapp --reload --port 8020
   ```
Then open http://localhost:8020/ in your browser and create an account.

Tip: You can also run:
```
bash
python knowledge.py
```
This uses port 8020 by default. You can change this in settings.json or on the web app.

---

## Using the app

- First time: you’ll be asked to register. After that, log in with your credentials. The first account created is assigned as "Administrator"
- Home: use the dashboard to open any module.

Suggested first steps:
1) Add a couple of people in Central Files if you keep contact notes.
2) Set up one or two accounts in Ledger and add a few transactions.
3) Open Battle Plans to create today’s to‑do list and set a quota.

---

## Backups and your data

- Your data is stored in a single file named data.sqlite (in the project folder).
- It's recommended you back it up regularly (copy it somewhere safe while the app is stopped). We will not do this for you.
- Logs are stored in the logs/ folder by date.

---

## Privacy and safety (important)

- This app is intended for use with a team of more-or-less trusted people.
- Do not expose it publicly on the internet without ensuring proper security.
- If you must use it over a network, ensure you understand the risks, use HTTPS, and protect access.
Ideally, you should run it exclusively over a service like Tailscale or Hamachi.
Some VPN that protects you from all outside access. Otherwise though, you should be fine.

While we have added methods which will help you protect your data,
We do not claim them to be fully reliable as no pen-testing has been done.

---

## Troubleshooting

- “Can’t install or run”
    - Confirm Python 3.13 is installed and selected.
    - If you use a virtual environment, make sure it’s activated.
- “Can’t open the site”
    - Check the terminal and log files for errors.
    - Make sure the server is running, and you’re visiting the correct port (default 8020). You can visit a specific port by entering in "http(s)://localhost:(port)" on your browser
- “I forgot my password”
    - There’s no built‑in reset password. 
    - If you forgot your password, you'd better either remember it or make a new account, since passwords are encrypted in a way that Nobody can read them, even if they have access to the database.
    - If it is utterly critical, you can delete the row in the database that stores the locked-out account, and register a new account under the same username. This will retain 95% of data for the account. 
---

## Questions and Answers

- Can I use this with multiple people?
    - Yes, but it should be with a known, trusted team. Not just anyone.
- Does it work offline?
    - Yes and no, it runs locally in your browser while the server is running.
    But it won't work if you want to connect from another device while offline.
- Can I use it on mobile?
    - Yes. Just gotta go to the same browser link

---

## License

This project is under the CC Zero v1.0 Universal Licence.
