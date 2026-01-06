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
    - There’s no built‑in reset password. 
    - If you forgot your password, you'd better either remember it or make a new account, since passwords are Salted meaning you can't read it in the database without having the password.
---

## FAQ

- Can I use this with multiple people?
    - Yes, but only with people you trust.
- Does it work offline?
    - Yes, it runs locally in your browser while the server is running.
    But it won't work if you want to connect from another device while offline.
- Can I use it on mobile?
    - Yes, it's less good, but it works well and still looks good.

---

## License

This project is under the CC Zero v1.0 Universal Licence.