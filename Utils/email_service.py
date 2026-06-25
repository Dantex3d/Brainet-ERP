import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf importbl7 settings


def send_email(to_email, subject, message):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender={
            "name": "Brainet",
            "email": settings.DEFAULT_FROM_EMAIL
        },
        to=[{"email": to_email}],
        subject=subject,
        html_content=message.replace("\n", "<br>")
    )

    try:
        api_instance.send_transac_email(email)
        return True
    except ApiException as e:
        print("Brevo error:", e)
        return False
