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


def send_recharge_notification_superadmin(
    to: str,
    tenant_name: str,
    amount_requested: int,
    amount_paid: str,
    payment_method: str,
    payment_reference: str,
    dashboard_url: str,
) -> None:
    method_label = "Orange Money" if payment_method == "orange_money" else "Wave"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0f9ff">
      <h2 style="color:#0369a1">🔔 Nouvelle demande de rechargement</h2>
      <p>Une nouvelle demande de rechargement a été soumise par <strong>{tenant_name}</strong>.</p>
      <table style="margin:24px 0;border-collapse:collapse;width:100%">
        <tr style="background:#e0f2fe">
          <td style="padding:10px;border:1px solid #7dd3fc">Client</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-weight:bold">{tenant_name}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #7dd3fc">Crédits demandés</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-weight:bold">{amount_requested}</td>
        </tr>
        <tr style="background:#e0f2fe">
          <td style="padding:10px;border:1px solid #7dd3fc">Montant payé</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-weight:bold">{amount_paid} FCFA</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #7dd3fc">Méthode</td>
          <td style="padding:10px;border:1px solid #7dd3fc">{method_label}</td>
        </tr>
        <tr style="background:#e0f2fe">
          <td style="padding:10px;border:1px solid #7dd3fc">Référence</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-family:monospace">{payment_reference}</td>
        </tr>
      </table>
      <p style="margin:32px 0">
        <a href="{dashboard_url}"
           style="background:#0369a1;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Traiter la demande
        </a>
      </p>
      <p style="color:#666;font-size:13px">SMS SaaS CI — Notification automatique</p>
    </div>
    """
    send_email(to, f"[SMS SaaS CI] Nouvelle demande de rechargement — {tenant_name}", html)


def send_recharge_approved_email(
    to: str, tenant_name: str, amount_requested: int, new_balance: int, note: str | None
) -> None:
    note_block = (
        f'<p style="background:#f0fdf4;padding:12px;border-left:4px solid #16a34a;margin:16px 0">'
        f'<strong>Note :</strong> {note}</p>'
    ) if note else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0fdf4">
      <h2 style="color:#16a34a">✅ Demande de rechargement approuvée</h2>
      <p>Bonjour,</p>
      <p>Votre demande de rechargement pour le compte <strong>{tenant_name}</strong> a été approuvée.</p>
      <table style="margin:24px 0;border-collapse:collapse;width:100%">
        <tr style="background:#dcfce7">
          <td style="padding:12px;border:1px solid #86efac">Crédits ajoutés</td>
          <td style="padding:12px;border:1px solid #86efac;font-weight:bold;color:#16a34a">+{amount_requested}</td>
        </tr>
        <tr>
          <td style="padding:12px;border:1px solid #86efac">Nouveau solde</td>
          <td style="padding:12px;border:1px solid #86efac;font-weight:bold">{new_balance} crédit(s)</td>
        </tr>
      </table>
      {note_block}
      <p style="margin:32px 0">
        <a href="{settings.FRONTEND_URL}/dashboard"
           style="background:#16a34a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Accéder à mon compte
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, f"✅ Rechargement approuvé — {amount_requested} crédit(s) ajouté(s)", html)


def send_recharge_rejected_email(
    to: str, tenant_name: str, amount_requested: int, reason: str
) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#fff1f2">
      <h2 style="color:#dc2626">❌ Demande de rechargement refusée</h2>
      <p>Bonjour,</p>
      <p>Votre demande de rechargement de <strong>{amount_requested} crédit(s)</strong>
         pour le compte <strong>{tenant_name}</strong> n'a pas pu être traitée.</p>
      <div style="background:#fee2e2;padding:16px;border-left:4px solid #dc2626;margin:24px 0;border-radius:4px">
        <strong>Motif du refus :</strong><br>{reason}
      </div>
      <p>Si vous pensez qu'il s'agit d'une erreur ou souhaitez soumettre une nouvelle demande,
         contactez notre support ou recommencez via votre espace client.</p>
      <p style="margin:32px 0">
        <a href="{settings.FRONTEND_URL}/dashboard/credits"
           style="background:#dc2626;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Soumettre une nouvelle demande
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, f"❌ Demande de rechargement refusée — {tenant_name}", html)


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
