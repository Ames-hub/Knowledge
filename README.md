# Knowledge

*Your digital central files and *

---

## What is Knowledge?

Knowledge is a FastAPI-powered program that I use to manage my life and
generally make things more convenient. Such as by:

- Logging and managing **case files** with full session details
- Define, track, and **graph custom statistics** over time
- Save and organise **bulletins**
- Create and manage **battle plans** (to-do lists, but more.)
- A Built-in **blame list**, to remember who did what.

---

## Who is it For?
Knowledge is for those who need something you can write details of your life
on, but don’t want to lug around a 365-page planner and forget where you wrote
that one idea at 3am. Such a person is me, for example.

Honestly, this is a personal project built to make my life easier.
It might help you too, it might not.<br>
But hey, it’s free. Give it a go ^^

---

## Installation

1. Clone the repository into a directory.
2. Open a terminal/command prompt in said directory.<br>
[Here's how](https://www.youtube.com/watch?v=bgSSJQolR0E)
3. (Optional, Slightly technical.) You can create a virtual environment
    in the directory for a cleaner installation using
    ```
    python3.12 -m venv venv
   ```
4. Run these commands in the terminal/command prompt
    ```shell
    python3.12 -m pip install -r requirements.txt
    uvicorn knowledge:fastapp --reload --port 8080
    ```

It is recommended using a system like PufferPanel to auto-manage the instance.
Or, using the dockercompose (that I will make soon. Probably)