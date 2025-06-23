import smtplib
from email.mime.text import MIMEText
from flask import url_for

def send_verification_email(destinatario, token):
    enlace_verificacion = url_for('main.verify_email', token=token, _external=True)
    cuerpo = f"""
    <h2>Verifica tu cuenta</h2>
    <p>Haz clic en el siguiente enlace para confirmar tu correo:</p>
    <a href="{enlace_verificacion}">Sí, soy yo</a><br><br>
    <p>Si no fuiste tú, ignora este mensaje.</p>
    """
    msg = MIMEText(cuerpo, 'html')
    msg['Subject'] = 'Confirma tu cuenta'
    msg['From'] = 'tucorreo@gmail.com'
    msg['To'] = destinatario

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as servidor:
            servidor.login('skolays92@gmail.com', 'rbbf ysbo alsu vbgq')
            servidor.send_message(msg)
    except Exception as e:
        print("Error al enviar el correo:", e)
        raise
