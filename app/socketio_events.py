from flask_socketio import emit, join_room
from flask_login import current_user
from . import socketio
from .models import Message, db
import os
import base64
import uuid
from flask import current_app

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
    image_data = data.get('image')

    image_url = None

    if image_data:
        header, encoded = image_data.split(',', 1)
        ext = header.split('/')[1].split(';')[0]
        filename = f"{uuid.uuid4()}.{ext}"
        folder_path = os.path.join(current_app.root_path, 'static', 'img', 'uploads')
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        image_url = f"/static/img/uploads/{filename}"

    group_id = data.get('group_id')
    receiver_id = data.get('receiver_id')

    if group_id:
        new_message = Message(
            sender_id=sender_id,
            group_id=group_id,
            content=message,
            image_url=image_url
        )
        db.session.add(new_message)
        db.session.commit()

        emit('receive_message', {
            'message': message,
            'sender_id': sender_id,
            'sender_username': current_user.username,
            'group_id': group_id,
            'image': image_url
        }, room=room)

    else:
        new_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=message,
            image_url=image_url
        )
        db.session.add(new_message)
        db.session.commit()

        emit('receive_message', {
            'message': message,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'image': image_url
        }, room=room)

        emit('desktop_notification', {
            'title': f"Nuevo mensaje de {current_user.username}",
            'body': message if message else "📷 Imagen enviada"
        }, room=f"user_{receiver_id}")

@socketio.on('typing')
def handle_typing(data):
    room = data['room']
    sender_id = data['sender_id']
    es_grupo = data.get('es_grupo', False)

    from .models import User
    user = db.session.get(User, sender_id)
    if not user:
        return

    emit('user_typing', {
        'username': user.username,
        'sender_id': sender_id
    }, room=room, include_self=False)

@socketio.on('marcar_leido')
def handle_marcar_leido(data):
    room = data.get('room')
    sender_id = data.get("sender_id")

    if room and sender_id:
        try:
            partes = room.split("-")
            if len(partes) == 2:
                user_id_1, user_id_2 = int(partes[0]), int(partes[1])
                receiver_id = user_id_2 if sender_id == user_id_1 else user_id_1

                mensajes = Message.query.filter_by(sender_id=receiver_id, receiver_id=sender_id, leido=False).all()
                for mensaje in mensajes:
                    mensaje.leido = True
                db.session.commit()

                emit('mensajes_leidos', {
                    'room': room,
                    'sender_id': sender_id
                }, room=room)

        except Exception as e:
            print(f"Error al marcar mensajes como leídos: {e}")
