from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse


def send_referral_email(referral):
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
    path = reverse("register")
    link = f"{site_url}{path}?ref={referral.token}"
    sponsor_name = referral.sponsor.username

    subject = f"{sponsor_name} vous invite sur Biketory"

    text_body = (
        f"Bonjour,\n\n"
        f"{sponsor_name} vous invite a rejoindre Biketory, "
        f"l'application pour visualiser vos traces GPS "
        f"et conquerir des hexagones.\n\n"
        f"Creez votre compte ici :\n{link}\n\n"
        f"A bientot sur Biketory !"
    )

    html_body = (
        f"<p>Bonjour,</p>"
        f"<p>{sponsor_name} vous invite a rejoindre Biketory, "
        f"l'application pour visualiser vos traces GPS "
        f"et conquerir des hexagones.</p>"
        f'<p><a href="{link}">Creez votre compte sur Biketory</a></p>'
        f"<p>A bientot sur Biketory !</p>"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[referral.email],
        reply_to=[referral.sponsor.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
