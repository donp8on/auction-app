import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Auction state
auction_item = None
lowest_price = None
auction_type = None
auction_duration = 30
bids = []
connected_users = {}
auction_initialized = False
auction_started = False
auction_ended = False
winner_announced = False
host_sid = None
auction_image = None

@app.route('/')
def index():
    return render_template('auction.html')


@socketio.on('join')
def handle_join(data):
    global host_sid
    username = data['username']
    sid = request.sid
    connected_users[sid] = username

    if host_sid is None:
        host_sid = sid
        print(f"[HOST CONNECTED] {username}")

    emit('you_are_host', {'isHost': sid == host_sid}, to=sid)
    emit('user_list', {
        'users': connected_users,
        'host_sid': host_sid
    }, broadcast=True)

    if auction_initialized:
        emit('auction_info', {
            'item': auction_item,
            'min_price': lowest_price,
            'type': auction_type,
            'duration': auction_duration,
            'image': auction_image
        }, to=sid)


@socketio.on('initialize_auction')
def initialize_auction(data):
    global auction_item, lowest_price, auction_type, auction_initialized, auction_image
    if request.sid != host_sid:
        return
    auction_item = data['item']
    lowest_price = data['min_price']
    auction_type = data['type']
    auction_image = data.get('image')

    auction_initialized = True
    socketio.emit('auction_info', {
        'item': auction_item,
        'min_price': lowest_price,
        'type': auction_type,
        'duration': auction_duration,
        'image': auction_image
    })


@socketio.on('start_auction')
def start_auction():
    global auction_started, bids, winner_announced, auction_ended
    if request.sid != host_sid:
        return
    auction_started = True
    auction_ended = False
    winner_announced = False
    bids = []
    socketio.emit('auction_started')
    thread = threading.Thread(target=countdown_and_announce)
    thread.start()


@socketio.on('place_bid')
def handle_bid(data):
    sid = request.sid
    if auction_ended or sid == host_sid:
        return
    bid_amount = float(data['bid'])
    username = connected_users.get(sid, f"User-{sid[:5]}")
    bids.append({'user': username, 'bid': bid_amount})
    socketio.emit('new_bid', {'user': username, 'bid': bid_amount})


@socketio.on('end_auction')
def end_auction():
    if request.sid == host_sid and not auction_ended:
        announce_winner()


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_users:
        del connected_users[sid]
        socketio.emit('user_list', {
            'users': connected_users,
            'host_sid': host_sid
        }, broadcast=True)


def announce_winner():
    global winner_announced, auction_ended
    if not bids:
        socketio.emit('winner', {'message': 'Auction ended. No bids were placed.'})
        auction_ended = True
        winner_announced = True
        return

    sorted_bids = sorted(bids, key=lambda x: x['bid'], reverse=True)
    winner = sorted_bids[0]
    amount = winner['bid'] if auction_type == 1 else (
        sorted_bids[1]['bid'] if len(sorted_bids) > 1 else lowest_price
    )

    message = f"{winner['user']} won the auction with a bid of ${amount}!"
    socketio.emit('winner', {'message': message})
    auction_ended = True
    winner_announced = True


def countdown_and_announce():
    socketio.sleep(auction_duration)
    if not auction_ended:
        announce_winner()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
