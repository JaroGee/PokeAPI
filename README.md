**PokeAPI Python Project**

**Overview**
This project is a small Python script that connects to the PokéAPI — a free, open RESTful Pokémon API — and lets you fetch and display data about your favourite Pokémon.
Think of it as your personal Pokédex, minus the Professor Oak lectures.

**Features**
Fetch Pokémon info (name, ID, type, abilities, stats, etc.)
Command-line interface (because GUI is for gym trainers, not coders)
JSON-parsed results displayed in a readable format
Easy to extend — build your own battle sim, web app, or terminal Pokédex

**Requirements**
Python 3.8+
requests library
Install it with:
pip install requests

**Usage**
Clone this repository:
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
Run the script:
python pokeapi.py
When prompted, type the name of a Pokémon:
> pikachu
Get results like:
⚡ Name: Pikachu
🧬 ID: 25
🥊 Type: electric
💪 Base HP: 35
🧪 Example Output
$ python pokeapi.py
Enter a Pokémon name: bulbasaur

🌿 Name: Bulbasaur
🧬 ID: 1
🥊 Type: grass / poison
💪 Base HP: 45
🧩 Project Structure
pokeapi/
│
├── pokeapi.py      # Main script that calls the API
├── README.md       # You’re reading it right now
└── requirements.txt (optional)

**Why**
Because Pokémon + Python = happiness.
Also, APIs are the perfect way to pretend you're coding when you're really just browsing the internet for Charmander stats.

**Author**
**Jaro Gee**
