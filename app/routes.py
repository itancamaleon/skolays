from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from .models import Message
from .models import User
from .models import User, FriendRequest
from . import db

main = Blueprint('main', __name__)

user_messages = {}

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
    if user_exists:
        flash('El usuario o correo ya está registrado.')
        return redirect(url_for('main.index'))

    existing_pins = {u.pin for u in User.query.all() if u.pin}
    for i in range(1000):
        new_pin = f"{i:03}"
        if new_pin not in existing_pins:
            break

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password, pin=new_pin)

    db.session.add(new_user)
    db.session.commit()

    flash(f'Registro exitoso! Tu PIN es {new_pin}. Ya puedes iniciar sesión.')
    return redirect(url_for('main.index'))

@main.route('/login', methods=['POST'])
def login():
    username_or_email = request.form.get('username_or_email')
    password = request.form.get('password')

    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

    if not user or not check_password_hash(user.password, password):
        flash('Usuario o contraseña incorrectos.')
        return redirect(url_for('main.index'))

    login_user(user)
    flash('Has iniciado sesión correctamente.')
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)

@main.route('/solicitudes')
@login_required
def solicitudes():
    solicitudes_pendientes = FriendRequest.query.filter_by(to_user_id=current_user.id, status='pending').all()
    return render_template('solicitudes.html', solicitudes=solicitudes_pendientes)

@main.route('/chats', methods=['GET', 'POST'])
@login_required
def chats():
    destino_id = request.form.get('destino') or request.args.get('destino')

    if not destino_id:
        return render_template('chats.html', mensajes=[], destino=None)

    destino = User.query.get_or_404(destino_id)

    if request.method == 'POST' and 'mensaje' in request.form:
        mensaje = request.form['mensaje']
        new_message = Message(
            sender_id=current_user.id,
            receiver_id=destino.id,
            content=mensaje
        )
        db.session.add(new_message)
        db.session.commit()
        return redirect(url_for('main.chats', destino=destino.id))

    # Obtener mensajes entre los dos usuarios
    mensajes = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == destino.id)) |
        ((Message.sender_id == destino.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template('chats.html', mensajes=mensajes, destino=destino)


@main.route('/aceptar_solicitud/<int:request_id>')
@login_required
def aceptar_solicitud(request_id):
    solicitud = FriendRequest.query.get_or_404(request_id)
    if solicitud.to_user == current_user and solicitud.status == 'pending':
        solicitud.status = 'accepted'
        current_user.friends.append(solicitud.from_user)
        solicitud.from_user.friends.append(current_user)  # amistad mutua
        db.session.commit()
    return redirect(url_for('main.solicitudes'))

@main.route('/configure')
@login_required
def configure():
    return render_template('configure.html', current_user=current_user)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.')
    return redirect(url_for('main.index'))

@main.route('/send_friend_request', methods=['POST'])
@login_required
def send_friend_request():
    pin = request.form.get('friend_pin')
    user_to = User.query.filter_by(pin=pin).first()

    if not user_to:
        flash('No existe un usuario con ese PIN.')
        return redirect(url_for('main.chats'))

    if user_to.id == current_user.id:
        flash('No puedes enviarte solicitud a ti mismo.')
        return redirect(url_for('main.chats'))

    # Verificar si ya existe la solicitud
    existing = FriendRequest.query.filter_by(from_user_id=current_user.id, to_user_id=user_to.id).first()
    if existing:
        flash('Ya enviaste una solicitud a este usuario.')
        return redirect(url_for('main.chats'))

    new_request = FriendRequest(from_user_id=current_user.id, to_user_id=user_to.id)
    db.session.add(new_request)
    db.session.commit()

    flash(f'Solicitud enviada a {user_to.username} (PIN: {user_to.pin})')
    return redirect(url_for('main.chats'))

@main.route('/responder_solicitud/<int:solicitud_id>', methods=['POST'])
@login_required
def responder_solicitud(solicitud_id):
    solicitud = FriendRequest.query.get_or_404(solicitud_id)

    if solicitud.to_user_id != current_user.id:
        flash("No tienes permiso para responder a esta solicitud.")
        return redirect(url_for('main.solicitudes'))

    accion = request.form.get('accion')
    if accion == 'aceptar':
        solicitud.status = 'accepted'

        solicitud.from_user.friends.append(solicitud.to_user)
        solicitud.to_user.friends.append(solicitud.from_user)

        flash(f"Aceptaste la solicitud de {solicitud.from_user.username}.")
    elif accion == 'rechazar':
        solicitud.status = 'rejected'
        flash(f"Rechazaste la solicitud de {solicitud.from_user.username}.")
    else:
        flash("Acción inválida.")

    db.session.commit()
    return redirect(url_for('main.solicitudes'))

from flask import request, jsonify, current_app
from flask_login import current_user, login_required
import os
from werkzeug.utils import secure_filename

@main.route('/subir_foto', methods=['POST'])
@login_required
def subir_foto():
    if 'foto' not in request.files:
        return jsonify(success=False, message='No se encontró el archivo'), 400

    archivo = request.files['foto']
    if archivo.filename == '':
        return jsonify(success=False, message='Archivo sin nombre'), 400

    nombre_archivo = secure_filename(f"{current_user.id}_foto.png")
    ruta_foto = os.path.join(current_app.root_path, 'static', 'perfil', nombre_archivo)

    os.makedirs(os.path.dirname(ruta_foto), exist_ok=True)

    archivo.save(ruta_foto)

    current_user.profile_picture_url = f'perfil/{nombre_archivo}'
    db.session.commit()

    return jsonify(success=True, url=url_for('static', filename=current_user.profile_picture_url))
