from flask_socketio import emit, join_room
from flask_login import current_user
from . import socketio
from .models import Message, db

@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    join_room(f"user_{current_user.id}")
    print(f"{current_user.username} joined room {room}")

@socketio.on('send_message')
def handle_send_message(data):
    message = data['message']
    room = data['room']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']

    new_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=message
    )
    db.session.add(new_message)
    db.session.commit()

    emit('receive_message', {
        'message': message,
        'sender_id': sender_id,
        'receiver_id': receiver_id
    }, room=room)

    emit('desktop_notification', {
        'title': f"Nuevo mensaje de {current_user.username}",
        'body': message
    }, room=f"user_{receiver_id}")
