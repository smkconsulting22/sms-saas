import logging
import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Envoie un email HTML via SMTP. Retourne True en cas de succès."""
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASSWORD

    # SMTP_USER vide = SMTP non configuré (SMTP_HOST a un défaut non vide)
    if not user:
        print("[EMAIL] SMTP non configuré (SMTP_USER vide) — envoi ignoré")
        logger.warning("SMTP non configuré — email non envoyé à %s", to)
        return False

    print(f"[EMAIL] Config: host={host} port={port} user={user}")
    print(f"[EMAIL] Tentative envoi à {to} via {host}:{port}")
    logger.info("Tentative envoi email to=%s host=%s port=%d subject=%r", to, host, port, subject)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"WidoZan <{user}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        use_ssl = (port == 465 or settings.SMTP_SSL)
        print(f"[EMAIL] Mode: {'SSL' if use_ssl else ('STARTTLS' if settings.SMTP_TLS else 'plain')}")

        if use_ssl:
            print(f"[EMAIL] Connexion SMTP_SSL {host}:{port}")
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            print(f"[EMAIL] Connexion SMTP {host}:{port}")
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            if settings.SMTP_TLS:
                print("[EMAIL] Début STARTTLS")
                server.starttls()
                server.ehlo()

        print(f"[EMAIL] Login avec user={user}")
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())
        server.quit()

        print(f"[EMAIL] Succès envoi à {to}")
        logger.info("Email envoyé avec succès to=%s subject=%r", to, subject)
        return True

    except Exception as e:
        print(f"[EMAIL] ERREUR: {str(e)}")
        logger.error(
            "Exception lors de l'envoi email to=%s subject=%r :\n%s",
            to, subject, traceback.format_exc(),
        )
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


# ── Demandes de création de compte ───────────────────────────────────────────

def send_account_request_confirmation(to: str, full_name: str, company_name: str) -> None:
    """Email de confirmation envoyé au demandeur après soumission."""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0f9ff">
      <h2 style="color:#0369a1">📋 Demande de compte reçue</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Nous avons bien reçu votre demande de création de compte pour <strong>{company_name}</strong>.</p>
      <p>Notre équipe va examiner votre demande et vous contacter par email dans les plus brefs délais.</p>
      <div style="background:#e0f2fe;padding:16px;border-radius:6px;margin:24px 0">
        <p style="margin:0;color:#0369a1">
          ⏳ Délai de traitement habituel : <strong>24 à 48 heures ouvrées</strong>
        </p>
      </div>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, "Votre demande de compte SMS SaaS CI a été reçue", html)


def send_account_request_superadmin(
    to: str,
    full_name: str,
    company_name: str,
    email: str,
    phone: str,
    message: str | None,
    dashboard_url: str,
) -> None:
    """Email de notification envoyé au super admin pour chaque nouvelle demande."""
    message_block = (
        f'<tr style="background:#e0f2fe"><td style="padding:10px;border:1px solid #7dd3fc">Message</td>'
        f'<td style="padding:10px;border:1px solid #7dd3fc">{message}</td></tr>'
    ) if message else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0f9ff">
      <h2 style="color:#0369a1">🆕 Nouvelle demande de création de compte</h2>
      <table style="margin:24px 0;border-collapse:collapse;width:100%">
        <tr style="background:#e0f2fe">
          <td style="padding:10px;border:1px solid #7dd3fc">Nom</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-weight:bold">{full_name}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #7dd3fc">Entreprise</td>
          <td style="padding:10px;border:1px solid #7dd3fc;font-weight:bold">{company_name}</td>
        </tr>
        <tr style="background:#e0f2fe">
          <td style="padding:10px;border:1px solid #7dd3fc">Email</td>
          <td style="padding:10px;border:1px solid #7dd3fc">{email}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #7dd3fc">Téléphone</td>
          <td style="padding:10px;border:1px solid #7dd3fc">{phone}</td>
        </tr>
        {message_block}
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
    send_email(to, f"[SMS SaaS CI] Nouvelle demande de compte — {company_name}", html)


def send_account_approved_email(
    to: str,
    full_name: str,
    company_name: str,
    temp_password: str,
    login_url: str,
) -> None:
    """Email envoyé au client quand son compte est approuvé avec ses identifiants."""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#f0fdf4">
      <h2 style="color:#16a34a">✅ Votre compte a été approuvé !</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Bonne nouvelle ! Votre demande de compte pour <strong>{company_name}</strong>
         a été approuvée. Voici vos identifiants de connexion :</p>
      <div style="background:#dcfce7;border:1px solid #86efac;border-radius:8px;padding:20px;margin:24px 0">
        <table style="width:100%;border-collapse:collapse">
          <tr>
            <td style="padding:8px;color:#166534;font-weight:bold;width:40%">Email</td>
            <td style="padding:8px;font-family:monospace;font-size:15px">{to}</td>
          </tr>
          <tr>
            <td style="padding:8px;color:#166534;font-weight:bold">Mot de passe temporaire</td>
            <td style="padding:8px;font-family:monospace;font-size:15px;letter-spacing:2px">{temp_password}</td>
          </tr>
        </table>
      </div>
      <div style="background:#fef9c3;border-left:4px solid #ca8a04;padding:12px 16px;margin:16px 0;border-radius:4px">
        <strong>⚠️ Important :</strong> Changez votre mot de passe dès votre première connexion.
      </div>
      <p style="margin:32px 0">
        <a href="{login_url}"
           style="background:#16a34a;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none">
          Se connecter maintenant
        </a>
      </p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, "✅ Votre compte SMS SaaS CI est activé — Vos identifiants", html)


def send_account_rejected_email(to: str, full_name: str, reason: str) -> None:
    """Email envoyé au demandeur quand sa demande est refusée."""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;background:#fff1f2">
      <h2 style="color:#dc2626">❌ Demande de compte non retenue</h2>
      <p>Bonjour <strong>{full_name}</strong>,</p>
      <p>Nous avons examiné votre demande de création de compte et nous ne sommes
         malheureusement pas en mesure de la valider pour le moment.</p>
      <div style="background:#fee2e2;padding:16px;border-left:4px solid #dc2626;margin:24px 0;border-radius:4px">
        <strong>Motif :</strong><br>{reason}
      </div>
      <p>Si vous avez des questions ou souhaitez en savoir plus, n'hésitez pas à nous contacter.</p>
      <p style="color:#666;font-size:13px">L'équipe SMS SaaS CI</p>
    </div>
    """
    send_email(to, "Votre demande de compte SMS SaaS CI", html)
