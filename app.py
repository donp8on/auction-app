import asyncio
import threading
import json
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

host_sid = None

# Auction state
auction_item = None
lowest_price = None
auction_type = None  # 1: First-price, 2: Second-price
auction_duration = 30
connected_users = {}
bids = []
auction_started = False
winner_announced = False
auction_initialized = False

@app.route('/')
def index():
    return render_template('auction.html', item=auction_item or '', min_price=lowest_price or '', auction_type=auction_type or '')

@socketio.on('join')
def handle_join(data):
    global host_sid
    username = data['username']
    sid = request.sid
    connected_users[sid] = username

    # First user becomes host
    if host_sid is None:
        host_sid = sid

    emit('user_list', list(connected_users.values()), broadcast=True)

    if auction_initialized:
        emit('auction_info', {
            'item': auction_item,
            'min_price': lowest_price,
            'type': auction_type,
            'duration': auction_duration
        })

@socketio.on('initialize_auction')
def initialize_auction(data):
    global auction_item, lowest_price, auction_type, auction_initialized
    if not auction_initialized:
        auction_item = data['item']
        lowest_price = data['min_price']
        auction_type = data['type']
        auction_initialized = True
        emit('auction_info', {
            'item': auction_item,
            'min_price': lowest_price,
            'type': auction_type,
            'duration': auction_duration
        }, broadcast=True)

@socketio.on('place_bid')
def handle_bid(data):
    global bids
    if auction_ended or request.sid == host_sid:
        return  # Host can't bid
    bid_amount = data['bid']
    username = connected_users[request.sid]
    bids.append({'user': username, 'bid': bid_amount})
    emit('new_bid', {'user': username, 'bid': bid_amount}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_users:
        del connected_users[request.sid]
        emit('user_list', list(connected_users.values()), broadcast=True)

def countdown_and_announce():
    global winner_announced
    socketio.sleep(auction_duration)
    if not bids:
        socketio.emit('winner', {'message': 'Auction ended. No bids placed.'})
        return
    sorted_bids = sorted(bids, key=lambda x: x['bid'], reverse=True)
    winner = sorted_bids[0]
    if auction_type == 1:
        amount = winner['bid']
    else:
        amount = sorted_bids[1]['bid'] if len(sorted_bids) > 1 else lowest_price
    message = f"{winner['user']} won the auction with a bid of ${amount}!"
    socketio.emit('winner', {'message': message})
    winner_announced = True

@socketio.on('start_auction')
def start_auction():
    global auction_started, bids, winner_announced, auction_ended
    if request.sid != host_sid:
        return  # Only host can start
    if not auction_started:
        auction_started = True
        bids = []
        winner_announced = False
        auction_ended = False
        socketio.emit('auction_started')
        thread = threading.Thread(target=countdown_and_announce)
        thread.start()


def announce_winner():
    global winner_announced, auction_ended
    if not bids:
        socketio.emit('winner', {'message': 'Auction ended. No bids were placed.'})
        winner_announced = True
        auction_ended = True
        return

    # Sort by bid amount descending
    sorted_bids = sorted(bids, key=lambda x: x['bid'], reverse=True)
    winner = sorted_bids[0]

    if auction_type == 1:
        amount = winner['bid']  # First-price auction
    else:
        amount = sorted_bids[1]['bid'] if len(sorted_bids) > 1 else lowest_price

    message = f"{winner['user']} won the auction with a bid of ${amount}!"
    socketio.emit('winner', {'message': message})  # 👈 Broadcast to all users

    print(message)  # Optional: log to server console
    winner_announced = True
    auction_ended = True



@socketio.on('end_auction')
def end_auction():
    global auction_ended
    if request.sid != host_sid:
        return  # Only host can end
    if not auction_ended:
        announce_winner()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)

