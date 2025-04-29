# Trojan Auctions - Real-Time Auction System

Welcome to **Trojan Auctions**, a Flask-SocketIO powered real-time auction platform. This system supports a host and multiple bidders, live updates via WebSockets, and winner determination using multiprocessing. 
It's perfect for class demos, real-time bidding games, or distributed systems education.

---
## Features
- Real-time bid updates using **WebSockets**
- Host + multiple bidder roles
- Countdown timer with animated display
- Winner announcement via **multiprocessing**
- Multithreading processes
- Confetti and visual feedback for winner
- Item image support
- Lobby music

---
## Architecture Overview
The system consists of:
- A central Flask server handling auctions and bid logic
- Multiple browser-based clients (host + bidders)

---
## How to Use the Auction
*** Run: python app.py ***
1. First user joins — becomes the **Host**
2. Host initializes the auction (item, price, type)
3. Other users join — become **Bidders**
4. Host starts auction
5. Everyone bids in real time
6. Winner is announced with confetti

---
## Multi-Machine Instructions
- Use host’s IP instead of localhost in `socketio.run(...)`
- Make sure ports 5000 and 6379 are open
- Make sure all clients are connected to the same network
