import logging
import emails as emails_pkg
from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Envoie un email HTML via SMTP. Retourne True en cas de succès."""
    if not settings.SMTP_USER or not settings.SMTP_HOST:
        logger.warning("SMTP non configuré — email non envoyé à %s", to)
        return False
    try:
        message = emails_pkg.html(
            html=html_body,
            subject=subject,
            mail_from=("SMS SaaS CI", settings.SMTP_USER),
        )
        smtp_params: dict = {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
            "timeout": 10,
        }
        if settings.SMTP_PORT == 465:
            smtp_params["ssl"] = True
        elif settings.SMTP_TLS:
            smtp_params["tls"] = True

        response = message.send(to=to, smtp=smtp_params)
        if response.status_code not in (250,):
            logger.error("Échec envoi email à %s : %s", to, response.status_text)
            return False
        logger.info("Email envoyé à %s : %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Erreur email à %s : %s", to, exc)
        return False


# ── Templates ────────────────────────────────────────────────────────────────

def send_welcome_email(to: str, full_name: str) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f9f9f9">
      <h2 style="color:#2563eb">Bienvenue sur SMS SaaS CI 🎉</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Votre compte a été créé avec succès. Vous pouvez dès maintenant accéder à votre tableau de bord
         et commencer à envoyer vos campagnes SMS.</p>
      <p style="margin:32px 0">
        <a href="{settings.FRONTEND_URL}/dashboard"
           style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Accéder au dashboard
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, "Bienvenue sur SMS SaaS CI", html)


def send_password_reset_email(to: str, full_name: str, reset_url: str) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f9f9f9">
      <h2 style="color:#2563eb">Réinitialisation de mot de passe</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Une demande de réinitialisation de mot de passe a été effectuée pour votre compte.
         Ce lien est valable <strong>1 heure</strong>.</p>
      <p style="margin:32px 0">
        <a href="{reset_url}"
           style="background:#dc2626;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Réinitialiser mon mot de passe
        </a>
      </p>
      <p style="color:#666;font-size:13px">
        Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, "Réinitialisation de votre mot de passe", html)


def send_low_balance_alert(to: str, tenant_name: str, balance: int) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#fff8f0">
      <h2 style="color:#d97706">⚠️ Solde de crédits bas</h2>
      <p>Bonjour,</p>
      <p>Le solde de crédits SMS de votre compte <strong>{tenant_name}</strong> est passé à
         <strong style="color:#dc2626">{balance} crédit(s)</strong>.</p>
      <p>Pour éviter toute interruption de service, rechargez votre solde dès maintenant.</p>
      <p style="margin:32px 0">
        <a href="{settings.FRONTEND_URL}/dashboard/credits"
           style="background:#d97706;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Recharger mes crédits
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, f"⚠️ Solde bas — {balance} crédit(s) restant(s)", html)


def send_credit_added_email(to: str, tenant_name: str, amount: int, new_balance: int) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0fdf4">
      <h2 style="color:#16a34a">✅ Rechargement de crédits confirmé</h2>
      <p>Bonjour,</p>
      <p>Votre compte <strong>{tenant_name}</strong> vient d'être rechargé.</p>
      <table style="margin:24px 0;border-collapse:collapse;width:100%">
        <tr style="background:#dcfce7">
          <td style="padding:12px;border:1px solid #86efac">Crédits ajoutés</td>
          <td style="padding:12px;border:1px solid #86efac;font-weight:bold;color:#16a34a">+{amount}</td>
        </tr>
        <tr>
          <td style="padding:12px;border:1px solid #86efac">Nouveau solde</td>
          <td style="padding:12px;border:1px solid #86efac;font-weight:bold">{new_balance}</td>
        </tr>
      </table>
      <p style="margin:32px 0">
        <a href="{settings.FRONTEND_URL}/dashboard"
           style="background:#16a34a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Voir mon tableau de bord
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, f"✅ {amount} crédit(s) ajouté(s) à votre compte", html)
